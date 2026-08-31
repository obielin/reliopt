"""
PipelineAblator — the first concrete `ComponentAblator` (see engine.py).

It ablates a `reliopt.pipeline.Pipeline` by *zero-ablation*: the named step is
replaced with a no-op/passthrough that returns its input unchanged, rather than
being literally removed from the sequence. The pipeline keeps the same number
of steps and the same wiring; the ablated step simply contributes nothing. The
resulting delta (full-program score minus ablated score, per `run_attribution`)
attributes the observed behaviour to that step.

This deliberately mirrors the language in engine.py's module docstring: a
component is "removed or replaced with a no-op/passthrough". Here it is always
the passthrough form — no step count changes — which keeps every step's
input/output contract intact for the steps that remain.

Scope: this works for `Pipeline`-structured programs only. Plain
`Program`-wrapped callables have no enumerable internal components and are not
supported — `components()` raises `TypeError` rather than silently returning an
empty list.
"""

from __future__ import annotations

import copy
from typing import Any

from reliopt.pipeline import Pipeline, passthrough


class PipelineAblator:
    """Implements the `ComponentAblator` protocol for `Pipeline` programs."""

    def components(self, program: Any) -> list[str]:
        """
        Return the pipeline's step names, in order.

        Raises `TypeError` if `program` is not a `Pipeline` — there is nothing
        to enumerate for an opaque callable, and returning `[]` would silently
        make `run_attribution` a no-op.
        """
        if not isinstance(program, Pipeline):
            raise TypeError(
                "PipelineAblator can only enumerate components of a Pipeline; "
                f"got {type(program).__name__}. Wrap your steps in "
                "reliopt.pipeline.Pipeline to use component attribution."
            )
        return list(program.names)

    def ablate(self, program: Any, component: str) -> Pipeline:
        """
        Return a deep-copied `Pipeline` with `component` zero-ablated — its
        step callable swapped for a passthrough that returns its input
        unchanged. The original pipeline is left untouched.

        Raises `TypeError` if `program` is not a `Pipeline`, `ValueError` if
        `component` is not one of its step names.
        """
        if not isinstance(program, Pipeline):
            raise TypeError(
                "PipelineAblator can only ablate a Pipeline; "
                f"got {type(program).__name__}."
            )
        if component not in program.names:
            raise ValueError(
                f"Unknown component {component!r}; pipeline steps are {program.names!r}."
            )
        clone = copy.deepcopy(program)
        clone.steps = [
            (name, passthrough if name == component else fn) for name, fn in clone.steps
        ]
        return clone
