# Copilot Review Instructions for reliopt

When reviewing PRs in this repository, prioritize these project-specific checks:

## No silent pass
Any Contract or scorer missing the data it needs must report `satisfied=False`
or an explicit "not measured" state — never silently default to passing.
See ARCHITECTURE.md's "Design principles worth preserving," #4.

## Gate vs. dial
A `Contract` excludes a candidate from the Pareto frontier entirely when
violated — it must never be scored, weighted, or averaged like an
`Objective`. Flag any code that blurs this distinction.

## No weighted-sum scores
Objectives must never be collapsed into a single scalar via arbitrary
weights. Flag any `0.4*x + 0.6*y`-style aggregation.

## Zero-ablation, not removal
Anything touching `attribution/` should ablate a component via
passthrough/no-op substitution, not by deleting it — check step count and
wiring stay unchanged after ablation.

## Test coverage for new Contracts/Objectives
A new Contract or Objective needs three test cases: satisfied, violated,
and "no data available." Flag a PR missing any of the three.

## Zero mandatory dependencies
Nothing in `src/reliopt/` (outside an explicitly optional extra) should
import a third-party package. Flag any new top-level import that isn't
stdlib.
