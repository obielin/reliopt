# reliopt

**Reliability-constrained, multi-objective optimization for LLM and agent programs.**

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
- **Automated stress-testing** — candidates are scored on perturbed variants of your trainset
  (reordered clauses, injected distractors, and your own domain-specific perturbers), not just
  the nominal examples.
- **Component attribution** (in progress — see Roadmap) — controlled ablation to answer *why*
  one architecture outperforms another, not just *that* it does.

reliopt is a meta-layer, not a replacement for your agent framework: it wraps arbitrary Python
callables today, with adapters for popular frameworks planned as the ecosystem grows.

## Related work

See [research/RELATED_WORK.md](research/RELATED_WORK.md) for how this relates to DSPy,
Promptfoo, Inspect, and MO-CAPO.

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

## Status

Early, actively-developed v0.1. The core loop (Program adapter → Contracts → Objectives →
Perturbation engine → Pareto compiler → Evidence Card) works end-to-end today; several pieces
are intentionally thin placeholders with clearly marked seams — see `ARCHITECTURE.md` for what's
real vs. stubbed, and `CHANGELOG.md` for what's shipped.

## Contributing

See `CONTRIBUTING.md`. Issues and PRs welcome — `good first issue` labels are being seeded.

## License

MIT