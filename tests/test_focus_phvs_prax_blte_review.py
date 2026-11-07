"""Exact primary-company results review for PHVS/PRAX/BLTE.

Verify issuer observation, date, registered trial, product token, and missing
uncertainty. A reported result is NOT a validated RAAS score or FDA outcome.
"""
from pathlib import Path
import json
import unittest
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_survey_evidence as collector
FEED=ROOT/"new-platform/frontend/data/benefit-assessment-research.json"
PACKETS=ROOT/"reports/focus-survey/source-packets"
CASES={
 "NCT06343779":{
  "ticker":"PHVS","drug":"Deucrictibant","indication":"Hereditary Angioedema",
  "date":"2025-12-03","source":"https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-rapide-3-pivotal-study",
  "factTokens":{"timeToResponse":["1.28","12 hours","17.47","228.67","0.0001"],
                "clinicalBenefit":["11.95","24 hours","134","93.2%"]}},
 "NCT06669754":{
  "ticker":"PHVS","drug":"Deucrictibant","indication":"Hereditary Angioedema (HAE)",
  "date":"2026-09-08","source":"https://ir.pharvaris.com/news-releases/news-release-details/pharvaris-announces-positive-topline-data-chapter-3-pivotal?trk=article-ssr-frontend-pulse_little-text-block",
  "factTokens":{"magnitude":["83%","87%","55","30","0.0001","CI not supplied"],
                "clinicalBenefit":["83%","87%","85","24 weeks"]}},
 "NCT06087276":{
  "ticker":"PRAX","drug":"60 mg ulixacaltamide","indication":"Essential Tremor",
  "date":"2025-10-16","source":"https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1",
  "factTokens":{"magnitude":["−4.3","−1.7","−2.6","199","233"],
                "responseRemission":["55%","33%","2.7","1.06","6.92","0.0369"]}},
 "NCT05244304":{
  "ticker":"BLTE","drug":"Tinlarebant","indication":"Stargardt Disease 1",
  "date":"2026-08-11","source":"https://belitebio.gcs-web.com/news-releases/news-release-details/belite-bio-announces-us-food-and-drug-administration-acceptance",
  "factTokens":{"magnitude":["35.7%","DDAF","not supplied"]}}
}
class SourceReview(unittest.TestCase):
 def test_trial_specific_company_endpoints_remain_source_facts_only(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  records={r["nctId"]:r for r in feed["records"]}
  self.assertEqual(len(records),len(feed["records"]))
  for nct,spec in CASES.items():
   with self.subTest(nct=nct):
    self.assertIn(nct,records)
    r=records[nct]
    self.assertEqual(r["ticker"],spec["ticker"])
    self.assertEqual(r["drug"],spec["drug"])
    self.assertEqual(r["indication"],spec["indication"])
    self.assertEqual(set(r["facts"]),set(spec["factTokens"]))
    self.assertEqual(r["advantages"],[])
    packet=json.loads((PACKETS/(nct+".json")).read_text(encoding="utf-8"))
    self.assertEqual(packet["nctId"],nct)
    self.assertEqual(packet["ticker"],spec["ticker"])
    self.assertIn(spec["indication"].lower(),[x.lower() for x in packet["registry"]["indications"]])
    for key,terms in spec["factTokens"].items():
     f=r["facts"][key]
     self.assertEqual(f["status"],"VERIFIED")
     self.assertEqual(f["sourceUrl"],spec["source"])
     self.assertEqual(f["sourceDate"],spec["date"])
     self.assertTrue(f["method"])
     self.assertLessEqual(len(f["value"]),500)
     for term in terms:
      self.assertIn(term,f["value"],(nct,key,term))
    for forbidden in ("raasScore","fdaProbability","approvalOdds","score","predictedApproval"):
     self.assertNotIn(forbidden,r)
 def test_combined_registry_intervention_matches_complete_token_only(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  reviewed=next(x for x in feed["records"] if x["nctId"]=="NCT06343779")
  packet=json.loads((PACKETS/"NCT06343779.json").read_text(encoding="utf-8"))
  row={"ticker":"PHVS","nct":"NCT06343779"}
  self.assertIn("Deucrictibant, Placebo",[x["name"] for x in packet["registry"]["interventions"]])
  self.assertIsNotNone(collector.reviewed_fact([reviewed],row,packet,"timeToResponse"))
  self.assertIsNone(collector.reviewed_fact([{**reviewed,"drug":"crictibant"}],row,packet,"timeToResponse"))
  self.assertIsNone(collector.reviewed_fact([{**reviewed,"drug":"Placebo"}],row,packet,"timeToResponse"))
  self.assertIsNone(collector.reviewed_fact([{**reviewed,"indication":"Cushing Syndrome"}],row,packet,"timeToResponse"))
 def test_issuer_sources_cannot_supply_unreported_forecast_or_survival(self):
  feed=json.loads(FEED.read_text(encoding="utf-8"))
  subset=[x for x in feed["records"] if x["nctId"] in CASES]
  self.assertEqual(len(subset),4)
  for r in subset:
   for key in ("survivalBenefit","safetyAdvantage","peakAnnualSales","valuationImpact","shareholderRisk"):
    self.assertNotIn(key,r["facts"])
  blte=next(x for x in subset if x["ticker"]=="BLTE")
  self.assertEqual(blte["facts"]["magnitude"]["confidence"],"LOW")
if __name__=="__main__":
 unittest.main()
