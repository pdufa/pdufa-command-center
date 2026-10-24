"""Every-trial audit tests; no historical trading returns are fabricated."""
import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.run_all_system_trials_backtest import (
    AUDIT_FIELDS, audit, trial_rows,
)


class AllTrialBacktestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.make_csv("pdufa_candidates.csv",
                      ["event_key","ticker","nct_id","drug","pdufa_date"],
                      [
                          ["AA|DRUG_20260601","AA","NCT01234567",
                           "Drug A","2026-06-01"],
                          ["BB|DRUG_20261201","BB","NCT01234568",
                           "Drug B","2026-12-01"]
                      ])
        self.make_csv("discovery_events.csv",
                      ["discovery_key","ticker","nct_id","drug","pdufa_date"],
                      [["CTG|STUDY","", "NCT01234569","Drug C",""]])
        self.make_csv("post_phase3_discoveries.csv",
                      ["ticker","nct_id","drug","pdufa_date"],
                      [["EE","NCT01234570","Drug E",""]])
        self.make_csv("phase_pipeline.csv",
                      ["ticker","nct_id","drug"],
                      [["DD","NCT01234571","Drug D"]])
        self.make_csv("all_phase_trials.csv",
                      ["ticker","nct_id","drug"],
                      [["GG","NCT01234572","Drug G"]])
        (self.root/"gem_stage_membership.json").write_text(json.dumps({
            "stages":{
                "GEM":{"entries":{
                    "A":{"exact_program":"AA|DRUG_20260601",
                         "ticker":"AA","status":"ACTIVE",
                         "pdufa_date":"2026-06-01"},
                    "Z":{"exact_program":"ZZ|DRUG_20260901",
                         "ticker":"ZZ","status":"ACTIVE",
                         "pdufa_date":"2026-09-01"}
                }},
                "GEM_JR":{"entries":{
                    "Y":{"exact_program":"YY|DRUG_20270101",
                         "ticker":"YY","status":"ACTIVE",
                         "pdufa_date":"2027-01-01"}
                }}
            }
        }))
        (self.root/"phase_pipeline_state.json").write_text(json.dumps({
            "stored_trials":900, "studies_scanned":1200,
            "registry_companies":7
        }))
        self.make_csv("post_phase3_historical_trade_events.csv",
                      ["event_key","ticker","pdufa_date"],[])
        self.make_csv("post_phase3_historical_adjusted_ohlcv.csv",
                      ["ticker","session","open","high","low","close",
                       "volume","source_url","adjustment_status"],[])

    def make_csv(self,name,fields,records):
        with (self.root/name).open("w",encoding="utf-8",newline="") as f:
            w=csv.writer(f)
            w.writerow(fields)
            w.writerows(records)

    def test_stage_merges_exact_identity_and_does_not_match_ticker(self):
        rows,members=trial_rows(self.root)
        aa=[x for x in rows if x["event_key"]=="AA|DRUG_20260601"]
        self.assertEqual(len(aa),1)
        self.assertEqual(aa[0]["stage"],"GEM")
        zz=[x for x in rows if x["event_key"]=="ZZ|DRUG_20260901"]
        self.assertEqual(len(zz),1)
        self.assertEqual(zz[0]["source"],"GEM_MEMBERSHIP")
        self.assertEqual(len(members),3)

    def test_complete_source_inventory_preserves_missing_count(self):
        rows,trades,summary,out=audit(self.root,as_of=date(2026,10,18))
        self.assertEqual(out["source_row_counts"]["ALL_PHASE_TRIALS"],1)
        self.assertEqual(out["scan_reported_stored_trials"],900)
        self.assertEqual(out["unavailable_scanned_trial_rows"],899)
        self.assertEqual(out["gem_stage_membership_counts"],
                         {"GEM":2,"GEM_JR":1})
        self.assertEqual(out["audited_saved_rows"],8)
        self.assertEqual(out["completed_hypothetical_trade_scenarios"],0)
        self.assertEqual(out["status"],"NOT_BACKTESTABLE_FROM_SAVED_DATA")
        self.assertEqual(len(summary),54)
        self.assertTrue(all(r["historical_backtest_status"]=="BLOCKED"
                            for r in rows))
        self.assertEqual(trades,[])

    def test_future_pdufa_blocks_regardless_of_present_trading_snapshot(self):
        rows,_,_,_=audit(self.root,as_of=date(2026,10,18))
        future=next(r for r in rows if r["ticker"]=="YY")
        self.assertEqual(future["blocker"],"FUTURE_PDUFA_NOT_COMPLETED")

    def test_discovery_without_pdufa_cannot_be_stock_return_trade(self):
        rows,_,_,_=audit(self.root,as_of=date(2026,10,18))
        no_decision=[r for r in rows if r["source"]=="DISCOVERY"]
        self.assertEqual(no_decision[0]["blocker"],
                         "NO_VERIFIED_PDUFA_DATE_OR_NONAPPLICATION_TRIAL")


if __name__ == "__main__":
    unittest.main()
