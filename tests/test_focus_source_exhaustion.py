"""Verify failed research sources trigger an alternate route rather than premature no-more claims."""
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_focus_source_exhaustion as audit
import collect_focus_direct_company_releases as company
import sync_focus_source_exhaustion_to_sheets as sink

class ExhaustionTests(unittest.TestCase):
 def fixtures(self):
  roster=audit.load(audit.ROSTER)["records"]
  catalog=audit.load(audit.CATALOG)["assessments"]
  ctx=audit.make_context(roster)
  return roster,catalog,ctx

 def test_company_fallbacks_are_attempted_without_overwriting_original_index(self):
  roster,_,ctx=self.fixtures()
  original=json.loads(company.SEEDS.read_text())["sources"]
  alternate=company.expand_official_candidates(roster,original)
  self.assertGreater(len(alternate),len(original))
  self.assertEqual(len({x["nctId"] for x in alternate}),29)
  self.assertLessEqual(len(alternate),87)
  self.assertEqual(company.SEEDS.read_text(),company.SEEDS.read_text())
  self.assertTrue(all(x["url"].startswith("https://") for x in alternate))
  self.assertTrue(all("clinicaltrials.gov" not in x["url"] and "sec.gov" not in x["url"]
                      for x in alternate))
  for nct in {r["nct"] for r in roster}:
   self.assertTrue(any(x["nctId"]==nct for x in alternate))

 def test_403_never_becomes_no_more_evidence(self):
  roster,catalog,ctx=self.fixtures()
  nct=roster[0]["nct"];ticker=roster[0]["ticker"]
  fake={**ctx,"issuer":{**ctx["issuer"],ticker:{"ticker":ticker,
               "status":"SEC_SOURCE_UNAVAILABLE","sourceError":"SEC_HTTP_403"}},
        "direct":{**ctx["direct"],nct:[{
          "nctId":nct,"ticker":ticker,"url":"https://example.org/company",
          "status":"SOURCE_LINK_ONLY_CONTENT_UNAVAILABLE","error":"HTTP_403",
          "ingredientCandidates":[]}]}}
  for src in ("SEC","COMPANY"):
   result=audit.assess_source(src,roster[0],"licensingValue",18,fake)
   self.assertEqual(result["status"],audit.BLOCKED)
  rows,summary=audit.audit(roster,catalog,fake)
  target=next(x for x in rows if x["nctId"]==nct and x["ingredientId"]=="licensingValue")
  self.assertEqual(target["nextAction"],"UNBLOCK_WITH_INDEPENDENT_PRIMARY_SOURCE")
  self.assertIn("SEC",target["blockedFamilies"])
  self.assertIn("COMPANY",target["blockedFamilies"])
  self.assertEqual(summary["researchExhausted"],0)
  self.assertIn("issuer-hosted", " ".join(target["suggestedFallbacks"]))

 def test_full_inventory_and_required_attempt_coverage_is_not_misrepresented(self):
  roster,catalog,ctx=self.fixtures()
  rows,summary=audit.audit(roster,catalog,ctx)
  self.assertEqual(len(rows),1102)
  self.assertEqual(summary["trials"],29)
  self.assertEqual(summary["surveys"],20)
  self.assertEqual(summary["ingredients"],38)
  self.assertEqual(summary["researchExhausted"],0)
  self.assertEqual(sum(x["sourcesRequired"] for x in rows),summary["sourceReceipts"])
  self.assertEqual(sum(x["sourcesAttempted"] for x in rows),summary["sourceAttempts"])
  self.assertEqual(len({(x["nctId"],x["ingredientId"]) for x in rows}),1102)
  self.assertTrue(all(x["sourcesAttempted"]<=x["sourcesRequired"] for x in rows))
  self.assertTrue(all(x["nextAction"] for x in rows))
  self.assertTrue(any(x["unsearchedFamilies"] for x in rows))
  self.assertTrue(any("SEC" in x["blockedFamilies"] for x in rows))
  verified=sum(x["isVerifiedIngredient"] for x in rows)
  self.assertEqual(verified,summary["verifiedIngredientInputs"])
  self.assertGreaterEqual(verified,3)
  self.assertTrue(all(not x["isResearchExhausted"] for x in rows))

 def test_protected_google_sheet_source_audit(self):
  roster,catalog,ctx=self.fixtures()
  before=(audit.OUT/"evidence.json").read_bytes()
  report=audit.run()
  self.assertEqual((audit.OUT/"evidence.json").read_bytes(),before)
  tables=sink.prepare()
  self.assertEqual(len(tables),2)
  self.assertEqual(len(tables[0][2]),1102)
  self.assertEqual(len(tables[0][1]),25)
  self.assertTrue(all(len(row)==25 for row in tables[0][2]))
  self.assertEqual(len(tables[1][2]),11)
  self.assertTrue(all(x[0].startswith("FOCUS Survey Auto ") for x in tables))
  self.assertEqual(report["researchExhausted"],0)

if __name__=="__main__":
 unittest.main()
