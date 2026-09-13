"""
Pareto frontier computation.

Deliberately NOT collapsing objectives into a weighted scalar (see the
project's founding rationale: weights are arbitrary and conceal trade-offs).
Given N candidates each scored on M objectives, return the non-dominated set.

A candidate A dominates candidate B if A is at least as good as B on every
objective and strictly better on at least one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from reliopt.attribution.engine import AttributionResult
from reliopt.objectives.base import ObjectiveScore


@dataclass
class Candidate:
    id: str
    config: dict[str, Any]
    objective_scores: list[ObjectiveScore]
    contract_results: list[Any]  # list[ContractResult], avoiding circular import here
    # Both None unless Compiler(attribution=True) was used — see compiler/engine.py.
    # attribution_results stays None (not []) when attribution wasn't requested at
    # all, so "not measured" is distinguishable from "measured, zero components."
    attribution_results: list[AttributionResult] | None = None
    # Set when attribution=True but this candidate's program isn't ablatable
    # (not a Pipeline) — explains an empty attribution_results rather than
    # leaving it a silent None. None when attribution wasn't requested, or was
    # requested and succeeded.
    attribution_skipped_reason: str | None = None

    @property
    def satisfies_all_strict_contracts(self) -> bool:
        return all(cr.satisfied for cr in self.contract_results if getattr(cr, "strict", True))

    def score(self, objective_name: str) -> float:
        for s in self.objective_scores:
            if s.objective_name == objective_name:
                return s.value
        raise KeyError(f"No score recorded for objective {objective_name!r}")


def _dominates(a: Candidate, b: Candidate) -> bool:
    at_least_as_good_everywhere = True
    strictly_better_somewhere = False
    for score_a, score_b in zip(a.objective_scores, b.objective_scores, strict=True):
        if score_a.objective_name != score_b.objective_name:
            raise ValueError("Candidates must be scored on the same objectives in the same order")
        higher_is_better = score_a.direction == "maximise"
        a_val, b_val = score_a.value, score_b.value
        if higher_is_better:
            if a_val < b_val:
                at_least_as_good_everywhere = False
            if a_val > b_val:
                strictly_better_somewhere = True
        else:
            if a_val > b_val:
                at_least_as_good_everywhere = False
            if a_val < b_val:
                strictly_better_somewhere = True
    return at_least_as_good_everywhere and strictly_better_somewhere


def pareto_frontier(candidates: list[Candidate]) -> list[Candidate]:
    """
    Returns the non-dominated candidates among those that satisfy all strict
    contracts. Candidates violating a strict contract are excluded entirely
    — this is the "rejected from deployment frontier" behaviour from the
    project's design doc, not a soft penalty.
    """
    eligible = [c for c in candidates if c.satisfies_all_strict_contracts]
    frontier = []
    for candidate in eligible:
        if not any(_dominates(other, candidate) for other in eligible if other is not candidate):
            frontier.append(candidate)
    return frontier
