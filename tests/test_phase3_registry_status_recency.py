"""Source-linked and nonqualifying nightly registered status / freshness audit."""
import copy
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_phase3_original_registry_pilot import SOURCE_CSV
from phase3_qualification_ledger import build_ledger
from phase3_registry_status_recency import (
    BUCKETS, PRIORITIES, build_report, safe_cell, write_csv,
)

AS_OF = datetime(2026, 10, 26, 20, tzinfo=timezone.utc)
DATES = ("2026-10-26", "2026-06-01", "2025-03-01", None,
         "2026-11-26", "2026-01-10")


class Phase3StatusRecencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        items = list(csv.DictReader(SOURCE_CSV.read_text(encoding="utf-8-sig").splitlines()))
        cls.saved = items
        original = []
        for i, row in enumerate(items):
            nct = row["nct_id"]
            original.append({
                "nct_id": nct, "census_ticker": row["ticker"],
                "census_company": row["company"],
                "census_status": row["status"],
                "current_registry_status": row["status"],
                "status_matches_dated_census": True,
                "phase3_in_current_registry": True,
                "registry_study_title": "Original registered study " + nct,
                "currently_registered_lead_sponsor": row["company"],
                "source_posted_update_date": DATES[i % len(DATES)],
                "source": "https://clinicaltrials.gov/api/v2/studies/" + nct,
                "source_sha256": hashlib.sha256(nct.encode()).hexdigest(),
                "fetched_at_utc": "2026-10-26T12:00:00+00:00",
                "verified_current_commercial_development_rights": False,
                "verified_us_fda_pdufa": False,
                "qualified_pipeline": None,
                "fda_approval_probability": None,
            })
        cls.original_registry = {
            "report_type": "MAIN_ORIGINAL_PHASE3_FULL_CENSUS_RESEARCH_ONLY",
            "census_total": 741,
            "source_identity_verified": 741,
            "source_errors": [],
            "original_source_records": original,
            "qualified_pipeline_total": None,
        }
        cls.original_ledger = build_ledger(cls.original_registry)

    def setUp(self):
        self.registry = copy.deepcopy(self.original_registry)
        self.ledger = copy.deepcopy(self.original_ledger)

    def build(self):
        return build_report(self.registry, self.ledger, AS_OF)

    def test_complete_denominators_and_no_pipeline_promotion(self):
        report = self.build()
        self.assertEqual(report["historical_trial_count"], 741)
        self.assertEqual(report["source_identity_verified"], 741)
        self.assertEqual(len(report["items"]), 741)
        self.assertEqual(sum(report["current_registry_status_counts"].values()), 741)
        self.assertEqual(sum(report["dated_census_status_counts"].values()), 741)
        self.assertEqual(sum(report["registry_status_group_counts"].values()), 741)
        self.assertEqual(sum(report["source_posted_update_age_counts"].values()), 741)
        self.assertEqual(sum(report["research_priority_counts"].values()), 741)
        self.assertEqual(set(report["source_posted_update_age_counts"]), set(BUCKETS))
        self.assertEqual(set(report["research_priority_counts"]), set(PRIORITIES))
        self.assertEqual(report["registration_freshness_gate_verified_count"], 0)
        self.assertEqual(report["independently_verified_commercial_rights"], 0)
        self.assertIsNone(report["qualified_pipeline_total"])
        self.assertTrue(all(
            row["commercial_rights_verified"] is False
            and row["qualified_pipeline"] is None
            and row["registry_identity_gate"] == "PASS"
            for row in report["items"]
        ))

    def test_all_six_source_date_buckets_are_accounted_for(self):
        report = self.build()
        self.assertEqual(
            set(name for name, count in report["source_posted_update_age_counts"].items() if count > 0),
            {
                "POSTED_LAST_90_DAYS", "POSTED_91_TO_180_DAYS",
                "POSTED_181_TO_365_DAYS", "POSTED_OVER_365_DAYS",
                "POSTED_DATE_MISSING", "POSTED_DATE_IN_FUTURE_REVIEW",
            },
        )
        self.assertEqual(report["original_source_posted_update_missing"], 123)
        self.assertEqual(report["original_source_posted_update_over_365_days"], 124)

    def test_active_ended_ambiguous_are_registry_labels_not_qualifications(self):
        report = self.build()
        self.assertGreater(report["registry_active_status_only_count"], 0)
        self.assertGreater(report["registry_ended_status_only_count"], 0)
        self.assertGreater(report["registry_status_group_counts"]["OTHER_OR_UNCLEAR_REGISTRY_STATUS"], 0)
        self.assertIn("not proof of active drug development", report["limitations"])
        self.assertTrue(all(row["qualified_pipeline"] is None for row in report["items"]))

    def test_original_status_mismatch_requires_first_priority_without_disqualification(self):
        record = self.registry["original_source_records"][0]
        new_status = "SUSPENDED" if record["census_status"] != "SUSPENDED" else "COMPLETED"
        record["current_registry_status"] = new_status
        record["status_matches_dated_census"] = False
        self.ledger = build_ledger(self.registry)
        report = self.build()
        row = next(x for x in report["items"] if x["nct_id"] == record["nct_id"])
        self.assertEqual(row["review_priority"], PRIORITIES[0])
        self.assertEqual(row["registry_identity_gate"], "REVIEW")
        self.assertIsNone(row["qualified_pipeline"])
        self.assertEqual(report["registry_status_changed_since_saved_census"], 1)

    def test_non_phase3_registry_flag_remains_a_review_not_final_failed_trial(self):
        record = self.registry["original_source_records"][0]
        record["phase3_in_current_registry"] = False
        self.ledger = build_ledger(self.registry)
        row = next(x for x in self.build()["items"] if x["nct_id"] == record["nct_id"])
        self.assertEqual(row["review_priority"], PRIORITIES[0])
        self.assertEqual(row["registry_identity_gate"], "REVIEW")
        self.assertFalse(row["phase3_in_current_registry"])
        self.assertIsNone(row["qualified_pipeline"])

    def test_ambiguous_status_is_second_priority_without_treating_drug_as_inactive(self):
        record = self.registry["original_source_records"][0]
        record["current_registry_status"] = "SUSPENDED"
        record["status_matches_dated_census"] = False
        self.ledger = build_ledger(self.registry)
        row = next(x for x in self.build()["items"] if x["nct_id"] == record["nct_id"])
        self.assertEqual(row["registry_status_group"], "OTHER_OR_UNCLEAR_REGISTRY_STATUS")
        self.assertEqual(row["review_priority"], PRIORITIES[0])  # source conflict dominates

    def test_stale_update_is_research_priority_not_original_source_freshness_pass(self):
        pos = next(i for i, r in enumerate(self.saved) if r["status"] == "RECRUITING")
        source = self.registry["original_source_records"][pos]
        source["source_posted_update_date"] = "2024-01-01"
        report = self.build()
        row = next(x for x in report["items"] if x["nct_id"] == source["nct_id"])
        self.assertEqual(row["source_update_recency_bucket"], "POSTED_OVER_365_DAYS")
        self.assertEqual(row["review_priority"], PRIORITIES[2])
        self.assertFalse(row["commercial_rights_verified"])
        self.assertEqual(report["registration_freshness_gate_verified_count"], 0)

    def test_future_posted_date_is_review_not_failure(self):
        source = self.registry["original_source_records"][0]
        source["source_posted_update_date"] = "2027-01-02"
        row = next(x for x in self.build()["items"] if x["nct_id"] == source["nct_id"])
        self.assertLess(row["source_update_age_days"], 0)
        self.assertEqual(row["source_update_recency_bucket"], "POSTED_DATE_IN_FUTURE_REVIEW")
        self.assertIsNone(row["qualified_pipeline"])

    def test_mismatched_source_sha_rejected(self):
        self.ledger["records"][0]["source_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            self.build()

    def test_malformed_or_mismatched_status_flag_rejected(self):
        self.registry["original_source_records"][0]["status_matches_dated_census"] = False
        with self.assertRaises(ValueError):
            self.build()

    def test_unsupported_rights_or_fda_promotion_rejected(self):
        for field, value in (
            ("qualified_pipeline", True),
            ("verified_current_commercial_development_rights", True),
            ("verified_us_fda_pdufa", True),
            ("fda_approval_probability", 0.9),
        ):
            with self.subTest(field=field):
                saved = self.registry["original_source_records"][0][field]
                self.registry["original_source_records"][0][field] = value
                with self.assertRaises(ValueError):
                    self.build()
                self.registry["original_source_records"][0][field] = saved

    def test_other_mandatory_gate_pass_rejected(self):
        self.ledger["records"][0]["gates"]["active_phase3_development"] = "PASS"
        with self.assertRaises(ValueError):
            self.build()

    def test_duplicate_or_missing_registry_trial_rejected(self):
        self.registry["original_source_records"][0]["nct_id"] = self.registry[
            "original_source_records"][1]["nct_id"]
        with self.assertRaises(ValueError):
            self.build()

    def test_malformed_or_impossible_posted_date_rejected(self):
        for bad in ("2026-13-12", "2026-02-30", "2026/01/01", "yesterday", 99):
            with self.subTest(bad=bad):
                self.registry["original_source_records"][0]["source_posted_update_date"] = bad
                with self.assertRaises(ValueError):
                    self.build()

    def test_non_utc_source_timestamp_rejected(self):
        self.registry["original_source_records"][0]["fetched_at_utc"] = "2026-10-26T12:00:00"
        self.ledger["records"][0]["source_fetched_at_utc"] = "2026-10-26T12:00:00"
        with self.assertRaises(ValueError):
            self.build()

    def test_empty_title_or_malformed_sponsor_rejected(self):
        self.registry["original_source_records"][0]["registry_study_title"] = ""
        with self.assertRaises(ValueError):
            self.build()

    def test_csv_complete_sortable_and_zero_promotions(self):
        report = self.build()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "status.csv"
            write_csv(report, target)
            with target.open(encoding="utf-8", newline="") as handle:
                records = list(csv.DictReader(handle))
        self.assertEqual(len(records), 741)
        self.assertEqual(len({row["nct_id"] for row in records}), 741)
        self.assertEqual([row["review_position"] for row in records],
                         [str(i) for i in range(1, 742)])
        self.assertTrue(all(row["qualified_pipeline"] == "" for row in records))
        self.assertTrue(all(row["commercial_rights_verified"] == "False" for row in records))

    def test_csv_formula_prevention_for_source_names(self):
        self.assertEqual(safe_cell("=HYPERLINK(1)"), "'=HYPERLINK(1)")
        self.assertEqual(safe_cell("   +SUM(1,2)"), "'   +SUM(1,2)")
        self.assertEqual(safe_cell("-100"), "'-100")
        self.assertEqual(safe_cell("Normal source"), "Normal source")

    def test_csv_requires_unqualified_complete_report(self):
        report = self.build()
        report["qualified_pipeline_total"] = 23
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            write_csv(report, Path(directory) / "invalid.csv")


if __name__ == "__main__":
    unittest.main()
