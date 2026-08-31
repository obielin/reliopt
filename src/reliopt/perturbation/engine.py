"""
Perturbation engine — generates stress-test variants of trainset examples so
candidates are scored on robustness, not just nominal accuracy.

v0.1 ships a small set of domain-agnostic, deterministic perturbers (no LLM
calls required, so this is free and fast to run) plus a `Perturber` protocol
so people can register LLM-based generators (paraphrase, adversarial
injection, etc.) for their specific domain — see CONTRIBUTING.md "Adding a
perturber." Shipping LLM-based perturbers as v0.1 built-ins was deliberately
deferred: they add per-compile API cost and domain-specific tuning that would
bloat the first release. Track this in the roadmap, not silently skip it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol


@dataclass
class Perturbation:
    original: dict[str, Any]
    perturbed: dict[str, Any]
    perturbation_type: str


class Perturber(Protocol):
    name: str

    def __call__(self, example: dict[str, Any]) -> Perturbation:
        ...


class ReorderClausesPerturber:
    """Naive deterministic perturber: if a text field has a comma-separated
    clause structure, swap the first two clauses. Cheap, no API calls,
    useful as a default/example — real coverage needs domain perturbers."""

    name = "reorder_clauses"

    def __call__(self, example: dict[str, Any]) -> Perturbation:
        perturbed = dict(example)
        for key, value in example.items():
            if isinstance(value, str) and "," in value:
                parts = value.split(",", 1)
                if len(parts) == 2:
                    perturbed[key] = f"{parts[1].strip()}, {parts[0].strip()}"
                    break
        return Perturbation(original=example, perturbed=perturbed, perturbation_type=self.name)


class InjectDistractorSentencePerturber:
    """Appends an unrelated, clearly-irrelevant sentence to any text field,
    to test whether the program is distracted by irrelevant context."""

    name = "inject_distractor"
    _DISTRACTORS: ClassVar[list[str]] = [
        "The weather in the office was mild that day.",
        "Unrelated note: the printer on the third floor was out of toner.",
        "For reference, the meeting had been rescheduled twice before.",
    ]

    def __call__(self, example: dict[str, Any]) -> Perturbation:
        perturbed = dict(example)
        for key, value in example.items():
            if isinstance(value, str) and len(value) > 0:
                distractor = random.choice(self._DISTRACTORS)
                perturbed[key] = f"{value} {distractor}"
                break
        return Perturbation(original=example, perturbed=perturbed, perturbation_type=self.name)


DEFAULT_PERTURBERS: list[Perturber] = [
    ReorderClausesPerturber(),
    InjectDistractorSentencePerturber(),
]


def generate_perturbations(
    trainset: list[dict[str, Any]],
    perturbers: list[Perturber] | None = None,
) -> list[Perturbation]:
    perturbers = perturbers or DEFAULT_PERTURBERS
    results: list[Perturbation] = []
    for example in trainset:
        for perturber in perturbers:
            results.append(perturber(example))
    return results
