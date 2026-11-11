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
        self.assertTrue(all("FDA_APPLICATION_PATH_NOT_VERIFIED_FOR_EXACT_PROGRAM" in r["reasons"] for r in review))
        self.assertEqual(len(added[0]["values"]),28)
        self.assertEqual(added[0]["values"][4],"YES - company/SEC/journal")
        self.assertEqual(added[0]["values"][23],5491198055)
        self.assertEqual(self.run_check(args,existing={NCT})[0],[])

    def test_31_column_destination_preserves_protected_history_and_source_positions(self):
        args=self.inputs()
        accepted,_=self.run_check(args)
        self.assertEqual(len(accepted),1)
        original=accepted[0]["values"]
        live=promote.physical_append_row(original,3)
        self.assertEqual(len(live),31)
        self.assertEqual(live[:3],original[:3])
        self.assertEqual(live[3:6],["Not verified","","Not yet predicted"])
        self.assertEqual(live[6],original[3])
        self.assertEqual(live[7],"YES - company/SEC/journal")
        self.assertEqual(live[26],5491198055)
        self.assertEqual(live[29],P3)
        self.assertEqual(live[30],CAP)
        self.assertEqual(live[13:24],original[10:21])
        self.assertEqual(live[13:22],[""]*9)
        rejected=original[:]
        rejected[10]="Provisional grade attempted"
        with self.assertRaisesRegex(ValueError,"retired research archive"):
            promote.physical_append_row(rejected,3)
        from importlib import util
        syncpath=PATH.parent/"sync_p3_post_data_from_google_sheet.py"
        spec=util.spec_from_file_location("focus_live_sync",syncpath)
        sync=util.module_from_spec(spec)
        spec.loader.exec_module(sync)
        recovered=sync.extract([live])
        self.assertEqual(len(recovered),1)
        self.assertEqual(recovered[0]["nct"],NCT)
        self.assertEqual(recovered[0]["marketCap"],5491198055)
        self.assertEqual(recovered[0]["regulatoryUrl"],FDA)
        self.assertEqual(recovered[0]["resultsUrl"],P3)
        self.assertEqual(recovered[0]["recordedReleaseDate"],original[5])
        self.assertEqual(recovered[0]["recordedPdufaDate"],original[25])
        live[8]="2026-09-10"  # I: verified registry/issuer result publication
        live[28]="2027-02-28" # AC: exact-date FDA target
        dated=sync.extract([live])[0]
        self.assertEqual(dated["recordedReleaseDate"],"2026-09-10")
        self.assertEqual(dated["recordedPdufaDate"],"2027-02-28")
        for invalid in ("2027-Q1","2027-02-30","2027-1-01",
                        "NDA planned 2027","2027-04-23; not accepted"):
            self.assertIsNone(sync.exact_date(invalid))
        self.assertIsNone(sync.exact_date("2026-09-10T00:00:00Z"))


    def test_unknown_sheet_layout_cannot_append(self):
        header=[""]*31
        header[:3]=["Ticker","NCT ID","Company"]
        header[3:6]=list(promote.LIVE_FOCUS_INSERTS)
        header[6]="Registry Status"
        header[26]="Market Cap USD"
        self.assertEqual(promote.focus_layout(header),3)
        header[26]="Wrong"
        with self.assertRaises(ValueError):
            promote.focus_layout(header)
        with self.assertRaises(ValueError):
            promote.physical_append_row([""]*27,3)

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
        added, review = promote.evaluate(*args[:4], set(), args[4],
                             phase3_check=lambda _: (_ for _ in ()).throw(ValueError("PHASE2")))
        self.assertEqual(added, [])
        self.assertIn("CTGOV_PHASE3_CURRENT_SOURCE_UNAVAILABLE", review[0]["reasons"])
        
class NewlyReviewedFocusCandidates(unittest.TestCase):
    def test_amlx_agio_mirm_all_have_exact_trial_public_results_fda_path_and_current_cap(self):
        import json
        with (PATH.parents[0] / "new-platform/backend/app/phase3_curated_announcements.json").open(encoding="utf-8") as source:
            complete=json.load(source)
        names={
            "APPLICATION|AMLX|AVEXITIDE_PBH_LUCIDITY":("AMLX","NCT06747468",3973879363),
            "APPLICATION|AGIO|MITAPIVAT_SCD_RISEUP_20270201":("AGIO","NCT05031780",1899554516),
            "APPLICATION|MIRM|MARALIXIBAT_EXPAND_CHOLESTATIC_2027":("MIRM","NCT06553768",6163930594),
        }
        cases={k:complete["cases"][k] for k in names}
        day=date(2026,11,11)
        caps=[{"ticker":ticker,"market_cap":str(cap),"market_cap_status":"VERIFIED",
            "market_cap_source":f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks",
            "market_cap_checked_at":"2026-11-11T04:20:58+00:00"}
            for ticker,_,cap in names.values()]
        census=[{"ticker":ticker,"nct_id":nct,"company":ticker}
                for ticker,nct,_ in names.values()]
        pool={nct:ticker for ticker,nct,_ in names.values()}
        approved,review=promote.evaluate(
            {"schemaVersion":"pdufa-curated-phase3-announcements-v1","cases":cases},
            caps,census,pool,set(),day,phase3_check=lambda nct:"ACTIVE_NOT_RECRUITING")
        self.assertEqual(review,[])
        self.assertEqual({x["nct"] for x in approved},set(pool))
        for row in approved:
            self.assertEqual(len(row["values"]),28)
            self.assertEqual(row["values"][4],"YES - company/SEC/journal")
            self.assertTrue(row["values"][26].startswith("https://"))
            self.assertTrue(row["values"][27].startswith("https://"))
            self.assertEqual(row["values"][10:19],[""]*9)
            if row["ticker"]=="AGIO":
                self.assertEqual(row["values"][25],"2027-02-01")
            else:
                self.assertIn("PDUFA not assigned",row["values"][25])
        approved_again,_=promote.evaluate(
            {"schemaVersion":"pdufa-curated-phase3-announcements-v1","cases":cases},
            caps,census,pool,set(pool),day,phase3_check=lambda nct:"ACTIVE_NOT_RECRUITING")
        self.assertEqual(approved_again,[])

    def test_issuer_results_without_verified_application_path_remain_review_only(self):
        args=self.inputs()
        candidate=args[0]["cases"]["APPLICATION|COGT|BEZUCLASTINIB_GIST"]
        candidate.pop("pdufa_assignment")
        approved,review=self.run_check(args)
        self.assertEqual(approved,[])
        self.assertIn("NO_CURRENT_VERIFIED_FDA_PATH",review[0]["reasons"])


if __name__ == "__main__":
    unittest.main()
