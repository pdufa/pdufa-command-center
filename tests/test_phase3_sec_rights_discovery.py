import copy
import sys
import unittest
import urllib.error
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from phase3_sec_rights_discovery import build_report, candidate_filings, validate_casebook


class SecRightsDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.casebook = {
            "report_type": "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY",
            "total_trials": 741, "saved_issuer_pointers": 130,
            "rights_unverified_trials": 741, "rights_verified_trials": 0,
            "qualified_pipeline_total": None, "items": [],
        }
        for i in range(741):
            ordinal = i % 130 + 1
            nct = f"NCT{i + 1:08d}"
            cik = f"{ordinal:010d}"
            self.casebook["items"].append({
                "nct_id": nct, "ticker": f"TEST{ordinal:03d}", "saved_sec_cik": cik,
                "saved_sec_submissions_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
                "original_registry_api_url": f"https://clinicaltrials.gov/api/v2/studies/{nct}",
                "original_registry_sha256": "a" * 64,
                "rights_verification_status": "NOT_ESTABLISHED",
                "independent_rights_source_url": None, "qualified_pipeline": None,
            })
        self.calls = []

    def fetch(self, cik):
        self.calls.append(cik)
        return ({
            "cik": str(int(cik)),
            "filings": {"recent": {
                "form": ["8-K", "10-K", "10-Q", "S-3"],
                "filingDate": ["2026-10-10", "2026-02-15", "2025-09-01", "2026-10-08"],
                "accessionNumber": ["0000123456-26-000001", "0000123456-26-000002",
                                    "0000123456-25-000003", "0000123456-26-000004"],
                "primaryDocument": ["filing.htm", "annual.htm", "quarter.htm", "s3.htm"],
            }},
        }, "b" * 64)

    def build(self, fetch=None):
        return build_report(self.casebook, fetcher=fetch or self.fetch,
                            as_of=date(2026, 10, 26), sleep=lambda _: None)

    def test_130_issuer_741_trial_research_only_coverage(self):
        report = self.build()
        self.assertEqual(len(self.calls), 130)
        self.assertEqual(report["issuer_metadata_fetched"], 130)
        self.assertEqual(report["total_trials"], 741)
        self.assertEqual(report["trials_with_issuer_filing_leads"], 741)
        self.assertEqual(report["verified_current_commercial_rights"], 0)
        self.assertIsNone(report["qualified_pipeline_total"])
        self.assertTrue(all(x["development_rights_verified"] is False and
                            x["qualified_pipeline"] is None for x in report["trials"]))
        self.assertEqual(len(report["issuers"][0]["candidate_filings"]), 3)

    def test_sec_primary_archive_url_requires_real_filing_metadata(self):
        filings = candidate_filings(self.fetch("0000000001")[0], "0000000001",
                                    date(2026, 10, 26))
        self.assertTrue(all(x["primary_document_url"].startswith(
            "https://www.sec.gov/Archives/edgar/data/1/") for x in filings))
        self.assertTrue(all(x["source_type"] == "SEC_FILING_METADATA_LINK_ONLY"
                            and x["rights_verified"] is False for x in filings))

    def test_sec_cik_mismatch_is_source_invalid_for_each_issuer(self):
        def mismatch(cik):
            payload, digest = self.fetch(cik)
            payload["cik"] = "9999999999"
            return payload, digest
        report = self.build(mismatch)
        self.assertEqual(report["issuer_metadata_fetched"], 0)
        self.assertEqual(report["issuer_status_counts"]["SEC_SOURCE_INVALID"], 130)
        self.assertEqual(report["verified_current_commercial_rights"], 0)

    def test_sec_retrieval_failure_never_looks_like_no_rights(self):
        def failure(cik):
            raise urllib.error.HTTPError("https://data.sec.gov", 403, "Forbidden", None, None)
        report = self.build(failure)
        self.assertEqual(report["issuer_metadata_unavailable_or_invalid"], 130)
        self.assertEqual(report["issuer_status_counts"]["SEC_SOURCE_UNAVAILABLE"], 130)
        self.assertEqual(report["rights_verified_trials"] if "rights_verified_trials" in report
                         else report["verified_current_commercial_rights"], 0)
        self.assertTrue(all(x["source_error_type"] == "HTTP_403" for x in report["issuers"]))

    def test_filename_traversal_and_fake_forms_filtered(self):
        payload, _ = self.fetch("0000000001")
        payload["filings"]["recent"]["primaryDocument"][0] = "../../../fake.htm"
        filings = candidate_filings(payload, "0000000001", date(2026, 10, 26))
        self.assertEqual(len(filings), 2)
        self.assertNotIn("S-3", [x["form"] for x in filings])

    def test_old_and_future_filings_not_mistaken_for_current(self):
        payload, _ = self.fetch("0000000001")
        payload["filings"]["recent"]["filingDate"][0] = "2027-01-01"
        payload["filings"]["recent"]["filingDate"][1] = "2020-01-01"
        filings = candidate_filings(payload, "0000000001", date(2026, 10, 26))
        self.assertEqual(len(filings), 1)
        self.assertEqual(filings[0]["form"], "10-Q")

    def test_corrupted_sec_vectors_fail_closed(self):
        payload, _ = self.fetch("0000000001")
        payload["filings"]["recent"]["primaryDocument"].pop()
        with self.assertRaises(ValueError):
            candidate_filings(payload, "0000000001", date(2026, 10, 26))

    def test_casebook_duplicate_nct_rejected(self):
        self.casebook["items"][0]["nct_id"] = self.casebook["items"][1]["nct_id"]
        with self.assertRaises(ValueError):
            validate_casebook(self.casebook)

    def test_casebook_rights_claim_rejected(self):
        self.casebook["items"][0]["rights_verification_status"] = "VERIFIED"
        with self.assertRaises(ValueError):
            validate_casebook(self.casebook)

    def test_casebook_sec_url_mismatch_rejected(self):
        self.casebook["items"][0]["saved_sec_submissions_url"] = "https://fake.example"
        with self.assertRaises(ValueError):
            validate_casebook(self.casebook)

    def test_invalid_sec_digest_not_accepted(self):
        def invalid_digest(cik):
            payload, _ = self.fetch(cik)
            return payload, "unverifiable"
        report = self.build(invalid_digest)
        self.assertEqual(report["issuer_metadata_fetched"], 0)
        self.assertEqual(report["issuer_status_counts"]["SEC_SOURCE_INVALID"], 130)


if __name__ == "__main__":
    unittest.main()
