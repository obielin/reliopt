"""
Contracts — hard/soft behavioral requirements a compiled program must satisfy.

A Contract is NOT the same thing as an Objective:
  - an Objective is something you want MORE or LESS of (a dial)
  - a Contract is a requirement a candidate either satisfies or violates
    (a gate). Candidates that violate a `strict=True` contract are excluded
    from the Pareto frontier entirely, regardless of how well they score on
    objectives.

Note on prior art (be upfront about this in docs/marketing): DSPy already has
`dspy.Assert`/`dspy.Suggest` for per-output constraints enforced via
backtracking/self-refinement. Contracts here serve a different purpose — they
gate *candidates* at evaluation/compile time across a whole trainset, feeding
the Pareto filter, rather than triggering retries within a single inference
call. The two are complementary: a dspy.Module using Assertions internally can
still be wrapped in a Program and scored against Contracts here.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any


@dataclass
class ContractResult:
    contract_name: str
    satisfied: bool
    observed_value: float | None = None
    threshold: float | None = None
    detail: str = ""


class Contract:
    """
    Base class. Most users should use the built-in factory methods below
    (Contract.groundedness(...), Contract.schema_valid(), etc.) rather than
    subclassing directly — but subclassing is the extension point for
    domain-specific contracts.
    """

    def __init__(
        self,
        name: str,
        check: Callable[[list[dict[str, Any]]], ContractResult],
        *,
        strict: bool = True,
    ):
        self.name = name
        self._check = check
        self.strict = strict

    def evaluate(self, run_records: list[dict[str, Any]]) -> ContractResult:
        """
        run_records: list of {"input":..., "output":..., "trajectory":...,
        "expected":...} dicts produced by the compiler for one candidate
        across the trainset.
        """
        return self._check(run_records)

    # -- built-in factories --------------------------------------------------

    @staticmethod
    def groundedness(minimum: float, *, strict: bool = True) -> Contract:
        """
        Placeholder scorer: expects each run_record to optionally carry a
        precomputed `record["groundedness_score"]` (e.g. from a retrieval
        overlap or NLI-based checker). Wire in a real scorer before relying
        on this — see CONTRIBUTING.md "Adding a contract scorer".
        """

        def _check(records: list[dict[str, Any]]) -> ContractResult:
            scores: list[float] = [
                v for r in records if (v := r.get("groundedness_score")) is not None
            ]
            if not scores:
                return ContractResult(
                    "groundedness", satisfied=False, detail="no groundedness_score found on any run record"
                )
            mean_score = sum(scores) / len(scores)
            return ContractResult(
                "groundedness",
                satisfied=mean_score >= minimum,
                observed_value=mean_score,
                threshold=minimum,
            )

        return Contract(f"groundedness>={minimum}", _check, strict=strict)

    @staticmethod
    def schema_valid(*, strict: bool = True) -> Contract:
        """Expects each output to be a dict/pydantic model; flags raw parse failures."""

        def _check(records: list[dict[str, Any]]) -> ContractResult:
            failures = sum(1 for r in records if r.get("schema_error"))
            satisfied = failures == 0
            return ContractResult(
                "schema_valid",
                satisfied=satisfied,
                observed_value=1 - (failures / len(records)) if records else 0,
                detail=f"{failures}/{len(records)} outputs failed schema validation",
            )

        return Contract("schema_valid", _check, strict=strict)

    @staticmethod
    def tool_scope(expected: list[str], *, strict: bool = True) -> Contract:
        """Flags any run whose trajectory used a tool outside `expected`."""

        def _check(records: list[dict[str, Any]]) -> ContractResult:
            violations = 0
            for r in records:
                used = set(r.get("tools_used", []))
                if not used.issubset(set(expected)):
                    violations += 1
            satisfied = violations == 0
            return ContractResult(
                "tool_scope",
                satisfied=satisfied,
                observed_value=1 - (violations / len(records)) if records else 0,
                detail=f"{violations}/{len(records)} runs used out-of-scope tools",
            )

        return Contract("tool_scope", _check, strict=strict)

    @staticmethod
    def wilson_lower_bound(
        successes_field: str,
        minimum: float,
        *,
        confidence: float = 0.95,
        strict: bool = True,
    ) -> Contract:
        """
        Gates on the lower bound of the Wilson score interval for a boolean
        success-rate field, rather than the raw observed proportion.

        Expects each run_record to optionally carry `record[successes_field]`
        as a bool (True = success). Records where the field is missing/None
        are excluded from the sample. A raw proportion (e.g. 9/10) can look
        good but be statistically unreliable at small sample sizes — the
        Wilson lower bound accounts for that, so a `strict=True` candidate
        can't clear the bar on a lucky small sample the way it could on the
        point estimate alone.
        """
        if not (0.0 < confidence < 1.0):
            raise ValueError(f"confidence must be in (0, 1), got {confidence}")

        z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
        result_name = f"wilson_lower_bound({successes_field})"

        def _check(records: list[dict[str, Any]]) -> ContractResult:
            outcomes = [bool(r[successes_field]) for r in records if r.get(successes_field) is not None]
            n = len(outcomes)
            if n == 0:
                return ContractResult(
                    result_name, satisfied=False, detail=f"no '{successes_field}' found on any run record"
                )

            successes = sum(outcomes)
            p_hat = successes / n
            z2 = z * z
            denom = 1 + z2 / n
            center = p_hat + z2 / (2 * n)
            margin = z * math.sqrt((p_hat * (1 - p_hat) / n) + (z2 / (4 * n * n)))
            lower_bound = (center - margin) / denom

            return ContractResult(
                result_name,
                satisfied=lower_bound >= minimum,
                observed_value=lower_bound,
                threshold=minimum,
                detail=f"{successes}/{n} successes, {confidence:.0%} Wilson lower bound={lower_bound:.4f}",
            )

        return Contract(f"{result_name}>={minimum}", _check, strict=strict)

    @staticmethod
    def abstain_when_unsupported(*, strict: bool = True) -> Contract:
        """
        Expects a `record["should_abstain"]` (ground truth) and
        `record["abstained"]` (what the program did) pair.

        Gates on the Wilson lower bound of the correct-abstention rate (see
        `wilson_lower_bound`), not the raw observed rate — a small sample can
        clear 0.9 on a lucky run without abstention actually being reliable.
        """

        def _check(records: list[dict[str, Any]]) -> ContractResult:
            relevant = [r for r in records if r.get("should_abstain") is not None]
            if not relevant:
                return ContractResult("abstain_when_unsupported", satisfied=True, detail="no applicable records")

            derived = [{"_correct": r.get("should_abstain") == r.get("abstained")} for r in relevant]
            inner = Contract.wilson_lower_bound("_correct", minimum=0.9).evaluate(derived)
            return ContractResult(
                "abstain_when_unsupported",
                satisfied=inner.satisfied,
                observed_value=inner.observed_value,
                threshold=inner.threshold,
                detail=inner.detail,
            )

        return Contract("abstain_when_unsupported", _check, strict=strict)
