# SPDX-License-Identifier: Apache-2.0
"""Run two reference controls and the solver under identical settlement rules."""

import argparse
import json
from collections import defaultdict, deque
from itertools import product
from math import prod
from pathlib import Path
from time import perf_counter_ns

from circulattice.checker import check
from circulattice.model import load_json, parse_problem
from circulattice.solver import solve

MAX_BUDGET = 100_000


def _check_budget(budget):
    if type(budget) is not int or not 0 <= budget <= MAX_BUDGET:
        raise ValueError(f"comparison budget must be an integer from 0 to {MAX_BUDGET}")


def pool_edges(problem, pool):
    return sorted(
        (
            e
            for e in problem.obligations
            if (e.agreement, e.currency) == (pool.agreement, pool.currency)
        ),
        key=lambda e: e.id,
    )


class SearchLimit(Exception):
    """The conventional strategy used its allowance of edge examinations."""


def _shortest_cycle(first, outgoing, spend):
    """Return a shortest simple cycle containing first, or an empty list."""
    queue = deque([first.creditor])
    parent = {first.creditor: None}
    while queue and first.debtor not in parent:
        for edge in outgoing.get(queue.popleft(), ()):
            spend()
            if edge.creditor not in parent:
                parent[edge.creditor] = edge
                queue.append(edge.creditor)
    if first.debtor not in parent:
        return []
    cycle = [first]
    vertex = first.debtor
    while vertex != first.creditor:
        edge = parent[vertex]
        cycle.append(edge)
        vertex = edge.debtor
    return cycle


def _next_cycle(edges, offsets, cash, funding, spend):
    outgoing = defaultdict(list)
    active = []
    for edge in edges:
        spend()
        if edge.eligible and offsets[edge.id] < edge.amount:
            outgoing[edge.debtor].append(edge)
            active.append(edge)
    best = None
    best_key = None
    for first in active:
        cycle = _shortest_cycle(first, outgoing, spend)
        if not cycle:
            continue
        quantity = min(e.amount - offsets[e.id] for e in cycle)
        relief = sum(min(quantity, max(0, cash[e.debtor] - funding[e.debtor])) for e in cycle)
        key = (len(cycle), -relief, -quantity, tuple(sorted(e.id for e in cycle)))
        if best_key is None or key < best_key:
            best_key = key
            best = cycle, quantity
    return best


def conventional(problem, *, budget):
    """Clear shortest available cycles, preferring reciprocal offset pairs."""
    _check_budget(budget)
    offsets = {e.id: 0 for e in problem.obligations}
    work = 0

    def spend():
        nonlocal work
        if work == budget:
            raise SearchLimit
        work += 1

    try:
        for pool in problem.pools:
            edges = pool_edges(problem, pool)
            cash = {p: 0 for p in pool.members}
            for e in edges:
                cash[e.debtor] += e.amount
            while True:
                best = _next_cycle(edges, offsets, cash, pool.funding, spend)
                if best is None:
                    break
                cycle, quantity = best
                for e in cycle:
                    offsets[e.id] += quantity
                    cash[e.debtor] -= quantity
            if any(cash[p] > pool.funding[p] for p in pool.members):
                return {"status": "no_candidate", "work": work}
    except SearchLimit:
        return {"status": "budget_exhausted", "work": work}
    return {"status": "feasible", "offsets": offsets, "work": work}


def exhaustive(problem, *, budget):
    """Try every eligible integer allocation per pool on small cases."""
    _check_budget(budget)
    offsets = {e.id: 0 for e in problem.obligations}
    work = 0
    for pool in problem.pools:
        edges = pool_edges(problem, pool)
        eligible = [e for e in edges if e.eligible]
        combinations = prod(e.amount + 1 for e in eligible)
        if combinations > budget - work:
            return {"status": "outside_control_scope", "work": work}
        # itertools.product materializes its iterables. The cap above bounds them.
        best = None
        best_value = -1
        gross = {p: 0 for p in pool.members}
        for e in edges:
            gross[e.debtor] += e.amount
        for vector in product(*(range(e.amount + 1) for e in eligible)):
            work += 1
            value = sum(vector)
            if value <= best_value:
                continue
            sent = {p: 0 for p in pool.members}
            received = sent.copy()
            for e, amount in zip(eligible, vector, strict=True):
                sent[e.debtor] += amount
                received[e.creditor] += amount
            if sent == received and all(gross[p] - sent[p] <= pool.funding[p] for p in sent):
                best_value, best = value, vector
        if best is None:
            return {"status": "infeasible", "work": work}
        offsets.update((e.id, x) for e, x in zip(eligible, best, strict=True))
    return {"status": "optimal", "work": work, "offsets": offsets}


def evaluate(problem, result, *, timing=False):
    """Independently check a candidate before describing full settlement."""
    row = {"status": result["status"], "work": result["work"], "pools": None}
    if "offsets" not in result:
        return row
    offsets = result["offsets"]
    if timing:
        start = perf_counter_ns()
    check(problem, offsets)
    if timing:
        row["checker_ns"] = perf_counter_ns() - start
    pools = []
    for pool in problem.pools:
        edges = pool_edges(problem, pool)
        cash = {p: 0 for p in pool.members}
        for e in edges:
            cash[e.debtor] += e.amount - offsets[e.id]
        full = sum(offsets[e.id] == e.amount for e in edges)
        mixed = sum(0 < offsets[e.id] < e.amount for e in edges)
        pools.append(
            {
                "agreement": pool.agreement,
                "currency": pool.currency,
                "obligations_covered": len(edges),
                "fully_offset": full,
                "part_offset_part_cash": mixed,
                "cash_only": len(edges) - full - mixed,
                "gross_minor": sum(e.amount for e in edges),
                "offset_minor": sum(offsets[e.id] for e in edges),
                "prefunding_minor": sum(cash.values()),
                "prefunding_by_payer": cash,
            }
        )
    row["pools"] = pools
    return row


def compare(problem, *, budget=MAX_BUDGET, timing=False):
    _check_budget(budget)
    rows = {}
    for name, method in (
        ("reference", solve),
        ("conventional", conventional),
        ("exhaustive_control", exhaustive),
    ):
        start = perf_counter_ns()
        result = method(problem, budget=budget)
        method_ns = perf_counter_ns() - start if timing else None
        row = evaluate(problem, result, timing=timing)
        if timing:
            row["method_ns"] = method_ns
            row.setdefault("checker_ns", None)
            row["elapsed_ns"] = perf_counter_ns() - start
        rows[name] = row
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "files", type=Path, nargs="*", help="problem files (default: fixed examples)"
    )
    parser.add_argument(
        "--timing", action="store_true", help="include measured end-to-end nanoseconds"
    )
    parser.add_argument("--budget", type=int, default=MAX_BUDGET, help="work limit per method")
    args = parser.parse_args()
    examples = Path(__file__).resolve().parents[1] / "examples"
    files = args.files or sorted(examples.glob("*.json"))
    for path in files:
        try:
            rows = compare(parse_problem(load_json(path)), budget=args.budget, timing=args.timing)
        except (OSError, ValueError) as exc:
            parser.exit(2, f"{path}: {exc}\n")
        print(
            json.dumps(
                {"case": path.name, "budget": args.budget, "methods": rows},
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
