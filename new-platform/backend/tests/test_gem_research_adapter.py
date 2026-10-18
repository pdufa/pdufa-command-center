"""Regression tests: a source headline or saved GEM label never grants eligibility."""
from datetime import date

from app.gem_research_adapter import analyze_member, verify_benchmarks, parse_runway


TODAY = date(2026, 10, 16)
ROW = {
    "ticker": "TEST", "id": "APPLICATION|TEST|EXACT_EVENT",
    "nctId": "NCT01234567", "pdufaDate": "2027-01-29",
}
EVENT = {
    "event_key": "TEST|EXACT_EVENT", "ticker": "TEST", "nct_id": "NCT01234567",
    "phase3_status": "PRIMARY_MET_VERIFIED", "phase3_date": "2025-08-01",
    "trial_evidence_url": "https://issuer.example/primary-results",
}
FINANCING = {
    "first_financing_date": "2025-09-15", "second_financing_date": "2026-03-15",
    "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
}
RECHECK = {
    "first_sec_status": "VERIFIED", "second_sec_status": "VERIFIED",
    "first_sec_url": "https://www.sec.gov/filing1",
    "second_sec_url": "https://www.sec.gov/filing2",
    "gem_entry_authorized": "YES",
}


def test_successful_exact_phase3_qualifies_with_optional_financing_recorded():
    result = verify_benchmarks(ROW, EVENT, FINANCING, RECHECK, TODAY)
    assert result["bothConfirmed"] is True
    assert result["phase3"] and result["secondFinancing"]


def test_generic_verified_readout_is_not_positive():
    changed = {**EVENT, "phase3_status": "RESULTS_VERIFIED"}
    result = verify_benchmarks(ROW, changed, FINANCING, RECHECK, TODAY)
    assert not result["bothConfirmed"]
    assert not result["phase3"]


def test_financing_recheck_hold_does_not_block_phase3_but_financing_stays_unverified():
    changed = {**RECHECK, "gem_entry_authorized": "NO"}
    result = verify_benchmarks(ROW, EVENT, FINANCING, changed, TODAY)
    assert result["clinicalQualified"] is True
    assert result["bothConfirmed"] is True
    assert not result["secondFinancing"]
    assert result["financingOptional"] is True


def test_financings_before_readout_cannot_be_verified_but_do_not_block_phase3():
    changed = {**FINANCING, "first_financing_date": "2025-07-25"}
    result = verify_benchmarks(ROW, EVENT, changed, RECHECK, TODAY)
    assert result["clinicalQualified"] is True
    assert result["bothConfirmed"] is True
    assert not result["secondFinancing"]


def test_exact_identity_is_required():
    changed = {**ROW, "ticker": "OTHER"}
    result = verify_benchmarks(changed, EVENT, FINANCING, RECHECK, TODAY)
    assert not result["bothConfirmed"]


def test_no_eod_cannot_generate_buy_score():
    result = analyze_member(
        ROW, EVENT, FINANCING, {**RECHECK, "gem_entry_authorized": "NO"},
        {}, None, {"complete": False}, TODAY,
    )
    assert result["entry"] is None
    assert result["close"] is None
    assert result["rvol"] is None
    assert result["runwayMonths"] is None
    assert result["researchOnly"] is True
    assert "WAIT" in result["tradeCall"] or "EXIT" in result["tradeCall"]


def test_runway_duplicate_ticker_is_quarantined():
    raw = """{"schema_version":1,"source":"SEC_STEP4_COMPANYFACTS","snapshots":[{"ticker":"A"},{"ticker":"A"},{"ticker":"B"}]}"""
    parsed = parse_runway(raw)
    assert "A" not in parsed
    assert "B" in parsed


def test_no_financings_phase3_can_enter_manual_research_review_only():
    result = analyze_member(
        ROW, EVENT, {}, {}, {},
        None, {"complete": False}, TODAY,
    )
    assert result["benchmarks"]["phase3"] is True
    assert result["benchmarks"]["clinicalQualified"] is True
    assert result["benchmarks"]["secondFinancing"] is False
    assert "optional" in " ".join(result["riskAlerts"]).lower()
    assert result["entry"] is None
    assert result["researchOnly"] is True


def test_missing_successful_phase3_never_qualifies_even_with_financing():
    changed = {**EVENT, "phase3_status": "RESULTS_VERIFIED"}
    result = analyze_member(ROW, changed, FINANCING, RECHECK, {},
                            None, {"complete": True}, TODAY)
    assert result["benchmarks"]["clinicalQualified"] is False
    assert result["entry"] is None
    assert result["researchOnly"] is True
