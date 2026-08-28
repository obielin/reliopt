# Related Work

## DSPy

[DSPy](https://github.com/stanfordnlp/dspy) optimizes LM programs against a
task metric — it compiles prompts/demonstrations/weights toward a score. It
also has [LM Assertions](https://arxiv.org/abs/2312.13382) (Dec 2023):
per-output hard/soft constraints enforced via backtracking and self-refinement
at compile-time or inference-time.

**Relationship to this project:** Assertions gate a single output within one
inference call. `Contract`/`Requirement` here gates a *candidate* across an
entire trainset at compile time, feeding a Pareto filter — a different
mechanism serving a different purpose. A `dspy.Module` using Assertions
internally can still be wrapped in a `Program` and scored here; the two are
complementary, not competing. This project does not claim to out-optimize
DSPy's search — it asks a different question (see THESIS.md).

## Promptfoo

[Promptfoo](https://github.com/promptfoo/promptfoo) is an evaluation and
red-teaming framework — assertions, benchmarks, adversarial testing, reporting.

**Relationship to this project:** Promptfoo tests and reports. This project's
value is what the compiler *does* with evaluation evidence — reject, search,
and return trade-off-aware candidates. Promptfoo (or Inspect, below) as an
evaluator backend is a natural integration point, not a competing rebuild.

## Inspect

[Inspect](https://github.com/UKGovernmentBEIS/inspect_ai) is the UK AI Security
Institute's evaluation framework — agents, tools, multiple scorers, sandboxes,
reusable tasks.

**Relationship to this project:** same distinction as Promptfoo. This project
is not an evaluation runtime; it is a compiler that consumes evaluation
evidence (potentially from Inspect) to make optimization and rejection
decisions.

## Multi-objective prompt optimization (e.g. MO-CAPO)

Multi-objective optimization of LM programs — explicitly trading off
performance against cost — is an active research direction, not something
this project originates.

**Relationship to this project:** the contribution here is not "multi-objective
search exists" but the *combination*: Requirements (statistically-gated,
excluding candidates entirely) + multi-objective Pareto search + automated
stress-testing + (planned) component attribution, as one coherent
compile → diagnose → optimize → explain loop with an evidence artifact at
the end. See RFC-0001 for the formal design.