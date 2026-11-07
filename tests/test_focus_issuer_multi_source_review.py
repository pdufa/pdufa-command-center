"""Offline source-review guards for actual issuer Phase 3 endpoints.

The word VERIFIED here means a reported number and source link have been
checked, not that a regulatory decision, trial score, or efficacy interpretation
has independently been established.
"""
import json,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
CATALOG=ROOT/"data/phase3_benefit_survey_catalog.json"
EXPECTED={
 "NCT06445023":{"ticker":"CLDX","drug":"barzolvolimab","indication":"Chronic Spontaneous Urticaria",
                  "facts":{"magnitude":["-20.2","-20.5","-10.7","0.00001"],
                           "responseRemission":["42.4%","42.1%","9.3%","49.0%","15.4%"]}},
 "NCT06455202":{"ticker":"CLDX","drug":"barzolvolimab","indication":"Chronic Spontaneous Urticaria",
                  "facts":{"magnitude":["-20.2","-19.7","-11.4","0.00001"],
                           "responseRemission":["45.7%","44.0%","12.6%","54.0%","17.6%"]}},
 "NCT04716231":{"ticker":"VERA","drug":"Atacicept","indication":"IgA Nephropathy",
                  "facts":{"magnitude":["+5.6","3.7","7.5","+5.0"],
                           "clinicalBenefit":["11","38","0.24","0.12","0.48"]}},
 "NCT06411899":{"ticker":"MLTX","drug":"Sonelokimab","indication":"Hidradenitis Suppurativa",
                  "facts":{"responseRemission":["VELA-1","34.8%","17.5%","0.001"]}},
 "NCT06411379":{"ticker":"MLTX","drug":"Sonelokimab","indication":"Hidradenitis Suppurativa",
                  "facts":{"responseRemission":["VELA-2","0.053","DID NOT","35.9%","25.6%","0.033"]}},
 "NCT04871282":{"ticker":"IMNM","drug":"AL102","indication":"Desmoid Tumor",
                  "facts":{"responseRemission":["RINGSIDE","56%","9%","0.0001"]}},
}
SOURCES={
 "CLDX":"https://ir.celldex.com/news-releases/news-release-details/celldex-announces-positive-results-phase-3-embarq-csu1-and",
 "VERA":"https://veratherapeutics.gcs-web.com/news-releases/news-release-details/vera-therapeutics-announces-trutaknatm-atacicept-vymj-stabilized",
 "MLTX":"https://ir.moonlaketx.com/news-releases/news-release-details/moonlake-immunotherapeutics-reports-week-16-results-vela-phase-3",
 "IMNM":"https://investors.immunome.com/immunome-presents-additional-clinical-data-for-varegacestat-in-desmoid-tumors-at-esmo-2026/",
}
DATE={"CLDX":"2026-09-22","VERA":"2026-09-15","MLTX":"2025-09-28","IMNM":"2026-10-26"}

class FiveSourceReview(unittest.TestCase):
 def test_exact_program_identity_values_source_and_no_auto_raas(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
  allowed={x["id"] for group in catalog["assessments"] for x in group["ingredients"]}
  records={x["nctId"]:x for x in feed["records"]}
  self.assertEqual(len(records),len(feed["records"]))
  for nct,expected in EXPECTED.items():
   with self.subTest(nct=nct):
    self.assertIn(nct,records)
    row=records[nct]
    self.assertEqual(row["ticker"],expected["ticker"])
    self.assertEqual(row["drug"],expected["drug"])
    self.assertEqual(row["indication"],expected["indication"])
    packet=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf-8"))
    self.assertEqual(packet["nctId"],nct)
    self.assertEqual(packet["ticker"],expected["ticker"])
    self.assertIn(row["drug"].lower(),[x["name"].lower()
        for x in packet["registry"]["interventions"]])
    self.assertIn(row["indication"].lower(),[x.lower()
        for x in packet["registry"]["indications"]])
    self.assertFalse(row.get("overallAdvantages"))
    self.assertEqual(row["advantages"],[])
    for field,terms in expected["facts"].items():
     self.assertIn(field,allowed)
     fact=row["facts"][field]
     self.assertEqual(fact["status"],"VERIFIED")
     self.assertEqual(fact["sourceUrl"],SOURCES[row["ticker"]])
     self.assertEqual(fact["sourceDate"],DATE[row["ticker"]])
     self.assertIn(fact["confidence"],("HIGH","MODERATE","LOW"))
     self.assertGreater(len(fact["method"]),80)
     for term in terms:
      self.assertIn(term,fact["value"],(nct,field,term))
    for forbidden in ("raasScore","fdaProbability","approvalOdds","investmentRecommendation"):
     self.assertNotIn(forbidden,row)
 def test_vela2_primary_failure_is_not_cherry_picked(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  vela2=next(x for x in feed["records"] if x["nctId"]=="NCT06411379")
  data=vela2["facts"]["responseRemission"]["value"]
  self.assertIn("DID NOT reach significance",data)
  self.assertIn("composite-strategy",data)
  self.assertIn("p=0.053",data)
  self.assertIn("treatment-policy",data)
  self.assertNotIn("approval probability",data.lower())
 def test_company_reports_not_scored_as_safety_superiority(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  for record in feed["records"]:
   if record["nctId"] in EXPECTED:
    self.assertFalse("safetyAdvantage" in record["facts"])
    self.assertFalse("shareholderRisk" in record["facts"])
    self.assertFalse("peakAnnualSales" in record["facts"])

if __name__=="__main__":
 unittest.main()
