import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_phase3_original_registry_pilot import SOURCE_CSV
from check_phase3_registered_sponsors_741 import (
    TOTAL_TRIALS, TOTAL_TICKERS, CATEGORIES, source_population,
    compare_registered_sponsor, sponsor_research_report, run_comparison,
)

RAW = SOURCE_CSV.read_text(encoding="utf-8-sig")
VERSION = {"dataTimestamp": "2026-10-26T09:00:00", "apiVersion": "2.0.5"}


def sample():
    return source_population(RAW)


def successful(row):
    return {
        "nct_id": row["nct_id"],
        "census_company": row["company"],
        "census_ticker": row["ticker"],
        "census_status": row["status"],
        "currently_registered_lead_sponsor": row["company"],
        "current_registry_status": row["status"],
        "source_posted_update_date": "2026-10-25",
        "fetched_at_utc": "2026-10-26T15:00:00Z",
        "status_matches_dated_census": True,
        "phase3_in_current_registry": True,
        "source": "https://clinicaltrials.gov/api/v2/studies/" + row["nct_id"],
        "source_retrieval_method": "batch_filter_ids",
        "canonical_returned_study_sha256": "c" * 64,
        "qualified_pipeline": None,
        "verified_us_fda_pdufa": False,
        "verified_current_commercial_development_rights": False,
        "fda_approval_probability": None,
    }


class OriginalRegistrySponsorResearchTests(unittest.TestCase):
    def test_whole_population_exactly_741_distinct_nct_and_130_tickers(self):
        rows = sample()
        self.assertEqual(len(rows), TOTAL_TRIALS)
        self.assertEqual(len({r["nct_id"] for r in rows}), TOTAL_TRIALS)
        self.assertEqual(len({r["ticker"] for r in rows}), TOTAL_TICKERS)
        self.assertEqual(rows, sample())
        for mutation in (
            RAW[:300], RAW.replace("nct_id,ticker,company,status,source_url",
                                   "nct_id,ticker,company,approved,source_url"),
            RAW.replace("NCT", "FCT", 1),
        ):
            with self.assertRaises(ValueError):
                source_population(mutation)

    def test_exact_and_text_variants_are_not_issuer_rights_verified(self):
        self.assertEqual(compare_registered_sponsor("Acme Bio Inc.", "Acme Bio Inc."),
                         "EXACT_REGISTERED_SPONSOR_TEXT_MATCH")
        self.assertEqual(compare_registered_sponsor("Acme Bio Inc.", " ACME   BIO INC. "),
                         "NORMALIZED_TEXT_VARIANT_REVIEW")
        self.assertEqual(compare_registered_sponsor("Acme Bio Inc.", "Acme Biologics LLC"),
                         "REGISTERED_SPONSOR_NAME_DIFFERENCE_REVIEW")
        self.assertEqual(compare_registered_sponsor("Acme Bio Inc.", None),
                         "REGISTERED_SPONSOR_NOT_REPORTED")

    def test_741_original_exact_matches_still_have_null_regulatory_conclusions(self):
        rows = sample()
        observations = [successful(row) for row in rows]
        report = sponsor_research_report(rows, observations, VERSION, VERSION, "2026-10-26T15:00:00Z")
        self.assertEqual(report["original_registry_source_identities_retrieved"], 741)
        self.assertEqual(report["registered_sponsor_exact_text_matches"], 741)
        self.assertEqual(report["registered_sponsor_text_categories"]["EXACT_REGISTERED_SPONSOR_TEXT_MATCH"], 741)
        self.assertEqual(report["tickers_with_unresolved_registered_sponsor_text_or_sources"], 0)
        self.assertEqual(report["source_errors_count"], 0)
        self.assertTrue(report["completed_read_only_source_comparison"])
        self.assertEqual(report["dated_census_company_denominator"], 130)
        self.assertEqual(len(report["per_nct_source_comparisons"]), 741)
        for key in ("qualified_pipeline_count", "current_issuer_rights_verified_count",
                    "fda_pdufa_verified_count", "fda_approval_probabilities"):
            self.assertIsNone(report[key])
        self.assertTrue(all(record["qualified_pipeline"] is None
                            and record["verified_fda_pdufa"] is False
                            and record["verified_current_issuer_rights"] is False
                            for record in report["per_nct_source_comparisons"]))

    def test_report_precisely_discloses_text_differences_missing_sponsor_and_source(self):
        rows = sample()
        observations = [successful(row) for row in rows]
        observations[0]["currently_registered_lead_sponsor"] = " " + rows[0]["company"].upper() + " "
        observations[1]["currently_registered_lead_sponsor"] = "New sublicensee LLC"
        observations[2]["currently_registered_lead_sponsor"] = None
        observations[3] = {"nct_id": rows[3]["nct_id"], "error": "BATCH_SOURCE_UNVERIFIED"}
        observations[4]["status_matches_dated_census"] = False
        observations[5]["phase3_in_current_registry"] = False
        report = sponsor_research_report(rows, observations, VERSION, VERSION, "2026-10-26T15:00:00Z")
        counts = report["registered_sponsor_text_categories"]
        self.assertEqual(counts["EXACT_REGISTERED_SPONSOR_TEXT_MATCH"], 737)
        self.assertEqual(counts["NORMALIZED_TEXT_VARIANT_REVIEW"], 1)
        self.assertEqual(counts["REGISTERED_SPONSOR_NAME_DIFFERENCE_REVIEW"], 1)
        self.assertEqual(counts["REGISTERED_SPONSOR_NOT_REPORTED"], 1)
        self.assertEqual(counts["ORIGINAL_REGISTRY_SOURCE_UNVERIFIED"], 1)
        self.assertEqual(sum(counts.values()), 741)
        self.assertEqual(report["original_registry_source_identities_retrieved"], 740)
        self.assertEqual(report["source_errors_count"], 1)
        self.assertFalse(report["completed_read_only_source_comparison"])
        self.assertEqual(report["current_status_differs_from_dated_census_ids"], [rows[4]["nct_id"]])
        self.assertEqual(report["current_registry_phase3_not_reported_ids"], [rows[5]["nct_id"]])
        self.assertIsNone(report["qualified_pipeline_count"])

    def test_mismatched_nct_and_forged_pipeline_fda_or_company_source_block_report(self):
        rows = sample()
        original = [successful(row) for row in rows]
        for field, value in (
            ("nct_id", "NCT00000000"),
            ("census_ticker", "FAKE"),
            ("census_company", "Unrelated Company"),
            ("source", "https://attacker.invalid/api/v2/studies/" + rows[0]["nct_id"]),
            ("source_retrieval_method", "unknown"),
            ("canonical_returned_study_sha256", "spoofed"),
            ("qualified_pipeline", True),
            ("verified_us_fda_pdufa", True),
            ("verified_current_commercial_development_rights", True),
            ("fda_approval_probability", 0.85),
        ):
            altered = [dict(x) for x in original]
            altered[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                sponsor_research_report(rows, altered, VERSION, VERSION, "2026-10-26T15:00:00Z")
        with self.assertRaises(ValueError):
            sponsor_research_report(rows, original[:740], VERSION, VERSION, "2026-10-26T15:00:00Z")
        with self.assertRaises(ValueError):
            sponsor_research_report(rows, list(reversed(original)), VERSION, VERSION, "2026-10-26T15:00:00Z")

    def test_stale_source_version_does_not_mean_success(self):
        rows = sample()
        data = [successful(row) for row in rows]
        different = {**VERSION, "dataTimestamp": "2026-10-27T09:00:00"}
        for before, after in ((VERSION, different), (None, VERSION), (VERSION, None)):
            result = sponsor_research_report(rows, data, before, after, "2026-10-26T15:00:00Z")
            self.assertFalse(result["completed_read_only_source_comparison"])

    def test_full_run_without_source_connection_preserves_report_and_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sponsor-unverified.json"
            with patch("check_phase3_registered_sponsors_741.registry_version", return_value=VERSION), patch(
                "check_phase3_registered_sponsors_741.safe_fetch_group",
                side_effect=lambda group: [
                    {"nct_id": row["nct_id"], "error": "BATCH_SOURCE_UNVERIFIED"}
                    for row in group],
            ):
                result = run_comparison(path)
            self.assertEqual(result, 1)
            report = json.loads(path.read_text())
            self.assertEqual(report["source_errors_count"], 741)
            self.assertEqual(report["registered_sponsor_exact_text_matches"], 0)
            self.assertEqual(report["dated_census_company_denominator"], 130)
            self.assertIsNone(report["qualified_pipeline_count"])


if __name__ == "__main__":
    unittest.main()
