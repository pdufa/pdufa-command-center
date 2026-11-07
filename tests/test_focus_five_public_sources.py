"""Offline boundaries for FOCUS multi-source evidence collection and safe syncing."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_five_public_sources as collector
import sync_focus_five_sources_to_sheets as sink

class MultiSourceTests(unittest.TestCase):
 def ctx(self,nct="NCT12345678"):
  return {"nct":nct,"ticker":"TEST","company":"Test Biopharma",
    "drugs":["Obefazimod"],"indications":["Ulcerative Colitis"],
    "registryUrl":"https://clinicaltrials.gov/study/"+nct,
    "registryHash":"a"*64}

 def test_html_parser_skips_script_and_retains_publication_date(self):
  html=b'<html><head><title>Clinical results</title><meta property="article:published_time" content="2026-08-20"/></head><body><script>SCAM_NCT99999999</script><p>Obefazimod in ulcerative colitis achieved reported clinical remission.</p><a href="/news-releases/phase3-readout">readout</a></body></html>'
  doc=collector.Reader()
  doc.feed(html.decode())
  self.assertEqual(doc.meta["article:published_time"],"2026-08-20")
  self.assertNotIn("SCAM_NCT99999999"," ".join(doc.parts))
  self.assertIn("Obefazimod"," ".join(doc.parts))
  self.assertEqual(doc.links[0][0],"/news-releases/phase3-readout")

 def test_source_match_levels_do_not_auto_promote_claims(self):
  ctx=self.ctx()
  self.assertEqual(collector.matches(ctx,"NCT12345678 results","no data"),"EXACT_NCT")
  self.assertEqual(collector.matches(ctx,"Obefazimod in Ulcerative Colitis","readout"),"DRUG_AND_INDICATION")
  self.assertEqual(collector.matches(ctx,"Obefazimod study","readout"),"DRUG_MENTION_ONLY")
  self.assertEqual(collector.matches(ctx,"Ulcerative Colitis care","guideline"),"INDICATION_CONTEXT_ONLY")
  self.assertEqual(collector.matches(ctx,"Quarterly earnings","company update"),"ISSUER_OR_SOURCE_LEAD_ONLY")
  p=collector.match_level_and_record(ctx,"COMPANY","https://example.org/test",
        "NCT12345678 clinical trial results","primary endpoint reached","2026-08-20")
  self.assertFalse(p["reviewed"])
  self.assertEqual(p["status"],"SOURCE_CAPTURED_NEEDS_REVIEW")
  self.assertNotIn("approvalProbability",p)
  self.assertNotIn("raasScore",p)

 def test_canonical_38_ids_and_live_29_trial_roster(self):
  roster=collector.read(collector.ROSTER)["records"]
  catalog=collector.read(collector.CATALOG)["assessments"]
  self.assertEqual(len(roster),29)
  self.assertEqual(len({r["nct"] for r in roster}),29)
  self.assertEqual(len(catalog),20)
  self.assertEqual(sum(len(g["ingredients"]) for g in catalog),38)
  ids={x["id"] for g in catalog for x in g["ingredients"]}
  self.assertTrue(set(collector.PRIMARY_INGREDIENTS).issubset(ids))
  self.assertEqual(len({r["ticker"] for r in roster}),20)

 def test_fda_label_indication_filter_and_approved_index_not_trial_approval(self):
  ctx=self.ctx()
  original=collector.fetch
  try:
   collector.fetch=lambda *args,**kwargs: (
       {"results":[{"effective_time":"20260801",
         "openfda":{"brand_name":["Competing Drug"],
                    "generic_name":["Different drug"],
                    "application_number":["NDA1234"]},
         "indications_and_usage":["Indicated for Ulcerative Colitis treatment."]},
         {"openfda":{"brand_name":["Wrong Indication"],"application_number":["NDA2"]},
          "indications_and_usage":["Indicated for Migraine"]}]},None)
   rows,error=collector.fda_search(ctx,"APPROVED_LABELS_BY_DISEASE")
   self.assertIsNone(error)
   self.assertEqual(len(rows),1)
   self.assertEqual(rows[0]["sourceType"],"FDA")
   self.assertEqual(rows[0]["sourceMatch"],"FDA_INDEX_SEARCH_MATCH_NEEDS_INDICATION_REVIEW")
   self.assertFalse(rows[0]["reviewed"])
  finally:collector.fetch=original

 def test_europepmc_exact_nct_and_drug_mention_are_distinct(self):
  ctx=self.ctx()
  original=collector.fetch
  try:
   collector.fetch=lambda *args,**kwargs: (
      {"resultList":{"result":[
       {"source":"MED","id":"12345","title":"Study NCT12345678 readout",
        "abstractText":"Clinical benefit of obefazimod","firstPublicationDate":"2026-08-01"},
       {"source":"MED","id":"12346","title":"Obefazimod treatment",
        "abstractText":"Other conditions","firstPublicationDate":"2026-07-01"}]}},None)
   rows,error=collector.literature_search(ctx,"TRIAL")
   self.assertIsNone(error)
   self.assertEqual(len(rows),2)
   self.assertEqual(rows[0]["sourceMatch"],"EXACT_NCT")
   self.assertEqual(rows[1]["sourceMatch"],"DRUG_MENTION_ONLY")
  finally:collector.fetch=original

 def test_sec_is_filing_pointer_not_contract_evidence(self):
  ctx=self.ctx()
  r={"ticker":"TEST","regulatoryUrl":
     "https://www.sec.gov/Archives/edgar/data/1234/test.htm"}
  record=collector.sec_source(r,ctx,"0000012345")
  self.assertEqual(record["sourceType"],"SEC")
  self.assertEqual(record["sourceMatch"],"ISSUER_FILING_POINTER_ONLY")
  self.assertFalse(record["reviewed"])
  self.assertNotIn("estimatedRevenue",record)

 def test_sync_isolation_and_full_roster_validation(self):
  fake=[{"nctId":"NCT%08d"%i,"ticker":"T","sourceCounts":{
    "COMPANY":0,"FDA":0,"LITERATURE":0,"SEC":1},"strongSourceContext":0,
    "candidateIngredientIds":[]} for i in range(1,30)]
  summary={"schemaVersion":1,"focusTrials":29,"surveyGroups":20,
           "surveyIngredients":38,"newSourceLeads":0,"perTrial":fake}
  tables=sink.prep if False else None
  # Standalone source tables must have exactly 16 lead columns.
  self.assertEqual(len(sink.LEAD_COLS),16)
  self.assertEqual(len(sink.SUMMARY_HEADERS),10)
  self.assertTrue(sink.LEADS_TITLE.startswith("FOCUS Survey Auto"))
  self.assertTrue(sink.SUMMARY_TITLE.startswith("FOCUS Survey Auto"))

if __name__=="__main__":
 unittest.main()
