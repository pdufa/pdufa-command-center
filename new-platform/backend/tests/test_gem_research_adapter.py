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


def test_requires_exact_positive_phase3_and_two_funded_closings():
    result = verify_benchmarks(ROW, EVENT, FINANCING, RECHECK, TODAY)
    assert result["bothConfirmed"] is True
    assert result["phase3"] and result["secondFinancing"]


def test_generic_verified_readout_is_not_positive():
    changed = {**EVENT, "phase3_status": "RESULTS_VERIFIED"}
    result = verify_benchmarks(ROW, changed, FINANCING, RECHECK, TODAY)
    assert not result["bothConfirmed"]
    assert not result["phase3"]


def test_financing_recheck_hold_cannot_pass():
    changed = {**RECHECK, "gem_entry_authorized": "NO"}
    result = verify_benchmarks(ROW, EVENT, FINANCING, changed, TODAY)
    assert not result["bothConfirmed"]
    assert not result["secondFinancing"]


def test_financings_before_readout_do_not_count():
    changed = {**FINANCING, "first_financing_date": "2025-07-25"}
    result = verify_benchmarks(ROW, EVENT, changed, RECHECK, TODAY)
    assert not result["bothConfirmed"]


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
