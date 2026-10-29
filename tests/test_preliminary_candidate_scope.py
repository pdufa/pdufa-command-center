from research.preliminary_candidate_scope import preliminary_candidate_scope


def _candidate(**changes):
    row = {"publicly_traded": True, "market_cap_usd": 300000000,
           "pipeline_member": True, "fda_pdufa_target_confirmed": True}
    row.update(changes)
    return row


def test_inclusive_approved_market_cap_bounds():
    for value in (300000000, "10000000000"):
        result = preliminary_candidate_scope(_candidate(market_cap_usd=value))
        assert result["scope"] == "CANDIDATE_FOR_EVIDENCE_REVIEW"
        assert result["prediction"] is None
        assert result["prediction_status"] == "ABSTAIN"


def test_unknown_invalid_or_out_of_range_cap_blocks():
    for value in (None, True, float("nan"), "NaN", "Infinity",
                  -1, 299999999, 10000000001, "unknown"):
        result = preliminary_candidate_scope(_candidate(market_cap_usd=value))
        assert result["scope"] == "BLOCKED"
        assert "MARKET_CAP_OUTSIDE_APPROVED_RANGE_OR_UNKNOWN" in result["blockers"]


def test_pipeline_and_pdufa_requirements_are_independent():
    result = preliminary_candidate_scope(_candidate(
        publicly_traded=False, pipeline_member=False, fda_pdufa_target_confirmed=False))
    assert len(result["blockers"]) == 3
    assert result["prediction_status"] == "ABSTAIN"


def test_malformed_candidate_fails_closed():
    assert preliminary_candidate_scope(None)["prediction_status"] == "ABSTAIN"
