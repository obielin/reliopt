# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `Contract.wilson_lower_bound(successes_field, minimum, confidence=0.95)`: a generic
  rate-based contract that gates on the lower bound of the Wilson score interval for a
  boolean field, instead of the raw observed proportion, so small samples can't clear a
  threshold on a lucky point estimate.
- Core v0.1 loop: `Program` adapter, `Contract` + 4 built-ins, `Objective` + 4 built-ins,
  perturbation engine with 2 deterministic perturbers, `Compiler` with grid/explicit search,
  Pareto frontier computation, `CompileResult`/`EvidenceCard` reporting.
- Attribution module scaffold (`ComponentAblator` protocol, `run_attribution` loop) — not yet
  wired to any real program type. See ARCHITECTURE.md.
- Runnable end-to-end demo (`examples/rag_demo.py`).
- Contributor infrastructure: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, GOVERNANCE.md,
  issue/PR templates.
