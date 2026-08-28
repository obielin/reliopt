# RFC-0001: Evidence-Gated Optimisation Model

## Summary

Defines the core Program → Contract/Requirement → Objective → Compiler →
Pareto frontier model, and the statistical standard (confidence-interval
gating, not raw rates) that Requirements must meet.

## Motivation

See `research/THESIS.md`. In short: task-performance optimization alone
conceals reliability trade-offs and can pass candidates on statistically
unsupported evidence (a small sample clearing a raw threshold by chance).

## Problem

Given several configurations of an AI program, how do we (a) reject
configurations that fail a reliability requirement with statistical
confidence, and (b) among the remainder, surface the trade-off between
competing objectives without collapsing it into one arbitrary score?

## Proposed design

- `Program`: adapter wrapping an arbitrary callable / `dspy.Module`.
- `Contract`/`Requirement`: a gate, not a dial. `strict=True` violations
  exclude a candidate from the frontier entirely (`compiler/pareto.py`).
  Rate-based requirements (`groundedness`, `abstain_when_unsupported`) gate on
  the Wilson score interval lower bound of the observed rate, not the raw
  rate — implemented in PR #2 (`wilson_lower_bound` factory) and retrofitted
  into `abstain_when_unsupported` in PR #4.
- `Objective`: a dial (accuracy, cost, latency, consistency) — direction
  (`maximise`/`minimise`), never collapsed into a weighted scalar.
- `Compiler`: runs each candidate config across the trainset (+ perturbations),
  evaluates Contracts and Objectives, hands off to Pareto computation.
- Pareto frontier: non-dominated candidates among those satisfying all strict
  Contracts.

## Alternatives considered

- **Weighted scalar score** (`0.4*accuracy + 0.2*robustness - 0.1*cost`):
  rejected — weights are arbitrary and conceal the actual trade-off (see
  THESIS.md principle 3).
- **Raw-rate thresholds** for rate-based requirements: rejected in favor of
  Wilson lower bound — a raw rate lets a small/lucky sample pass a threshold
  it hasn't actually demonstrated (see PR #2's motivation).

## Statistical implications

Wilson score interval chosen over a normal approximation because it behaves
correctly at small sample sizes and at rates near 0 or 1 (see
`contracts/base.py::wilson_lower_bound` for the implementation, using stdlib
`statistics.NormalDist` — no new dependency).

## API implications

`Contract.wilson_lower_bound(successes_field, minimum, confidence=0.95,
strict=True)` is the canonical rate-gating factory; other rate-based
Contracts should call it internally rather than duplicate interval math
(see PR #4).

## Backward compatibility

Pre-1.0, no compatibility guarantees yet.

## Risks

- Wilson interval assumes independent Bernoulli trials per example; if a
  future perturbation strategy introduces correlated failures (e.g. one
  underlying bug causing many correlated failures), the interval's coverage
  guarantee weakens. Flagged here, not yet mitigated.

## Open questions

- Should `Objective.consistency` also move to an interval-based measure once
  `repeat_n > 1` is exercised in real (not toy) usage?

## Decision

**Accepted and implemented** — this RFC documents design already merged via
PR #2 and PR #4, written retroactively per the project's RFC process.