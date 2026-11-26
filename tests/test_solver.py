# SPDX-License-Identifier: Apache-2.0
import unittest
from pathlib import Path

from circulattice.checker import check
from circulattice.model import MAX_AMOUNT, load_json, parse_problem
from circulattice.solver import MAX_BUDGET, solve

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class SolverTests(unittest.TestCase):
    def test_arbitrary_precision_and_parallel_obligations(self):
        raw = load_json(EXAMPLES / "cycle.json")
        for row in raw["obligations"]:
            row["amount"] = MAX_AMOUNT
        raw["obligations"].append(dict(raw["obligations"][0], id="parallel", amount=1))
        raw["pools"][0]["funding"]["A"] = 1
        p = parse_problem(raw)
        result = solve(p)
        self.assertEqual(result["status"], "optimal")
        check(p, result["offsets"])
        self.assertEqual(sum(result["offsets"].values()), 3 * MAX_AMOUNT)

    def test_budget_boundary_and_repeatability(self):
        raw = load_json(EXAMPLES / "cycle.json")
        raw["obligations"][0]["amount"] += 1
        raw["pools"][0]["funding"]["A"] = 1
        p = parse_problem(raw)
        complete = solve(p)
        work = complete["work"]
        self.assertGreater(work, 0)
        self.assertEqual(solve(p, budget=work), complete)
        self.assertEqual(
            solve(p, budget=work - 1), {"status": "budget_exhausted", "work": work - 1}
        )
        for key in ("participants", "obligations", "pools"):
            raw[key].reverse()
        raw["pools"][0]["members"].reverse()
        self.assertEqual(solve(parse_problem(raw)), complete)

    def test_closed_zero_cash_cycle(self):
        p = parse_problem(load_json(EXAMPLES / "cycle.json"))
        result = solve(p, budget=0)
        self.assertEqual(result["offsets"], {e.id: e.amount for e in p.obligations})
        check(p, result["offsets"])

    def test_ineligible_cash_is_reserved(self):
        raw = load_json(EXAMPLES / "cycle.json")
        raw["obligations"][1]["eligible"] = False
        self.assertEqual(solve(parse_problem(raw)), {"status": "infeasible", "work": 0})

    def test_budget_type_and_range(self):
        p = parse_problem(load_json(EXAMPLES / "cycle.json"))
        for budget in [True, -1, 0.5, MAX_BUDGET + 1]:
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                solve(p, budget=budget)
