"""
Compiler(attribution=...): the opt-in wiring from the normal
compile() -> select() -> evidence_card() flow into run_attribution().

Covers the three states a candidate can end up in:
  - attribution=False (default): nothing populated, nothing computed.
  - attribution=True, program wraps a Pipeline: attribution_results populated,
    matching a direct run_attribution() call over the same pipeline.
  - attribution=True, program does NOT wrap a Pipeline: attribution_skipped_reason
    explains why, rather than a silently empty result.

Also checks EvidenceCard.render() actually prints real attribution data, not
just that the field got populated.
"""

from __future__ import annotations

from reliopt import Objective, Program
from reliopt.attribution import PipelineAblator, run_attribution
from reliopt.compiler.engine import Compiler
from reliopt.pipeline import Pipeline

TRAINSET = [{"n": 3, "expected": 7}]


def _step1(n: int) -> int:
    return n * 2


def _step2(value: object) -> int:
    # Defensive against an ablated step1 handing us a dict instead of a
    # number (see reliopt.pipeline.passthrough) — mirrors the pattern in
    # examples/attribution_demo.py.
    if not isinstance(value, (int, float)):
        return -1
    return int(value) + 1


def _make_pipeline() -> Pipeline:
    return Pipeline([("step1", _step1), ("step2", _step2)])


def test_attribution_false_by_default_populates_nothing():
    program = Program(_make_pipeline(), name="toy_pipeline")
    program.objectives(Objective.accuracy())
    compiler = Compiler(program=program, contracts=[], objectives=program._objectives)

    result = compiler.run(trainset=TRAINSET)
    candidate = result.candidates[0]

    assert candidate.attribution_results is None
    assert candidate.attribution_skipped_reason is None

    card = result.evidence_card(candidate.id)
    assert card.attribution == {}
    assert card.attribution_skipped_reason == ""
    assert "component attribution" not in card.render()


def test_attribution_true_with_pipeline_matches_direct_run_attribution():
    pipeline = _make_pipeline()
    program = Program(pipeline, name="toy_pipeline")
    program.objectives(Objective.accuracy())
    compiler = Compiler(program=program, contracts=[], objectives=program._objectives, attribution=True)

    result = compiler.run(trainset=TRAINSET)
    candidate = result.candidates[0]

    assert candidate.attribution_skipped_reason is None
    assert candidate.attribution_results is not None

    def evaluate_fn(p: Pipeline) -> dict[str, float]:
        wrapped = Program(p, name="toy_pipeline")
        records = compiler._evaluate_candidate(wrapped, TRAINSET, [])
        return {"accuracy": Objective.accuracy().evaluate(records).value}

    expected_results = run_attribution(program=pipeline, ablator=PipelineAblator(), evaluate_fn=evaluate_fn)

    assert [r.component for r in candidate.attribution_results] == [r.component for r in expected_results]
    for actual, expected in zip(candidate.attribution_results, expected_results, strict=True):
        assert actual.component == expected.component
        assert actual.deltas == expected.deltas

    # Sanity on the actual numbers, not just "it matches some other call":
    # ablating either step breaks the n=3 -> 7 chain entirely.
    by_component = {r.component: r.deltas for r in candidate.attribution_results}
    assert by_component["step1"]["accuracy"] == 1.0
    assert by_component["step2"]["accuracy"] == 1.0

    card = result.evidence_card(candidate.id)
    assert card.attribution == {r.component: r.deltas for r in expected_results}
    assert card.attribution_skipped_reason == ""

    rendered = card.render()
    assert "component attribution:" in rendered
    assert f"    {'step1':<20} accuracy: +1.000" in rendered
    assert f"    {'step2':<20} accuracy: +1.000" in rendered


def test_attribution_true_with_non_pipeline_sets_skipped_reason_not_silent_empty():
    def toy(question: str) -> str:
        return question

    program = Program(toy, name="toy")
    program.objectives(Objective.accuracy())
    compiler = Compiler(program=program, contracts=[], objectives=program._objectives, attribution=True)

    result = compiler.run(trainset=[{"question": "q", "expected": "q"}])
    candidate = result.candidates[0]

    assert candidate.attribution_results is None
    assert candidate.attribution_skipped_reason is not None
    assert "Pipeline" in candidate.attribution_skipped_reason

    card = result.evidence_card(candidate.id)
    assert card.attribution == {}
    assert card.attribution_skipped_reason == candidate.attribution_skipped_reason
    assert "skipped" in card.render().lower()
