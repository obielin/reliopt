"""
Trajectory — the structured record of one execution of a Program.

This is intentionally a plain, serialisable data structure (not tied to any
particular agent framework's internal call representation) so it can be:
  - scored by Objectives/Contracts
  - diffed against other trajectories for the perturbation engine
  - fed into attribution analysis (which steps/components produced which
    behavioural properties)

v0.1 scope: one TrajectoryStep per Program.run() call boundary. Richer
step-level tracing of *sub*-calls inside a dspy.Module or LangGraph node is
a v0.2 item — see ARCHITECTURE.md's roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrajectoryStep:
    step_type: str
    inputs: dict[str, Any] = field(default_factory=dict)
    output: Any = None
    latency_seconds: float = 0.0
    cost_usd: float | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Trajectory:
    steps: list[TrajectoryStep] = field(default_factory=list)

    @property
    def total_latency_seconds(self) -> float:
        return sum(s.latency_seconds for s in self.steps)

    @property
    def total_cost_usd(self) -> float:
        return sum(s.cost_usd or 0.0 for s in self.steps)

    @property
    def had_error(self) -> bool:
        return any(s.error for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [
                {
                    "step_type": s.step_type,
                    "latency_seconds": s.latency_seconds,
                    "cost_usd": s.cost_usd,
                    "error": s.error,
                    "metadata": s.metadata,
                }
                for s in self.steps
            ],
            "total_latency_seconds": self.total_latency_seconds,
            "total_cost_usd": self.total_cost_usd,
            "had_error": self.had_error,
        }
