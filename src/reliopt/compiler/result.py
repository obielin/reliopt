"""
CompileResult / EvidenceCard — what compile() hands back to the user.

Deliberately structured as "here's the evidence, here are your options" rather
than "here's the one best program" — the developer picks a profile
(quality_first / balanced / low_cost / high_reliability) rather than the
framework silently choosing for them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from reliopt.compiler.pareto import Candidate, pareto_frontier

Profile = Literal["quality_first", "balanced", "low_cost", "high_reliability"]


@dataclass
class EvidenceCard:
    """
    The explanatory artifact: not just a score, but why a candidate is or
    isn't recommended. `attribution` is populated only when
    Compiler(attribution=True) was used (v0.3 scope per ARCHITECTURE.md) —
    left as an empty dict otherwise, not silently omitted, so callers can
    tell the difference between "not measured" and "measured as zero."
    """

    candidate_id: str
    objective_summary: dict[str, float]
    contract_summary: dict[str, bool]
    rejected: bool
    rejection_reason: str = ""
    attribution: dict[str, dict[str, float]] = field(default_factory=dict)
    failure_clusters: dict[str, int] = field(default_factory=dict)

    def render(self) -> str:
        lines = [f"Candidate {self.candidate_id}"]
        for name, value in self.objective_summary.items():
            lines.append(f"  {name:<20} {value:.4f}")
        for name, satisfied in self.contract_summary.items():
            mark = "✅" if satisfied else "❌ contract violated"
            lines.append(f"  contract: {name:<20} {mark}")
        if self.rejected:
            lines.append(f"  REJECTED from deployment frontier: {self.rejection_reason}")
        if self.failure_clusters:
            lines.append("  failure clusters:")
            for cluster, count in sorted(self.failure_clusters.items(), key=lambda kv: -kv[1]):
                lines.append(f"    {cluster:<30} {count}")
        if self.attribution:
            lines.append("  component attribution:")
            for component, deltas in self.attribution.items():
                delta_str = ", ".join(f"{k}: {v:+.3f}" for k, v in deltas.items())
                lines.append(f"    {component:<20} {delta_str}")
        return "\n".join(lines)


@dataclass
class CompileResult:
    candidates: list[Candidate]

    def pareto_frontier(self) -> list[Candidate]:
        return pareto_frontier(self.candidates)

    def select(self, profile: Profile) -> Candidate:
        frontier = self.pareto_frontier()
        if not frontier:
            raise ValueError("No candidates satisfy all strict contracts — nothing to select from.")

        def obj(c: Candidate, name: str) -> float:
            try:
                return c.score(name)
            except KeyError:
                return 0.0

        if profile == "quality_first":
            key = lambda c: -obj(c, "accuracy")
        elif profile == "low_cost":
            key = lambda c: obj(c, "cost")
        elif profile == "high_reliability":
            key = lambda c: -obj(c, "consistency")
        else:  # balanced — simple normalised-rank average across objectives present
            def key(c: Candidate) -> float:
                ranks = []
                for name in {s.objective_name for s in c.objective_scores}:
                    values = [x.score(name) for x in frontier]
                    higher_is_better = next(s.direction for s in c.objective_scores if s.objective_name == name) == "maximise"
                    sorted_vals = sorted(values, reverse=higher_is_better)
                    ranks.append(sorted_vals.index(c.score(name)))
                return sum(ranks) / len(ranks) if ranks else 0.0

        return sorted(frontier, key=key)[0]

    def evidence_card(self, candidate_id: str) -> EvidenceCard:
        candidate = next((c for c in self.candidates if c.id == candidate_id), None)
        if candidate is None:
            raise KeyError(f"No candidate with id {candidate_id!r}")
        rejected = not candidate.satisfies_all_strict_contracts
        violated = [cr.contract_name for cr in candidate.contract_results if not cr.satisfied]
        return EvidenceCard(
            candidate_id=candidate.id,
            objective_summary={s.objective_name: s.value for s in candidate.objective_scores},
            contract_summary={cr.contract_name: cr.satisfied for cr in candidate.contract_results},
            rejected=rejected,
            rejection_reason=f"violated: {', '.join(violated)}" if violated else "",
        )

    def render_table(self) -> str:
        frontier_ids = {c.id for c in self.pareto_frontier()}
        objective_names = [s.objective_name for s in self.candidates[0].objective_scores] if self.candidates else []
        header = "Candidate".ljust(12) + "".join(name.ljust(12) for name in objective_names) + "Status"
        lines = [header]
        for c in self.candidates:
            row = c.id.ljust(12)
            for name in objective_names:
                row += f"{c.score(name):.3f}".ljust(12)
            status = "Pareto-optimal" if c.id in frontier_ids else "dominated/rejected"
            row += status
            lines.append(row)
        return "\n".join(lines)
