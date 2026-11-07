"""Offline regression tests for automatic Phase 3 POST-DATA promotion."""
from __future__ import annotations
import importlib.util
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PATH=Path(__file__).resolve().parents[1] / "scripts/auto_promote_p3_post_data.py"
spec=importlib.util.spec_from_file_location("auto_p3",PATH)
promote=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=promote
spec.loader.exec_module(promote)

NCT="NCT05208047"
TICKER="COGT"
P3="https://investors.example.com/peak-results"
FDA="https://investors.example.com/nda-accepted"
CAP="https://api.nasdaq.com/api/quote/COGT/summary?assetclass=stocks"

class PromotionTests(unittest.TestCase):
    def inputs(self):
        today=date.today()
        yesterday=(today-timedelta(days=1)).isoformat()
        target=(today+timedelta(days=24)).isoformat()
        catalog={"schemaVersion":"pdufa-curated-phase3-announcements-v1","cases":{
            "APPLICATION|COGT|BEZUCLASTINIB_GIST": {
                "nctId":NCT, "reviewedOn":today.isoformat(),
                "reviewerMethod":"PRIMARY_PUBLIC_ISSUER_DISCLOSURE",
                "phase3_results":{"review_status":"VERIFIED","source_url":P3,
                                  "published_at":yesterday,"event_date":yesterday},
                "pdufa_assignment":{"review_status":"VERIFIED","source_url":FDA,
                                    "published_at":yesterday,"event_date":yesterday,
                                    "pdufa_target_date":target}
            }}}
        caps=[{"ticker":TICKER,"market_cap":"5491198055","market_cap_source":CAP,
               "market_cap_checked_at":datetime.now(timezone.utc).isoformat(),
               "market_cap_status":"VERIFIED"}]
        census=[{"nct_id":NCT,"ticker":TICKER,"company":"Cogent Biosciences, Inc."}]
        pool={NCT}
        return catalog,caps,census,pool,today

    def run_check(self, args, existing=frozenset()):
        catalog,caps,census,pool,today=args
        return promote.evaluate(catalog,caps,census,pool,existing,today,
                                phase3_check=lambda _: "RECRUITING")

    def test_qualified_released_trial_enters_p3_once(self):
        args=self.inputs()
        added,review=self.run_check(args)
        self.assertEqual([x["nct"] for x in added],[NCT])
        self.assertFalse(review)
        self.assertEqual(len(added[0]["values"]),28)
        self.assertEqual(added[0]["values"][4],"YES - company/SEC/journal")
        self.assertEqual(added[0]["values"][23],5491198055)
        self.assertEqual(self.run_check(args,existing={NCT}),([],[]))

    def test_no_results_documentation_no_promotion(self):
        args=self.inputs()
        args[0]["cases"]["APPLICATION|COGT|BEZUCLASTINIB_GIST"]["phase3_results"]["review_status"]="NEEDS_REVIEW"
        added,review=self.run_check(args)
        self.assertEqual(added,[])
        self.assertIn("PHASE3_PUBLIC_RESULTS_NOT_REVIEWED",review[0]["reasons"])

    def test_old_cap_no_promotion(self):
        args=self.inputs()
        args[1][0]["market_cap_checked_at"]=(datetime.now(timezone.utc)-timedelta(days=9)).isoformat()
        added,review=self.run_check(args)
        self.assertEqual(added,[])
        self.assertIn("CAP_NOT_CURRENT_VERIFIED_300M_10B",review[0]["reasons"])

    def test_out_of_band_cap_no_promotion(self):
        args=self.inputs()
        args[1][0]["market_cap"]="10000000001"
        added,_=self.run_check(args)
        self.assertEqual(added,[])

    def test_missing_exact_pool_identity_no_promotion(self):
        args=self.inputs()
        args[3].clear()
        added,review=self.run_check(args)
        self.assertEqual(added,[])
        self.assertIn("NOT_IN_MASTER_POOL",review[0]["reasons"])

    def test_passed_pdufa_not_automatically_promoted(self):
        args=self.inputs()
        args[0]["cases"]["APPLICATION|COGT|BEZUCLASTINIB_GIST"]["pdufa_assignment"]["pdufa_target_date"]=(date.today()-timedelta(days=1)).isoformat()
        added,review=self.run_check(args)
        self.assertEqual(added,[])
        self.assertIn("NO_CURRENT_VERIFIED_FDA_PDUFA_PATH",review[0]["reasons"])

    def test_wrong_registry_phase_blocked(self):
        args=self.inputs()
        with self.assertRaises(ValueError):
            promote.evaluate(*args[:4],set(),args[4],
                             phase3_check=lambda _: (_ for _ in ()).throw(ValueError("PHASE2")))
        
if __name__ == "__main__":
    unittest.main()
