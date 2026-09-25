import json

from reliopt.compiler.result import EvidenceCard


def test_evidence_card_to_dict_matches_known_fields():
    card = EvidenceCard(
        candidate_id="candidate_42",
        objective_summary={"accuracy": 0.95, "latency": 150.0},
        contract_summary={"groundedness": True, "schema_valid": False},
        rejected=True,
        rejection_reason="violated: schema_valid",
        attribution={"retriever": {"accuracy": 0.15}},
        attribution_skipped_reason="",
        failure_clusters={"contract:schema_valid": 3},
    )

    data = card.to_dict()

    expected = {
        "candidate_id": "candidate_42",
        "objective_summary": {"accuracy": 0.95, "latency": 150.0},
        "contract_summary": {"groundedness": True, "schema_valid": False},
        "rejected": True,
        "rejection_reason": "violated: schema_valid",
        "attribution": {"retriever": {"accuracy": 0.15}},
        "attribution_skipped_reason": "",
        "failure_clusters": {"contract:schema_valid": 3},
    }
    assert data == expected


def test_evidence_card_to_dict_is_json_serializable():
    card = EvidenceCard(
        candidate_id="candidate_0",
        objective_summary={"accuracy": 1.0, "cost": 0.002},
        contract_summary={"groundedness": True},
        rejected=False,
        rejection_reason="",
        attribution={"step1": {"accuracy": 0.5}},
        attribution_skipped_reason="",
        failure_clusters={},
    )

    data = card.to_dict()
    serialized = json.dumps(data)
    deserialized = json.loads(serialized)
    assert deserialized == data


def test_evidence_card_to_dict_with_skipped_attribution():
    card = EvidenceCard(
        candidate_id="candidate_1",
        objective_summary={"accuracy": 0.8},
        contract_summary={"groundedness": True},
        rejected=False,
        rejection_reason="",
        attribution={},
        attribution_skipped_reason="Pipeline required for component attribution",
        failure_clusters={},
    )

    data = card.to_dict()
    assert data["attribution"] == {}
    assert (
        data["attribution_skipped_reason"]
        == "Pipeline required for component attribution"
    )
    assert json.dumps(data)


def test_evidence_card_to_dict_mutation_safety():
    card = EvidenceCard(
        candidate_id="cand_test",
        objective_summary={"accuracy": 0.9},
        contract_summary={"groundedness": True},
        rejected=False,
        rejection_reason="",
        attribution={"step1": {"accuracy": 0.1}},
        failure_clusters={"err": 1},
    )

    data = card.to_dict()
    data["objective_summary"]["accuracy"] = 0.0
    data["attribution"]["step1"]["accuracy"] = 0.0
    data["failure_clusters"]["err"] = 999

    assert card.objective_summary["accuracy"] == 0.9
    assert card.attribution["step1"]["accuracy"] == 0.1
    assert card.failure_clusters["err"] == 1


def test_evidence_card_to_dict_integration_with_compile_result():
    from reliopt import Contract, Objective, Program
    from reliopt.compiler.engine import Compiler

    def toy(question: str) -> str:
        return "yes"

    prog = Program(toy)
    prog.contracts(Contract.schema_valid(strict=False))
    prog.objectives(Objective.accuracy())

    compiler = Compiler(
        program=prog,
        contracts=prog._contracts,
        objectives=prog._objectives,
    )
    result = compiler.run(trainset=[{"question": "q", "expected": "yes"}])
    candidate = result.candidates[0]
    card = result.evidence_card(candidate.id)

    data = card.to_dict()
    assert data["candidate_id"] == candidate.id
    assert "accuracy" in data["objective_summary"]
    assert "schema_valid" in data["contract_summary"]
    assert data["rejected"] is False
    assert json.dumps(data)
