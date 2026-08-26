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
