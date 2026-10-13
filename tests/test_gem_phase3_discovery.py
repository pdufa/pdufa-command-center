"""Phase 3 result discovery must never label registry rows as verified success."""
import unittest
from datetime import date
from unittest.mock import patch

from gem_phase3_discovery import (
    DISCOVERY_COLUMNS, discover_phase3_results, gem_discrimination_audit,
)


TODAY = date(2026, 10, 13)


def lead(**updates):
    row = {
        "ticker": "ABCD", "nct_id": "NCT01234567",
        "drug": "Molecule A", "indication": "Condition A",
        "source_type": "CLINICALTRIALS_RESULTS",
        "phase3_results_posted_at": "2026-09-17",
        "phase3_results_source": "https://clinicaltrials.gov/study/NCT01234567",
        "verification_status": "REGISTERED_RESULTS_POSTED",
        "first_seen_at": "2026-09-18T12:00:00+00:00",
        "last_checked_at": "2026-10-12T09:00:00+00:00",
    }
    row.update(updates)
    return row


def scan(rows):
    with patch("gem_phase3_discovery.read_rows", return_value=rows):
        return discover_phase3_results("data", as_of=TODAY)


class Phase3DiscoveryTests(unittest.TestCase):
    def test_results_posted_is_not_successful_phase3(self):
        result, meta = scan([lead()])
        self.assertEqual(len(result), 1)
        self.assertIn("NEEDS ENDPOINT REVIEW", result[0]["Discovery category"])
        self.assertIn("Independent endpoint", result[0]["What is missing"])
        self.assertEqual(meta["status"], "REVIEW_EVIDENCE_NOT_ADJUDICATED")
        self.assertNotIn("GEM score", DISCOVERY_COLUMNS)

    def test_future_or_untraceable_evidence_rejected(self):
        result, meta = scan([
            lead(phase3_results_posted_at="2027-01-01"),
            lead(phase3_results_source="http://example.org"),
            lead(first_seen_at="2026-10-14T00:00:00Z"),
        ])
        self.assertEqual(result, [])
        self.assertEqual(meta["rejected_missing_or_future_evidence"], 3)

    def test_ambiguous_identity_does_not_auto_join_ticker(self):
        result, meta = scan([lead(nct_id="NCTBAD"),
                             lead(ticker="???")])
        self.assertEqual(result, [])
        self.assertEqual(meta["rejected_ambiguous_identity"], 2)

    def test_issuer_and_registry_remain_two_distinct_research_sources(self):
        result, _ = scan([
            lead(),
            lead(source_type="ISSUER_TOPLINE_RELEASE",
                 phase3_results_source="https://issuer.example/press-release",
                 verification_status="ISSUER_TOPLINE_EXACT_TRIAL_REVIEW"),
        ])
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]["Discovery category"].startswith("ISSUER READOUT"))

    def test_conflicting_duplicate_source_is_not_last_wins(self):
        result, meta = scan([
            lead(), lead(drug="Different unverified molecule"),
        ])
        self.assertEqual(result, [])
        self.assertGreaterEqual(meta["ambiguous_duplicates"], 1)

    def test_identical_duplicate_does_not_repeat_candidate(self):
        result, meta = scan([lead(), lead()])
        self.assertEqual(len(result), 1)
        self.assertEqual(meta["ambiguous_duplicates"], 0)

    def test_partial_limit_is_explicit(self):
        with patch("gem_phase3_discovery.read_rows", return_value=[lead(), lead(ticker="WXYZ")]):
            found, meta = discover_phase3_results("data", as_of=TODAY, limit=1)
        self.assertEqual(len(found), 1)
        self.assertEqual(meta["unprocessed_due_to_limit"], 1)
        self.assertEqual(meta["status"], "REVIEW_PARTIAL_INPUT_TRUNCATED")

    def test_ranking_audit_detects_tied_scores(self):
        scores = [
            {"Phase 3 score": 90, "Post-Financing score": None},
            {"Phase 3 score": 90, "Post-Financing score": None},
            {"Phase 3 score": 80, "Post-Financing score": None},
        ]
        report = gem_discrimination_audit(scores, ("Phase 3", "Post-Financing"))
        self.assertEqual(report["Phase 3"]["tied_candidates"], 2)
        self.assertEqual(report["Phase 3"]["unique_scores"], 2)
        self.assertEqual(report["Phase 3"]["status"], "LIMITED_DISCRIMINATION")
        self.assertEqual(report["Post-Financing"]["status"], "NO_RANKED_CANDIDATES")

    def test_scans_ui_contains_discovery_and_historical_audit(self):
        from pathlib import Path
        base = Path(__file__).resolve().parents[1]
        ui = (base / "gem_scans_ui.py").read_text(encoding="utf-8")
        self.assertIn("BROAD PHASE 3 DISCOVERY", ui)
        self.assertIn("GEM RANKING QUALITY", ui)
        self.assertIn("render_gem_calibration(root)", ui)


if __name__ == "__main__":
    unittest.main()
