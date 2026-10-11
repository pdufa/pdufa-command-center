"""Step 3 tests: score gates, auditable append-only storage, and trial identity."""
import csv
import tempfile
import unittest
from pathlib import Path

from clinical_step3 import (WEIGHTS, evaluate, load_trial_catalog,
                             read_history, save_review, valid_url)


def valid_review():
    cats = {
        name: {
            "score": max_points // 2,
            "source_url": "https://clinicaltrials.gov/study/NCT12345678",
            "evidence_date": "2025-01-01",
            "reason": f"Source documents primary endpoint and {name.lower()} evidence."
        }
        for name, max_points in WEIGHTS.items()
    }
    return {
        "nct_id": "NCT12345678", "ticker": "ABC", "drug": "Drug X",
        "indication": "Disease Y", "phase": "PHASE3",
        "trial_source": "https://clinicaltrials.gov/study/NCT12345678",
        "ownership_verified": True,
        "ownership_evidence_url": "https://www.sec.gov/Archives/edgar/data/1/review.html",
        "ownership_evidence_date": "2025-01-01",
        "reviewer": "test-analyst", "categories": cats,
    }


class TestStep3(unittest.TestCase):
    def test_complete_source_supported_record_scored(self):
        row = evaluate(valid_review())
        self.assertEqual(row["score_total"], sum(w // 2 for w in WEIGHTS.values()))
        self.assertEqual(row["clinical_evidence_score"] + row["trial_design_score"], row["score_total"])
        self.assertEqual(row["status"], "SCORED — DOCUMENTED REVIEW")
        self.assertTrue(row["payload_checksum"])

    def test_no_score_until_ownership_verified(self):
        review = valid_review()
        review["ownership_verified"] = False
        row = evaluate(review)
        self.assertIsNone(row["score_total"])
        self.assertIn("NOT SCORED", row["status"])

    def test_missing_category_means_not_scored_not_zero(self):
        review = valid_review()
        review["categories"]["Statistical strength"]["score"] = "NOT ASSESSED"
        row = evaluate(review)
        self.assertIsNone(row["score_total"])
        self.assertIn("Statistical strength", row["explanation"])

    def test_genuine_zero_not_missing(self):
        review = valid_review()
        review["categories"]["Statistical strength"]["score"] = 0
        self.assertIsNotNone(evaluate(review)["score_total"])

    def test_invalid_score_above_weight_rejected(self):
        review = valid_review()
        review["categories"]["Safety and tolerability"]["score"] = 21
        with self.assertRaises(ValueError):
            evaluate(review)

    def test_category_requires_link_and_reason(self):
        review = valid_review()
        review["categories"]["Trial design quality"]["source_url"] = ""
        with self.assertRaises(ValueError):
            evaluate(review)
        review = valid_review()
        review["categories"]["Trial design quality"]["reason"] = "unclear"
        with self.assertRaises(ValueError):
            evaluate(review)

    def test_refuse_insecure_source_and_future_date(self):
        self.assertFalse(valid_url("javascript:alert(1)"))
        review = valid_review()
        review["categories"]["Earlier clinical efficacy evidence"]["evidence_date"] = "2099-01-01"
        with self.assertRaises(ValueError):
            evaluate(review)

    def test_no_unlinked_unknown_nct(self):
        review = valid_review()
        review["nct_id"] = "NCTfake"
        with self.assertRaises(ValueError):
            evaluate(review)

    def test_immutable_history_revisions(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "nested" / "assessments.sqlite3"
            review = valid_review()
            first = save_review(review, db)
            review["categories"]["Safety and tolerability"]["score"] = 1
            second = save_review(review, db)
            hist = read_history(db)
            self.assertEqual((first, second), (1, 2))
            self.assertEqual(len(hist), 2)
            self.assertEqual(hist[0]["score_total"] + (WEIGHTS["Safety and tolerability"]//2 - 1), hist[1]["score_total"])
            self.assertNotEqual(hist[0]["payload_checksum"], hist[1]["payload_checksum"])

    def test_trial_catalog_keeps_distinct_issuer_links_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "trials.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                wr = csv.DictWriter(f, fieldnames=["nct_id", "ticker", "phase", "drug", "indication"])
                wr.writeheader()
                wr.writerows([
                    {"nct_id": "NCT12345678", "ticker": "AAA", "phase": "PHASE1", "drug": "X", "indication": "D"},
                    {"nct_id": "NCT12345678", "ticker": "BBB", "phase": "PHASE2", "drug": "X", "indication": "D"},
                    {"nct_id": "NCT12345678", "ticker": "AAA", "phase": "PHASE1", "drug": "X", "indication": "D"},
                    {"nct_id": "NCT87654321", "ticker": "CCC", "phase": "PHASE4", "drug": "Z", "indication": "D"},
                ])
            catalog = load_trial_catalog(path)
            self.assertEqual(len(catalog), 2)
            self.assertEqual({r["Ticker"] for r in catalog}, {"AAA", "BBB"})
            self.assertTrue(all(r["Issuer match"].startswith("UNVERIFIED") for r in catalog))


if __name__ == "__main__":
    unittest.main()
