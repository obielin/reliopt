"""
reliopt — a framework for reliability-constrained, multi-objective
optimization of LLM and agent programs.

Core thesis: the best AI program isn't the one with the highest task score.
It's the one that satisfies its behavioral contracts while achieving the best
defensible trade-off between quality, robustness, cost, and efficiency.

    from reliopt import Program, Contract, Objective

    program = Program(my_rag_agent)  # wraps any callable, dspy.Module, etc.

    program.contracts(
        Contract.groundedness(minimum=0.90),
        Contract.schema_valid(),
    )

    program.objectives(
        Objective.accuracy(maximise=True),
        Objective.cost(minimise=True),
    )

    result = program.compile(trainset=data)
    print(result.pareto_frontier())
    print(result.evidence_card())
"""

from reliopt.compiler.result import CompileResult, EvidenceCard
from reliopt.contracts.base import Contract
from reliopt.objectives.base import Objective
from reliopt.program import Program

__all__ = [
    "CompileResult",
    "Contract",
    "EvidenceCard",
    "Objective",
    "Program",
]

__version__ = "0.1.0-dev"
