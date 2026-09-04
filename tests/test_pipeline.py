"""
Pipeline primitive: a sequence of named steps where each step's output feeds
the next. These tests pin the calling convention (first step gets kwargs, later
steps get the previous return value positionally) and the structural
guarantees PipelineAblator relies on (unique ordered names).
"""

import pytest

from reliopt import Program
from reliopt.pipeline import Pipeline, passthrough


def _three_step_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("retrieve", lambda question: [f"doc about {question}", "distractor doc"]),
            ("rerank", lambda docs: [d for d in docs if "about" in d]),
            ("generate", lambda docs: f"answer: {docs[0]}"),
        ]
    )


def test_pipeline_runs_three_step_sequence_in_order():
    pipe = _three_step_pipeline()
    assert pipe(question="capital of France") == "answer: doc about capital of France"


def test_pipeline_is_callable_through_program():
    pipe = _three_step_pipeline()
    program = Program(pipe, name="rag_pipeline")
    run = program.run(question="capital of France")
    assert run.error is None
    assert run.output == "answer: doc about capital of France"


def test_pipeline_names_are_ordered():
    assert _three_step_pipeline().names == ["retrieve", "rerank", "generate"]


def test_pipeline_rejects_empty_steps():
    with pytest.raises(ValueError, match="at least one step"):
        Pipeline([])


def test_pipeline_rejects_duplicate_names():
    with pytest.raises(ValueError, match="unique"):
        Pipeline([("a", lambda x: x), ("a", lambda x: x)])


def test_pipeline_rejects_non_callable_step():
    with pytest.raises(TypeError, match="not callable"):
        Pipeline([("a", "not a function")])


def test_passthrough_returns_single_value_unchanged():
    assert passthrough(42) == 42
    assert passthrough(question="q") == {"question": "q"}
    sentinel = object()
    assert passthrough(sentinel) is sentinel
