# SPDX-License-Identifier: Apache-2.0
"""Integral minimum-cost residual payment flow, solved separately in each pool."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from .model import Obligation, Pool, Problem

DEFAULT_BUDGET = 1_000_000
MAX_BUDGET = 10_000_000


class Result(TypedDict, total=False):
    status: Literal["optimal", "infeasible", "budget_exhausted"]
    work: int
    offsets: dict[str, int]


@dataclass
class _Arc:
    tail: int
    head: int
    capacity: int
    cost: int


class _BudgetStop(Exception):
    pass


@dataclass
class _Meter:
    limit: int
    used: int = 0

    def scan(self) -> None:
        if self.used == self.limit:
            raise _BudgetStop
        self.used += 1


def _add(arcs: list[_Arc], tail: int, head: int, capacity: int, cost: int) -> int:
    index = len(arcs)
    arcs.append(_Arc(tail, head, capacity, cost))
    arcs.append(_Arc(head, tail, 0, -cost))
    return index


def _path(arcs: list[_Arc], nodes: int, meter: _Meter) -> list[int]:
    """Bellman-Ford handles the negative cost of reversing previous payments."""
    distance: list[int | None] = [None] * nodes
    parent = [-1] * nodes
    distance[0] = 0
    for _ in range(nodes - 1):
        changed = False
        for i, arc in enumerate(arcs):
            meter.scan()
            before, after = distance[arc.tail], distance[arc.head]
            if arc.capacity and before is not None:
                candidate = before + arc.cost
                if after is None or candidate < after:
                    parent[arc.head] = i
                    distance[arc.head] = candidate
                    changed = True
        if not changed:
            break
    sink = nodes - 1
    if distance[sink] is None:
        return []
    path = []
    while sink != 0:
        i = parent[sink]
        path.append(i)
        sink = arcs[i].tail
    return path


def _pool_offsets(pool: Pool, rows: list[Obligation], meter: _Meter) -> dict[str, int] | None:
    # Each member has an account node and an outgoing spending gate.
    account = {member: 1 + i * 2 for i, member in enumerate(pool.members)}
    sink = len(account) * 2 + 1
    net_debit = dict.fromkeys(pool.members, 0)
    remaining = dict(pool.funding)
    arcs: list[_Arc] = []
    row_arcs = {}
    for row in rows:
        if row.eligible:
            net_debit[row.debtor] += row.amount
            net_debit[row.creditor] -= row.amount
            row_arcs[row.id] = _add(
                arcs, account[row.debtor] + 1, account[row.creditor], row.amount, 1
            )
        else:
            remaining[row.debtor] -= row.amount

    if min(remaining.values()) < 0:
        return None
    required = 0
    for member, node in account.items():
        _add(arcs, node, node + 1, remaining[member], 0)
        debit = net_debit[member]
        if debit > 0:
            _add(arcs, 0, node, debit, 0)
            required += debit
        elif debit < 0:
            _add(arcs, node, sink, -debit, 0)

    while required:
        path = _path(arcs, sink + 1, meter)
        if not path:
            return None
        quantity = min(arcs[i].capacity for i in path)
        for i in path:
            arcs[i].capacity -= quantity
            arcs[i ^ 1].capacity += quantity
        required -= quantity

    # Remaining forward edge capacity is the part of the obligation offset.
    return {row.id: arcs[row_arcs[row.id]].capacity if row.eligible else 0 for row in rows}


def solve(problem: Problem, *, budget: int = DEFAULT_BUDGET) -> Result:
    """Return a complete optimum, a proven infeasibility, or a bounded-search stop."""
    if type(budget) is not int or not 0 <= budget <= MAX_BUDGET:
        raise ValueError(f"budget must be an integer from 0 to {MAX_BUDGET}")
    groups: dict[tuple[str, str], list[Obligation]] = {}
    for row in problem.obligations:
        groups.setdefault((row.agreement, row.currency), []).append(row)
    meter = _Meter(budget)
    offsets = {}
    try:
        for pool in problem.pools:
            part = _pool_offsets(pool, groups.get((pool.agreement, pool.currency), []), meter)
            if part is None:
                return {"status": "infeasible", "work": meter.used}
            offsets.update(part)
    except _BudgetStop:
        return {"status": "budget_exhausted", "work": meter.used}
    return {"status": "optimal", "offsets": offsets, "work": meter.used}
