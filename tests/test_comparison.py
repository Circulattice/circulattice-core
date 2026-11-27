# SPDX-License-Identifier: Apache-2.0
import unittest
from pathlib import Path
from random import Random

from benchmarks.compare import compare, conventional, evaluate, exhaustive
from circulattice.model import load_json, parse_problem
from circulattice.solver import solve

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def fixture(name):
    return parse_problem(load_json(EXAMPLES / (name + ".json")))


class ComparisonTests(unittest.TestCase):
    def test_conventional_can_fund_all_obligations_with_less_offset(self):
        rows = compare(fixture("competing"))
        for name, expected in (
            ("conventional", 4),
            ("reference", 6),
            ("exhaustive_control", 6),
        ):
            (pool,) = rows[name]["pools"]
            self.assertEqual(pool["obligations_covered"], 4)
            self.assertEqual(pool["offset_minor"], expected)
            self.assertEqual(pool["prefunding_minor"], 8 - expected)

    def test_conventional_failure_is_unknown(self):
        rows = compare(fixture("tight-branch"))
        self.assertEqual(rows["conventional"]["status"], "no_candidate")
        self.assertIsNone(rows["conventional"]["pools"])
        self.assertEqual(rows["exhaustive_control"]["status"], "optimal")
        self.assertEqual(
            rows["reference"]["pools"][0]["prefunding_by_payer"],
            {"A": 0, "B": 2, "C": 0},
        )

    def test_currency_isolation_can_make_full_settlement_impossible(self):
        rows = compare(fixture("currency-gap"))
        self.assertEqual(rows["exhaustive_control"]["status"], "infeasible")
        self.assertEqual(rows["reference"]["status"], "infeasible")
        for row in rows.values():
            self.assertIsNone(row["pools"])

    def test_a_later_payer_can_require_rerouting_the_first_payment(self):
        # A paying C first blocks B's only payment. Rerouting A to D lets
        # B pay C, while AC and CA offset under C's zero funding cap.
        raw = load_json(EXAMPLES / "cycle.json")
        raw["participants"] = raw["pools"][0]["members"] = list("ABCD")
        raw["pools"][0]["funding"] = {"A": 1, "B": 1, "C": 0, "D": 0}
        raw["obligations"] = [
            dict(raw["obligations"][0], id=a + b, debtor=a, creditor=b, amount=1)
            for a, b in ("AC", "AD", "BC", "CA")
        ]
        problem = parse_problem(raw)
        expected = {"AC": 1, "AD": 0, "BC": 0, "CA": 1}
        for result in (solve(problem), exhaustive(problem, budget=16)):
            self.assertEqual(result["status"], "optimal")
            self.assertEqual(result["offsets"], expected)

    def test_restricted_agreements_keep_separate_residual_funding(self):
        rows = compare(fixture("agreement-rights"))
        for row in rows.values():
            pools = {p["agreement"]: p for p in row["pools"]}
            self.assertEqual(pools["G"]["prefunding_by_payer"], {"A": 3, "B": 1, "C": 0})
            self.assertEqual(pools["H"]["prefunding_by_payer"], {"A": 0, "C": 2})
            self.assertEqual(pools["G"]["part_offset_part_cash"], 1)

    def test_budget_omits_partial_plans(self):
        p = fixture("competing")
        self.assertEqual(conventional(p, budget=1), {"status": "budget_exhausted", "work": 1})
        self.assertEqual(exhaustive(p, budget=1), {"status": "outside_control_scope", "work": 0})

    def test_comparison_entry_points_reject_invalid_limits(self):
        p = fixture("cycle")
        for method in (conventional, exhaustive, compare):
            for budget in (True, -1, 1.5, 100_001, 10**100):
                with self.subTest(method=method.__name__, budget=budget):
                    with self.assertRaises(ValueError):
                        method(p, budget=budget)

    def test_large_amount_excluded_before_enumeration(self):
        raw = load_json(EXAMPLES / "cycle.json")
        raw["obligations"][0]["amount"] = 10**15
        self.assertEqual(
            exhaustive(parse_problem(raw), budget=100_000),
            {"status": "outside_control_scope", "work": 0},
        )

    def test_deterministic_numbers_are_separate_from_timings(self):
        p = fixture("cash-chain")
        rows = compare(p)
        self.assertEqual(rows, compare(p))
        for method, row in compare(p, timing=True).items():
            self.assertGreaterEqual(
                row.pop("elapsed_ns"), row.pop("method_ns") + row.pop("checker_ns")
            )
            self.assertEqual(row, rows[method])
        for row in compare(fixture("currency-gap"), timing=True).values():
            self.assertIsNone(row["checker_ns"])

    def test_invalid_candidate_cannot_generate_metrics(self):
        with self.assertRaises(ValueError):
            evaluate(fixture("cycle"), {"status": "feasible", "work": 0, "offsets": {}})

    def test_reference_matches_integer_enumeration_on_small_random_graphs(self):
        rng = Random(1701)
        for case in range(64):
            raw = load_json(EXAMPLES / "cycle.json")
            members = raw["participants"]
            raw["pools"][0]["funding"] = {p: rng.randrange(5) for p in members}
            edges = []
            for i in range(5):
                debtor, creditor = rng.sample(members, 2)
                edges.append(
                    dict(
                        raw["obligations"][0],
                        id="e" + str(i),
                        debtor=debtor,
                        creditor=creditor,
                        amount=rng.randint(1, 3),
                        eligible=rng.choice([True, True, False]),
                    )
                )
            raw["obligations"] = edges
            rows = compare(parse_problem(raw))
            with self.subTest(case=case):
                control, ref = rows["exhaustive_control"], rows["reference"]
                self.assertEqual(ref["status"], control["status"])
                if ref["status"] == "optimal":
                    self.assertEqual(
                        ref["pools"][0]["offset_minor"],
                        control["pools"][0]["offset_minor"],
                    )
                self.assertNotEqual(control["status"], "outside_control_scope")
