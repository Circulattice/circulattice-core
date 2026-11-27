<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Circulattice

[![License](https://img.shields.io/github/license/Circulattice/circulattice-core)](LICENSE)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/Circulattice/circulattice-core/badge)](https://scorecard.dev/viewer/?uri=github.com/Circulattice/circulattice-core)

Circulattice finds payment obligations that can offset one another within an agreement and currency. It returns the amount to offset on each obligation and checks that each payer has enough opening cash to pay the rest. It is an LF Decentralized Trust Lab based on research by AksumLabs OÜ.

## Try a three-party cycle

A owes B three cents, B owes C three cents, and C owes A three cents. All three debts are eligible for offset under the same agreement. Clearing the circle cancels all nine cents of obligations. Each participant gives up a three-cent claim and clears a three-cent debt, so nobody needs opening cash.

Run the example from the repository root with Python 3.11 or later. Both commands use only the standard library.

```sh
python -m circulattice solve examples/cycle.json > plan.json
python -m circulattice check examples/cycle.json plan.json
```

The checker reads the original obligations and the proposed offsets independently. For this plan it prints `{"feasible": true}`.

## Compare two ways to clear a batch

```sh
python -m benchmarks.compare examples/competing.json
```

In this example, A owes B, B owes A, B owes C, and C owes A. Each debt is two cents. Clearing the reciprocal A–B pair first leaves four cents to pay. Clearing A → B → C → A leaves just one payment of two cents from B to A. [Example input](examples/competing.json) · [Benchmark methods and results](docs/comparison.md)

## The settlement model

The solver maximizes the amount offset within each agreement and currency. Each payer must cover its remaining outgoing payments with opening cash. Incoming payments become available only after the batch. The solver reports whether it found an optimum, proved the batch infeasible, or reached its search limit. The checker verifies a proposed allocation’s feasibility. [Equations, input format and exit codes](docs/model.md)

## Development

Run the tests with `python -m unittest discover -s tests -v`. The developer guide covers the Python API, building a wheel and testing an installation. [Developer guide](docs/development.md) · [Contributing](CONTRIBUTING.md) · [Governance](GOVERNANCE.md) · [Maintainers](MAINTAINERS.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [Security reporting](SECURITY.md)

For published versions, see [Releases](https://github.com/Circulattice/circulattice-core/releases). To document practical use, propose an `ADOPTERS.md` entry with a public reference.

## License

Code and synthetic test inputs are licensed under Apache-2.0. Documentation is licensed under CC BY 4.0. [Code license](LICENSE) · [Documentation license](LICENSES/CC-BY-4.0.txt)
