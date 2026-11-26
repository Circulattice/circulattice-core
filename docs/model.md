<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# The single-batch obligation model

Consider an agreement denominated in one currency. A member can use only the opening funds assigned to that agreement and currency. The model assumes that eligible obligations can be partly or fully offset, that funds are reserved separately for each pool, and that all remaining payments must be prefunded before the batch. Incoming payments cannot finance another outgoing payment in that batch. Actual legal permissions, asset reservations and payment finality are external assumptions.

## Input and arithmetic

The version 1 JSON object contains `version`, `participants`, `pools` and `obligations`. Each pool has `agreement`, `currency`, `members` and a `funding` object with one cap per member. Each obligation has a unique `id`, a distinct `debtor` and `creditor`, `agreement`, `currency`, `amount` and the boolean `eligible`. Both endpoints must belong to its declared pool. Multiple obligations between the same two members are allowed. An original can be partly offset, fully offset or paid entirely in cash. A cash-only original has `eligible=false`. [Worked JSON example](../examples/cycle.json)

Use integer minor units with a consistent externally agreed unit for each currency. No rounding, exchange rates, unit conversion or floating-point monetary arithmetic occur. A three-letter uppercase currency label identifies a unit namespace. The parser does not certify ISO membership or currency scale. The same real cash cannot be pledged to two input pools. An operator must check this allocation before modeling settlement.

| Boundary | Value |
| --- | --- |
| Encoded file and nesting | At most 1 MiB of UTF-8 and 16 nested containers per JSON file |
| Identifiers | 1–64 ASCII letters, digits, dots, underscores or hyphens, starting with a letter or digit |
| Participants | 1–64 unique IDs |
| Pools | Up to 32 unique agreement/currency pairs, each with at least one member |
| Obligations | Up to 256 across the whole problem |
| Amounts / funding | Obligations 1 to 10¹⁵, caps 0 to 10¹⁵, inclusive |
| Unsupported fields, duplicate keys/IDs, fractional numbers, self-payments | Input error |

Python integers retain exact sums even when an aggregate exceeds the input limit or binary64’s exact range. Empty obligation books are feasible with an empty allocation. A zero cap is an explicit constraint. Omitting a member’s cap is an error.

## Feasibility and objective

Within each pool, let obligation *e* carry amount *aₑ*, offset *xₑ* and residual *rₑ = aₑ − xₑ*. For every original, *0 ≤ xₑ ≤ aₑ*, integer, and *xₑ = 0* when the original is ineligible. At every member *v*, enforce

```text
sum(x on outgoing edges of v) = sum(x on incoming edges of v)
sum(r on outgoing edges of v) ≤ opening funding[v]
```

The first equation preserves each member’s signed net obligation. The second accounts for all residuals, including fixed cash obligations. Feasible means that every original is covered by offset plus available prefunding. There is no partial-settlement success. The objective maximizes the sum of offsets separately in each pool, equivalently minimizing its gross prefunded residual. There is no exchange rate or cross-pool tradeoff. Gross offset counts each original’s reduction. It is independent of how banks might reuse incoming cash over time.

## How the solver finds an optimum

1. Reserve the entire amount of each ineligible outgoing obligation against its payer’s cap. A negative remainder proves infeasibility.
2. In the eligible graph let *dᵥ* be outgoing original amount minus incoming original amount. Residuals must carry this same signed imbalance. Add a super-source to positive-debit members and connect negative-debit members to a super-sink.
3. Split each member into an account and an outgoing gate. Cap that gate at the remaining prefunding. Each eligible original becomes a directed edge from its debtor’s gate to its creditor’s account, with capacity *aₑ* and cost one per unit. Other forward arcs cost zero.
4. Starting at zero flow, send the bottleneck amount along a shortest residual source-to-sink path. Each reverse arc can undo earlier choices. Bellman–Ford handles its negative cost. Exhaustion of all required debit gives the solution. Absence of an augmenting path while demand remains proves no feasible plan exists in this model.

Any feasible allocation maps to a flow of the required value, by taking each eligible residual as its edge flow. Conversely, such a flow obeys the original conservation equations and the member caps. Its cost is exactly the sum of eligible residuals. The ineligible cash adds a constant, so a minimum-cost flow gives the desired maximum offset. Initial costs are nonnegative. Shortest-path augmentation preserves minimum cost at each attained flow value: the residual network retains no negative-cost cycle, since shortest-path distance potentials give nonnegative reduced costs on reachable arcs and the new reverse arcs on the chosen path have zero reduced cost. Integer capacities and bottleneck augmentation give integer residuals. An exhausted work allowance supplies neither an allocation nor an infeasibility proof.

Fixed identifier order, stable arc insertion and strict distance improvements select one deterministic solution when several have the same objective. Equivalent input array orderings give the same offsets and work count. Tie selection conveys no fairness or priority rule.

## Bounds and verification

Per pool with *n* members and *m* eligible originals, the flow graph has *V = 2n + 2* vertices and *E = O(m + n)* residual arcs. A shortest-path search costs *O(VE)*. Each successful augmentation sends at least one unit, so at most *F* augmentations are needed where *F* is the total eligible positive net debit in minor units. Allow one final unsuccessful search. This is a pseudo-polynomial worst-case bound of *O((F + 1)VE)*, with *O(V + E)* flow storage, plus bounded input and output. A shared counter limits residual-arc inspections across all pools. The default is 1,000,000 and the accepted range is 0–10,000,000. Input parsing, graph construction and output are outside the counter. Fully balanced eligible books may require zero inspections.

The checker independently totals signed offsets and gross residual debits from the original input. Time is linear in the number of originals plus member-pool entries, with storage proportional to the original IDs and member-pool entries. It shares the validated input model. The checker uses no graph search or optimization labels. A feasible but suboptimal candidate can pass. It cannot verify an infeasibility declaration, a budget claim, legal eligibility, a signature, timing or receipt of cash.

## Command outcomes

| Operation | Exit | Output |
| --- | --- | --- |
| `solve` finds an optimum | 0 | JSON with `status="optimal"`, `work` and a complete map of offsets |
| `solve` proves no funded allocation exists | 3 | `infeasible` and work, with no offsets |
| `solve` exhausts the budget | 4 | `budget_exhausted` and work, with no offsets |
| `check` accepts a candidate | 0 | `{"feasible": true}` |
| `check` has no witness (an infeasible or stopped solver result), or cannot read the files | 4 | Incomplete verification. A missing witness produces JSON with `verification="incomplete"`. |
| Malformed input, rejected candidate or solver file error | 2 | Diagnostic on stderr |

The `check` command takes a file containing an `offsets` object and checks that property only. The checker recalculates feasibility even when the candidate claims optimality. An envelope that declares failure and also contains offsets is inconsistent and is rejected. Preserve the original problem that accompanies a plan. IDs are not cryptographic commitments. A plan may accidentally fit a different problem.
