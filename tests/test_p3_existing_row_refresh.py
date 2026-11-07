"""Offline safety tests for refreshing existing P3 POST-DATA rows."""
from __future__ import annotations
import importlib.util
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"refresh_existing_p3_post_data.py"
sys.path.insert(0,str(SCRIPT.parent))
spec=importlib.util.spec_from_file_location("p3_existing_refresh",SCRIPT)
refresh=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=refresh
spec.loader.exec_module(refresh)

ID="NCT05208047"
TICKER="COGT"
CAPURL="https://api.nasdaq.com/api/quote/COGT/summary?assetclass=stocks"
FDAURL="https://investors.example.com/nda-accepted"


class ExistingRowRefreshTests(unittest.TestCase):
    def setUp(self):
        self.today=date.today()
        self.now=datetime.now(timezone.utc).isoformat()
        self.headers=[""]*28
        for index,title in refresh.HEADERS.items():
            self.headers[index]=title
        self.row=[""]*28
        values={0:TICKER,1:ID,2:"Cogent Biosciences",3:"REGISTRY_NOT_RECHECKED",
                4:"YES — COMPANY POSTED",5:"2025-11-10",
                6:"https://clinicaltrials.gov/study/"+ID,
                7:"2026-11-06",8:"2026-11-06T18:00:00+00:00",
                9:"COMPANY_PHASE3_RESULTS",10:"Human RAAS notes",11:9,
                12:"Metric history",13:21,14:0,15:67,
                16:"PARTIAL",17:"2026-11-04",18:"Open RAAS",
                19:"FDA NDA review",20:"Analyst comment",
                21:"https://example.com/existing-fda",22:self.today.isoformat(),
                23:5490000000,24:"2026-11-06",
                25:(self.today+timedelta(days=25)).isoformat(),
                26:"https://example.com/issuer-readout",
                27:"https://example.com/old-cap"}
        for k,v in values.items():self.row[k]=v
        self.caps=[{"ticker":TICKER, "market_cap":"5491198055",
                    "market_cap_source":CAPURL,
                    "market_cap_checked_at":self.now,
                    "market_cap_status":"VERIFIED"}]
        self.catalog={"schemaVersion":"pdufa-curated-phase3-announcements-v1","cases":{}}
        self.registry={ID:{"protocolSection":{
            "identificationModule":{"nctId":ID},
            "designModule":{"phases":["PHASE3"]},
            "statusModule":{"overallStatus":"ACTIVE_NOT_RECRUITING"}
        }}}

    def plan(self):
        return refresh.build_plan([self.headers,self.row],self.caps,self.catalog,
                                  self.registry,self.today,self.now)

    def cells(self,data):
        return {d["range"].split("!")[-1]:d["values"][0][0] for d in data}

    def test_refresh_cap_and_registry_without_replacing_human_research(self):
        data, report=self.plan()
        cells=self.cells(data)
        self.assertEqual(cells["D4"],"ACTIVE_NOT_RECRUITING")
        self.assertEqual(cells["X4"],5491198055)
        self.assertEqual(cells["AB4"],CAPURL)
        self.assertEqual(report["counts"]["capUpdated"],1)
        self.assertTrue(all(
            int("".join(str(ord(c)-64) for c in k.rstrip("4"))) >= 0
            for k in cells))
        # K-U and A-C are immutable; not even blank placeholders may be posted.
        self.assertFalse(set(cells).intersection({
            f"{refresh.a1_col(i)}4" for i in refresh.IMMUTABLE}))

    def test_official_registry_results_added_when_missing(self):
        self.row[4]="NO"
        self.registry[ID]["protocolSection"]["statusModule"]["resultsFirstPostDateStruct"]={
            "date":(self.today-timedelta(days=1)).isoformat()}
        self.registry[ID]["resultsSection"]={"participantFlowModule":{"groups":[]}}
        data,report=self.plan()
        cells=self.cells(data)
        self.assertEqual(cells["E4"],"YES")
        self.assertIn("AA4",cells)
        self.assertEqual(cells["J4"],"CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT")
        self.assertEqual(report["counts"]["resultsUpdated"],1)

    def test_do_not_replace_issuer_result_with_registry_date(self):
        self.registry[ID]["protocolSection"]["statusModule"]["resultsFirstPostDateStruct"]={
            "date":self.today.isoformat()}
        self.registry[ID]["resultsSection"]={"outcomeMeasuresModule":{}}
        data,_=self.plan()
        cells=self.cells(data)
        self.assertNotIn("E4",cells)
        self.assertNotIn("F4",cells)
        self.assertNotIn("AA4",cells)
        self.assertNotIn("J4",cells)

    def test_no_registry_results_not_equivalent_to_no_issuer_results(self):
        data,_=self.plan()
        cells=self.cells(data)
        self.assertNotIn("E4",cells)
        self.assertNotIn("F4",cells)

    def test_missing_or_old_cap_keeps_saved_amount_and_reports_review(self):
        self.caps=[]
        data,report=self.plan()
        cells=self.cells(data)
        self.assertNotIn("X4",cells)
        self.assertIn("MARKET_CAP_NOT_IN_CURRENT_LEDGER",report["records"][0]["review"])
        self.caps=[dict(self.caps[0])] if self.caps else [{"ticker":TICKER,
            "market_cap":"10000000001", "market_cap_source":CAPURL,
            "market_cap_checked_at":self.now, "market_cap_status":"VERIFIED"}]
        data,report=self.plan()
        self.assertNotIn("X4",self.cells(data))
        self.assertIn("MARKET_CAP_OUTSIDE_ACTIVE_RANGE",report["records"][0]["review"])

    def test_stale_cap_not_promoted(self):
        self.caps[0]["market_cap_checked_at"]=(datetime.now(timezone.utc)-timedelta(days=8)).isoformat()
        data,report=self.plan()
        self.assertNotIn("X4",self.cells(data))
        self.assertIn("MARKET_CAP_STALE",report["records"][0]["review"])

    def test_exact_nct_newer_fda_review_updates_issuer_status(self):
        yesterday=(self.today-timedelta(days=1)).isoformat()
        self.row[22]=yesterday
        self.catalog["cases"]={"APPLICATION|COGT|BEZUCLASTINIB": {
            "nctId":ID,"reviewedOn":self.today.isoformat(),
            "reviewerMethod":"PRIMARY_PUBLIC_ISSUER_DISCLOSURE",
            "pdufa_assignment":{"review_status":"VERIFIED",
               "published_at":yesterday,"event_date":yesterday,
               "pdufa_target_date":(self.today+timedelta(days=24)).isoformat(),
               "source_url":FDAURL}}}
        data,report=self.plan()
        cells=self.cells(data)
        self.assertEqual(cells["V4"],FDAURL)
        self.assertEqual(cells["W4"],self.today.isoformat())
        self.assertEqual(report["counts"]["fdaUpdated"],1)

    def test_outdated_fda_source_cannot_overwrite_newer_manual_review(self):
        yesterday=(self.today-timedelta(days=1)).isoformat()
        self.catalog["cases"]={"APPLICATION|COGT|BEZUCLASTINIB": {
            "nctId":ID,"reviewedOn":yesterday,
            "reviewerMethod":"PRIMARY_PUBLIC_ISSUER_DISCLOSURE",
            "pdufa_assignment":{"review_status":"VERIFIED",
               "published_at":yesterday,"event_date":yesterday,
               "pdufa_target_date":(self.today+timedelta(days=24)).isoformat(),
               "source_url":FDAURL}}}
        data,_=self.plan()
        cells=self.cells(data)
        self.assertNotIn("V4",cells)
        self.assertNotIn("Z4",cells)
        self.assertNotIn("W4",cells)

    def test_secondary_cap_fills_missing_primary_once_without_touching_raas(self):
        self.caps = []
        backup={"COGT":(523250000,self.today.isoformat(),
                        "https://stockanalysis.com/stocks/cogt/market-cap/")}
        data,report=refresh.build_plan([self.headers,self.row],self.caps,self.catalog,
                self.registry,self.today,self.now,backup_caps=backup)
        cells=self.cells(data)
        self.assertEqual(cells["X4"],523250000)
        self.assertEqual(cells["Y4"],self.today.isoformat())
        self.assertEqual(cells["AB4"],backup["COGT"][2])
        self.assertEqual(report["counts"]["backupCapRowsUpdated"],1)
        self.assertEqual(report["records"][0]["marketCapSourceKind"],
                         "SECONDARY_DATED_PUBLISHER_QUOTE")
        self.assertNotIn("MARKET_CAP_NOT_IN_CURRENT_LEDGER",report["records"][0]["review"])
        self.assertFalse(set(cells).intersection({
            f"{refresh.a1_col(i)}4" for i in refresh.IMMUTABLE}))

    def test_verified_primary_market_cap_has_priority_over_backup(self):
        backup={"COGT":(523250000,self.today.isoformat(),
                        "https://stockanalysis.com/stocks/cogt/market-cap/")}
        data,report=refresh.build_plan([self.headers,self.row],self.caps,self.catalog,
                self.registry,self.today,self.now,backup_caps=backup)
        self.assertEqual(self.cells(data)["X4"],5491198055)
        self.assertEqual(report["counts"]["backupCapRowsUpdated"],0)

    def test_primary_verified_out_of_range_never_masked_by_secondary(self):
        self.caps[0]["market_cap"]="12000000000"
        backup={"COGT":(523250000,self.today.isoformat(),
                        "https://stockanalysis.com/stocks/cogt/market-cap/")}
        data,report=refresh.build_plan([self.headers,self.row],self.caps,self.catalog,
                self.registry,self.today,self.now,backup_caps=backup)
        self.assertNotIn("X4",self.cells(data))
        self.assertIn("MARKET_CAP_OUTSIDE_ACTIVE_RANGE",report["records"][0]["review"])

    def test_secondary_older_than_existing_preserves_current_market_cap(self):
        self.caps=[]
        self.row[24]=self.today.isoformat()
        older=(self.today-timedelta(days=1)).isoformat()
        backup={"COGT":(523250000,older,
                        "https://stockanalysis.com/stocks/cogt/market-cap/")}
        data,report=refresh.build_plan([self.headers,self.row],self.caps,self.catalog,
                self.registry,self.today,self.now,backup_caps=backup)
        self.assertNotIn("X4",self.cells(data))
        self.assertIn("BACKUP_MARKET_CAP_OLDER_THAN_SAVED",report["records"][0]["review"])

    def test_forged_secondary_url_is_rejected(self):
        self.caps=[]
        backup={"COGT":(523250000,self.today.isoformat(),
                        "https://forged.example/stocks/cogt/market-cap/")}
        data,report=refresh.build_plan([self.headers,self.row],self.caps,self.catalog,
                self.registry,self.today,self.now,backup_caps=backup)
        self.assertNotIn("X4",self.cells(data))
        self.assertIn("BACKUP_MARKET_CAP_SOURCE_INVALID",report["records"][0]["review"])

    def test_duplicate_identity_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate NCT"):
            refresh.validate_grid([self.headers,self.row,self.row])

    def test_registry_mismatched_nct_never_updates_stage_or_results(self):
        self.registry[ID]["protocolSection"]["identificationModule"]["nctId"]="NCT12345678"
        data,report=self.plan()
        cells=self.cells(data)
        self.assertNotIn("D4",cells)
        self.assertNotIn("E4",cells)
        self.assertIn("CTGOV_IDENTITY_OR_RESULTS_NEEDS_REVIEW_ValueError",
                      report["records"][0]["review"])


if __name__=="__main__":
    unittest.main()
