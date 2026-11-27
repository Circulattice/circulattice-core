# SPDX-License-Identifier: Apache-2.0
import unittest

from circulattice.checker import check
from circulattice.model import parse_problem


def reciprocal_book():
    members = ["A", "B"]
    pool = {
        "agreement": "G",
        "currency": "USD",
        "members": members,
        "funding": {"A": 4, "B": 4},
    }
    ab = {
        "id": "ab",
        "agreement": "G",
        "currency": "USD",
        "debtor": "A",
        "creditor": "B",
        "amount": 4,
        "eligible": True,
    }
    ba = dict(ab, id="ba", debtor="B", creditor="A")
    return {"version": 1, "participants": members, "pools": [pool], "obligations": [ab, ba]}


class CheckerTests(unittest.TestCase):
    def test_accepts_each_feasible_quantity_including_suboptimal_offsets(self):
        problem = parse_problem(reciprocal_book())
        for quantity in range(5):
            with self.subTest(quantity=quantity):
                self.assertIsNone(check(problem, {"ba": quantity, "ab": quantity}))

    def test_requires_all_and_only_original_ids(self):
        problem = parse_problem(reciprocal_book())
        for offsets in (
            {},
            {"ab": 0},
            {"ab": 0, "x": 0},
            {"ab": 0, "ba": 0, "x": 0},
            ["ab", "ba"],
            {1: 0, "ba": 0},
        ):
            with self.subTest(offsets=offsets), self.assertRaises(ValueError):
                check(problem, offsets)

    def test_offset_bounds_and_exact_integer_type(self):
        problem = parse_problem(reciprocal_book())
        for quantity in (True, False, "1", 1.0, None, -1, 5):
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                check(problem, {"ab": quantity, "ba": quantity})

    def test_balanced_books_require_per_participant_conservation(self):
        with self.assertRaisesRegex(ValueError, "incoming and outgoing"):
            check(parse_problem(reciprocal_book()), {"ab": 1, "ba": 2})

    def test_one_minor_unit_mismatch_above_binary64_exact_range(self):
        book = reciprocal_book()
        amount = 10**15
        ab, ba = book["obligations"]
        book["obligations"] = [
            dict(edge, id=f"{edge['id']}{i}", amount=amount) for edge in (ab, ba) for i in range(10)
        ]
        problem = parse_problem(book)
        offsets = {edge.id: amount for edge in problem.obligations}
        self.assertIsNone(check(problem, offsets))
        offsets["ab9"] -= 1
        with self.assertRaisesRegex(ValueError, "incoming and outgoing"):
            check(problem, offsets)

    def test_conservation_cannot_cross_agreements_or_currencies(self):
        for field, value in (("agreement", "H"), ("currency", "EUR")):
            with self.subTest(field=field):
                book = reciprocal_book()
                second = dict(book["pools"][0])
                second[field] = value
                book["pools"].append(second)
                book["obligations"][1][field] = value
                with self.assertRaisesRegex(ValueError, "incoming and outgoing"):
                    check(parse_problem(book), {"ab": 4, "ba": 4})

    def test_ineligible_obligation_cannot_be_offset_even_in_a_cycle(self):
        book = reciprocal_book()
        book["obligations"][1]["eligible"] = False
        problem = parse_problem(book)
        self.assertIsNone(check(problem, {"ab": 0, "ba": 0}))
        with self.assertRaisesRegex(ValueError, "prohibited"):
            check(problem, {"ab": 1, "ba": 1})

    def test_gross_prefunding_ignores_receipts_and_other_wallets(self):
        book = reciprocal_book()
        book["pools"][0]["funding"] = {"A": 2, "B": 6}
        problem = parse_problem(book)
        self.assertIsNone(check(problem, {"ab": 2, "ba": 2}))
        with self.assertRaisesRegex(ValueError, "exceeds funding"):
            check(problem, {"ab": 1, "ba": 1})

    def test_funding_cannot_be_borrowed_from_another_pool(self):
        for field, value in (("agreement", "H"), ("currency", "EUR")):
            with self.subTest(field=field):
                book = reciprocal_book()
                book["pools"][0]["funding"]["A"] = 0
                second = dict(book["pools"][0], funding={"A": 4, "B": 4})
                second[field] = value
                book["pools"].append(second)
                book["obligations"][1][field] = value
                with self.assertRaisesRegex(ValueError, "exceeds funding"):
                    check(parse_problem(book), {"ab": 0, "ba": 0})
