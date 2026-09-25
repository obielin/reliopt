# Related Work

## Per-output constraint mechanisms

Some LM-programming approaches enforce correctness constraints on individual outputs within a
single inference call — hard/soft assertions checked via backtracking or self-refinement, so a
call that violates a constraint is retried or revised before returning
([arXiv:2312.13382](https://arxiv.org/abs/2312.13382)).

**Relationship to this project:** that mechanism operates *within* one call. `Contract`/
`wilson_lower_bound` here operates *across* an entire trainset at compile time, gating whether a
candidate configuration is admitted to the Pareto frontier at all — a different mechanism
serving a different purpose. A program using per-output assertions internally can still be
wrapped in a `Program` and scored here; the two compose rather than compete. This project makes
no claim to out-optimize per-call constraint enforcement — it asks a different question (see
THESIS.md).

## Evaluation and red-teaming frameworks

A mature category of tooling exists for running evaluations, adversarial testing, and reporting
on LLM applications — assertions, benchmark suites, scorers, sandboxes, reusable eval tasks.
This is genuinely useful, widely adopted infrastructure for answering "how did this candidate
perform?"

**Relationship to this project:** this project sits one layer above that question. Its focus is
what a compiler *does* with evaluation evidence once it exists — reject, search, and return
trade-off-aware candidates — not the evaluation runtime itself. An existing evaluation framework
is a natural backend to plug into, not something this project aims to rebuild.

## Multi-objective prompt optimization

Optimizing LM programs against more than one objective simultaneously — explicitly trading off
task performance against cost — is an active academic research direction this project draws on,
not one it originates.

**Relationship to this project:** the contribution here is not "multi-objective search exists"
but the combination: statistically-gated Requirements (excluding candidates entirely, not just
penalizing them) + multi-objective Pareto search + automated stress-testing + component
attribution (shipped — see ARCHITECTURE.md), as one coherent compile → diagnose → optimize →
explain loop with an evidence artifact at the end. See RFC-0001 for the formal design.
