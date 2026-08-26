"""
Objectives — the dials the compiler optimises, feeding the multi-objective
Pareto search. Deliberately kept separate from Contracts (see contracts/base.py
for why): an Objective says "more/less is better," a Contract says "this must
hold."

v0.1 built-ins per the agreed scope: accuracy, cost, latency, and one
reliability metric (consistency). Groundedness/calibration/robustness scorers
are v0.2+ per ARCHITECTURE.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Literal

Direction = Literal["maximise", "minimise"]


@dataclass
class ObjectiveScore:
    objective_name: str
    value: float
    direction: Direction


class Objective:
    def __init__(self, name: str, score_fn: Callable[[list[dict[str, Any]]], float], *, direction: Direction):
        self.name = name
        self._score_fn = score_fn
        self.direction = direction

    def evaluate(self, run_records: list[dict[str, Any]]) -> ObjectiveScore:
        return ObjectiveScore(self.name, self._score_fn(run_records), self.direction)

    # -- built-in factories --------------------------------------------------

    @staticmethod
    def accuracy(*, maximise: bool = True) -> "Objective":
        def _score(records: list[dict[str, Any]]) -> float:
            scored = [r for r in records if "correct" in r]
            if not scored:
                return 0.0
            return sum(1 for r in scored if r["correct"]) / len(scored)

        return Objective("accuracy", _score, direction="maximise" if maximise else "minimise")

    @staticmethod
    def cost(*, minimise: bool = True) -> "Objective":
        def _score(records: list[dict[str, Any]]) -> float:
            costs = [r["trajectory"].total_cost_usd for r in records if r.get("trajectory") is not None]
            return sum(costs) / len(costs) if costs else 0.0

        return Objective("cost", _score, direction="minimise" if minimise else "maximise")

    @staticmethod
    def latency(*, minimise: bool = True) -> "Objective":
        def _score(records: list[dict[str, Any]]) -> float:
            latencies = [r["trajectory"].total_latency_seconds for r in records if r.get("trajectory") is not None]
            return sum(latencies) / len(latencies) if latencies else 0.0

        return Objective("latency", _score, direction="minimise" if minimise else "maximise")

    @staticmethod
    def consistency(*, maximise: bool = True) -> "Objective":
        """
        Placeholder v0.1 reliability metric: fraction of repeated runs (same
        input, run `n` times) that produced the same output. Expects
        `record["repeat_outputs"]: list` to be populated by the compiler when
        repeat_n > 1. Returns 1.0 (best-case, not "verified") if no repeats
        were run — flagged clearly so it isn't mistaken for a real score.
        """

        def _score(records: list[dict[str, Any]]) -> float:
            with_repeats = [r for r in records if r.get("repeat_outputs")]
            if not with_repeats:
                return 1.0
            agreements = []
            for r in with_repeats:
                outputs = r["repeat_outputs"]
                most_common = max(set(outputs), key=outputs.count)
                agreements.append(outputs.count(most_common) / len(outputs))
            return sum(agreements) / len(agreements)

        return Objective("consistency", _score, direction="maximise" if maximise else "minimise")
