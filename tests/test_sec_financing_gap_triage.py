"""Offline guardrails for SEC primary-source discovery queue."""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.sec_financing_gap_triage import FIELDS, run, sec_document_url, triage


def record(key, ticker, category="SEC", claim="FINANCING_CLOSURE",
           expected="", reason="No exact transaction"):
    return {
        "event_key": key, "ticker": ticker, "category": category,
        "claim": claim, "verification_required": "YES",
        "verification_status": "REVIEW_REQUIRED",
        "expected": expected, "reason": reason,
    }


class SecGapTriageTests(unittest.TestCase):
    def setUp(self):
        self.registry = [
            {"ticker": "SMMT", "company": "Summit Therapeutics",
             "cik10": "0001599298"},
            {"ticker": "MLYS", "company": "Mineralys Therapeutics",
             "cik10": "0001933414"},
            {"ticker": "CAPR", "company": "Capricor Therapeutics",
             "cik10": "0001133869"},
            {"ticker": "BLTE", "company": "Belite Bio",
             "cik10": "0001889109"},
        ]
        self.queue = [
            record("SMMT|A", "SMMT", expected="2025-10-31"),
            record("MLYS|B", "MLYS", expected="2025-09-04"),
            record("CAPR|C", "CAPR"),
            record("BLTE|D", "BLTE", "FINANCIAL", "CASH_AND_RUNWAY"),
        ]
        self.cfg = {
            "SMMT": {"events": {"SMMT|A": {
                "individual_financing_close": {
                    "date": "2026-10-05",
                    "sec_url": ("https://www.sec.gov/Archives/edgar/data/"
                                "1599298/000119312526415755/d126889dpre14a.htm"),
                },
            }}},
            "CAPR": {"events": {"CAPR|C": {
                "financing_research_documents": [
                    "https://www.sec.gov/Archives/edgar/data/1133869/"
                    "000110465926097294/capr-20260630x10q.htm",
                    "https://www.sec.gov/Archives/edgar/data/1599298/"
                    "000119312526415755/wrong-company.htm",
                ],
            }}},
        }

    def test_research_classes_do_not_clear_financing_gates(self):
        rows = triage(self.queue, self.registry, self.cfg)
        by_ticker = {r["ticker"]: r for r in rows}
        self.assertEqual(by_ticker["SMMT"]["research_class"],
                         "DIFFERENT_TRANSACTION_DATE_REVIEW")
        self.assertEqual(by_ticker["SMMT"]["saved_closing_date"], "2025-10-31")
        self.assertEqual(by_ticker["SMMT"]["different_mapped_closing_date"],
                         "2026-10-05")
        self.assertEqual(by_ticker["MLYS"]["research_class"],
                         "DATED_CLOSING_NEEDS_SEC_CLAUSE")
        self.assertEqual(by_ticker["CAPR"]["research_class"],
                         "TRANSACTION_NOT_IDENTIFIED")
        self.assertEqual(by_ticker["BLTE"]["research_class"],
                         "CASH_AND_RUNWAY_PRIMARY_RECONCILIATION")
        for row in rows:
            self.assertEqual(row["source_claim_verified"], "NO")
            self.assertEqual(row["second_post_phase3_financing_verified"], "NO")
            self.assertEqual(row["trade_entry_authorized"], "NO")
            self.assertIn("google.com/search?q=", row["google_sec_company_search"])
            self.assertIn("CIK", row["sec_submissions_url"])
        self.assertIn("capr-20260630x10q.htm",
                      by_ticker["CAPR"]["known_sec_source_urls"])
        self.assertNotIn("wrong-company",
                         by_ticker["CAPR"]["known_sec_source_urls"])

    def test_sec_registry_inventory_conflicts_have_exact_ticker_identity(self):
        # The canonical SEC filings-inventory queue uses REGISTRY:TICKER,
        # unlike the financing queue's TICKER|PROGRAM event identities.
        companies = [
            {"ticker": "QNCX", "company": "Quince Therapeutics",
             "cik10": "0001662774"},
            {"ticker": "TBPH", "company": "Theravance Biopharma",
             "cik10": "0001583107"},
        ]
        queue = [
            record("REGISTRY:QNCX", "QNCX", "SEC", "FILINGS_INVENTORY"),
            record("REGISTRY:TBPH", "TBPH", "SEC", "FILINGS_INVENTORY"),
        ]
        rows = triage(queue, companies, {})
        self.assertEqual({x["ticker"] for x in rows}, {"QNCX", "TBPH"})
        for row in rows:
            self.assertEqual(row["research_class"],
                             "SEC_ISSUER_CIK_TICKER_IDENTITY_RECONCILIATION")
            self.assertEqual(row["priority"], "1")
            self.assertEqual(row["source_claim_verified"], "NO")
            self.assertEqual(row["second_post_phase3_financing_verified"], "NO")
            self.assertEqual(row["trade_entry_authorized"], "NO")
        with self.assertRaisesRegex(ValueError, "Claim event/ticker mismatch"):
            triage([record("REGISTRY:TBPH", "QNCX", "SEC",
                           "FILINGS_INVENTORY")], companies, {})
        with self.assertRaisesRegex(ValueError, "Claim event/ticker mismatch"):
            triage([record("REGISTRY:QNCX", "QNCX", "SEC",
                           "FINANCING_CLOSURE")], companies, {})

    def test_sec_url_must_be_correct_issuer_and_real_archive_file(self):
        valid = ("https://www.sec.gov/Archives/edgar/data/1133869/"
                 "000110465926097294/capr-20260630x10q.htm")
        self.assertTrue(sec_document_url(valid, "0001133869"))
        for url in (
            valid + "?q=1",
            valid.replace("1133869", "1599298"),
            "https://other.sec.gov/Archives/edgar/data/1133869/"
            "000110465926097294/capr-20260630x10q.htm",
            "https://sec.gov.evil.net/Archives/edgar/data/1133869/"
            "000110465926097294/capr-20260630x10q.htm",
            valid.replace("capr-20260630x10q.htm", "../bad.htm"),
        ):
            self.assertFalse(sec_document_url(url, "0001133869"))

    def test_mandatory_queue_cannot_include_resolved_or_duplicate_claims(self):
        bad = dict(self.queue[0], verification_status="VERIFIED")
        with self.assertRaises(ValueError):
            triage([bad], self.registry, self.cfg)
        with self.assertRaises(ValueError):
            triage([self.queue[0], self.queue[0]], self.registry, self.cfg)

    def test_report_count_guard_and_research_only_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "config").mkdir()
            (root / "config/issuer_sources.json").write_text(json.dumps(self.cfg))
            with (root / "data/company_registry.csv").open("w", newline="") as stream:
                w = csv.DictWriter(stream, fieldnames=list(self.registry[0]))
                w.writeheader()
                w.writerows(self.registry)
            with (root / "data/pdufa_source_review_queue.csv").open("w", newline="") as stream:
                w = csv.DictWriter(stream, fieldnames=list(self.queue[0]))
                w.writeheader()
                w.writerows(self.queue)
            path = root / "data/pdufa_source_report.json"
            path.write_text(json.dumps({
                "latest_run_id": "12345", "required_findings_unresolved": 5,
            }))
            outcsv = root / "reports/triage.csv"
            outjson = root / "reports/triage.json"
            with self.assertRaisesRegex(ValueError, "mismatch"):
                run(root, outcsv, outjson)
            self.assertFalse(outcsv.exists())
            path.write_text(json.dumps({
                "latest_run_id": "12345", "required_findings_unresolved": 4,
            }))
            result = run(root, outcsv, outjson)
            self.assertEqual(result["findings_scoped"], 4)
            self.assertTrue(result["research_only"])
            self.assertEqual(result["source_claims_verified"], 0)
            self.assertEqual(len(list(csv.DictReader(outcsv.open()))), 4)
            self.assertEqual(list(csv.DictReader(outcsv.open()))[0].keys(), set(FIELDS))


if __name__ == "__main__":
    unittest.main()
