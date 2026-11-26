# SPDX-License-Identifier: Apache-2.0
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class CliTests(unittest.TestCase):
    def invoke(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "circulattice", *map(str, args)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_solution_round_trip_and_tamper(self):
        source = EXAMPLES / "cycle.json"
        result = self.invoke("solve", source)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "plan.json"
            candidate.write_text(result.stdout, encoding="utf-8")
            checked = self.invoke("check", source, candidate)
            self.assertEqual(json.loads(checked.stdout), {"feasible": True})
            bad = json.loads(result.stdout)
            bad["offsets"]["ab"] = 1
            candidate.write_text(json.dumps(bad), encoding="utf-8")
            self.assertEqual(self.invoke("check", source, candidate).returncode, 2)

    def test_no_partial_candidate_on_stopped_or_infeasible_run(self):
        for name, args, code, status in [
            ("currency-gap", (), 3, "infeasible"),
            ("cash-chain", ("--budget", "0"), 4, "budget_exhausted"),
        ]:
            result = self.invoke("solve", EXAMPLES / (name + ".json"), *args)
            self.assertEqual(result.returncode, code)
            self.assertEqual(json.loads(result.stdout)["status"], status)
            self.assertNotIn("offsets", json.loads(result.stdout))

    def test_checker_distinguishes_no_witness_from_invalid_allocation(self):
        source = EXAMPLES / "cycle.json"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "result.json"
            self.assertEqual(self.invoke("check", source, path).returncode, 4)
            for status in ("budget_exhausted", "infeasible"):
                path.write_text(json.dumps({"status": status}), encoding="utf-8")
                checked = self.invoke("check", source, path)
                self.assertEqual(checked.returncode, 4)
                self.assertEqual(json.loads(checked.stdout)["verification"], "incomplete")
                path.write_text(json.dumps({"status": status, "offsets": {}}), encoding="utf-8")
                self.assertEqual(self.invoke("check", source, path).returncode, 2)
