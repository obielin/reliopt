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

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ContractResult:
    contract_name: str
    satisfied: bool
    observed_value: Optional[float] = None
    threshold: Optional[float] = None
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
    def groundedness(minimum: float, *, strict: bool = True) -> "Contract":
        """
        Placeholder scorer: expects each run_record to optionally carry a
        precomputed `record["groundedness_score"]` (e.g. from a retrieval
        overlap or NLI-based checker). Wire in a real scorer before relying
        on this — see CONTRIBUTING.md "Adding a contract scorer".
        """

        def _check(records: list[dict[str, Any]]) -> ContractResult:
            scores = [r.get("groundedness_score") for r in records if r.get("groundedness_score") is not None]
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
    def schema_valid(*, strict: bool = True) -> "Contract":
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
    def tool_scope(expected: list[str], *, strict: bool = True) -> "Contract":
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
    def abstain_when_unsupported(*, strict: bool = True) -> "Contract":
        """
        Expects a `record["should_abstain"]` (ground truth) and
        `record["abstained"]` (what the program did) pair.
        """

        def _check(records: list[dict[str, Any]]) -> ContractResult:
            relevant = [r for r in records if r.get("should_abstain") is not None]
            if not relevant:
                return ContractResult("abstain_when_unsupported", satisfied=True, detail="no applicable records")
            correct = sum(1 for r in relevant if r.get("should_abstain") == r.get("abstained"))
            rate = correct / len(relevant)
            return ContractResult(
                "abstain_when_unsupported",
                satisfied=rate >= 0.9,
                observed_value=rate,
                threshold=0.9,
            )

        return Contract("abstain_when_unsupported", _check, strict=strict)
