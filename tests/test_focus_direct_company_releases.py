"""Validate all 29 exact-trial official issuer release links without inflating surveys."""
from __future__ import annotations
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import collect_focus_direct_company_releases as collection
import collect_focus_five_public_sources as existing
import sync_focus_direct_company_to_sheets as sink

class DirectSourceTests(unittest.TestCase):
 def fixtures(self):
  roster=existing.read(collection.ROSTER)["records"]
  seeds=collection.validate(roster,existing.read(collection.SEEDS))
  packets={r["nct"]:existing.read(collection.PACKETS/(r["nct"]+".json")) for r in roster}
  return roster,seeds,packets

 def test_whole_roster_has_exact_official_company_source_link(self):
  roster,seeds,packets=self.fixtures()
  self.assertEqual(len(roster),29)
  self.assertEqual(len(seeds),29)
  self.assertEqual({r["nct"] for r in roster},{x["nctId"] for x in seeds})
  self.assertEqual(len({r["ticker"] for r in roster}),20)
  self.assertEqual(len({x["nctId"] for x in seeds}),29)
  self.assertEqual(len(sink.COLUMNS),11)
  self.assertTrue(sink.TITLE.startswith("FOCUS Survey Auto "))

 def test_source_capture_strong_exact_and_blocked_link_are_distinct(self):
  roster,seeds,packets=self.fixtures()
  all_urls={x["url"] for x in seeds}
  results={url:{"error":"HTTP_403","document":None} for url in all_urls}
  known=next(x for x in seeds if x["nctId"]=="NCT06445023")
  results[known["url"]]={"error":None,"document":{
     "title":"Celldex Phase 3 EMBARQ-CSU1 and CSU2 results",
     "body":"Celldex Phase 3 barzolvolimab chronic spontaneous urticaria "
         "NCT06445023 and NCT06455202 primary endpoint UAS7 at Week 12 "
         "showed efficacy and placebo differences.",
     "detectedDate":"2026-09-22","contentSha256":"a"*64,"sourceChars":200
  }}
  ledger,candidates,summary=collection.build(roster,seeds,packets,results)
  self.assertEqual(len(ledger),29)
  self.assertEqual(summary["trials"],29)
  self.assertEqual(summary["selectedLinks"],29)
  self.assertEqual(summary["verifiedSurveyAnswersCreated"],0)
  self.assertEqual(summary["capturedPages"],2)
  self.assertEqual(summary["blockedOrUnavailable"],27)
  self.assertEqual({x["nctId"] for x in candidates},{"NCT06445023","NCT06455202"})
  self.assertTrue(all(x["sourceMatch"]=="EXACT_NCT" for x in candidates))
  self.assertTrue(all(x["reviewed"] is False for x in candidates))
  self.assertTrue(all(x["status"]=="SOURCE_CAPTURED_NEEDS_REVIEW" for x in candidates))
  self.assertTrue(any(x["status"]=="SOURCE_LINK_ONLY_CONTENT_UNAVAILABLE" for x in ledger))

 def test_wrong_issuer_or_wrong_nct_is_rejected(self):
  roster,seeds,_=self.fixtures()
  wrong=[{**seeds[0],"ticker":"WRONG"}]+seeds[1:]
  with self.assertRaisesRegex(ValueError,"INVALID_DIRECT_COMPANY"):
   collection.validate(roster,{"schemaVersion":1,"sources":wrong})
  duplicate=seeds+[seeds[0]]
  with self.assertRaisesRegex(ValueError,"INVALID_DIRECT_COMPANY"):
   collection.validate(roster,{"schemaVersion":1,"sources":duplicate})

if __name__=="__main__":
 unittest.main()
