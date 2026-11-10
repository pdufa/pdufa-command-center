"""MAIN R73: original published index must never become a signed SAP or FDA call."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"/"scripts"))
from verify_focus_r73_launch_htn_document_index import validate

def fixtures():
 return (
   json.loads((ROOT/"frontend"/"data"/"focus-r73-launch-htn-original-document-index.json").read_text()),
   json.loads((ROOT/"frontend"/"data"/"focus-r71-five-main-publication-source-review.json").read_text())
 )

class OriginalDocumentIndexR73(unittest.TestCase):
 def test_seven_exact_documents_and_zero_scientific_certification(self):
  manifest,r71=fixtures()
  x=validate(manifest,r71)
  self.assertEqual(x["indexedSourceDocumentLinks"],7)
  self.assertEqual(x["protocolVersions"],3)
  self.assertEqual(x["statisticalAnalysisPlanDocuments"],3)
  self.assertEqual(x["methodsSupplements"],1)
  self.assertEqual(x["verifiedOriginalPDFBytes"],0)
  self.assertEqual(x["signedPreunblindingStatisticalPlans"],0)
  self.assertEqual(x["signedScientificReviews"],0)
  self.assertEqual(x["validatedFDAForecasts"],0)
  self.assertEqual(x["futureFDAOutcome"],"ABSTAIN")

 def test_forged_document_identity_revisions_and_score_fail_closed(self):
  attacks=[
   lambda r:r["documents"].pop(),
   lambda r:r["documents"].reverse(),
   lambda r:r["documents"][1].__setitem__("title","Trial protocol version 3.0"),
   lambda r:r["documents"][2].__setitem__("role","SAP_AMENDMENT"),
   lambda r:r["documents"][1].__setitem__("filename","junk.pdf"),
   lambda r:r["documents"][1].__setitem__("publicOriginalIndexLink","https://attacker.example/file.pdf"),
   lambda r:r["documents"][1].__setitem__("sha256","a"*64),
   lambda r:r["documents"][1].__setitem__("firstPublicAvailabilityDate","2025-01-01"),
   lambda r:r["documents"][1].__setitem__("prospectivelySignedAndLockedBeforeUnblinding",True),
   lambda r:r.__setitem__("sourceDocumentHashesVerified",7),
   lambda r:r.__setitem__("originalPreunblindingSignaturesVerified",1),
   lambda r:r.__setitem__("originalLockChronologiesVerified",1),
   lambda r:r.__setitem__("originalFullPdfScientificReviewsSigned",1),
   lambda r:r.__setitem__("validatedFDAApplicationForecasts",23),
   lambda r:r.__setitem__("officialFutureFDAOutcome","APPROVAL"),
   lambda r:r.__setitem__("clinicalGrade",5),
   lambda r:r.__setitem__("trainingOrProductionWrites",True),
   lambda r:r.__setitem__("newApprovedGrade",99)
  ]
  original,r71=fixtures()
  for i,attack in enumerate(attacks):
   with self.subTest(i=i):
    poisoned=copy.deepcopy(original)
    attack(poisoned)
    with self.assertRaises(ValueError):
     validate(poisoned,r71)

 def test_upstream_original_nct_and_pmid_not_switchable(self):
  manifest,r71=fixtures()
  r71["cases"][3]["pmid"]="99999999"
  with self.assertRaises(ValueError):
   validate(manifest,r71)

if __name__=="__main__":
 unittest.main()
