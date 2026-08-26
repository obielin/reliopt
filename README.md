# reliopt

**Reliability-constrained, multi-objective optimization for LLM and agent programs.**

## The thesis

A good AI program is not the one with the highest score. It's the one that satisfies its
behavioral contracts while achieving the best defensible trade-off between quality,
robustness, cost, and efficiency.

Frameworks like [DSPy](https://github.com/stanfordnlp/dspy) ask: *how do I automatically make
this LM program perform better against a metric?* This framework asks a different question:
*what implementation of this program satisfies its behavioral requirements, remains robust
under plausible variation, and provides the best acceptable quality–cost–reliability trade-off?*

Concretely, that means:

- **Contracts, not just scores** — hard/soft behavioral requirements (groundedness, schema
  validity, tool scope) that gate candidates, separate from the objectives you're optimizing.
- **Pareto frontiers, not a weighted-sum score** — collapsing accuracy/cost/robustness into one
  number conceals the trade-off. This framework returns the non-dominated candidate set and lets
  you pick a profile (`quality_first`, `balanced`, `low_cost`, `high_reliability`).
- **Automated stress-testing** — candidates are scored on perturbed variants of your trainset
  (reordered clauses, injected distractors, and your own domain-specific perturbers), not just
  the nominal examples.
- **Component attribution** (in progress — see Roadmap) — controlled ablation to answer *why*
  one architecture outperforms another, not just *that* it does.

This is a meta-layer, not a replacement for your agent framework: it wraps arbitrary Python
callables and `dspy.Module` instances today, with LangGraph/pydantic-ai adapters planned.

## How this differs from adjacent projects

- **DSPy** already has [LM Assertions](https://arxiv.org/abs/2312.13382) — per-output hard/soft
  constraints enforced via backtracking. Contracts here serve a different purpose: they gate
  *candidates* across a whole trainset at compile time, feeding a Pareto filter, rather than
  triggering retries within a single inference call. A `dspy.Module` using Assertions internally
  can still be wrapped and scored here — the two are complementary, not competing.
- **Promptfoo / Inspect** are evaluation and red-teaming runtimes — they test and report. This
  framework's value isn't the evaluation runtime; it's what the compiler *does* with the
  evidence: diagnose, search, and return trade-off-aware candidates. Integrating with either as
  an evaluator backend is a natural extension point, not a competing rebuild.
- **Multi-objective prompt optimization** (e.g. MO-CAPO) already exists as a research direction.
  The contribution here is the combination — contracts + multi-objective search + automated
  stress-testing + component attribution as one coherent compile → diagnose → optimize → explain
  loop, not any one piece in isolation.

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
