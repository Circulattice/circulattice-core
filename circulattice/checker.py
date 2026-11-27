# SPDX-License-Identifier: Apache-2.0
"""Check a proposed offset for every obligation in a validated problem."""

from collections import Counter

from .model import Problem


def check(problem: Problem, offsets: object) -> None:
    """Raise ValueError for an infeasible allocation. Feasibility is the only claim."""
    if type(offsets) is not dict or any(type(key) is not str for key in offsets):
        raise ValueError("offsets must be an object with string obligation IDs")
    if offsets.keys() != {edge.id for edge in problem.obligations}:
        raise ValueError("offsets must contain exactly the supplied obligation IDs")

    net_offset: Counter[tuple[str, str, str]] = Counter()
    cash_required: Counter[tuple[str, str, str]] = Counter()
    for edge in problem.obligations:
        quantity = offsets[edge.id]
        if type(quantity) is not int or not 0 <= quantity <= edge.amount:
            raise ValueError(f"{edge.id}: offset must be an integer within obligation bounds")
        if quantity and not edge.eligible:
            raise ValueError(f"{edge.id}: offset is prohibited")
        payer = (edge.agreement, edge.currency, edge.debtor)
        payee = (edge.agreement, edge.currency, edge.creditor)
        net_offset[payer] += quantity
        net_offset[payee] -= quantity
        cash_required[payer] += edge.amount - quantity

    for pool in problem.pools:
        for member in pool.members:
            account = (pool.agreement, pool.currency, member)
            if net_offset[account] != 0:
                raise ValueError(f"{account}: incoming and outgoing offsets differ")
            if cash_required[account] > pool.funding[member]:
                raise ValueError(f"{account}: gross residual debit exceeds funding")
