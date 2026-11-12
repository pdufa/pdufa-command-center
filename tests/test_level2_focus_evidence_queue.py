"""Level 2 saved FOCUS cohort: evidence leads remain distinct from hypotheses."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
PATH = ROOT / "scripts" / "level2_focus_evidence_queue.py"
SPEC = importlib.util.spec_from_file_location("level2_focus_evidence_queue", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def sample():
    return {
        "schemaVersion": 1,
        "asOf": "2026-11-10",
        "records": [{
            "nct": "NCT01234567", "ticker": "TEST", "company": "Synthetic Test Co.",
            "resultsUrl": "https://clinicaltrials.gov/study/NCT01234567",
            "regulatoryUrl": "https://example.org/synthetic-program",
        }],
    }


class FocusLevelTwoQueueTests(unittest.TestCase):
    def test_source_leads_not_clinical_evidence(self):
        report = MODULE.build_review_queue(sample())
        self.assertEqual(report["trial_count"], 1)
        self.assertFalse(report["current_live_focus_membership_confirmed"])
        self.assertEqual(report["level2_assessments_completed"], 0)
        self.assertEqual(report["outcome_predictions_generated"], 0)
        item = report["records"][0]
        self.assertEqual(len(item["source_leads"]), 2)
        self.assertEqual(item["hypothesis_review"]["sources"], [])
        self.assertFalse(item["hypothesis_review"]["scientifically_verified"])
        self.assertFalse(item["hypothesis_review"]["assessment_complete"])
        self.assertIsNone(item["approval_probability"])
        self.assertIn("mechanism_claim", item["hypothesis_review"]["missing_for_review"])

    def test_actual_saved_focus_snapshot_is_29_distinct_trials(self):
        path = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        report = MODULE.build_review_queue(data)
        self.assertEqual(report["snapshot_as_of"], data["asOf"])
        self.assertEqual(report["trial_count"], len(data["records"]))
        self.assertEqual(len(set(row["nct"] for row in report["records"])), len(data["records"]))
        for item in report["records"]:
            self.assertEqual(
                item["status"], "SOURCE_COLLECTION_AND_HYPOTHESIS_REVIEW_REQUIRED"
            )
            self.assertEqual(
                item["hypothesis_review"]["status"],
                "INCOMPLETE_HYPOTHESIS_AWAITING_EVIDENCE",
            )
            self.assertFalse(item["hypothesis_review"]["assessment_complete"])
            self.assertTrue(all(
                s["status"] == "UNOPENED_SNAPSHOT_SOURCE_LEAD_NOT_VERIFIED"
                for s in item["source_leads"]
            ))

    def test_reject_duplicate_trial(self):
        data = sample()
        data["records"].append(data["records"][0].copy())
        with self.assertRaises(ValueError):
            MODULE.build_review_queue(data)

    def test_reject_invalid_trial_identity(self):
        for value in ("NCT1", "NCT١٢٣٤٥٦٧٨", "NCT123456789"):
            with self.subTest(nct=value):
                data = sample()
                data["records"][0]["nct"] = value
                with self.assertRaises(ValueError):
                    MODULE.build_review_queue(data)

    def test_reject_source_lead_with_credentials_or_fragments(self):
        for value in (
            "https://user:secret@example.org/study",
            "https://example.org/study#fragment",
            "http://example.org/study",
            "https://example.org/name with spaces",
            "https://example.org:bad/study",
        ):
            with self.subTest(url=value):
                data = sample()
                data["records"][0]["resultsUrl"] = value
                with self.assertRaises(ValueError):
                    MODULE.build_review_queue(data)

    def test_reject_bad_as_of_and_missing_cohort(self):
        for as_of in ("2026-02-30", "2026-11", "2026-13-01"):
            data = sample()
            data["asOf"] = as_of
            with self.assertRaises(ValueError):
                MODULE.build_review_queue(data)
        data = sample()
        data["records"] = []
        with self.assertRaises(ValueError):
            MODULE.build_review_queue(data)

    def test_saved_fda_status_does_not_make_approval_prediction(self):
        data = sample()
        data["records"][0]["fdaStatus"] = "NDA accepted, PDUFA date assigned"
        data["records"][0]["recordedPdufaDate"] = "2026-12-01"
        report = MODULE.build_review_queue(data)
        self.assertEqual(report["outcome_predictions_generated"], 0)
        self.assertIsNone(report["records"][0]["approval_probability"])
        self.assertFalse(report["records"][0]["phase_verified_by_this_queue"])


if __name__ == "__main__":
    unittest.main()
