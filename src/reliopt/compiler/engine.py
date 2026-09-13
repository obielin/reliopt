"""
Compiler — orchestrates the full compile loop:

    for each candidate configuration:
        run program (as configured) over trainset + perturbations
        score objectives
        evaluate contracts
        (opt-in) run component attribution — see `attribution` field below
    return CompileResult (Pareto frontier + evidence cards)

v0.1 search strategy: grid/explicit search over a user-supplied
`config_space` (a dict of param name -> list of values) or an explicit
`candidates` list of config dicts, applied to the wrapped Program via a
`configure_fn(program, config) -> Program`. This is deliberately NOT yet
DSPy-style automatic prompt/demonstration optimization — plugging in a
smarter search strategy (bayesian, evolutionary, or DSPy-optimizer-backed)
is the natural v0.2 extension point; see ARCHITECTURE.md and
CONTRIBUTING.md "Adding a search strategy". Shipping *some* automated search
now (rather than manual-only) was a deliberate scope decision — see
project history in this repo's CHANGELOG.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from reliopt.attribution.engine import AttributionResult, run_attribution
from reliopt.attribution.pipeline_ablator import PipelineAblator
from reliopt.compiler.pareto import Candidate
from reliopt.compiler.result import CompileResult
from reliopt.contracts.base import Contract
from reliopt.objectives.base import Objective
from reliopt.perturbation.engine import Perturber, generate_perturbations
from reliopt.pipeline import Pipeline
from reliopt.program import Program

ConfigureFn = Callable[[Any, dict[str, Any]], Any]


def _default_configure_fn(program: Any, config: dict[str, Any]) -> Any:
    """No-op default: returns the program unchanged. Real usage should pass
    a configure_fn that applies `config` (e.g. model name, temperature,
    retriever top_k) to a fresh copy of the program."""
    return program


@dataclass
class Compiler:
    program: Any  # reliopt.program.Program
    contracts: list[Contract]
    objectives: list[Objective]
    config_space: dict[str, list[Any]] | None = None
    candidates: list[dict[str, Any]] | None = None
    configure_fn: ConfigureFn = _default_configure_fn
    perturbers: list[Perturber] | None = None
    repeat_n: int = 1
    max_candidates: int = 25
    enrich_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    """
    Optional hook run on each record right after execution, before contracts/
    objectives see it. Use this to populate domain-specific fields that
    built-in contracts expect but can't compute themselves — e.g.
    `groundedness_score`, `schema_error`, `tools_used`, `should_abstain`/
    `abstained`. Without this, Contract.groundedness()/schema_valid()/
    tool_scope() will find no data and correctly report unsatisfied rather
    than silently passing — see contracts/base.py docstrings.
    """
    attribution: bool = False
    """
    Opt-in, default OFF. When True, run component attribution for every
    candidate whose configured program wraps a `Pipeline` (see pipeline.py
    and attribution/pipeline_ablator.py) — the only `ComponentAblator`
    implementation today. This is never turned on silently: it's roughly
    "one extra full evaluation per ablatable component" on top of normal
    candidate scoring (see attribution/engine.py), so defaulting it on would
    silently multiply compute cost across every candidate in the search.
    A candidate whose program isn't a `Pipeline` is not silently skipped
    either — see `Candidate.attribution_skipped_reason`.
    """

    def _candidate_configs(self) -> list[dict[str, Any]]:
        if self.candidates is not None:
            return self.candidates
        if self.config_space:
            keys = list(self.config_space.keys())
            combos = list(itertools.product(*(self.config_space[k] for k in keys)))
            configs = [dict(zip(keys, combo, strict=True)) for combo in combos]
            return configs[: self.max_candidates]
        # No search space given: single candidate = program as-is.
        return [{}]

    def run(self, *, trainset: list[dict[str, Any]]) -> CompileResult:
        perturbations = generate_perturbations(trainset, self.perturbers) if self.perturbers is not None else []
        candidate_results: list[Candidate] = []

        for i, config in enumerate(self._candidate_configs()):
            configured_program = self.configure_fn(self.program, config)
            run_records = self._evaluate_candidate(configured_program, trainset, perturbations)

            objective_scores = [obj.evaluate(run_records) for obj in self.objectives]
            contract_results = [contract.evaluate(run_records) for contract in self.contracts]

            attribution_results: list[AttributionResult] | None = None
            attribution_skipped_reason: str | None = None
            if self.attribution:
                attribution_results, attribution_skipped_reason = self._attribution_for_candidate(
                    configured_program, trainset
                )

            candidate_results.append(
                Candidate(
                    id=f"candidate_{i}",
                    config=config,
                    objective_scores=objective_scores,
                    contract_results=contract_results,
                    attribution_results=attribution_results,
                    attribution_skipped_reason=attribution_skipped_reason,
                )
            )

        return CompileResult(candidates=candidate_results)

    def _attribution_for_candidate(
        self, configured_program: Any, trainset: list[dict[str, Any]]
    ) -> tuple[list[AttributionResult] | None, str | None]:
        """
        Component attribution for one already-configured candidate. Only
        called when `attribution=True`. Returns
        `(attribution_results, attribution_skipped_reason)` — exactly one of
        the two is non-None, mirroring `Candidate`'s two fields.

        Ablation targets the `Pipeline` a candidate's `Program` wraps
        (`configured_program.target`), since `PipelineAblator` — currently
        the only `ComponentAblator` — enumerates and ablates `Pipeline` steps,
        not `Program` instances. A candidate that isn't `Program`-wrapping a
        `Pipeline` at all (e.g. a bare Pipeline, or a plain callable) is
        handled the same way via `getattr(..., "target", configured_program)`.
        """
        target = getattr(configured_program, "target", configured_program)
        if not isinstance(target, Pipeline):
            reason = (
                "attribution=True but this candidate's program is not a Pipeline "
                f"(got {type(target).__name__}); component attribution is only "
                "implemented for Pipeline-structured programs today — see "
                "attribution/pipeline_ablator.py."
            )
            return None, reason

        program_name = getattr(configured_program, "name", None)

        def evaluate_fn(pipeline: Pipeline) -> dict[str, float]:
            wrapped = Program(pipeline, name=program_name)
            # Nominal trainset only, no perturbations: run_attribution already
            # costs one extra full evaluation per ablatable component (see its
            # docstring) — running each of those against perturbations too
            # would compound that multiplier further, on top of what the
            # candidate's normal scoring above already pays.
            records = self._evaluate_candidate(wrapped, trainset, [])
            return {obj.name: obj.evaluate(records).value for obj in self.objectives}

        results = run_attribution(program=target, ablator=PipelineAblator(), evaluate_fn=evaluate_fn)
        return results, None

    def _evaluate_candidate(
        self,
        program: Any,
        trainset: list[dict[str, Any]],
        perturbations: list[Any],
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for example in trainset:
            record = self._run_one(program, example)
            records.append(record)

        for perturbation in perturbations:
            record = self._run_one(program, perturbation.perturbed)
            record["perturbation_type"] = perturbation.perturbation_type
            records.append(record)

        if self.enrich_fn is not None:
            records = [self.enrich_fn(r) for r in records]

        return records

    def _run_one(self, program: Any, example: dict[str, Any]) -> dict[str, Any]:
        expected = example.get("expected")
        run_input = {k: v for k, v in example.items() if k != "expected"}

        repeat_outputs = []
        primary_run = None
        for i in range(max(1, self.repeat_n)):
            run = program.run(**run_input)
            if i == 0:
                primary_run = run
            repeat_outputs.append(run.output)

        correct = None
        if expected is not None and primary_run is not None:
            correct = primary_run.output == expected

        return {
            "input": run_input,
            "expected": expected,
            "output": primary_run.output if primary_run else None,
            "trajectory": primary_run.trajectory if primary_run else None,
            "correct": correct,
            "repeat_outputs": repeat_outputs if self.repeat_n > 1 else [],
            "error": primary_run.error if primary_run else None,
        }
