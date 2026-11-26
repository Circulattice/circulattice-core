<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Development

Run the reference package from a source checkout on CPython 3.11 or later. Its runtime imports only the standard library. The comparison runner is shipped in the source distribution. The wheel contains the reference package and CLI.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m ruff format --check .
python -m ruff check .
python -m mypy
python -m unittest discover -s tests -v
python -m benchmarks.compare
python -m build --no-isolation
```

In PowerShell, use `.\.venv\Scripts\Activate.ps1` for activation. The build writes a source archive and a wheel to `dist/`. To test the installed command, use a fresh environment and run it outside the checkout.

```sh
# POSIX shell, from the checkout with a freshly built dist/ directory.
checkout="$(pwd)"
scratch="$(mktemp -d)"
python -m venv "$scratch/install"
"$scratch/install/bin/python" -m pip install --no-deps "$checkout"/dist/*.whl
cd "$scratch"
"$scratch/install/bin/circulattice" solve "$checkout/examples/cycle.json" > plan.json
"$scratch/install/bin/circulattice" check "$checkout/examples/cycle.json" plan.json
```

## Library entry points

```python
from circulattice.checker import check
from circulattice.model import load_json, parse_problem
from circulattice.solver import solve

problem = parse_problem(load_json("examples/cycle.json"))
result = solve(problem, budget=100_000)
if result["status"] == "optimal":
    check(problem, result["offsets"])  # returns None or raises ValueError
```

Use the input factory before calling either algorithm. The dataclasses represent already validated inputs. The CLI rejects unknown model fields and duplicate JSON keys. The `check` command runs in its own process without importing the solver. Examples exercise funding, eligibility and partition failures. Separate tests compare tiny optimal allocations with a direct enumeration of integer offsets. [Model](model.md) · [Comparator](comparison.md)

## Threat model and limitations

Treat both the obligation book and the proposed allocation as untrusted input. The parser checks IDs, amounts, memberships and input limits. The checker recalculates the offsets and funding required for every payer. A valid book can still omit an obligation or misstate a funding limit. Anyone relying on a result must establish the source of the book and the authority to offset its obligations.

Use ordinary local files. Opening a special file or a network mount can block. The search budget counts arc inspections and leaves file I/O, elapsed time and memory outside its limit.

The CLI computes a single batch. Payment execution, intraday cash reuse, FX conversion and legal finality are outside the model. Use synthetic inputs when sharing a reproducer. [Security reporting](../SECURITY.md)
