from reliopt.contracts.base import Contract


def test_wilson_lower_bound_satisfied_with_large_sample():
    records = [{"ok": True}] * 92 + [{"ok": False}] * 8  # 92% raw rate, n=100
    contract = Contract.wilson_lower_bound("ok", minimum=0.85)
    result = contract.evaluate(records)
    assert result.satisfied
    assert result.observed_value >= 0.85


def test_wilson_lower_bound_violated_with_small_sample():
    # Same 90% raw rate as above but n=10 — too few observations to trust the
    # point estimate, so the Wilson lower bound should fall short of 0.85
    # even though 9/10 = 0.9 looks fine on its own.
    records = [{"ok": True}] * 9 + [{"ok": False}] * 1
    contract = Contract.wilson_lower_bound("ok", minimum=0.85)
    result = contract.evaluate(records)
    assert not result.satisfied
    assert result.observed_value < 0.85


def test_wilson_lower_bound_no_data_reports_unsatisfied():
    contract = Contract.wilson_lower_bound("ok", minimum=0.85)
    result = contract.evaluate([{"other_field": 1}])
    assert not result.satisfied
    assert result.observed_value is None


def test_abstain_when_unsupported_satisfied_with_large_sample():
    # 98% correct abstention decisions over a large enough sample that the
    # Wilson lower bound clears the 0.9 threshold.
    records = [{"should_abstain": True, "abstained": True}] * 98
    records += [{"should_abstain": True, "abstained": False}] * 2
    contract = Contract.abstain_when_unsupported()
    result = contract.evaluate(records)
    assert result.satisfied
    assert result.observed_value >= 0.9


def test_abstain_when_unsupported_violated_with_small_sample():
    # Same 90% raw correctness rate as the 0.9 threshold, but n=10 is too
    # small to trust — the Wilson lower bound should fall short even though
    # the raw rate alone would have passed under the old check.
    records = [{"should_abstain": True, "abstained": True}] * 9
    records += [{"should_abstain": False, "abstained": True}] * 1
    contract = Contract.abstain_when_unsupported()
    result = contract.evaluate(records)
    assert not result.satisfied
    assert result.observed_value < 0.9


def test_abstain_when_unsupported_no_applicable_records_unchanged():
    contract = Contract.abstain_when_unsupported()
    result = contract.evaluate([{"should_abstain": None}, {"foo": "bar"}])
    assert result.satisfied
    assert result.detail == "no applicable records"
