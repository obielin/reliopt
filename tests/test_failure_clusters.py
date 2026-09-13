"""
Compiler._failure_clusters / EvidenceCard.failure_clusters: group failed
records by *why* they failed (contract violated / accuracy wrong /
perturbation type) — the dependency-free alternative to embedding-based
clustering (see ARCHITECTURE.md and CONTRIBUTING.md's roadmap).

Always computed (no opt-in flag: it's pure computation over records already
collected for scoring, unlike attribution's extra program executions).
"""

from __future__ import annotations

from reliopt import Contract, Objective, Program
from reliopt.compiler.engine import Compiler


def _identity(x: int) -> int:
    return x


def test_no_failures_produces_empty_dict_not_fabricated_zero_entries():
    program = Program(_identity, name="identity")
    program.objectives(Objective.accuracy())
    program.contracts(Contract.schema_valid(strict=False))

    trainset = [{"x": i, "expected": i} for i in range(3)]

    def enrich(record: dict) -> dict:
        record["schema_error"] = False  # every record is schema-valid
        return record

    compiler = Compiler(
        program=program,
        contracts=program._contracts,
        objectives=program._objectives,
        enrich_fn=enrich,
    )
    result = compiler.run(trainset=trainset)

    candidate = result.candidates[0]
    assert candidate.failure_clusters == {}

    card = result.evidence_card(candidate.id)
    assert card.failure_clusters == {}
    assert "failure clusters" not in card.render()


def test_contract_failing_on_subset_of_records_shows_correct_count():
    program = Program(_identity, name="identity")
    program.objectives(Objective.accuracy())
    program.contracts(Contract.schema_valid(strict=False))

    # 5 records, all correct (output == expected) so accuracy never fails —
    # isolates the contract-failure count from any objective-failure count.
    trainset = [{"x": i, "expected": i} for i in range(5)]

    def enrich(record: dict) -> dict:
        record["schema_error"] = record["input"]["x"] < 3  # first 3 fail schema
        return record

    compiler = Compiler(
        program=program,
        contracts=program._contracts,
        objectives=program._objectives,
        enrich_fn=enrich,
    )
    result = compiler.run(trainset=trainset)

    candidate = result.candidates[0]
    assert candidate.failure_clusters == {"contract:schema_valid": 3}
    assert "objective:accuracy" not in candidate.failure_clusters

    card = result.evidence_card(candidate.id)
    assert card.failure_clusters == {"contract:schema_valid": 3}
    rendered = card.render()
    assert "failure clusters:" in rendered
    assert f"    {'contract:schema_valid':<30} 3" in rendered


def test_record_failing_contract_and_accuracy_contributes_to_both_labels():
    program = Program(_identity, name="identity")
    program.objectives(Objective.accuracy())
    program.contracts(Contract.schema_valid(strict=False))

    # A single record, deliberately wrong (expected != output) and flagged
    # schema-invalid: it must land in BOTH clusters, not just one.
    trainset = [{"x": 0, "expected": 999}]

    def enrich(record: dict) -> dict:
        record["schema_error"] = True
        return record

    compiler = Compiler(
        program=program,
        contracts=program._contracts,
        objectives=program._objectives,
        enrich_fn=enrich,
    )
    result = compiler.run(trainset=trainset)

    candidate = result.candidates[0]
    assert candidate.failure_clusters == {
        "objective:accuracy": 1,
        "contract:schema_valid": 1,
    }


def test_perturbed_record_is_labeled_by_perturbation_type_nominal_is_not():
    from reliopt.perturbation.engine import InjectDistractorSentencePerturber

    def echo(text: str) -> str:
        return text

    program = Program(echo, name="echo")
    program.objectives(Objective.accuracy())

    trainset = [{"text": "hello, world", "expected": "hello, world"}]

    compiler = Compiler(
        program=program,
        contracts=[],
        objectives=program._objectives,
        perturbers=[InjectDistractorSentencePerturber()],
    )
    result = compiler.run(trainset=trainset)

    candidate = result.candidates[0]
    # Nominal record: output == expected, no perturbation_type -> no clusters
    # from it. Perturbed record: text gets a distractor appended, so the echo
    # no longer matches `expected` -> accuracy fails, and it's labeled by its
    # perturbation type.
    assert candidate.failure_clusters == {
        "objective:accuracy": 1,
        "perturbation:inject_distractor": 1,
    }
