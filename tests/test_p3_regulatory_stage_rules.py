"""P3 exact-NCT eligibility tests against the reviewed issuer evidence catalog."""
import importlib.util
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/auto_promote_p3_post_data.py"
spec=importlib.util.spec_from_file_location("p3_gate",SCRIPT)
gate=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=gate
spec.loader.exec_module(gate)
CUTOFF=date(2026,11,7)

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

    def test_source_catalog_yields_four_qualified_candidates_and_keeps_izar_for_review(self):
        catalog=json.loads((ROOT/"new-platform/backend/app/phase3_curated_announcements.json").read_text())
        cases={k:v for k,v in catalog["cases"].items() if "|CLDX|" in k or "|MLTX|" in k}
        self.assertEqual(len(cases),4)
        ncts={v["nctId"] for v in cases.values()}
        self.assertEqual(ncts,{"NCT06445023","NCT06455202","NCT06411899","NCT06411379"})
        self.assertEqual(sorted(v["regulatory_path"]["stage"] for v in cases.values()),
                         ["PLANNED","PLANNED","SUBMITTED","SUBMITTED"])
        caps=[x for x in gate.load_csv(ROOT/"data/phase_pipeline_market_caps.csv")
              if x["ticker"] in {"CLDX","MLTX"}]
        census=[x for x in gate.load_csv(ROOT/"data/phase3_all_years_300m_10b_trials.csv")
                if x["nct_id"] in ncts]
        self.assertEqual(len(census),4)
        pool={x["nct_id"]:x["ticker"] for x in census}
        selected={"schemaVersion":catalog["schemaVersion"],"cases":cases}
        additions,review=gate.evaluate(selected,caps,census,pool,set(),CUTOFF,
                                      phase3_check=lambda n:"COMPLETED")
        self.assertEqual({a["nct"] for a in additions},ncts)
        for a in additions:
            self.assertEqual(a["values"][15],"")
            self.assertEqual(a["values"][16],"NOT YET SCORED")
            self.assertTrue(300_000_000<=a["values"][23]<=10_000_000_000)
            if a["ticker"]=="CLDX":
                self.assertIn("filing planned 2027",a["values"][25])
            else:
                self.assertIn("submitted 2026-09-30",a["values"][25])
        self.assertIn("p=0.053",next(a for a in additions if a["nct"]=="NCT06411379")["values"][20])
        self.assertIn("NCT06641076",{r["nct"] for r in review})

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
