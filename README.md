# reliopt

[![PyPI](https://img.shields.io/pypi/v/reliopt)](https://pypi.org/project/reliopt/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) [![CI](https://github.com/obielin/reliopt/actions/workflows/ci.yml/badge.svg)](https://github.com/obielin/reliopt/actions/workflows/ci.yml) [![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)

**Reliability-constrained, multi-objective optimization for LLM and agent programs.**

## Table of contents

- [The thesis](#the-thesis)
- [Related work](#related-work)
- [Install](#install)
- [Quick start](#quick-start)
- [Example output](#example-output)
- [Status](#status)
- [Contributing](#contributing)
- [License](#license)

## The thesis

A good AI program is not the one with the highest score. It's the one that satisfies its
behavioral contracts while achieving the best defensible trade-off between quality,
robustness, cost, and efficiency.

Concretely, that means:

- **Contracts, not just scores** — hard/soft behavioral requirements (groundedness, schema
  validity, tool scope) that gate candidates, separate from the objectives you're optimizing.
  A candidate that violates a contract is excluded from consideration entirely, no matter how
  well it scores elsewhere.
- **Pareto frontiers, not a weighted-sum score** — collapsing accuracy/cost/robustness into one
  number conceals the trade-off. This framework returns the non-dominated candidate set and
  lets you pick a profile (`quality_first`, `balanced`, `low_cost`, `high_reliability`).
- **Component attribution, not just an aggregate score** — for programs built as a `Pipeline`
  (a named sequence of steps), controlled zero-ablation swaps one named step for a passthrough
  and measures the score delta, answering *why* one architecture outperforms another, not just
  *that* it does.
- **Automated stress-testing** — candidates are scored on perturbed variants of your trainset
  (reordered clauses, injected distractors, and your own domain-specific perturbers), not just
  the nominal examples.

reliopt is a meta-layer, not a replacement for your agent framework: it wraps arbitrary Python
callables today, with adapters for popular frameworks planned as the ecosystem grows.

## Related work

See [research/RELATED_WORK.md](research/RELATED_WORK.md) for how this relates to per-output
constraint mechanisms, evaluation/red-teaming frameworks, and multi-objective prompt
optimization.

## Install

```
pip install reliopt
```

## Quick start

```python
from reliopt import Program, Contract, Objective

program = Program(my_rag_agent)

program.contracts(
    Contract.groundedness(minimum=0.90),
    Contract.schema_valid(),
)

program.objectives(
    Objective.accuracy(),
    Objective.cost(minimise=True),
    Objective.latency(minimise=True),
)

result = program.compile(trainset=data)

print(result.render_table())
best = result.select("balanced")
print(result.evidence_card(best.id).render())
```

See `examples/rag_demo.py` for a runnable end-to-end walkthrough.

## Example output

Output of `python examples/rag_demo.py`, run against the fake, deterministic RAG program
that ships with the repo (zero API calls/cost):

```
6 candidate programs tested
5 rejected for contract violations
Pareto-optimal candidates: 1

Candidate   accuracy    cost        latency     Status
candidate_0 0.667       0.000       0.000       dominated/rejected
candidate_1 1.000       0.000       0.000       dominated/rejected
candidate_2 1.000       0.000       0.000       dominated/rejected
candidate_3 1.000       0.000       0.000       dominated/rejected
candidate_4 1.000       0.000       0.000       dominated/rejected
candidate_5 1.000       0.000       0.000       Pareto-optimal

Evidence card for 'balanced' pick:
Candidate candidate_5
  accuracy             1.0000
  cost                 0.0000
  latency              0.0000
  contract: groundedness         ✅
```

## Status

Early, actively-developed v0.1. The core loop (Program adapter → Contracts → Objectives →
Perturbation engine → Pareto compiler → Evidence Card) works end-to-end today; several pieces
are intentionally thin placeholders with clearly marked seams — see `ARCHITECTURE.md` for what's
real vs. stubbed, and `CHANGELOG.md` for what's shipped.

## Contributing

New to the project? Start with an issue labeled
[`good first issue`](https://github.com/obielin/reliopt/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

See `CONTRIBUTING.md`. Issues and PRs welcome — `good first issue` labels are being seeded.

## License

MIT