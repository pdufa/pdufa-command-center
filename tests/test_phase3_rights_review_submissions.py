"""Evidence submission workflow for 741 NCTs x 6 legal-rights review requirements."""
import copy
from datetime import datetime, timedelta, timezone
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from phase3_rights_review_submissions import (
    build_review_coverage, REVIEW_CHECKS, REQUIRED_REVIEW, source_url,
)
import test_phase3_rights_review_worklist as rights_fixture_module


class RightsReviewSubmissionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture = rights_fixture_module.Phase3RightsWorklistTests()
        fixture.setUp()
        cls.original_worklist = fixture.report()

    def setUp(self):
        # Immutable underlying research input copied per test to prevent state sharing.
        self.worklist = copy.deepcopy(self.original_worklist)
        self.first = next(x for x in self.worklist["items"] if x["nct_id"] == "NCT00000001")
        self.check = REQUIRED_REVIEW[0]
        self.pending = {
            "nct_id": "NCT00000001", "ticker": self.first["ticker"],
            "issuer_sec_cik": self.first["issuer_sec_cik"],
            "check": self.check, "source_url": "https://example.com/2026/licensing",
            "source_sha256": None,
            "observed_at_utc": "2026-10-25T14:00:00Z",
            "reviewer_status": "PENDING",
            "claim": "This disclosure may discuss a licensing relationship for follow-up.",
        }
        document = self.first["sec_source_documents_fetched"][0]
        self.attested = dict(
            self.pending,
            source_url=document["url"], source_sha256=document["sha256"],
            reviewer_status="REVIEWER_REPORTS_SUPPORT",
            reviewer="Document review analyst", reviewed_at_utc="2026-10-26T09:00:00Z",
        )

    def build(self, submissions):
        return build_review_coverage(self.worklist, submissions)

    def test_empty_repo_intake_displays_true_six_gate_denominator(self):
        r = self.build([])
        self.assertEqual((r["trial_denominator"], r["requirements_per_trial"]), (741, 6))
        self.assertEqual(r["checklist_slot_denominator"], 4446)
        self.assertEqual(r["submitted_evidence_item_count"], 0)
        self.assertEqual(r["distinct_review_slots_with_submissions"], 0)
        self.assertEqual(r["review_slots_without_submissions"], 4446)
        self.assertEqual(r["trial_count_with_any_submissions"], 0)
        self.assertEqual(len(r["items"]), 741)
        self.assertEqual(r["independently_verified_commercial_rights"], 0)
        self.assertIsNone(r["qualified_pipeline_total"])
        self.assertTrue(all(item["checklist_independently_verified"] is False
                            and item["commercial_rights_verified"] is False
                            and item["qualified_pipeline"] is None for item in r["items"]))

    def test_pending_external_source_is_not_verified(self):
        r = self.build([self.pending])
        self.assertEqual((r["distinct_review_slots_with_submissions"],
                          r["review_slots_without_submissions"]), (1, 4445))
        self.assertEqual(r["trial_count_with_any_submissions"], 1)
        self.assertEqual(r["review_slots_with_reviewer_reported_findings"], 0)
        first = next(x for x in r["items"] if x["nct_id"] == "NCT00000001")
        slot = first["checks"][self.check]
        self.assertEqual(slot["status"], "PENDING_SOURCE_REVIEW")
        self.assertEqual(slot["submissions"][0]["source_provenance"],
                         "SOURCE_LINK_NOT_FETCHED_IN_THIS_RUN")
        self.assertEqual(r["independently_verified_commercial_rights"], 0)

    def test_reviewer_attestation_source_bound_but_nonqualifying(self):
        r = self.build([self.attested])
        self.assertEqual(r["review_slots_with_reviewer_reported_findings"], 1)
        self.assertEqual(r["checklist_slot_state_counts"][
            "REVIEWER_REPORTED_SUPPORT_NOT_ADJUDICATED"], 1)
        self.assertEqual(r["independently_verified_commercial_rights"], 0)
        self.assertIsNone(r["qualified_pipeline_total"])
        slot = next(x for x in r["items"] if x["nct_id"] == "NCT00000001")["checks"][self.check]
        self.assertEqual(slot["submissions"][0]["source_provenance"],
                         "EXACT_FETCHED_ISSUER_PRIMARY_DOCUMENT")
        self.assertEqual(slot["submissions"][0]["result"],
                         "RESEARCH_REPORT_ONLY_NOT_AN_INDEPENDENT_RIGHTS_DETERMINATION")

    def test_all_six_reported_support_still_no_rights_pass(self):
        submitted = [dict(self.attested, check=check) for check in REQUIRED_REVIEW]
        r = self.build(submitted)
        self.assertEqual(r["trials_with_all_six_submitted_checks"], 1)
        self.assertEqual(r["trials_with_all_six_reviewer_reported_checks"], 1)
        self.assertEqual(r["review_slots_with_reviewer_reported_findings"], 6)
        self.assertEqual(r["independently_verified_commercial_rights"], 0)
        self.assertIsNone(r["qualified_pipeline_total"])

    def test_conflicting_reviewers_report_conflict(self):
        second_doc = self.first["sec_source_documents_fetched"][1]
        other = dict(self.attested, source_url=second_doc["url"],
                     source_sha256=second_doc["sha256"],
                     reviewer="Another document reviewer",
                     reviewer_status="REVIEWER_REPORTS_NO_SUPPORT")
        r = self.build([self.attested, other])
        self.assertEqual(r["submitted_evidence_item_count"], 2)
        self.assertEqual(r["distinct_review_slots_with_submissions"], 1)
        self.assertEqual(r["checklist_slot_state_counts"]["REVIEWER_REPORTS_CONFLICT"], 1)
        self.assertEqual(r["independently_verified_commercial_rights"], 0)

    def test_fetched_doc_must_belong_to_exact_issuer_filing_index(self):
        document = self.first["sec_source_documents_fetched"][0]
        document["url"] = "https://www.sec.gov/Archives/edgar/data/999999/1234/forged.htm"
        submission = dict(self.attested, source_url=document["url"])
        with self.assertRaises(ValueError):
            self.build([submission])

    def test_fetched_doc_must_match_original_filing_candidate(self):
        document = self.first["sec_source_documents_fetched"][0]
        document["url"] = "https://www.sec.gov/Archives/edgar/data/1/9999999999999999/forged.htm"
        submission = dict(self.attested, source_url=document["url"])
        with self.assertRaises(ValueError):
            self.build([submission])

    def test_reviewed_external_source_without_fetched_original_is_rejected(self):
        with self.assertRaises(ValueError):
            self.build([dict(self.attested, source_url=self.pending["source_url"])])

    def test_provided_digest_on_unfetched_source_is_rejected(self):
        with self.assertRaises(ValueError):
            self.build([dict(self.pending, source_sha256="a" * 64)])

    def test_wrong_fetched_digest_is_rejected(self):
        with self.assertRaises(ValueError):
            self.build([dict(self.attested, source_sha256="f" * 64)])

    def test_wrong_issuer_cik_or_ticker_is_rejected(self):
        for field, value in (("ticker", "WRONG"), ("issuer_sec_cik", "0000000999")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build([dict(self.pending, **{field: value})])

    def test_unknown_check_or_nct_fails_closed(self):
        for field, value in (("check", "RIGHTS_APPROVED"), ("nct_id", "NCT99999999")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.build([dict(self.pending, **{field: value})])

    def test_duplicate_issuer_source_for_same_check_rejected(self):
        with self.assertRaises(ValueError):
            self.build([self.pending, self.pending])

    def test_unreviewed_submission_cannot_smuggle_reviewer(self):
        with self.assertRaises(ValueError):
            self.build([dict(self.pending, reviewer="False reviewer")])

    def test_reviewed_requires_identity_date_and_source_bytes(self):
        for missing in ("reviewer", "reviewed_at_utc", "source_sha256"):
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                item = dict(self.attested)
                item.pop(missing)
                self.build([item])

    def test_review_date_cannot_precede_observation(self):
        with self.assertRaises(ValueError):
            self.build([dict(self.attested, reviewed_at_utc="2026-10-01T09:00:00Z")])

    def test_future_or_naive_timestamp_rejected(self):
        for bad in ("2099-01-01T00:00:00Z", "2026-10-25T14:00:00",
                    "2026-10-25T14:00:00+01:00"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.build([dict(self.pending, observed_at_utc=bad)])

    def test_untrusted_source_urls_rejected(self):
        urls = ("http://example.com", "https://localhost/doc",
                "https://127.0.0.1/doc", "https://user:secret@example.com/file",
                "https://example.com:443/file", "https://example.com/file#anchor",
                "https://example.com/\nmalicious", "https://example.local/file")
        for value in urls:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.build([dict(self.pending, source_url=value)])

    def test_worklist_forged_rights_claim_or_incomplete_scope_rejected(self):
        self.worklist["items"][0]["rights_review_checklist"][self.check] = "VERIFIED"
        with self.assertRaises(ValueError):
            self.build([])
        self.worklist["items"][0]["rights_review_checklist"][self.check] = "NOT_VERIFIED"
        self.worklist["items"].pop()
        with self.assertRaises(ValueError):
            self.build([])

    def test_reviewed_report_not_fetched_under_correct_trial_rejected(self):
        other = next(x for x in self.worklist["items"] if x["nct_id"] == "NCT00000002")
        submission = dict(
            self.attested, nct_id=other["nct_id"], ticker=other["ticker"],
            issuer_sec_cik=other["issuer_sec_cik"],
        )
        with self.assertRaises(ValueError):
            self.build([submission])

    def test_pending_claim_requires_substantive_text(self):
        with self.assertRaises(ValueError):
            self.build([dict(self.pending, claim="short")])

    def test_malformed_submissions_fail_closed(self):
        for value in (None, {}, ["not-a-dict"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.build(value)


if __name__ == "__main__":
    unittest.main()
