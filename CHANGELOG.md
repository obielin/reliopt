# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `EvidenceCard.failure_clusters` is now populated, via `Compiler._failure_clusters` —
  no new dependency: every run record is grouped by *why* it failed, not by embedding
  similarity (that alternative was rejected for v0.1 on the dependency grounds; see
  ARCHITECTURE.md). Labels are `"objective:accuracy"`, `"contract:<name>"` (that record
  alone re-evaluated against the contract), and `"perturbation:<type>"` — a record can
  land in more than one cluster, never forced into just one. Always computed (no opt-in
  flag: pure computation over records already collected for scoring, not an extra program
  execution, unlike attribution).
- `Compiler(attribution=True)` (opt-in, default `False`): runs component attribution for
  every candidate whose configured program wraps a `Pipeline`, using `PipelineAblator`
  against the nominal trainset only (no perturbations, to avoid compounding attribution's
  own per-component cost multiplier). Adds `Candidate.attribution_results` /
  `Candidate.attribution_skipped_reason`, and `CompileResult.evidence_card()` now populates
  `EvidenceCard.attribution` from it — `EvidenceCard.render()` prints a "component
  attribution" section when present, or an explicit "skipped — ..." line when the candidate's
  program wasn't a `Pipeline`, rather than a silently empty result either way.
- `Pipeline` (`reliopt.pipeline`): a dependency-free program primitive — an ordered list
  of named `(name, callable)` steps, each step's output feeding the next, the whole thing
  callable so it drops straight into `Program`. Gives component attribution something with
  enumerable internal structure to work on.
- `PipelineAblator` (`reliopt.attribution.PipelineAblator`): the first concrete
  `ComponentAblator`. `components()` returns a `Pipeline`'s step names (and raises
  `TypeError`, never `[]`, for a non-`Pipeline` program); `ablate()` returns a deep-copied
  `Pipeline` with the named step zero-ablated — swapped for a passthrough that returns its
  input unchanged, not literally removed. Available for `Pipeline`-structured programs
  only. Runnable end-to-end demo: `examples/attribution_demo.py`.
- `Contract.wilson_lower_bound(successes_field, minimum, confidence=0.95)`: a generic
  rate-based contract that gates on the lower bound of the Wilson score interval for a
  boolean field, instead of the raw observed proportion, so small samples can't clear a
  threshold on a lucky point estimate.
- Core v0.1 loop: `Program` adapter, `Contract` + 4 built-ins, `Objective` + 4 built-ins,
  perturbation engine with 2 deterministic perturbers, `Compiler` with grid/explicit search,
  Pareto frontier computation, `CompileResult`/`EvidenceCard` reporting.
- Attribution module scaffold (`ComponentAblator` protocol, `run_attribution` loop) — now
  with a concrete implementation for `Pipeline` programs, wired into `Compiler`/
  `EvidenceCard` as opt-in (see above). See ARCHITECTURE.md.
- Runnable end-to-end demo (`examples/rag_demo.py`).
- Contributor infrastructure: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, GOVERNANCE.md,
  issue/PR templates.
