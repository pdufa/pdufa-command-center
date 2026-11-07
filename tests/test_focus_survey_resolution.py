"""Verify exact FOCUS survey research dispositions, never invented verification."""
from pathlib import Path
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import resolve_focus_survey_ingredients as resolve
import sync_focus_survey_resolution_to_sheets as sheet

class TestResolution(unittest.TestCase):
 def test_inventory_all_1102_and_no_fabricated_grade(self):
  roster=resolve.load(resolve.ROSTER)["records"]
  groups=resolve.load(resolve.CATALOG)["assessments"]
  slots=resolve.load(resolve.OUT/"evidence.json")["slots"]
  triage=resolve.load(resolve.OUT/"review-queue.json")["observations"]
  pubs=resolve.load(resolve.OUT/"publication-triage.json")["articles"]
  packets={r["nct"]:resolve.load(resolve.REGISTRY_PATH/(r["nct"]+".json")) for r in roster}
  matrix=resolve.build(roster,groups,slots,packets,triage,pubs)
  summary=resolve.summary_of(matrix,roster)
  self.assertEqual(len(roster),29)
  self.assertEqual(len(matrix),1102)
  self.assertEqual(summary["researchDispositionCoveragePercent"],100.0)
  self.assertEqual(summary["verifiedSurveyAnswers"],0)
  self.assertEqual(summary["verifiedSurveyPercent"],0.0)
  self.assertEqual(sum(summary["dispositions"].values()),1102)
  self.assertEqual(len(summary["bySurvey"]),20)
  self.assertEqual(len(summary["byTrial"]),29)
  self.assertTrue(all(x["applicability"]=="NOT_YET_ADJUDICATED" for x in matrix))
  self.assertTrue(all(x["missingEvidenceRequirement"] for x in matrix))
  self.assertTrue(all(x["nextEvidenceStep"] for x in matrix))
  self.assertTrue(all(x["recommendedSource"].startswith("https://") for x in matrix))
  self.assertTrue(all(x["sourcePacketHash"] for x in matrix))
  self.assertTrue(all(x["isSurveyAnswerVerified"]==False for x in matrix))
  self.assertEqual(len({(x["nctId"],x["ingredientId"]) for x in matrix}),1102)
  self.assertTrue(any(x["researchDisposition"]=="PRIMARY_SOURCE_INTERPRETATION_REQUIRED"
       for x in matrix))
  self.assertTrue(any(x["researchDisposition"]=="MODELING_INPUTS_UNAVAILABLE"
       for x in matrix))

 def test_rejected_tampered_packet_and_missing_ingredient(self):
  roster=resolve.load(resolve.ROSTER)["records"]
  groups=resolve.load(resolve.CATALOG)["assessments"]
  slots=resolve.load(resolve.OUT/"evidence.json")["slots"]
  triage=resolve.load(resolve.OUT/"review-queue.json")["observations"]
  pubs=resolve.load(resolve.OUT/"publication-triage.json")["articles"]
  packets={r["nct"]:resolve.load(resolve.REGISTRY_PATH/(r["nct"]+".json")) for r in roster}
  with self.assertRaisesRegex(ValueError,"SURVEY_INVENTORY_INCOMPLETE|SURVEY_DISPOSITIONS_INCOMPLETE"):
   resolve.build(roster,groups,slots[:-1],packets,triage,pubs)
  first=roster[0]["nct"]
  tampered={**packets[first],"ticker":"WRONG"}
  with self.assertRaisesRegex(ValueError,"EXACT_REGISTRY_PACKET_REQUIRED"):
   resolve.build(roster,groups,slots,{**packets,first:tampered},triage,pubs)
  wrong=[{**slots[0],"status":"VERIFIED","reviewedSourceUrl":None}]+slots[1:]
  with self.assertRaisesRegex(ValueError,"VERIFIED_WITHOUT_PROVENANCE"):
   resolve.build(roster,groups,wrong,packets,triage,pubs)

 def test_worklist_and_sheet_output_preserve_sources(self):
  # Existing source evidence is never replaced by a generated research worklist.
  before=(resolve.OUT/"evidence.json").read_bytes()
  summary=resolve.run()
  after=(resolve.OUT/"evidence.json").read_bytes()
  self.assertEqual(before,after)
  self.assertEqual(summary["slots"],1102)
  tables=sheet.prepare_tables()
  self.assertEqual([a[0] for a in tables],
      ["FOCUS Survey Auto Resolution","FOCUS Survey Auto Resolution Summary"])
  self.assertEqual(len(tables[0][2]),1102)
  self.assertEqual(len(tables[1][2]),20)
  self.assertTrue(all(h.startswith("FOCUS Survey Auto ") for h,_,_ in tables))

if __name__=="__main__":
 unittest.main()
