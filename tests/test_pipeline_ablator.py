"""
PipelineAblator: the first concrete ComponentAblator. Verifies component
enumeration, zero-ablation semantics (named step -> passthrough, other steps
untouched), non-mutation of the original, and that a non-Pipeline program is a
hard TypeError rather than a silent empty result.
"""

import pytest

from reliopt import Program
from reliopt.attribution import PipelineAblator, run_attribution
from reliopt.pipeline import Pipeline, passthrough

CALLS: list[str] = []


def _tracing_pipeline() -> Pipeline:
    CALLS.clear()

    def retrieve(question):
        CALLS.append("retrieve")
        return f"[docs for {question}]"

    def rerank(docs):
        CALLS.append("rerank")
        return f"{docs}+reranked"

    def generate(docs):
        CALLS.append("generate")
        return f"{docs}=>answer"

    return Pipeline([("retrieve", retrieve), ("rerank", rerank), ("generate", generate)])


def test_components_returns_step_names_in_order():
    ablator = PipelineAblator()
    assert ablator.components(_tracing_pipeline()) == ["retrieve", "rerank", "generate"]


def test_components_raises_typeerror_on_non_pipeline():
    ablator = PipelineAblator()
    with pytest.raises(TypeError, match="Pipeline"):
        ablator.components(Program(lambda question: question))

    with pytest.raises(TypeError):
        ablator.components(lambda question: question)


def test_ablate_middle_step_passes_through_and_leaves_others_untouched():
    pipe = _tracing_pipeline()
    ablator = PipelineAblator()
    ablated = ablator.ablate(pipe, "rerank")

    # The ablated step is now the passthrough; the neighbours are the originals.
    assert dict(ablated.steps)["rerank"] is passthrough
    assert dict(ablated.steps)["retrieve"] is dict(pipe.steps)["retrieve"]
    assert dict(ablated.steps)["generate"] is dict(pipe.steps)["generate"]

    # Running it: retrieve + generate still execute, rerank does not, and its
    # output is passed straight through unchanged.
    result = ablated(question="q")
    assert CALLS == ["retrieve", "generate"]
    assert result == "[docs for q]=>answer"  # no "+reranked"


def test_ablate_does_not_mutate_original():
    pipe = _tracing_pipeline()
    original_steps = list(pipe.steps)
    PipelineAblator().ablate(pipe, "retrieve")
    assert pipe.steps == original_steps
    assert pipe(question="q") == "[docs for q]+reranked=>answer"


def test_ablate_raises_typeerror_on_non_pipeline():
    with pytest.raises(TypeError, match="Pipeline"):
        PipelineAblator().ablate(Program(lambda question: question), "retrieve")


def test_ablate_raises_valueerror_on_unknown_component():
    with pytest.raises(ValueError, match="Unknown component"):
        PipelineAblator().ablate(_tracing_pipeline(), "nope")


def test_run_attribution_end_to_end_over_pipeline():
    pipe = _tracing_pipeline()

    def evaluate_fn(program):
        output = program(question="q")
        return {
            "has_docs": 1.0 if "docs for q" in output else 0.0,
            "has_rerank": 1.0 if "+reranked" in output else 0.0,
            "has_answer": 1.0 if "=>answer" in output else 0.0,
        }

    results = run_attribution(program=pipe, ablator=PipelineAblator(), evaluate_fn=evaluate_fn)

    assert [r.component for r in results] == ["retrieve", "rerank", "generate"]
    by_component = {r.component: r.deltas for r in results}
    # Ablating rerank should drop only the rerank signal.
    assert by_component["rerank"]["has_rerank"] == 1.0
    assert by_component["rerank"]["has_answer"] == 0.0
