# SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from circulattice.model import MAX_AMOUNT, MAX_BYTES, load_json, parse_problem


def small():
    return {
        "version": 1,
        "participants": ["B", "A"],
        "pools": [
            {
                "agreement": "G",
                "currency": "USD",
                "members": ["A", "B"],
                "funding": {"A": 10, "B": 0},
            }
        ],
        "obligations": [
            {
                "id": "one",
                "agreement": "G",
                "currency": "USD",
                "debtor": "A",
                "creditor": "B",
                "eligible": True,
                "amount": 1,
            }
        ],
    }


class ModelTests(unittest.TestCase):
    def test_input_is_canonical_and_detached(self):
        raw = small()
        p = parse_problem(raw)
        raw["pools"][0]["funding"]["A"] = 0
        self.assertEqual(p.participants, ("A", "B"))
        self.assertEqual(p.pools[0].funding["A"], 10)
        with self.assertRaises(TypeError):
            p.pools[0].funding["A"] = 0

    def test_rejects_duplicate_ids_pools_or_members(self):
        for key in ["participants", "pools", "obligations"]:
            raw = small()
            raw[key].append(deepcopy(raw[key][0]))
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_problem(raw)
        raw = small()
        raw["pools"][0]["members"].append("A")
        with self.assertRaises(ValueError):
            parse_problem(raw)

    def test_requires_membership_and_explicit_cap(self):
        for tag, edit in [
            ("nonmember", lambda raw: raw["obligations"][0].update(creditor="C")),
            ("membership", lambda raw: raw["pools"][0].update(members=["A", "Z"])),
            ("missing cap", lambda raw: raw["pools"][0].update(funding={"A": 3})),
            ("extra cap", lambda raw: raw["pools"][0]["funding"].update(Z=1)),
            ("unknown pool", lambda raw: raw["obligations"][0].update(currency="EUR")),
            ("extra field", lambda raw: raw.update(scale=2)),
            ("self", lambda raw: raw["obligations"][0].update(creditor="A")),
            ("currency", lambda raw: raw["pools"][0].update(currency="usd")),
            ("permission", lambda raw: raw["obligations"][0].update(eligible=1)),
            ("flag version", lambda raw: raw.update(version=True)),
        ]:
            raw = small()
            edit(raw)
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                parse_problem(raw)

    def test_money_is_bounded_integer(self):
        for value in [-1, 0, 1.5, True, "1", MAX_AMOUNT + 1]:
            raw = small()
            raw["obligations"][0]["amount"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_problem(raw)
        for cap in [-1, False, 1.0, MAX_AMOUNT + 1]:
            raw = small()
            raw["pools"][0]["funding"]["A"] = cap
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                parse_problem(raw)

    def test_json_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.json"
            for text in [
                '{"outer":{"k":0,"k":1}}',
                "1e2",
                "NaN",
                "1.0",
                "[" * 1500 + "]" * 1500,
                " " * (MAX_BYTES + 1),
            ]:
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_json(path)
            path.write_text(json.dumps(small()), encoding="utf-8")
            self.assertEqual(parse_problem(load_json(path)), parse_problem(small()))

    def test_empty_book_and_dimensions(self):
        raw = small()
        raw.update(pools=[], obligations=[])
        self.assertEqual(parse_problem(raw).obligations, ())
        for key, size in [("participants", 65), ("pools", 33), ("obligations", 257)]:
            raw = small()
            raw[key] = [raw[key][0]] * size
            with self.subTest(key=key), self.assertRaises(ValueError):
                parse_problem(raw)
