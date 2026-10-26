"""SEC submissions indexes must not silently become verified drug rights."""
import sys
import urllib.error
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_phase3_sec_rights_filing_candidates import (
    audit, extract_filing_candidates, load_originals, sec_filing_url,
)


class SecRightsSourceDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        trials, companies = load_originals()
        cls.by_cik = {r["cik"]: r for r in companies}

    @staticmethod
    def make_payload(cik, ticker="EXAMPLE"):
        return {
            "cik": int(cik), "tickers": [ticker],
            "filings": {"recent": {
                "form": ["10-K", "8-K", "10-Q", "4"],
                "filingDate": ["2026-03-02", "2026-08-25", "2026-06-01", "2026-10-01"],
                "accessionNumber": [
                    "0001234567-26-000003", "0001234567-26-000004",
                    "0001234567-26-000002", "0001234567-26-000005",
                ],
                "primaryDocument": ["annual.htm", "material.htm", "quarterly.htm", "form4.htm"],
            }}
        }

    def test_all_130_issuer_metadata_and_741_trial_links_not_rights(self):
        def mock_fetch(cik):
            return self.make_payload(cik, self.by_cik[cik]["ticker"])
        report = audit(mock_fetch, lambda _: None)
        self.assertEqual(report["sec_metadata_retrieved"], 130)
        self.assertEqual(report["sec_metadata_unresolved"], 0)
        self.assertEqual(report["issuers_with_candidate_primary_filings"], 130)
        self.assertEqual(report["trials_with_issuer_filing_candidate_pointers"], 741)
        self.assertEqual(len(report["trials"]), 741)
        self.assertEqual(len({r["nct_id"] for r in report["trials"]}), 741)
        self.assertEqual(report["current_rights_primary_documents_verified"], 0)
        self.assertEqual(report["fda_pdufa_verified"], 0)
        self.assertIsNone(report["qualified_pipeline_count"])
        self.assertTrue(all(not r["current_rights_primary_source_verified"] and
                            r["qualified_pipeline"] is None for r in report["trials"]))
        self.assertTrue(all(r["ticker_present_in_sec_submissions"] is True
                            for r in report["issuers"]))

    def test_network_failure_stays_unresolved(self):
        first = next(iter(self.by_cik))
        def mock_fetch(cik):
            if cik == first:
                raise OSError("SEC temporarily unavailable")
            return self.make_payload(cik, self.by_cik[cik]["ticker"])
        report = audit(mock_fetch, lambda _: None)
        self.assertEqual(report["sec_metadata_retrieved"], 129)
        self.assertEqual(report["sec_metadata_unresolved"], 1)
        missing = [r for r in report["issuers"] if r["cik"] == first]
        self.assertEqual(missing[0]["sec_source_status"], "UNRESOLVED")
        self.assertIsNone(missing[0]["official_metadata_retrieved_at_utc"])
        affected = [r for r in report["trials"] if r["issuer_cik"] == first]
        self.assertTrue(affected)
        self.assertTrue(all(not r["issuer_primary_document_candidates"] for r in affected))
        self.assertIsNone(report["qualified_pipeline_count"])

    def test_three_http403_errors_stop_all_remaining_sec_automated_requests(self):
        requested = []
        def blocked(cik):
            requested.append(cik)
            raise urllib.error.HTTPError(
                "https://data.sec.gov/submissions/CIK" + cik + ".json",
                403, "Forbidden", {}, None)
        report = audit(blocked, lambda _: None)
        self.assertEqual(len(requested), 3)
        self.assertEqual(report["sec_actual_requests_attempted"], 3)
        self.assertTrue(report["sec_access_denied_circuit_breaker"])
        self.assertEqual(report["sec_metadata_unresolved"], 130)
        self.assertEqual(sum(r["sec_source_status"] == "SEC_ACCESS_BLOCKED_403"
                             for r in report["issuers"]), 127)
        self.assertEqual(report["trials_with_issuer_filing_candidate_pointers"], 0)
        self.assertIsNone(report["qualified_pipeline_count"])

    def test_reject_mismatched_cik(self):
        data = self.make_payload("0001234567")
        with self.assertRaisesRegex(ValueError, "mismatched"):
            extract_filing_candidates("0001234568", data)

    def test_links_sanitize_primary_documents(self):
        url = sec_filing_url("0001234567", "0001234567-26-000003", "annual.htm")
        self.assertEqual(url, "https://www.sec.gov/Archives/edgar/data/1234567/000123456726000003/annual.htm")
        with self.assertRaises(ValueError):
            sec_filing_url("0001234567", "0001234567-26-000003", "../../other.htm")

    def test_annual_and_current_forms_are_only_research_candidates(self):
        data = self.make_payload("0001234567")
        results = extract_filing_candidates("0001234567", data)
        self.assertEqual(results["relevant_form_entries"], 3)
        self.assertTrue(results["latest_annual_report"]["is_annual_report"])
        self.assertTrue(all(r["rights_document_relevance"] == "NOT_YET_REVIEWED"
                            for r in results["candidate_filings"]))
        self.assertNotIn("4", {r["form"] for r in results["candidate_filings"]})

    def test_reject_misaligned_sec_metadata_columns(self):
        data = self.make_payload("0001234567")
        data["filings"]["recent"]["form"].pop()
        with self.assertRaisesRegex(ValueError, "differing lengths"):
            extract_filing_candidates("0001234567", data)


if __name__ == "__main__":
    unittest.main()
