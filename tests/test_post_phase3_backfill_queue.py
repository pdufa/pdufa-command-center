"""Backfill queue is research-only, not a PDUFA trading eligibility shortcut."""
import csv
import tempfile
import unittest
from pathlib import Path

from post_phase3_backfill_queue import build_backfill_queue


def csv_file(path, items):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(items[0]))
        writer.writeheader()
        writer.writerows(items)


class HistoricalBackfillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.key = "TEST|DRUG_20260930"
        self.event = {
            "event_key":self.key, "ticker":"TEST", "drug":"Drug",
            "indication":"Condition", "nct_id":"NCT01234567",
            "phase3_date":"2025-07-01", "phase3_status":"RESULTS_REVIEW",
            "trial_evidence_url":"https://investor.example/phase3",
            "pdufa_date":"2026-09-30", "pdufa_confirmation":"REPORTED_ONLY",
            "pdufa_evidence_url":"", "outcome":"APPROVED",
        }
        self.finance = {
            "event_key":self.key, "second_financing_closed":"YES",
            "first_financing_date":"2025-08-01", "second_financing_date":"2025-10-01",
            "first_financing_source":"https://www.sec.gov/Archives/edgar/data/123456/filing1.htm",
            "second_financing_source":"https://www.sec.gov/Archives/edgar/data/123456/filing2.htm",
            "second_financing_audit_status":"VERIFIED_SECOND_POST_PHASE3_FINANCING",
            "second_financing_evidence_note":"Post-readout two funding events per issuer retrospective ledger",
        }
        csv_file(self.root/"company_registry.csv",[
            {"ticker":"TEST","cik10":"0000123456"},
        ])

    def build(self):
        csv_file(self.root/"pdufa_candidates.csv",[self.event])
        csv_file(self.root/"second_financing_status.csv",[self.finance])
        return build_backfill_queue(self.root)

    def test_dual_financing_creates_priority_not_verified_trade(self):
        rows, meta = self.build()
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]["priority"].startswith("1"))
        self.assertEqual(rows[0]["eligible_for_historical_trade_backtest"],
                         "NO — RESEARCH QUEUE ONLY")
        self.assertIn("FINANCING_1_AND_2_FIRST_PUBLIC_DATES",
                      rows[0]["missing_historical_requirements"])
        self.assertIn("SPLIT_ADJUSTED_HISTORICAL_DAILY_OHLCV",
                      rows[0]["missing_historical_requirements"])
        self.assertEqual(meta["historical_trade_verified_from_worklist"],0)

    def test_wrong_cik_not_treated_as_same_issuer_financing(self):
        self.finance["second_financing_source"] = (
            "https://www.sec.gov/Archives/edgar/data/789123/other.htm")
        rows,_=self.build()
        self.assertTrue(rows[0]["priority"].startswith("2"))
        self.assertIn("TWO_DISTINCT_SAME_ISSUER_SEC_FINANCING_CLOSES",
                      rows[0]["missing_historical_requirements"])

    def test_missing_nct_primary_readout_never_inferred(self):
        self.event["nct_id"]=""
        rows,_=self.build()
        self.assertIn("CLINICAL_TRIAL_NCT_ID",rows[0]["missing_historical_requirements"])
        self.assertIn("PRIMARY_ENDPOINT_BENEFIT_SAFETY_ADJUDICATION",
                      rows[0]["missing_historical_requirements"])

    def test_no_funding_ledger_stays_in_research_queue(self):
        csv_file(self.root/"pdufa_candidates.csv",[self.event])
        rows,meta=build_backfill_queue(self.root)
        self.assertEqual(len(rows),1)
        self.assertTrue(rows[0]["priority"].startswith("3"))
        self.assertEqual(meta["existing_financing_records"],0)

    def test_duplicate_financing_event_never_prioritized(self):
        csv_file(self.root/"pdufa_candidates.csv",[self.event])
        csv_file(self.root/"second_financing_status.csv",[self.finance,self.finance])
        rows,meta=build_backfill_queue(self.root)
        self.assertIn("DUPLICATE_OR_AMBIGUOUS_EVENT_RECORD",
                      rows[0]["missing_historical_requirements"])
        self.assertEqual(rows[0]["eligible_for_historical_trade_backtest"],
                         "NO — RESEARCH QUEUE ONLY")
