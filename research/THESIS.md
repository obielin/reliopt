# Thesis

## Mission

An open-source Python framework for evidence-gated optimisation of LLM and agent
programs. It searches system configurations, evaluates them under nominal and
stressed conditions, rejects candidates that cannot demonstrate specified
reliability requirements with statistical confidence, and identifies
Pareto-optimal feasible systems across quality, robustness, cost, and latency.

## The core claim

A good AI program is not the one with the highest score. It is the one that
satisfies its behavioral requirements while achieving the best defensible
trade-off between quality, robustness, cost, and efficiency — and "satisfies"
means demonstrated with statistical confidence, not cleared on a raw point
estimate that a small or lucky sample could produce by chance.

## Non-goals

This project is explicitly **not**:

- another agent-building framework (it wraps existing ones — see Program adapter)
- a runtime access-control or governance platform
- an LLM firewall
- a generic evaluation dashboard
- a prompt library
- a production observability platform
- an autonomous code-rewriting system

## Five principles

1. **Evidence over assertion.** Reliability claims must be supported by recorded
   evaluations, not asserted. A `Contract`/`Requirement` that reports "satisfied"
   must be able to show the data it satisfied on.
2. **Requirements before optimisation.** A high-performing candidate that fails
   a requirement is not feasible, regardless of its objective scores. This is
   why `Contract` violations exclude a candidate from the Pareto frontier
   entirely (see `compiler/pareto.py`) rather than penalizing it.
3. **Trade-offs over magic scores.** We do not collapse accuracy, cost, latency,
   and robustness into one weighted number. The weights would be arbitrary and
   would conceal the trade-off a developer actually needs to see. See the Pareto
   frontier design, not a scalar objective function.
4. **Statistical rigor over point estimates.** A rate-based requirement
   (`abstain_when_unsupported`, `groundedness`) gates on a confidence interval
   lower bound (Wilson score interval — see PR #2, #4), not the raw observed
   rate, so a small sample can't pass by chance.
5. **Framework neutrality.** Developers should not have to rewrite an
   application in this framework. `Program` wraps arbitrary callables and
   `dspy.Module` instances; LangGraph and other adapters are planned, not
   required rewrites.

These are architectural constraints, not aspirations — a PR that violates one
of them (e.g. reintroducing a weighted-sum score, or a requirement that gates
on a raw rate instead of a confidence bound) should be rejected in review
regardless of how well-tested it is.