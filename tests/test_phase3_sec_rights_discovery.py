import copy
import hashlib
import json
import re
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_sec_rights_discovery import discover, case_issuers, recent_primary_filings


def fixture_casebook():
    items = []
    for i in range(741):
        serial = i % 130 + 1
        cik = f"{serial:010d}"
        items.append({
            "nct_id": f"NCT{i+1:08d}", "ticker": f"T{serial:03d}",
            "saved_sec_cik": cik,
            "saved_sec_submissions_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
            "rights_verification_status": "NOT_ESTABLISHED",
            "independent_rights_source_url": None,
            "qualified_pipeline": None,
        })
    return {
        "report_type": "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY",
        "total_trials": 741, "saved_issuer_pointers": 130,
        "rights_verified_trials": 0, "rights_unverified_trials": 741,
        "qualified_pipeline_total": None, "items": items,
    }


def mock_fetch(url):
    if url.startswith("https://data.sec.gov/submissions/CIK"):
        cik = re.search(r"CIK([0-9]{10})", url).group(1)
        serial = int(cik)
        return json.dumps({
            "cik": int(cik), "tickers": [f"T{serial:03d}"],
            "filings": {"recent": {
                "form": ["8-K", "10-K", "10-Q"],
                "filingDate": ["2026-10-01", "2026-09-20", "2026-09-01"],
                "accessionNumber": [
                    f"{cik}-26-000001", f"{cik}-26-000002", f"{cik}-26-000003"],
                "primaryDocument": ["current.htm", "annual.htm", "quarterly.htm"],
            }},
        }).encode()
    if url.startswith("https://www.sec.gov/Archives/edgar/data/"):
        return b"<html>We entered into a license arrangement for an unrelated product.</html>"
    raise AssertionError(f"Unexpected off-domain request {url}")


class SECDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.casebook = fixture_casebook()

    def test_pilot_sources_fetched_but_rights_never_verified(self):
        report = discover(self.casebook, fetch=mock_fetch,
                          max_issuers=2, as_of=date(2026, 10, 26))
        self.assertEqual(report["total_issuers"], 130)
        self.assertEqual(report["total_trials"], 741)
        self.assertEqual(report["official_indices_validated"], 2)
        self.assertEqual(report["documents_fetched"], 4)
        self.assertEqual(report["document_rights_language_leads"], 4)
        self.assertEqual(report["issuer_status_counts"]["NOT_SCANNED"], 128)
        self.assertEqual(report["independently_verified_current_rights"], 0)
        self.assertIsNone(report["qualified_pipeline_total"])
        self.assertEqual(len(report["issuer_rows"]), 130)
        for row in report["issuer_rows"][:2]:
            self.assertFalse(row["rights_verified"])
            for doc in row["document_fetches"]:
                self.assertEqual(doc["retrieval_status"], "FETCHED_RESEARCH_ONLY")
                self.assertRegex(doc["sha256"], r"^[a-f0-9]{64}$")
                self.assertFalse(doc["commercial_rights_verified"])

    def test_no_identifying_agent_makes_no_request(self):
        report = discover(self.casebook, max_issuers=1, agent="",
                          as_of=date(2026, 10, 26))
        self.assertEqual(report["issuer_status_counts"]["IDENTIFYING_AGENT_REQUIRED"], 1)
        self.assertEqual(report["issuer_status_counts"]["NOT_SCANNED"], 129)
        self.assertEqual(report["documents_fetched"], 0)

    def test_mismatched_cik_filing_index_is_rejected(self):
        def wrong(url):
            if "data.sec.gov" in url:
                return mock_fetch(url).replace(b'"cik": 1', b'"cik": 999')
            raise AssertionError("Must not fetch filing with wrong issuer CIK")
        report = discover(self.casebook, fetch=wrong, max_issuers=1,
                          as_of=date(2026, 10, 26))
        self.assertEqual(report["issuer_status_counts"]["INVALID_OR_MISMATCHED_OFFICIAL_SOURCE"], 1)
        self.assertEqual(report["documents_fetched"], 0)

    def test_network_unavailable_is_not_no_legal_rights(self):
        def unavailable(url):
            raise OSError("Simulated 403")
        report = discover(self.casebook, fetch=unavailable, max_issuers=2,
                          as_of=date(2026, 10, 26))
        self.assertEqual(report["issuer_status_counts"]["SOURCE_UNAVAILABLE"], 2)
        self.assertEqual(report["independently_verified_current_rights"], 0)

    def test_missing_casebook_trial_fails_closed(self):
        self.casebook["items"].pop()
        with self.assertRaises(ValueError):
            case_issuers(self.casebook)

    def test_conflicting_saved_issuer_link_fails_closed(self):
        self.casebook["items"][0]["saved_sec_submissions_url"] = "https://example.org/not-sec"
        with self.assertRaises(ValueError):
            case_issuers(self.casebook)

    def test_existing_rights_claim_fails_closed(self):
        self.casebook["items"][0]["rights_verification_status"] = "VERIFIED"
        with self.assertRaises(ValueError):
            case_issuers(self.casebook)

    def test_untrusted_filename_dropped(self):
        payload = {
            "cik": 1, "tickers": ["T001"],
            "filings": {"recent": {
                "form": ["8-K"], "filingDate": ["2026-10-01"],
                "accessionNumber": ["0000000001-26-000001"],
                "primaryDocument": ["../traversal.htm"],
            }},
        }
        result = recent_primary_filings(json.dumps(payload).encode(), "0000000001",
                                        "T001", date(2026, 10, 26))
        self.assertEqual(result, [])

    def test_future_filing_not_used(self):
        payload = {
            "cik": 1, "tickers": ["T001"],
            "filings": {"recent": {
                "form": ["10-K"], "filingDate": ["2027-01-01"],
                "accessionNumber": ["0000000001-27-000001"],
                "primaryDocument": ["annual.htm"],
            }},
        }
        self.assertEqual(recent_primary_filings(json.dumps(payload).encode(),
                                                "0000000001", "T001", date(2026, 10, 26)), [])

    def test_fetch_without_rights_words_not_a_negative_finding(self):
        def fetch(url):
            if "data.sec.gov" in url:
                return mock_fetch(url)
            return b"<html>Financial statements and business overview.</html>"
        report = discover(self.casebook, fetch=fetch, max_issuers=1,
                          as_of=date(2026, 10, 26))
        self.assertEqual(report["documents_fetched"], 2)
        self.assertEqual(report["document_rights_language_leads"], 0)
        self.assertEqual(report["independently_verified_current_rights"], 0)


if __name__ == "__main__":
    unittest.main()
