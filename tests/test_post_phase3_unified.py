import csv
import json
from datetime import date, timedelta

from post_phase3_unified import build_queue


TODAY = date(2026, 10, 11)
EVENT = "ACME|DRUG_INDICATION_20261201"
GATES = (
    "trial_identity", "phase3_primary", "clinical_benefit", "safety",
    "second_financing", "no_unresolved_dilution",
    "post_readout_price_base", "normalized_volume",
)


def write_csv(root, name, rows):
    if not rows:
        (root / name).write_text("", encoding="utf-8")
        return
    with (root / name).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def fixture(tmp_path, *, due=40, outcome="", stage="VERIFIED_SUCCESS", gate="ENTRY READY — ATTESTED EVIDENCE / NOT INDEPENDENTLY AUDITED"):
    (tmp_path / "step7_live_status.json").write_text(json.dumps(
        {"generated_at_utc": "2026-10-11T14:13:50+00:00"}), encoding="utf-8")
    write_csv(tmp_path, "pdufa_candidates.csv", [{
        "event_key": EVENT, "ticker": "ACME", "drug": "Drug A",
        "indication": "Disease A", "nct_id": "NCT01234567",
        "pdufa_date": (TODAY + timedelta(days=due)).isoformat(),
        "pdufa_confirmation": "VERIFIED",
        "pdufa_evidence_url": "https://www.sec.gov/Archives/edgar/data/1/x",
        "phase3_status": stage, "phase3_date": "2026-01-01",
        "trial_evidence_url": "https://issuer.example/results",
        "outcome": outcome, "conflict_flag": "NONE",
    }])
    write_csv(tmp_path, "step7_financing_review.csv", [{
        "Exact financing event": EVENT,
        "Current gate": gate, "Proposed trade status": gate,
        "Historical second closing": "DOCUMENTED — RECHECK REQUIRED",
        "Gate reasons": "", "Audited gate details": " | ".join(
            f"{name}: PASS — reviewer confirmed" for name in GATES),
        "Source scan": "FINANCING_VERIFIED", "Recheck freshness": "RECENT",
        "Second source": "https://www.sec.gov/Archives/edgar/data/1/close",
    }])
    write_csv(tmp_path, "step7_pre_phase3_feed.csv", [])
    return tmp_path


def test_green_only_with_current_verified_event(tmp_path):
    rows, status = build_queue(fixture(tmp_path), TODAY)
    assert len(rows) == 1
    assert rows[0]["Entry qualification"] == "GREEN — GATES ATTESTED"
    assert status["green_count"] == 1
    assert rows[0]["Planned exit (-7 days)"] == (TODAY + timedelta(days=33)).isoformat()


def test_one_missing_gate_cannot_be_green(tmp_path):
    fixture(tmp_path)
    funding = [{
        "Exact financing event": EVENT, "Current gate": "ENTRY READY — ATTESTED",
        "Proposed trade status": "ENTRY READY — ATTESTED",
        "Historical second closing": "DOCUMENTED — RECHECK REQUIRED",
        "Recheck freshness": "RECENT", "Source scan": "FINANCING_VERIFIED",
        "Audited gate details": "trial_identity: PASS",
    }]
    write_csv(tmp_path, "step7_financing_review.csv", funding)
    rows, _ = build_queue(tmp_path, TODAY)
    assert rows[0]["Entry qualification"].startswith("REVIEW")


def test_blocked_sec_does_not_allow_green(tmp_path):
    fixture(tmp_path)
    funding = [{
        "Exact financing event": EVENT, "Current gate": "ENTRY READY — ATTESTED",
        "Proposed trade status": "ENTRY READY — ATTESTED",
        "Historical second closing": "DOCUMENTED — RECHECK REQUIRED",
        "Recheck freshness": "STALE", "Source scan": "SOURCE_BLOCKED_RETAINED",
        "Audited gate details": " | ".join(f"{name}: PASS" for name in GATES),
    }]
    write_csv(tmp_path, "step7_financing_review.csv", funding)
    rows, _ = build_queue(tmp_path, TODAY)
    assert rows[0]["Entry qualification"].startswith("REVIEW")


def test_stale_snapshot_invalidates_green(tmp_path):
    fixture(tmp_path)
    rows, status = build_queue(tmp_path, TODAY + timedelta(days=1))
    assert status["feed_current"] is False
    assert status["green_count"] == 0


def test_last_week_never_starts_position(tmp_path):
    rows, _ = build_queue(fixture(tmp_path, due=7), TODAY)
    assert rows[0]["Entry qualification"] == "RED WINDOW — NO NEW ENTRY"


def test_resolved_event_is_not_eligible(tmp_path):
    rows, _ = build_queue(fixture(tmp_path, outcome="APPROVED"), TODAY)
    assert rows[0]["Entry qualification"].startswith("EXCLUDED")


def test_missing_exact_financing_event_is_not_ticker_matched(tmp_path):
    fixture(tmp_path)
    write_csv(tmp_path, "step7_financing_review.csv", [{
        "Exact financing event": "ACME|ANOTHER_DRUG", "Current gate": "ENTRY READY",
    }])
    rows, _ = build_queue(tmp_path, TODAY)
    assert rows[0]["Entry qualification"].startswith("REVIEW")
    assert rows[0]["Financing #2"] == "REVIEW — NOT DOCUMENTED"


def test_trial_registry_posting_is_never_called_phase3_success(tmp_path):
    fixture(tmp_path)
    write_csv(tmp_path, "step7_pre_phase3_feed.csv", [{
        "Ticker": "BETA", "Drug": "Other", "Indication": "New condition",
        "NCT ID": "NCT87654321", "Trial phase": "Phase 3",
        "Research category": "RESULT POSTED — CLINICAL REVIEW",
        "NCT source": "https://clinicaltrials.gov/study/NCT87654321",
    }])
    rows, status = build_queue(tmp_path, TODAY)
    lead = next(x for x in rows if x["Ticker"] == "BETA")
    assert lead["Phase 3 evidence"] == "REGISTRY RESULTS POSTED — REVIEW"
    assert lead["Entry qualification"].startswith("REVIEW")
    assert status["research_leads"] == 1


def test_external_lead_must_be_sourced_and_never_promoted(tmp_path):
    fixture(tmp_path)
    write_csv(tmp_path, "post_phase3_discoveries.csv", [{
        "ticker": "NEW", "drug": "Drug B", "indication": "Disease B",
        "nct_id": "NCT11112222", "readout_date": "2026-09-01",
        "source_url": "https://investors.example/new-results",
    }, {
        "ticker": "BAD", "drug": "Drug C", "indication": "Disease C",
        "nct_id": "NCT99999999", "readout_date": "2026-09-01",
        "source_url": "http://untrusted.invalid/post",
    }])
    rows, status = build_queue(tmp_path, TODAY)
    assert "NEW" in {x["Ticker"] for x in rows}
    assert "BAD" not in {x["Ticker"] for x in rows}
    lead = next(x for x in rows if x["Ticker"] == "NEW")
    assert lead["Source lane"] == "INDEPENDENT RESEARCH — SOURCE LINKED"
    assert lead["Entry qualification"].startswith("REVIEW")
    assert status["green_count"] == 1


def test_duplicate_regulatory_identity_cannot_be_approved(tmp_path):
    fixture(tmp_path)
    write_csv(tmp_path, "pdufa_candidates.csv", [
        {"event_key": EVENT, "ticker": "ACME", "drug": "Drug A"},
        {"event_key": EVENT, "ticker": "ACME", "drug": "Different Drug"},
    ])
    rows, status = build_queue(tmp_path, TODAY)
    assert status["green_count"] == 0
    assert rows == []

# GitHub Actions uses unittest discovery, not pytest; explicitly execute
# each fixture-based scenario inside its own temporary directory.
import tempfile
import unittest
from pathlib import Path


class TestUnifiedPostPhase3Stage1(unittest.TestCase):
    def test_source_and_stage_regressions(self):
        scenarios = (
            test_green_only_with_current_verified_event,
            test_one_missing_gate_cannot_be_green,
            test_blocked_sec_does_not_allow_green,
            test_stale_snapshot_invalidates_green,
            test_last_week_never_starts_position,
            test_resolved_event_is_not_eligible,
            test_missing_exact_financing_event_is_not_ticker_matched,
            test_trial_registry_posting_is_never_called_phase3_success,
            test_external_lead_must_be_sourced_and_never_promoted,
            test_duplicate_regulatory_identity_cannot_be_approved,
        )
        for scenario in scenarios:
            with self.subTest(scenario=scenario.__name__):
                with tempfile.TemporaryDirectory() as directory:
                    scenario(Path(directory))
