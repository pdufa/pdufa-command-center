import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_phase3_original_registry_pilot import SOURCE_CSV, STATUSES
from check_phase3_64_original_sources import (
    SAMPLE_LIMIT, select_64_original_studies,
    summarize_original_source_batch, run_64_source_check,
)


def sample():
    return select_64_original_studies(SOURCE_CSV.read_text(encoding="utf-8-sig"))


def fake_result(row):
    return {
        "nct_id": row["nct_id"],
        "census_status": row["status"],
        "census_ticker": row["ticker"],
        "source": "https://clinicaltrials.gov/api/v2/studies/" + row["nct_id"],
        "source_sha256": "a" * 64,
        "fetched_at_utc": "2026-10-26T15:00:00Z",
        "status_matches_dated_census": True,
        "phase3_in_current_registry": True,
        "verified_us_fda_pdufa": False,
        "verified_current_commercial_development_rights": False,
        "qualified_pipeline": None,
        "fda_approval_probability": None,
    }


class SourceBreadthTests(unittest.TestCase):
    def test_64_original_nct_ids_cover_eight_statuses_and_at_least_50_companies(self):
        selection = sample()
        self.assertEqual(len(selection), SAMPLE_LIMIT)
        self.assertEqual(len({r["nct_id"] for r in selection}), SAMPLE_LIMIT)
        self.assertGreaterEqual(len({r["ticker"] for r in selection}), 50)
        self.assertTrue(set(STATUSES).issubset({r["status"] for r in selection}))
        self.assertEqual(selection, sample())  # deterministic, bounded and repeatable
        for row in selection:
            self.assertEqual(row["source_url"],
                             "https://clinicaltrials.gov/study/" + row["nct_id"])

    def test_report_adjudicates_zero_pipeline_and_fda_claims_even_on_success(self):
        selected = sample()
        report = summarize_original_source_batch(
            selected, [fake_result(item) for item in selected], "2026-10-26T15:00:00Z"
        )
        self.assertEqual(report["retrieved_exact_identity_count"], 64)
        self.assertEqual(report["failed_original_source_count"], 0)
        self.assertTrue(report["all_original_sources_retrieved"])
        self.assertIsNone(report["qualified_pipeline_total"])
        self.assertIsNone(report["verified_fda_pdufa_total"])
        self.assertIsNone(report["calibrated_approval_probabilities"])
        self.assertEqual(len(report["source_records"]), 64)
        self.assertEqual(len(report["selected_original_nct_ids"]), 64)
        self.assertEqual(report["status_differences_from_dated_census"], [])
        self.assertEqual(report["no_longer_phase3_in_source"], [])

    def test_changed_status_and_phase_are_explicit_nonfatal_research_flags(self):
        selected = sample()
        observed = [fake_result(row) for row in selected]
        observed[0]["status_matches_dated_census"] = False
        observed[1]["phase3_in_current_registry"] = False
        report = summarize_original_source_batch(selected, observed, "2026-10-26T15:00:00Z")
        self.assertEqual(report["status_differences_from_dated_census"], [selected[0]["nct_id"]])
        self.assertEqual(report["no_longer_phase3_in_source"], [selected[1]["nct_id"]])
        self.assertTrue(report["all_original_sources_retrieved"])
        self.assertIsNone(report["qualified_pipeline_total"])

    def test_failed_source_does_not_disappear_or_count_as_verified(self):
        selected = sample()
        observed = [fake_result(row) for row in selected]
        observed[3] = {"nct_id": selected[3]["nct_id"], "error": "URLError"}
        report = summarize_original_source_batch(selected, observed, "2026-10-26T15:00:00Z")
        self.assertFalse(report["all_original_sources_retrieved"])
        self.assertEqual(report["retrieved_exact_identity_count"], 63)
        self.assertEqual(report["failed_original_source_count"], 1)
        self.assertEqual(report["source_errors"], [{"nct_id": selected[3]["nct_id"],"error_type":"URLError"}])
        self.assertIsNone(report["qualified_pipeline_total"])

    def test_forged_source_identifiers_and_fda_status_are_rejected(self):
        selected = sample()
        for edit in (
            {"source": "https://attacker.test/api/v2/studies/" + selected[0]["nct_id"]},
            {"nct_id": "NCT00000000"},
            {"source_sha256": "INVALID"},
            {"qualified_pipeline": True},
            {"verified_us_fda_pdufa": True},
            {"verified_current_commercial_development_rights": True},
            {"fda_approval_probability": 0.95},
            {"census_ticker": "FAKE"},
        ):
            observed = [fake_result(row) for row in selected]
            observed[0].update(edit)
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                summarize_original_source_batch(selected, observed, "2026-10-26T15:00:00Z")

    def test_incomplete_or_duplicated_samples_and_results_fail_closed(self):
        selected = sample()
        observed = [fake_result(row) for row in selected]
        for test_sample, test_results in (
            (selected[:63], observed[:63]),
            (selected, observed[:63]),
            (selected, observed + [observed[0]]),
            (selected, observed[1:] + observed[:1]),
            (selected[:-1] + selected[:1], observed),
        ):
            with self.assertRaises(ValueError):
                summarize_original_source_batch(test_sample, test_results, "2026-10-26T15:00:00Z")
        source = SOURCE_CSV.read_text(encoding="utf-8-sig")
        for altered in (source[:500], source.replace("NCT", "FCT", 1),
                        source.replace("RECRUITING", "FDA_APPROVED", 1)):
            with self.assertRaises(ValueError):
                select_64_original_studies(altered)

    def test_run_report_with_errors_has_artifact_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as dirname:
            file = Path(dirname) / "report.json"
            with patch("check_phase3_64_original_sources._fetch_catching",
                       side_effect=lambda row: {"nct_id": row["nct_id"], "error": "URLError"}):
                status = run_64_source_check(file)
            self.assertEqual(status, 1)
            report = json.loads(file.read_text(encoding="utf-8"))
            self.assertEqual(report["failed_original_source_count"], 64)
            self.assertEqual(report["retrieved_exact_identity_count"], 0)
            self.assertFalse(report["all_original_sources_retrieved"])
            self.assertIsNone(report["qualified_pipeline_total"])


if __name__ == "__main__":
    unittest.main()
