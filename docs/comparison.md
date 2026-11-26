<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Comparing complete, prefunded settlement

The comparison asks how much gross value can be offset while every remaining debit is fully backed by its payer's opening funding. All three methods receive the same obligations, authorizations, account memberships and funding caps. The independent checker must accept every reported allocation before the runner computes settlement metrics.

From a source checkout, run the fixed examples in filename order. The final command adds one timing observation per method.

```sh
python -m benchmarks.compare
python -m benchmarks.compare examples/competing.json
python -m benchmarks.compare --budget 1 examples/competing.json
python -m benchmarks.compare --timing
```

Output is one JSON object per input. Financial results and work counts are deterministic. Each pool reports its agreement and currency, original gross amount, offset amount and prefunding by payer in native minor units. A complete plan covers each original by full offset, a combination of offset and prefunding, or full prefunding. Required cash equals gross minus offset in that pool. The funding convention assumes simultaneous settlement with no reuse of incoming cash. These static quantities measure neither intraday peaks on a live rail nor legal discharge.

## Methods

| Method | Selection and stopping rule | Meaning of success |
| --- | --- | --- |
| Reference | Calls the shipped solver with the common numeric work allowance. | An optimal result claims maximum total offset separately in every pool. |
| Conventional | Clears reciprocal pairs first, then progressively longer cycles. For each live edge, breadth-first search finds a shortest path back to its debtor, breaking path ties in edge-ID order. Among these candidates the method prefers shortest length, greatest funding-deficit relief, greatest cancellable amount, then ID order. Each augmentation exhausts at least one edge. | Every residual can be fully funded. A missing candidate leaves feasibility unknown. |
| Exhaustive control | Tries all integer offset assignments permitted by the eligible edges of each pool. Tests circulation, caps and objective independently. A preflight stops before enumerating a pool whose assignment count would exceed the remaining allowance. | A best feasible assignment or a proof that a pool has none, within the enumerated domain. |

The default and maximum allowance is 100,000 per method per case. The `--budget` option accepts any integer from zero through this limit. Work counts use different units. For the conventional method one unit is one edge examination during construction of the live graph or a BFS traversal. For the control it is one integer assignment tried. For the reference solver one unit is one residual arc examined in a shortest-path relaxation pass. Equal counters imply neither equal runtime nor equivalent search coverage. An exhausted method supplies no financial outcome. When the control is outside scope, its unexamined assignments imply no finding about optimality.

The conventional method considers only reductions on original eligible directed edges. Each augmentation exhausts at least one of the E original edges, so a pool can require at most E augmentations. For E edges and V members in a pool, finding candidate paths costs O(E(V+E)) edge/vertex work per round; tie-breaking additionally sorts at most V IDs per candidate. The exhaustive control requires work proportional to the product of (eligible amount + 1), times the cost of inspecting a candidate. It is suited to tiny integer cases.

## Fixed cases

| Input | Question | Expected observation |
| --- | --- | --- |
| `cycle.json` | Can a three-way cycle clear with zero opening cash? | All nine units offset under all three methods. |
| `cash-chain.json` | What happens on an acyclic chain with sufficient cash? | All five units require prefunding. |
| `agreement-rights.json` | Can two agreements share a balance, or a cash-only instruction be offset? | Four units offset in G. Funding remains four units in G and two in H. |
| `competing.json` | What does the shortest-cycle preference cost under ample funding? | Both plans cover all four originals. The conventional method offsets four of eight units. The optimum offsets six. |
| `tight-branch.json` | What if one residual payer has zero funding? | The conventional method yields no complete plan. A three-way offset leaves two funded units. |
| `currency-gap.json` | Can reciprocal amounts in different currencies offset each other? | Full funding is impossible. Both exact methods detect this. |

The six synthetic books isolate the effect of cycle choice, eligibility and funding. The exhaustive control agrees with the reference solver on all six. The competing-cycle result depends on the conventional method’s shortest-cycle ordering. Use a representative workload to study how often that choice matters in practice.

Earlier AksumLabs experiments found no consistent advantage over a strengthened conventional baseline, and some workloads exceeded their performance budget. Those experiments used a different settlement model. [Research context in the approved proposal](https://github.com/LF-Decentralized-Trust/lab-proposals/blob/main/proposals/circulattice.md)

## Computation and interpretation

With `--timing`, `method_ns` measures the method call and `checker_ns` measures independent verification. A null checker time means the method returned no allocation. Total elapsed nanoseconds include the method call, independent feasibility check of any candidate and accounting. They exclude JSON input/output, input parsing and interpreter startup. Methods run once each in the same interpreter in reference, conventional, control order. Cache order, instrumentation and host load affect these observations. Repeated runs do not change the fixed financial inputs. For performance studies, record hardware, interpreter, repeats, order and distributions.
