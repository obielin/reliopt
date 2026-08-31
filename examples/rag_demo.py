"""
Runnable demo: a toy RAG-style program, compiled against a groundedness
contract and accuracy/cost/latency objectives, across a small config space.

This mirrors the worked example from the project's design doc:

    17 candidate programs tested
    4 rejected for contract violations
    Pareto-optimal candidates: 3

Run with:  python examples/rag_demo.py

Note: this uses a fake, deterministic "retriever" and "answerer" so the demo
runs with zero API calls/cost — swap `fake_rag` for a real retrieval+LM
pipeline (or a dspy.Module) to see this against a real program. See
README.md Quick start for the wrapping pattern.
"""

from __future__ import annotations

import random

from reliopt import Contract, Objective, Program
from reliopt.compiler.engine import Compiler

# A small fake knowledge base so groundedness has something real to check against.
KNOWLEDGE_BASE = {
    "capital of france": "Paris is the capital of France.",
    "capital of germany": "Berlin is the capital of Germany.",
    "capital of japan": "Tokyo is the capital of Japan.",
}


def fake_rag(question: str, top_k: int = 1, model: str = "small") -> str:
    """
    Deterministic stand-in for a RAG pipeline. `top_k` and `model` are the
    "configuration" knobs the compiler searches over — in a real program
    these would change retriever depth / which LLM answers.
    """
    key = next((k for k in KNOWLEDGE_BASE if k in question.lower()), None)
    if key is None:
        return "I don't know."
    retrieved = KNOWLEDGE_BASE[key]
    if model == "small" and top_k == 1:
        # Simulates a cheap model occasionally dropping the grounding detail.
        return retrieved.split(" is ")[0] if random.random() < 0.2 else retrieved
    return retrieved


def configure(program: Program, config: dict) -> Program:
    return Program(
        lambda question: fake_rag(question, top_k=config.get("top_k", 1), model=config.get("model", "small")),
        name="fake_rag",
    )


def enrich_with_groundedness(record: dict) -> dict:
    """Post-hoc groundedness scorer: did the output retain the retrieved
    sentence's grounding detail ('is the capital of')? In a real system this
    would be an NLI/overlap-based checker — see CONTRIBUTING.md 'Adding a
    contract scorer'. Wired in via Compiler(enrich_fn=...)."""
    output = record.get("output") or ""
    record["groundedness_score"] = 1.0 if "is the capital of" in output else 0.4
    return record


def main() -> None:
    random.seed(7)  # reproducible demo output

    program = Program(fake_rag)
    program.contracts(Contract.groundedness(minimum=0.90))
    program.objectives(
        Objective.accuracy(),
        Objective.cost(minimise=True),
        Objective.latency(minimise=True),
    )

    trainset = [
        {"question": "What is the capital of France?", "expected": "Paris is the capital of France."},
        {"question": "What is the capital of Germany?", "expected": "Berlin is the capital of Germany."},
        {"question": "What is the capital of Japan?", "expected": "Tokyo is the capital of Japan."},
    ]

    compiler = Compiler(
        program=program,
        contracts=program._contracts,
        objectives=program._objectives,
        config_space={"top_k": [1, 2, 3], "model": ["small", "large"]},
        configure_fn=configure,
        repeat_n=5,  # repeat each example to let groundedness variance show up
        enrich_fn=enrich_with_groundedness,
    )

    result = compiler.run(trainset=trainset)

    print(f"{len(result.candidates)} candidate programs tested")
    frontier = result.pareto_frontier()
    rejected = len(result.candidates) - len(frontier)
    print(f"{rejected} rejected for contract violations")
    print(f"Pareto-optimal candidates: {len(frontier)}\n")

    print(result.render_table())
    print()

    if frontier:
        best = result.select("balanced")
        print("Evidence card for 'balanced' pick:")
        print(result.evidence_card(best.id).render())


if __name__ == "__main__":
    main()
