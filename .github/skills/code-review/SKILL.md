---
name: code-review
description: Domain-specific review guidance for reliopt — statistical rigor, the Contract/Objective distinction, zero-ablation semantics, and the "no silent pass" principle. Use when reviewing any pull request that touches src/reliopt/, especially contracts/, objectives/, attribution/, or compiler/.
---

# reliopt code review guidance

## Statistical claims need real justification
Any rate-based Contract must gate on a confidence interval (see
`wilson_lower_bound` in `contracts/base.py`), not a raw observed proportion.
A raw-rate contract can pass on a small, lucky sample. Flag any new
Contract that checks `some_rate >= threshold` directly instead of via
`wilson_lower_bound`.

## The Contract/Objective boundary is load-bearing
Read `contracts/base.py`'s module docstring and `ARCHITECTURE.md`'s design
principles before reviewing anything that adds a new Contract or Objective.
A Contract that gets averaged into a score, or an Objective that excludes
a candidate outright, is a design bug, not a style issue — treat it as a
blocking comment, not a suggestion.

## Attribution is zero-ablation, always
Reviewing `attribution/`: an ablator must replace a component with a
no-op/passthrough, never delete it from the sequence. Check that ablated
and unablated candidates have the same step count. See
`pipeline_ablator.py`'s `ablate()` as the reference implementation.

## "No data" must report failure, not silently pass
Every Contract/Objective factory needs to handle the case where its
required field is entirely absent from the run records. The correct
behavior is `satisfied=False` (Contracts) or a clearly-flagged placeholder
(Objectives, e.g. `Objective.consistency`'s repeat_n=1 case) — never a
silent `True` or an unflagged default value.

## New Contracts/Objectives need three tests, minimum
Satisfied case, violated case, and no-data-available case. A PR adding a
new factory method without all three is incomplete, regardless of whether
CI passes.
