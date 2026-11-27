<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Contributing

Start with the model and runnable examples in the [README](README.md). If a change alters financial semantics, feasibility checks or comparison methodology, first describe the proposed behavior, alternatives and test cases in a public issue or design proposal. Use a synthetic example that a reviewer can run. [Governance](GOVERNANCE.md) · [Code of conduct](CODE_OF_CONDUCT.md)

Fork the repository, create a branch from the current upstream `main`, and keep each change focused. Run the documented tests and include the commands and observed results in the pull request. Add a regression test for changed behavior. For performance claims, identify the dataset, constraints, comparator, work limit and measurement environment. A reviewer must be able to reproduce the comparison and inspect failed or incomplete settlements.

## Origin and licensing

Contribute only material you are entitled to submit. Identify any third-party work, original authors, license and required attribution. Confirm employer or other rightsholder authorization where applicable. Use synthetic payment records in issues, examples and tests.

The Labs charter licenses code under Apache-2.0 and documentation under CC BY 4.0. [Code license](LICENSE) · [Documentation license](https://creativecommons.org/licenses/by/4.0/) · [Charter, section 6](https://github.com/LF-Decentralized-Trust-labs/governance/blob/main/lf-decentralized-trust-labs_Charter.pdf)

## Sign off every commit

Read the Developer Certificate of Origin 1.1. Your sign-off certifies your right to submit your contribution and acknowledges the public record. Inspect the repository's effective author identity with the following commands.

```sh
git config --get user.name
git config --get user.email
```

Use your own name and email. When you can make the certification, create your commit with `git commit -s` and inspect its `Signed-off-by` trailer with `git log -1 --format=%B`. Each commit in a pull request needs its own sign-off. [Developer Certificate of Origin](https://developercertificate.org/) · [LFDT GitHub contribution guide](https://lf-decentralized-trust.github.io/governance/guidelines/github-contribution-guide/)

Open a pull request from your fork into upstream `main`. Link its design discussion, summarize the changes and tests, and disclose limitations or outstanding review questions. For a vulnerability, use the private intake in the [security policy](SECURITY.md).
