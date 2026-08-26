"""
Attribution — controlled ablation of program components to attribute
observed behavioral properties (accuracy, groundedness, robustness, cost) to
specific parts of the program.

This is the project's deepest research contribution (see ARCHITECTURE.md) and
is intentionally NOT fully implemented yet — building a real version requires
a way to enumerate a program's "components" generically (retriever, reranker,
reasoning step, verifier, ...), which depends on the Program adapter maturing
beyond the v0.1 single-call-boundary tracing in trajectory.py.

What's here now: the data shape and the ablation-loop skeleton, so that
(a) the seam exists and compiler/result.py's EvidenceCard.attribution field
has a real producer to wire up, and (b) a contributor can implement one
component-enumeration strategy (e.g. for dspy.Module sub-modules specifically)
without redesigning the interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


class ComponentAblator(Protocol):
    """
    A strategy for producing an ablated variant of a program with one named
    component removed or replaced with a no-op/passthrough.
    """

    def components(self, program: Any) -> list[str]:
        """Return the names of ablatable components for this program."""
        ...

    def ablate(self, program: Any, component: str) -> Any:
        """Return a new program instance with `component` removed/no-op'd."""
        ...


@dataclass
class AttributionResult:
    component: str
    deltas: dict[str, float]  # objective_name -> (full_program_score - ablated_score)


def run_attribution(
    *,
    program: Any,
    ablator: ComponentAblator,
    evaluate_fn: Callable[[Any], dict[str, float]],
) -> list[AttributionResult]:
    """
    evaluate_fn: given a (possibly ablated) program, returns
    {objective_name: score} — typically a thin wrapper around
    Compiler._evaluate_candidate + Objective.evaluate for a fixed trainset.

    NOTE: this runs the full trainset once per component (linear in the
    number of ablatable components, not combinatorial) — still non-trivial
    API cost for large programs/trainsets. Flag this to users prominently
    in docs; see CONTRIBUTING.md "Attribution cost considerations."
    """
    baseline_scores = evaluate_fn(program)
    results: list[AttributionResult] = []
    for component in ablator.components(program):
        ablated_program = ablator.ablate(program, component)
        ablated_scores = evaluate_fn(ablated_program)
        deltas = {
            name: baseline_scores.get(name, 0.0) - ablated_scores.get(name, 0.0)
            for name in baseline_scores
        }
        results.append(AttributionResult(component=component, deltas=deltas))
    return results
