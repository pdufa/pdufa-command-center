import copy
import hashlib
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_sec_rights_documents_pilot import build_report, validate_leads, choose_documents, read_text


def mock_sources():
    casebook = {
        "report_type": "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY",
        "total_trials": 741, "saved_issuer_pointers": 130,
        "rights_verified_trials": 0, "rights_unverified_trials": 741,
        "qualified_pipeline_total": None, "items": [],
    }
    leads = {
        "report_type": "MAIN_PHASE3_SEC_RIGHTS_FILING_LEADS_RESEARCH_ONLY",
        "as_of": "2026-10-26", "total_issuers": 130, "total_trials": 741,
        "verified_current_commercial_rights": 0, "qualified_pipeline_total": None,
        "issuers": [], "trials": [],
    }
    for i in range(1, 131):
        ticker, cik = f"TEST{i:03d}", f"{i:010d}"
        current_acc, annual_acc = f"{cik}-26-000001", f"{cik}-26-000002"
        candidates = [
            {"form": "8-K", "filed_date": "2026-10-01",
             "accession_number": current_acc,
             "primary_document_url": f"https://www.sec.gov/Archives/edgar/data/{i}/{current_acc.replace('-', '')}/current.htm",
             "source_type": "SEC_FILING_METADATA_LINK_ONLY", "rights_verified": False},
            {"form": "10-K", "filed_date": "2026-09-01",
             "accession_number": annual_acc,
             "primary_document_url": f"https://www.sec.gov/Archives/edgar/data/{i}/{annual_acc.replace('-', '')}/annual.htm",
             "source_type": "SEC_FILING_METADATA_LINK_ONLY", "rights_verified": False},
        ]
        leads["issuers"].append({
            "ticker": ticker, "cik": cik, "linked_trial_count": 0,
            "sec_submissions_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
            "retrieval_status": "FILING_METADATA_LEADS", "candidate_filings": candidates,
            "source_sha256": "a" * 64, "rights_verified": False,
        })
    by_ticker = {r["ticker"]: r for r in leads["issuers"]}
    for i in range(741):
        j = i % 130 + 1
        ticker, cik, nct = f"TEST{j:03d}", f"{j:010d}", f"NCT{i+1:08d}"
        casebook["items"].append({
            "nct_id": nct, "ticker": ticker, "saved_sec_cik": cik,
            "saved_sec_submissions_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
            "original_registry_api_url": f"https://clinicaltrials.gov/api/v2/studies/{nct}",
            "original_registry_sha256": "f" * 64,
            "rights_verification_status": "NOT_ESTABLISHED",
            "independent_rights_source_url": None, "qualified_pipeline": None,
        })
        by_ticker[ticker]["linked_trial_count"] += 1
        leads["trials"].append({
            "nct_id": nct, "ticker": ticker, "saved_sec_cik": cik,
            "issuer_retrieval_status": "FILING_METADATA_LEADS",
            "issuer_candidate_filing_count": 2,
            "development_rights_verified": False, "qualified_pipeline": None,
        })
    return casebook, leads


class SECRightsDocumentPilotTests(unittest.TestCase):
    def setUp(self):
        self.casebook, self.leads = mock_sources()
        self.urls = []

    def fetch(self, url):
        self.urls.append(url)
        if url.endswith("annual.htm"):
            return b"<html>Consolidated financial statements</html>"
        return b"<html>Collaboration and license for other programs. </html>"

    def report(self, fetch=None, max_issuers=2):
        return build_report(self.casebook, self.leads, fetch=fetch or self.fetch,
                            max_issuers=max_issuers)

    def test_documents_fetched_with_sha_and_no_rights_promotion(self):
        result = self.report()
        self.assertEqual(result["total_trials"], 741)
        self.assertEqual(result["issuers_with_official_filing_leads"], 130)
        self.assertEqual(result["issuers_selected"], 2)
        self.assertEqual(result["documents_retrieved"], 4)
        self.assertEqual(result["documents_with_rights_language_locators"], 2)
        self.assertEqual(result["issuers_not_selected"], 128)
        self.assertEqual(result["independently_verified_current_rights"], 0)
        self.assertIsNone(result["qualified_pipeline_total"])
        self.assertEqual(len(self.urls), 4)
        for issuer in result["issuers"][:2]:
            for document in issuer["documents"]:
                self.assertEqual(document["retrieval_status"], "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY")
                self.assertRegex(document["source_sha256"], r"^[a-f0-9]{64}$")
                self.assertFalse(document["verified_trial_development_rights"])

    def test_identifying_user_agent_required(self):
        result = build_report(self.casebook, self.leads, max_issuers=1, agent="")
        self.assertEqual(result["issuers_selected"], 1)
        self.assertEqual(result["document_status_counts"]["IDENTIFYING_AGENT_REQUIRED"], 2)
        self.assertEqual(result["documents_retrieved"], 0)

    def test_access_denied_response_not_treated_as_filing(self):
        result = self.report(fetch=lambda url: b"<html><title>Access Denied</title></html>", max_issuers=1)
        self.assertEqual(result["documents_retrieved"], 0)
        self.assertEqual(result["documents_access_failed_or_blocked"], 2)

    def test_network_error_is_unavailable_not_rights_fail(self):
        def blocked(url):
            raise OSError("403")
        result = self.report(fetch=blocked, max_issuers=1)
        self.assertEqual(result["document_status_counts"]["SOURCE_UNAVAILABLE"], 2)
        self.assertEqual(result["independently_verified_current_rights"], 0)

    def test_altered_sec_url_fails_closed(self):
        self.leads["issuers"][0]["candidate_filings"][0]["primary_document_url"] = "https://evil.example/filing.htm"
        with self.assertRaises(ValueError):
            validate_leads(self.casebook, self.leads)

    def test_casebook_and_filing_issuer_mismatch_fails_closed(self):
        self.leads["trials"][0]["saved_sec_cik"] = "0001234567"
        with self.assertRaises(ValueError):
            validate_leads(self.casebook, self.leads)

    def test_missing_trial_in_filing_leads_fails_closed(self):
        self.leads["trials"].pop()
        with self.assertRaises(ValueError):
            validate_leads(self.casebook, self.leads)

    def test_no_index_filing_means_no_primary_document_attempt(self):
        issuer = self.leads["issuers"][0]
        issuer["retrieval_status"] = "SEC_SOURCE_UNAVAILABLE"
        issuer["source_sha256"] = None
        issuer["candidate_filings"] = []
        for row in self.leads["trials"]:
            if row["ticker"] == issuer["ticker"]:
                row["issuer_retrieval_status"] = "SEC_SOURCE_UNAVAILABLE"
                row["issuer_candidate_filing_count"] = 0
        result = self.report(max_issuers=1)
        self.assertEqual(result["issuers_with_official_filing_leads"], 129)
        self.assertEqual(result["issuers_selected"], 1)
        self.assertTrue(all("/data/2/" in url for url in self.urls))
        self.assertEqual(result["documents_retrieved"], 2)

    def test_duplicate_accession_rejected(self):
        self.leads["issuers"][0]["candidate_filings"][1]["accession_number"] = (
            self.leads["issuers"][0]["candidate_filings"][0]["accession_number"])
        with self.assertRaises(ValueError):
            validate_leads(self.casebook, self.leads)

    def test_future_dated_filing_rejected(self):
        self.leads["issuers"][0]["candidate_filings"][0]["filed_date"] = "2027-01-01"
        with self.assertRaises(ValueError):
            validate_leads(self.casebook, self.leads)

    def test_manual_rights_promotion_rejected(self):
        self.leads["verified_current_commercial_rights"] = 1
        with self.assertRaises(ValueError):
            validate_leads(self.casebook, self.leads)


if __name__ == "__main__":
    unittest.main()
