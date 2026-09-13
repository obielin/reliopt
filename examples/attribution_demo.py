"""
Runnable demo: native component attribution over a 3-step Pipeline.

A toy retrieve -> rerank -> generate pipeline (all fake and deterministic, zero
API calls) is run through `run_attribution()` with `PipelineAblator`. Each step
is zero-ablated in turn — replaced by a passthrough that returns its input
unchanged — and re-evaluated over a small trainset. The printed deltas
(full-program score minus zero-ablated score) attribute the observed accuracy
and groundedness to specific steps.

Run with:  python examples/attribution_demo.py

Expected shape of the output:
  - ablating `retrieve` costs accuracy *and* groundedness — nothing reaches
    `generate` but the raw question string;
  - ablating `rerank` costs accuracy only — the wrong-but-still-grounded
    near-miss doc ends up on top, so the answer is a real KB fact, just not
    the right one;
  - ablating `generate` costs accuracy *and* groundedness — the retrieval
    state dict is returned instead of an answer string.
"""

from __future__ import annotations

from reliopt import Objective, Program
from reliopt.attribution import PipelineAblator, run_attribution
from reliopt.compiler.engine import Compiler
from reliopt.pipeline import Pipeline

# A tiny fake knowledge base so "groundedness" has something real to check.
KNOWLEDGE_BASE = {
    "france": "Paris is the capital of France.",
    "germany": "Berlin is the capital of Germany.",
    "japan": "Tokyo is the capital of Japan.",
}
GROUNDED_FACTS = set(KNOWLEDGE_BASE.values())


def _topic(question: str) -> str | None:
    return next((k for k in KNOWLEDGE_BASE if k in question.lower()), None)


def retrieve(question: str) -> dict:
    """Fake retriever: return the answer sentence *and* a plausible-but-wrong
    grounded fact from another entry, with the near-miss listed first so
    reranking has real work to do."""
    q = question if isinstance(question, str) else str(question)
    topic = _topic(q)
    answer = KNOWLEDGE_BASE.get(topic or "")
    near_miss = next((v for k, v in KNOWLEDGE_BASE.items() if k != topic), None)
    docs = [d for d in (near_miss, answer) if d]
    return {"question": q, "docs": docs}


def rerank(state: dict) -> dict:
    """Fake reranker: float the doc that names the question's country to the
    top. Tolerates an ablated upstream step: `retrieve` zero-ablated returns
    `{"question": ...}` with no "docs" key (a dict, but not the shape this
    step expects), so check for the key too, not just the type."""
    if not isinstance(state, dict) or "docs" not in state:
        return state
    country = (_topic(state.get("question", "")) or "").capitalize()
    docs = sorted(state["docs"], key=lambda d: 0 if country and country in d else 1)
    return {**state, "docs": docs}


def generate(state: dict) -> str:
    """Fake generator: answer with the top-ranked doc. Tolerates an ablated
    upstream step (non-dict input)."""
    if not isinstance(state, dict):
        return str(state)
    return state["docs"][0] if state.get("docs") else "I don't know."


TRAINSET = [
    {"question": "What is the capital of France?", "expected": "Paris is the capital of France."},
    {"question": "What is the capital of Germany?", "expected": "Berlin is the capital of Germany."},
    {"question": "What is the capital of Japan?", "expected": "Tokyo is the capital of Japan."},
]


def evaluate(program) -> dict[str, float]:
    """The `evaluate_fn` `run_attribution` expects: given a (possibly ablated)
    program, return {objective_name: score}. In real usage this would be a thin
    wrapper around Compiler._evaluate_candidate + Objective.evaluate."""
    outputs = [program(question=ex["question"]) for ex in TRAINSET]
    correct = sum(1 for out, ex in zip(outputs, TRAINSET, strict=True) if out == ex["expected"])
    grounded = sum(1 for out in outputs if isinstance(out, str) and out in GROUNDED_FACTS)
    n = len(TRAINSET)
    return {"accuracy": correct / n, "groundedness": grounded / n}


def main() -> None:
    pipeline = Pipeline(
        [
            ("retrieve", retrieve),
            ("rerank", rerank),
            ("generate", generate),
        ]
    )

    baseline = evaluate(pipeline)
    print("Baseline (full pipeline):")
    for name, value in baseline.items():
        print(f"  {name:<13} {value:.2f}")
    print()

    results = run_attribution(program=pipeline, ablator=PipelineAblator(), evaluate_fn=evaluate)

    print("Attribution — delta = full-program score minus zero-ablated score")
    print("(positive delta => that step was contributing to the score)\n")
    header = f"  {'component':<12}" + "".join(f"{k:>15}" for k in baseline)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for result in results:
        row = f"  {result.component:<12}" + "".join(f"{result.deltas[k]:>+15.2f}" for k in baseline)
        print(row)

    print()
    print("=" * 70)
    print("Same pipeline, reached the normal way: compile(attribution=True)")
    print("=" * 70)
    print()
    demo_wired_through_compiler(pipeline)


def demo_wired_through_compiler(pipeline: Pipeline) -> None:
    """
    Everything above called `run_attribution()` directly. This shows the
    same attribution reached through the ordinary
    compile() -> select() -> evidence_card() path, via
    `Compiler(attribution=True)` (opt-in, default off — see
    compiler/engine.py). No contracts here, just enough objectives to have
    something for the Evidence Card to report.
    """
    program = Program(pipeline, name="rag_pipeline")
    program.objectives(Objective.accuracy())

    compiler = Compiler(
        program=program,
        contracts=[],
        objectives=program._objectives,
        attribution=True,
    )
    result = compiler.run(trainset=TRAINSET)

    # Single candidate here (no config_space given) — attribution_results is
    # populated because `program.target` is a Pipeline; a plain-callable
    # Program would instead get `attribution_skipped_reason` set. See
    # tests/test_compiler_attribution.py for both cases.
    candidate = result.candidates[0]
    assert candidate.attribution_results is not None, "expected attribution to run for a Pipeline candidate"

    print(result.evidence_card(candidate.id).render())


if __name__ == "__main__":
    main()
