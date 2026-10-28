"""Regression guard for the historical source-review queue, not an FDA model.

This test ensures the saved read-only Neon metadata inventory cannot silently
become current GEM/GEM_JR membership, an authorized trial import, or a source
verification/approval probability. No live database connection is opened.
"""
import json
import unittest
from pathlib import Path

from app.scientific_historical_crosswalk import audit_historical_crosswalk

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "snapshot" / "gem_stage_membership.json"
QUEUE = ROOT / "SCIENTIFIC_HISTORICAL_REVIEW_QUEUE_20261025.json"


class HistoricalCandidateQueueTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = json.loads(SNAP.read_text(encoding="utf-8"))
        self.queue = json.loads(QUEUE.read_text(encoding="utf-8"))

    def test_queue_is_historical_and_contains_all_distinct_hints(self):
        self.assertEqual(self.queue["schema_version"],
                         "science-historical-candidate-review-queue-v1")
        self.assertEqual(self.queue["source_snapshot_as_of"], "2026-10-16")
        self.assertFalse(self.queue["current_list_membership_verified"])
        self.assertFalse(self.queue["import_executed"])
        self.assertEqual(self.queue["independent_scientific_sources_verified"], 0)
        self.assertEqual(self.queue["historical_application_crosswalks_approved"], 0)
        self.assertIsNone(self.queue["regulatory_outcome_probability"])

        recorded = {row["nct_id"] for row in self.queue["records"]}
        audit = audit_historical_crosswalk(
            self.snapshot,
            reference_date=self.queue["audit_date"],
            archived_nct_ids=recorded,
        )
        self.assertEqual(audit["distinct_hinted_trials"], 17)
        self.assertEqual(audit["historical_entries"], 19)
        self.assertEqual(audit["distinct_archived_hinted_trials"], 17)
        self.assertEqual(audit["missing_archive_nct_ids"], [])
        self.assertTrue(audit["freshness_lapsed"])
        self.assertEqual(len(recorded), len(self.queue["records"]))
        self.assertEqual(len(recorded), self.queue["source_archive_record_count"])
        self.assertEqual(recorded, {
            nct for entry in audit["records"]
            for nct in entry["hinted_nct_ids"]
        })

    def test_applicational_hints_never_promoted_to_verified_trial_link(self):
        report = self.queue["records"]
        linked_entries = 0
        for item in report:
            self.assertFalse(item["independent_regulatory_crosswalk_approved"])
            self.assertFalse(item["independent_scientific_evidence_verified"])
            self.assertFalse(item["imported_into_scientific_render"])
            self.assertIsNone(item["approval_probability"])
            self.assertEqual(item["completed_scientific_assessments"], 0)
            self.assertTrue(item["archive_metadata"]["present_in_main_neon"])
            self.assertIsInstance(item["archive_metadata"]["has_posted_results"], bool)
            self.assertIsInstance(item["archive_metadata"]["digest_field_present"], bool)
            self.assertTrue(item["candidate_associations"])
            for association in item["candidate_associations"]:
                self.assertIn(association["historical_stage"], ("GEM", "GEM_JR"))
                if association["association_type"] == "DIRECT_TRIAL_SOURCE_IDENTITY":
                    linked_entries += 1
                    self.assertEqual(association["source_key"],
                                     "TRIAL|" + item["nct_id"])
                else:
                    self.assertEqual(association["association_type"],
                                     "UNVERIFIED_APPLICATION_HINT")
                    self.assertTrue(association["source_key"].startswith(
                        "APPLICATION|"))
        self.assertEqual(linked_entries, 3)

    def test_evidence_prioritization_is_not_claim_of_statistical_significance(self):
        rows = self.queue["records"]
        self.assertEqual(sum(r["archive_metadata"]["has_posted_results"]
                             for r in rows), self.queue["with_posted_results"])
        self.assertEqual(
            sum(r["archive_metadata"]["p_value_presence"] == "REPORTED"
                for r in rows),
            self.queue["with_reported_pvalue_presence"],
        )
        self.assertEqual(self.queue["with_posted_results"], 5)
        self.assertEqual(self.queue["with_reported_pvalue_presence"], 4)
        self.assertTrue(self.queue["review_priority_only"])
        # The queue never asserts a p-value magnitude, a passed endpoint,
        # or an overall FDA approval rating.
        self.assertTrue(all("p_value" not in row or
                            "p_value_presence" in row["archive_metadata"]
                            for row in rows))


if __name__ == "__main__":
    unittest.main()
