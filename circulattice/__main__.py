# SPDX-License-Identifier: Apache-2.0
"""File-oriented CLI. The check command never imports the solver."""

import argparse
import json
import sys
from pathlib import Path

from .model import load_json, parse_problem


def main() -> int:
    parser = argparse.ArgumentParser(prog="circulattice")
    commands = parser.add_subparsers(dest="command", required=True)
    solve_parser = commands.add_parser("solve", help="compute an offset plan")
    solve_parser.add_argument("problem", type=Path)
    solve_parser.add_argument("--budget", type=int, help="maximum arc inspections")
    check_parser = commands.add_parser("check", help="verify offsets against the original problem")
    check_parser.add_argument("problem", type=Path)
    check_parser.add_argument("candidate", type=Path, help="solve output containing offsets")
    args = parser.parse_args()
    try:
        problem = parse_problem(load_json(args.problem))
        if args.command == "solve":
            from .solver import DEFAULT_BUDGET, solve

            result = solve(problem, budget=DEFAULT_BUDGET if args.budget is None else args.budget)
            print(json.dumps(result, sort_keys=True))
            return {"optimal": 0, "infeasible": 3, "budget_exhausted": 4}[result["status"]]

        from .checker import check

        candidate = load_json(args.candidate)
        if isinstance(candidate, dict) and candidate.get("status") in (
            "infeasible",
            "budget_exhausted",
        ):
            if "offsets" in candidate:
                raise ValueError("a result without a solution cannot also contain offsets")
            print(json.dumps({"verification": "incomplete", "reason": "no_candidate"}))
            return 4
        if not isinstance(candidate, dict) or "offsets" not in candidate:
            raise ValueError("a candidate must contain an offsets object")
        check(problem, candidate["offsets"])
        print(json.dumps({"feasible": True}))
        return 0
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 4 if args.command == "check" else 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
