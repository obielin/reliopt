"""
Program — the adapter layer that wraps an arbitrary callable, dspy.Module,
or (eventually) LangGraph/pydantic-agent graph into something the compiler
can introspect, run, and score.

Design decision (deliberate): we do NOT require people to rebuild their agent
in our framework. `compile(my_python_function)` and `compile(my_dspy_program)`
both work. This is a meta-layer that sits on top of whatever agent framework
someone already uses, not a replacement for it.
"""

from __future__ import annotations

import inspect
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from reliopt.contracts.base import Contract
from reliopt.objectives.base import Objective
from reliopt.trajectory import Trajectory, TrajectoryStep


@dataclass
class ProgramRun:
    """The result of a single execution of a wrapped program."""

    inputs: dict[str, Any]
    output: Any
    trajectory: Trajectory
    latency_seconds: float
    error: Optional[Exception] = None


class Program:
    """
    Wraps a callable so it can be run, traced, and scored consistently
    regardless of what it's built with underneath.

    Supported today:
        - plain Python callables: `Program(my_function)`
        - dspy.Module instances (duck-typed via `.forward`/`__call__`)

    Planned adapters (not yet implemented — see CONTRIBUTING.md):
        - LangGraph compiled graphs
        - pydantic-ai agents
        - raw OpenAI/Anthropic tool-use loops
    """

    def __init__(self, target: Callable[..., Any], *, name: Optional[str] = None):
        self.target = target
        self.name = name or getattr(target, "__name__", target.__class__.__name__)
        self._contracts: list[Contract] = []
        self._objectives: list[Objective] = []

    # -- configuration -----------------------------------------------------

    def contracts(self, *contracts: Contract) -> "Program":
        """Attach hard/soft behavioral requirements. Chainable."""
        self._contracts.extend(contracts)
        return self

    def objectives(self, *objectives: Objective) -> "Program":
        """Attach the metrics to optimise (and their direction). Chainable."""
        self._objectives.extend(objectives)
        return self

    # -- execution -----------------------------------------------------------

    def run(self, **inputs: Any) -> ProgramRun:
        """
        Execute the wrapped target once, recording a Trajectory of whatever
        steps we can observe (currently: just the single call boundary —
        richer step-level tracing for dspy.Module sub-calls is a v0.2 item,
        see ARCHITECTURE.md).
        """
        step = TrajectoryStep(step_type="program_call", inputs=dict(inputs))
        start = time.perf_counter()
        error = None
        output = None
        try:
            output = self._invoke(**inputs)
        except Exception as exc:  # noqa: BLE001 — deliberately broad, we record and re-surface
            error = exc
        elapsed = time.perf_counter() - start

        step.output = output
        step.latency_seconds = elapsed
        step.error = str(error) if error else None

        trajectory = Trajectory(steps=[step])
        return ProgramRun(
            inputs=dict(inputs),
            output=output,
            trajectory=trajectory,
            latency_seconds=elapsed,
            error=error,
        )

    def _invoke(self, **inputs: Any) -> Any:
        if hasattr(self.target, "forward") and callable(getattr(self.target, "forward")):
            # dspy.Module-style: prefer .forward if present
            return self.target.forward(**inputs)
        if callable(self.target):
            sig_params = inspect.signature(self.target).parameters
            if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig_params.values()):
                return self.target(**inputs)
            # filter to only accepted kwargs so plain functions don't choke
            accepted = {k: v for k, v in inputs.items() if k in sig_params}
            return self.target(**accepted)
        raise TypeError(f"Program target {self.target!r} is not callable")

    def compile(self, *, trainset: list[dict[str, Any]], **kwargs: Any):
        """
        Entry point into the compiler. Kept as a thin delegator so Program
        stays a lightweight adapter and all the actual search/scoring logic
        lives in reliopt.compiler (see compiler/engine.py).
        """
        from reliopt.compiler.engine import Compiler

        return Compiler(program=self, contracts=self._contracts, objectives=self._objectives, **kwargs).run(
            trainset=trainset
        )

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"Program({self.name!r}, contracts={len(self._contracts)}, objectives={len(self._objectives)})"
