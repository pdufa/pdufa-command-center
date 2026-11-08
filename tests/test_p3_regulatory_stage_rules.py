"""P3 exact-NCT eligibility tests against the reviewed issuer evidence catalog."""
import copy
import importlib.util
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/auto_promote_p3_post_data.py"
spec=importlib.util.spec_from_file_location("p3_gate",SCRIPT)
gate=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=gate
spec.loader.exec_module(gate)
FIXTURE=json.loads((ROOT/"tests/fixtures/p3_regulatory_source_snapshot_20261107.json").read_text())
CUTOFF=date.fromisoformat(FIXTURE["asOf"])

class RegulatoryTests(unittest.TestCase):
    def test_four_evidence_stages_have_distinct_statuses(self):
        path="https://www.sec.gov/Archives/edgar/data/1821586/000182158626000013/moonlake-pressreleasexq320.htm"
        published="2026-11-04"
        for stage,detail in [
            ("PLANNED",{"planned_filing_period":"2027"}),
            ("SUBMITTED",{"submitted_on":"2026-09-30"}),
            ("ACCEPTED",{"accepted_on":"2026-10-01"}),
            ("PDUFA_ASSIGNED",{"pdufa_target_date":"2026-12-15"})
        ]:
            item={"regulatory_path":{"stage":stage,"application_type":"BLA",
                  "review_status":"VERIFIED","source_url":path,
                  "published_at":published,"event_date":"2026-09-30",**detail}}
            result,issue=gate.classify_regulatory_path(item,CUTOFF,CUTOFF)
            self.assertIsNone(issue)
            self.assertEqual(result["stage"],stage)
            if stage=="PDUFA_ASSIGNED": self.assertEqual(result["display"],"2026-12-15")
            if stage in {"PLANNED","SUBMITTED","ACCEPTED"}:
                self.assertNotEqual(result["display"],"2026-12-15")

    def test_false_pdufa_and_stale_filing_are_rejected(self):
        item={"regulatory_path":{"stage":"PLANNED","application_type":"BLA",
             "review_status":"VERIFIED","source_url":"https://issuer.example.com/filing",
             "published_at":"2026-11-04","event_date":"2026-11-04",
             "planned_filing_period":"2027","pdufa_target_date":"2027-09-01"}}
        result,issue=gate.classify_regulatory_path(item,CUTOFF,CUTOFF)
        self.assertIsNone(result)
        self.assertEqual(issue,"PLANNED_FILING_NOT_CURRENT_OR_FALSE_PDUFA")
        del item["regulatory_path"]["pdufa_target_date"]
        item["regulatory_path"]["planned_filing_period"]="2025"
        self.assertIsNone(gate.classify_regulatory_path(item,CUTOFF,CUTOFF)[0])

    def test_reviewed_source_snapshot_yields_four_candidates_and_keeps_izar_for_review(self):
        catalog=copy.deepcopy(FIXTURE["catalog"])
        cases={k:v for k,v in catalog["cases"].items() if "|CLDX|" in k or "|MLTX|" in k}
        self.assertEqual(len(cases),4)
        ncts={v["nctId"] for v in cases.values()}
        self.assertEqual(ncts,{"NCT06445023","NCT06455202","NCT06411899","NCT06411379"})
        self.assertEqual(sorted(v["regulatory_path"]["stage"] for v in cases.values()),
                         ["PLANNED","PLANNED","SUBMITTED","SUBMITTED"])
        # Live ledgers can refresh after this snapshot cutoff. Freeze their
        # actual dated observations, rather than weakening the future-date gate.
        caps=copy.deepcopy(FIXTURE["caps"])
        census=copy.deepcopy(FIXTURE["census"])
        self.assertEqual(len(census),4)
        pool={x["nct_id"]:x["ticker"] for x in census}
        selected={"schemaVersion":catalog["schemaVersion"],"cases":cases}
        with patch.object(gate,"load_csv",return_value=FIXTURE["discoveries"]):
            additions,review=gate.evaluate(selected,caps,census,pool,set(),CUTOFF,
                                          phase3_check=lambda n:"COMPLETED")
        self.assertEqual({a["nct"] for a in additions},ncts)
        for a in additions:
            self.assertEqual(a["values"][15],"")
            self.assertEqual(a["values"][16],"")
            self.assertEqual(a["values"][11:19],[""]*8)
            self.assertEqual(a["values"][6],"https://clinicaltrials.gov/study/"+a["nct"])
            self.assertTrue(gate.link_ok(a["values"][21]))
            self.assertTrue(gate.link_ok(a["values"][26]))
            self.assertTrue(300_000_000<=a["values"][23]<=10_000_000_000)
            if a["ticker"]=="CLDX":
                self.assertIn("filing planned 2027",a["values"][25])
            else:
                self.assertIn("submitted 2026-09-30",a["values"][25])
        self.assertIn("p=0.053",next(a for a in additions if a["nct"]=="NCT06411379")["values"][20])
        self.assertIn("NCT06641076",{r["nct"] for r in review})

    def test_market_caps_after_the_snapshot_cutoff_still_fail_closed(self):
        caps=copy.deepcopy(FIXTURE["caps"])
        for cap in caps:
            cap["market_cap_checked_at"]=(CUTOFF+timedelta(days=1)).isoformat()+"T00:00:00+00:00"
        census=FIXTURE["census"]
        pool={row["nct_id"]:row["ticker"]for row in census}
        with patch.object(gate,"load_csv",return_value=FIXTURE["discoveries"]):
            additions,review=gate.evaluate(FIXTURE["catalog"],caps,census,pool,set(),CUTOFF,
                                          phase3_check=lambda n:"COMPLETED")
        self.assertEqual(additions,[])
        target_ids={item["nctId"]for item in FIXTURE["catalog"]["cases"].values()}
        rejected=[r for r in review if r["nct"]in target_ids]
        self.assertEqual(len(rejected),4)
        self.assertTrue(all("CAP_NOT_CURRENT_VERIFIED_300M_10B"in r["reasons"]for r in rejected))

    def test_master_pool_is_not_the_empty_local_csv(self):
        self.assertEqual(gate.master_pool_identity([["ticker","company","nct_id"],
                   ["CLDX","Celldex","NCT06445023"]]),{"NCT06445023":"CLDX"})
        with self.assertRaises(ValueError):
            gate.master_pool_identity([["ticker","company","nct_id"]])
        with self.assertRaises(ValueError):
            gate.master_pool_identity([["ticker","company","nct_id"],
                ["CLDX","Celldex","NCT06445023"],
                ["MLTX","MoonLake","NCT06445023"]])

if __name__=="__main__":
    unittest.main()
