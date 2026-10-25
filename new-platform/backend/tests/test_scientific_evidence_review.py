"""Offline tests for review promotion safeguards."""
import copy
import unittest
from datetime import datetime, timezone

from app.scientific_dossier import build_scientific_dossier
from app.scientific_evidence_review import attach_reviewed_finding


class ReviewedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.dossier = build_scientific_dossier(
            "TRIAL|NCT12345678", "NCT12345678",
            {"protocolSection": {"identificationModule": {"nctId": "NCT12345678"}}},
        )
        self.finding = {
            "nct_id": "NCT12345678", "domain": "clinical_results",
            "claim": "The publication describes a prespecified endpoint.",
            "source_kind": "pubmed", "source_id": "12345678",
            "source_locator": "Results paragraph 2",
            "source_date": "2024-03-10", "reviewer": "Test reviewer",
            "reviewed_at": "2026-10-20T12:00:00Z",
            "rationale": "Exact endpoint language located in publication.",
            "stance": "inconclusive", "certainty": "low",
        }

    def test_explicit_review_is_source_linked_and_unscored(self):
        original = copy.deepcopy(self.dossier)
        out = attach_reviewed_finding(self.dossier, self.finding)
        self.assertEqual(self.dossier, original)
        finding = out["domains"]["clinical_results"]["reviewed_findings"][0]
        self.assertEqual(finding["source_url"], "https://pubmed.ncbi.nlm.nih.gov/12345678/")
        self.assertEqual(finding["verification_status"], "analyst_reviewed_claim")
        self.assertFalse(finding["independent_replication_confirmed"])
        self.assertIsNone(out["overall_score"])
        self.assertIsNone(out["fda_approval_probability"])
        self.assertEqual(out["assessment_status"], "incomplete")
        self.assertTrue(all(d["score"] is None for d in out["domains"].values()))

    def test_wrong_trial_rejected(self):
        finding = {**self.finding, "nct_id": "NCT87654321"}
        with self.assertRaisesRegex(ValueError, "NCT mismatch"):
            attach_reviewed_finding(self.dossier, finding)

    def test_missing_review_details_rejected(self):
        for key in ("claim", "source_locator", "rationale", "reviewer",
                    "source_date", "reviewed_at", "stance", "certainty"):
            with self.subTest(key=key):
                finding = {**self.finding}
                finding.pop(key)
                with self.assertRaises(ValueError):
                    attach_reviewed_finding(self.dossier, finding)

    def test_unapproved_source_and_wrong_registry_rejected(self):
        for kind, source in (("website", "12345678"), ("pubmed", "bad"),
                             ("clinicaltrials", "NCT87654321")):
            with self.subTest(kind=kind, source=source):
                with self.assertRaises(ValueError):
                    attach_reviewed_finding(self.dossier, {
                        **self.finding, "source_kind": kind, "source_id": source,
                    })

    def test_future_or_naive_review_rejected(self):
        for when in ("2099-01-01T12:00:00Z", "2026-10-20T12:00:00"):
            with self.subTest(when=when):
                with self.assertRaises(ValueError):
                    attach_reviewed_finding(self.dossier, {
                        **self.finding, "reviewed_at": when,
                    })

    def test_future_source_date_rejected(self):
        with self.assertRaises(ValueError):
            attach_reviewed_finding(self.dossier, {
                **self.finding, "source_date": "2026-10-21",
            })

    def test_scored_domain_rejected(self):
        dossier = copy.deepcopy(self.dossier)
        dossier["domains"]["clinical_results"]["score"] = 95
        with self.assertRaisesRegex(ValueError, "scored"):
            attach_reviewed_finding(dossier, self.finding)

    def test_fda_record_requires_explicit_application_number(self):
        finding = {**self.finding, "source_kind": "fda", "source_id": "NDA012345"}
        out = attach_reviewed_finding(self.dossier, finding)
        self.assertEqual(out["domains"]["clinical_results"]["reviewed_findings"][0]["source_id"], "NDA012345")
        self.assertIsNone(out["overall_score"])


if __name__ == "__main__":
    unittest.main()
