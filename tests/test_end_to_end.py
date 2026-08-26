"""
End-to-end test: a toy program, compiled with contracts + objectives across
a small config space, should produce a Pareto frontier and evidence cards
without erroring. This is the "does the whole pipeline actually run" smoke
test — not a claim that any of the scoring logic is production-grade yet.
"""

from reliopt import Program, Contract, Objective


def toy_answerer(question: str, verbosity: int = 1) -> str:
    """A deliberately trivial 'program': verbosity=2 pads the answer,
    simulating a config knob that trades cost/latency for... nothing useful,
    so we can see the Pareto frontier correctly reject it on cost without
    a compensating accuracy gain."""
    answer = "Paris" if "capital of France" in question else "unknown"
    if verbosity == 2:
        answer = f"{answer} (padded with extra reasoning tokens for no benefit)"
    return answer


def configure_verbosity(program: Program, config: dict) -> Program:
    verbosity = config.get("verbosity", 1)
    wrapped = Program(lambda question: toy_answerer(question, verbosity=verbosity), name="toy_answerer")
    return wrapped


def test_full_compile_loop_produces_pareto_frontier():
    program = Program(toy_answerer)
    program.contracts(Contract.schema_valid(strict=False))  # lenient - toy program returns raw strings
    program.objectives(
        Objective.accuracy(),
        Objective.latency(),
    )

    trainset = [
        {"question": "What is the capital of France?", "expected": "Paris"},
        {"question": "What is the capital of Germany?", "expected": "unknown"},
    ]

    from reliopt.compiler.engine import Compiler

    compiler = Compiler(
        program=program,
        contracts=program._contracts,
        objectives=program._objectives,
        config_space={"verbosity": [1, 2]},
        configure_fn=configure_verbosity,
    )
    result = compiler.run(trainset=trainset)

    assert len(result.candidates) == 2
    frontier = result.pareto_frontier()
    assert len(frontier) >= 1

    card = result.evidence_card(result.candidates[0].id)
    rendered = card.render()
    assert "candidate_0" in rendered.lower() or "Candidate" in rendered


def test_contract_rejects_violating_candidate():
    def bad_program(question: str) -> str:
        return "not json"  # will fail our strict schema contract below

    program = Program(bad_program)
    program.contracts(Contract.schema_valid(strict=True))
    program.objectives(Objective.accuracy())

    # Force a schema_error on every record via a custom contract check for this test
    from reliopt.contracts.base import Contract as C

    def _always_fails(records):
        from reliopt.contracts.base import ContractResult

        return ContractResult("always_fails", satisfied=False, detail="forced failure for test")

    strict_contract = C("always_fails", _always_fails, strict=True)

    result = program.compile(trainset=[{"question": "x", "expected": "y"}])
    # Manually re-run with the forced-failing contract to test rejection behaviour
    from reliopt.compiler.engine import Compiler

    compiler = Compiler(program=program, contracts=[strict_contract], objectives=program._objectives)
    result = compiler.run(trainset=[{"question": "x", "expected": "y"}])

    frontier = result.pareto_frontier()
    assert frontier == [], "candidate violating a strict contract must be excluded from the frontier"
