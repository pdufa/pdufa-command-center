"""Regression cases observed in real partial source runs."""
import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import source_verification as v, recheck_events as recheck
from scripts import nightly_missing_sources as scan

CIK = "0000000001"
COMPANY = {"ticker": "ABC", "company": "Test Pharma", "cik10": CIK}
EVENT = {"event_key": "ABC|DRUG", "ticker": "ABC", "company": "Test Pharma",
         "drug": "TestDrug", "indication": "lung cancer", "pdufa_date": "2026-11-01"}
DOC = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/ex99-1.htm"


def rows(path, records):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=records[0]); w.writeheader(); w.writerows(records)


def facts(form="10-Q", cash_tag="CashAndCashEquivalentsAtCarryingValue", flow=-25):
    base = {"end": "2026-09-30", "filed": "2026-10-10", "form": form, "accn": "0000000001-26-000001"}
    return {"cik": 1, "facts": {"us-gaap": {
        cash_tag: {"units": {"USD": [{**base, "val": 100}]}},
        "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [{**base, "val": flow, "start": "2026-07-01"}]}}
    }}}


class ScanRepairs(unittest.TestCase):
    def verifier(self, payload, **kwargs):
        raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return v.Verifier([COMPANY], fetch=lambda u: raw, as_of=date(2026, 10, 12), **kwargs)

    def test_legacy_documentless_accession_does_not_discard_current_inventory(self):
        payload = {"cik": 1, "tickers": ["ABC"], "filings": {"recent": {
            "form": ["8-K", "10-Q"], "filingDate": ["2026-10-10", "1999-03-15"],
            "accessionNumber": ["0000000001-26-000001", "0000000001-99-000001"],
            "primaryDocument": ["current.htm", ""]}}}
        result = self.verifier(payload).registry(COMPANY)
        self.assertEqual(result["verification_status"], "VERIFIED")
        payload["filings"]["recent"]["accessionNumber"][1] = "not-an-accession"
        self.assertEqual(self.verifier(payload).registry(COMPANY)["verification_status"], "REVIEW_REQUIRED")

    def test_transition_report_is_current_financial_evidence(self):
        result = self.verifier(facts(form="10-KT")).financial(EVENT)
        self.assertEqual([r["verification_status"] for r in result], ["VERIFIED", "VERIFIED"])

    def test_positive_operating_flow_resolves_runway_as_not_applicable(self):
        result = self.verifier(facts(flow=25)).financial(EVENT)
        self.assertEqual(result[1]["verification_status"], "NOT_APPLICABLE")
        self.assertTrue(result[1]["source_sha256"])
        self.assertEqual(v.summary(result)["required_findings_unresolved"], 0)

    def test_restricted_cash_is_named_and_does_not_become_spendable_runway(self):
        result = self.verifier(facts(cash_tag="CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")).financial(EVENT)
        self.assertEqual(result[0]["claim"], "LIQUIDITY_FACT")
        self.assertEqual(result[0]["verification_status"], "VERIFIED")
        self.assertEqual(result[1]["verification_status"], "REVIEW_REQUIRED")
        self.assertIn("restricted", result[1]["reason"])

    def test_different_accessions_cannot_supply_one_runway(self):
        payload = facts()
        payload["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"][0]["accn"] = "0000000001-26-000002"
        self.assertEqual(self.verifier(payload).financial(EVENT)[1]["verification_status"], "REVIEW_REQUIRED")

    def test_collector_and_verifier_use_identical_cash_and_period_arithmetic(self):
        payload = facts()
        with patch.object(recheck, "get", return_value=json.dumps(payload)):
            collected = recheck.cash_check(CIK)
        verified = self.verifier(payload).financial({**EVENT, "cash": str(collected["cash"]), "cash_runway_months": str(collected["runway"])})
        self.assertEqual([r["verification_status"] for r in verified], ["VERIFIED", "VERIFIED"])

    def test_official_issuer_target_requires_explicit_host_mapping_and_company(self):
        url = "https://ir.testpharma.com/release"
        event = {**EVENT, "pdufa_evidence_url": url}
        source = b"Test Pharma announced TestDrug for lung cancer. FDA PDUFA target date is November 1, 2026."
        verifier = self.verifier(source, issuer_sources={"ABC": {"hosts": ["ir.testpharma.com"]}})
        self.assertEqual(verifier.regulatory(event)[0]["verification_status"], "VERIFIED")
        wrong = self.verifier(source.replace(b"Test Pharma", b"Other Company"), issuer_sources={"ABC": {"hosts": ["ir.testpharma.com"]}})
        self.assertEqual(wrong.regulatory(event)[0]["verification_status"], "REVIEW_REQUIRED")

    def test_missing_decision_date_can_be_recovered_from_explicit_action_clause(self):
        event = {**EVENT, "outcome": "APPROVED", "pdufa_evidence_url": DOC}
        source = b"On October 10, 2026, FDA approved TestDrug for lung cancer. Test Pharma announced the decision."
        result = self.verifier(source).regulatory(event)[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertIn("2026-10-10", result["observed"])

    def test_release_dateline_does_not_create_a_false_target_conflict(self):
        source = b"Test Pharma on February 25, 2026 announced TestDrug for lung cancer with a PDUFA goal date of November 1, 2026."
        result = self.verifier(source).regulatory({**EVENT, "pdufa_evidence_url": DOC})[0]
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertEqual(result["observed"], "2026-11-01")

    def test_two_explicit_target_dates_still_require_reconciliation(self):
        text = "PDUFA goal date of November 1, 2026, extended to a target action date of December 1, 2026."
        self.assertEqual(v.target_dates(text), {"2026-11-01", "2026-12-01"})

    def test_dose_suffix_does_not_hide_exact_active_drug_identity(self):
        self.assertTrue(v.drug_matches({"drug": "Ameluz PDT"}, "Ameluz is a photosensitizer"))
        self.assertTrue(v.drug_matches({"drug": "Phentolamine Ophthalmic Solution 0.75%"}, "phentolamine ophthalmic solution for presbyopia"))
        self.assertFalse(v.drug_matches({"drug": "TestDrug + OtherDrug"}, "TestDrug only"))

    def test_matching_financing_ledger_supplies_fresh_closing_evidence_only(self):
        review = {"second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
                  "second_financing_source": DOC, "second_financing_date": "2026-10-10"}
        event = {**EVENT, "_financing_review": review}
        result = self.verifier(b"On October 10, 2026, Test Pharma completed its public offering for $25 million.").financing(event)
        self.assertEqual(result["verification_status"], "VERIFIED")
        self.assertIn("not the post-Phase-3 second-financing sequence", result["reason"])
        review["second_financing_source"] = DOC.replace("/data/1/", "/data/2/")
        self.assertEqual(self.verifier(b"closed").financing(event)["verification_status"], "REVIEW_REQUIRED")

    def test_short_interest_keeps_shares_separate_from_float_percentage(self):
        quote = {"chart": {"error": None, "result": [{"meta": {"symbol": "ABC"},
            "timestamp": [datetime(2026, 10, 9, 20, tzinfo=timezone.utc).timestamp()],
            "indicators": {"quote": [{"close": [10], "volume": [1000]}]}}]}}
        nasdaq = {"data": {"symbol": "ABC", "shortInterestTable": {"rows": [{
            "settlementDate": "09/30/2026", "interest": "12,345", "daysToCover": 2.1}]}}}
        def fetch(url):
            if "/short-interest" in url: return json.dumps(nasdaq).encode()
            if "/options/" in url: raise v.SourceUnavailable("HTTP_401")
            return json.dumps(quote).encode()
        result = v.Verifier([COMPANY], fetch=fetch, as_of=date(2026, 10, 12)).market(EVENT)
        short = next(r for r in result if r["claim"] == "SHORT_INTEREST")
        self.assertEqual(short["verification_status"], "VERIFIED")
        self.assertEqual(json.loads(short["observed"])["short_shares"], 12345)
        self.assertNotIn("float_percentage", json.loads(short["observed"]))
        self.assertEqual(v.summary(result)["required_findings_unresolved"], 0)
        self.assertEqual(v.summary(result)["optional_findings_unavailable"], 2)

    def test_supplemental_unavailable_data_cannot_waive_required_market_failure(self):
        result = self.verifier({}).market(EVENT)
        self.assertGreater(v.summary(result)["required_findings_unresolved"], 0)
        self.assertEqual(v.summary(result)["optional_findings_unavailable"], 3)


if __name__ == "__main__": unittest.main()
