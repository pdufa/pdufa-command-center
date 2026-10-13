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


def fixture(tmp_path, *, due=40, outcome="", stage="VERIFIED_SUCCESS", gate="ENTRY READY — ATTESTED EVIDENCE / NOT INDEPENDENTLY AUDITED", closed=True):
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
    if closed:
        write_csv(tmp_path, "second_financing_status.csv", [{
            "event_key": EVENT, "second_financing_status": "CLOSED",
            "second_financing_closed": "YES",
            "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
            "second_financing_source": "https://www.sec.gov/Archives/edgar/data/1/close",
            "verified_as_of": TODAY.isoformat(),
        }])
    write_csv(tmp_path, "step7_pre_phase3_feed.csv", [])
    return tmp_path


def test_green_only_with_current_verified_event(tmp_path):
    rows, status = build_queue(fixture(tmp_path), TODAY)
    assert len(rows) == 1
    assert rows[0]["Entry qualification"] == "GREEN — GATES ATTESTED"
    assert status["green_count"] == 1
    assert rows[0]["Planned exit (-3 days)"] == (TODAY + timedelta(days=37)).isoformat()


def test_unified_gate_and_score_columns_in_one_row(tmp_path):
    rows, status = build_queue(fixture(tmp_path), TODAY)
    row = rows[0]
    assert row["Entry qualification"] == "GREEN — GATES ATTESTED"
    assert row["Evidence score /100"] == 65
    assert row["Clinical evidence /30"] == 30
    assert row["Financing evidence /20"] == 20
    assert row["Trading setup /20"] == 0
    assert row["PDUFA evidence /15"] == 15
    assert row["Evidence rank"] == 1
    assert row["Rating status"].startswith("PARTIAL")
    assert status["green_count"] == 1


def test_unrated_lead_cannot_jump_a_verified_event(tmp_path):
    fixture(tmp_path)
    write_csv(tmp_path, "post_phase3_discoveries.csv", [{
        "ticker":"NEW", "drug":"Drug B", "indication":"Disease B",
        "nct_id":"NCT11112222", "readout_date":"2026-09-01",
        "source_url":"https://issuer.example/clinical",
    }])
    rows, status=build_queue(tmp_path,TODAY)
    lead=next(x for x in rows if x["Ticker"]=="NEW")
    assert lead["Entry qualification"].startswith("REVIEW")
    assert lead["Evidence score /100"] is None
    assert lead["Evidence rank"] is None
    assert status["green_count"]==1


def test_second_financing_completed_requires_audited_exact_event(tmp_path):
    fixture(tmp_path, closed=False)
    rows, _ = build_queue(tmp_path, TODAY)
    assert rows[0]["2nd Financing Completed"] == "NOT VERIFIED"
    assert rows[0]["Entry qualification"].startswith("REVIEW")
    closed = {
        "event_key": EVENT,
        "second_financing_status": "CLOSED",
        "second_financing_closed": "YES",
        "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
        "second_financing_source": "https://www.sec.gov/Archives/edgar/data/1/close",
        "verified_as_of": TODAY.isoformat(),
    }
    write_csv(tmp_path, "second_financing_status.csv", [closed])
    rows, _ = build_queue(tmp_path, TODAY)
    assert rows[0]["2nd Financing Completed"] == "YES — VERIFIED (HISTORICAL)"
    write_csv(tmp_path, "second_financing_status.csv", [{**closed, "event_key": "ACME|OTHER"}])
    rows, _ = build_queue(tmp_path, TODAY)
    assert rows[0]["2nd Financing Completed"] == "NOT VERIFIED"


def test_stale_sources_remove_rating_without_reclassifying_as_green(tmp_path):
    fixture(tmp_path)
    rows,status=build_queue(tmp_path,TODAY + timedelta(days=1))
    assert status["green_count"]==0
    assert rows[0]["Evidence score /100"] is None
    assert "STALE" in rows[0]["Rating status"]


def test_ranks_exist_for_review_candidates_with_no_strict_evidence(tmp_path):
    fixture(tmp_path)
    # A reported but unverified PDUFA and an unadjudicated primary endpoint
    # cannot produce a strict evidence score, yet should be research-ranked.
    write_csv(tmp_path, "pdufa_candidates.csv", [{
        "event_key": EVENT, "ticker": "ACME", "drug": "Drug A",
        "indication": "Disease A", "nct_id": "NCT01234567",
        "pdufa_date": (TODAY + timedelta(days=40)).isoformat(),
        "pdufa_confirmation": "REPORTED_ONLY",
        "phase3_date": "2026-01-01",
        "phase3_status": "RESULTS_REVIEW",
        "outcome": "", "conflict_flag": "NONE",
    }])
    write_csv(tmp_path, "step7_financing_review.csv", [{
        "Exact financing event": EVENT,
        "Current gate": "REVIEW — ENTRY BLOCKED",
        "Source scan": "SOURCE_BLOCKED_RETAINED",
        "Recheck freshness": "STALE",
        "Historical second closing": "NOT VERIFIED",
    }])
    events, status = build_queue(tmp_path, TODAY)
    row = events[0]
    assert row["Entry qualification"].startswith("REVIEW")
    assert row["Evidence score /100"] is None
    assert row["Evidence rank"] is None
    assert row["Research rank"] == 1
    assert row["Research priority /100"] > 0
    assert "RESEARCH TRIAGE ONLY" in row["Research priority status"]
    assert status["green_count"] == 0
    assert status["research_ranked"] == 1


def test_unverified_external_readout_lead_gets_research_rank_not_trade_green(tmp_path):
    fixture(tmp_path)
    write_csv(tmp_path, "post_phase3_discoveries.csv", [{
        "ticker":"NEW", "drug":"Drug B", "indication":"Disease B",
        "nct_id":"NCT11112222", "readout_date":"2026-09-01",
        "source_url":"https://issuer.example/readout",
    }])
    rows, status = build_queue(tmp_path, TODAY)
    lead = next(row for row in rows if row["Ticker"] == "NEW")
    assert lead["Evidence score /100"] is None
    assert lead["Entry qualification"] == "REVIEW — RESEARCH LEAD"
    assert lead["Research rank"] is not None
    assert lead["Research priority /100"] > 0
    assert status["research_ranked"] == 2


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


def test_no_new_entry_at_pdufa_minus_three(tmp_path):
    rows, _ = build_queue(fixture(tmp_path, due=3), TODAY)
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
            test_unified_gate_and_score_columns_in_one_row,
            test_unrated_lead_cannot_jump_a_verified_event,
            test_second_financing_completed_requires_audited_exact_event,
            test_stale_sources_remove_rating_without_reclassifying_as_green,
            test_ranks_exist_for_review_candidates_with_no_strict_evidence,
            test_unverified_external_readout_lead_gets_research_rank_not_trade_green,
            test_one_missing_gate_cannot_be_green,
            test_blocked_sec_does_not_allow_green,
            test_stale_snapshot_invalidates_green,
            test_no_new_entry_at_pdufa_minus_three,
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
