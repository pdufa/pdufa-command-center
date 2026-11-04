"""Tests: reviewable source coverage, never fabricated RAAS outputs."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("receipt",ROOT/"scripts/raas_registry_evidence_summary.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def row(nct,posted):
    return {"nctId":nct,"ticker":"TEST","sourceUrl":"https://clinicaltrials.gov/study/"+nct,
      "sourceSha256":"a"*64,"hasPostedResults":posted,
      "evidenceState":"POSTED_RESULTS_UNGRADED" if posted else "PROTOCOL_ONLY",
      "registeredPrimaryOutcomes":[{"measure":"Change in symptoms"}],
      "primaryPostedEvidence":[{"analysesCount":2}] if posted else [],
      "seriousAdverseEventTermCount":3 if posted else 0,
      "overallRaasScore":None}
class ReceiptTests(unittest.TestCase):
    def test_real_results_are_distinguished_from_missing_and_protocol_only(self):
        a,b,c="NCT00000001","NCT00000002","NCT00000003"
        x={"schemaVersion":1,"scope":"RAAS_CT_GOV_LIVE_EVIDENCE",
            "latestAttemptAt":"2026-11-04T15:00:00+00:00","errors":[
            {"nctId":c,"reason":"NOT_RETURNED_BY_REGISTRY_SEARCH"}],
            "records":[row(a,True),row(b,False)]}
        r=mod.summarize(x,{a:"TEST",b:"TEST",c:"TEST"},[b,c])
        s=r["summary"]
        self.assertEqual(s["sourceRecordsStored"],2)
        self.assertEqual(s["postedRegistryResults"],1)
        self.assertEqual(s["protocolOnly"],1)
        self.assertEqual(s["sourceRecordsStillMissing"],1)
        self.assertEqual(s["missingRecordsRecoveredFromOriginal35"],1)
        self.assertEqual(s["trialsWithPrimaryRegistryAnalyses"],1)
        self.assertEqual(s["approvedOverallRaasScores"],0)
        self.assertEqual(r["pendingRegistryNctIds"],[c])
    def test_source_mismatch_duplicate_and_false_score_are_rejected(self):
        n="NCT00000001"
        initial={"schemaVersion":1,"scope":"RAAS_CT_GOV_LIVE_EVIDENCE",
                 "records":[row(n,True)],"errors":[]}
        self.assertEqual(mod.summarize(initial,{n:"TEST"},[])["summary"]["researchTrials"],1)
        for change in [{"ticker":"OTHER"},{"sourceUrl":"https://example.invalid"},
                       {"overallRaasScore":99},{"hasPostedResults":False},
                       {"sourceSha256":"not-a-sha"}]:
            bad={**initial,"records":[{**row(n,True),**change}]}
            with self.assertRaisesRegex(ValueError,"RAAS_SOURCE"):
                mod.summarize(bad,{n:"TEST"},[])
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            mod.summarize({**initial,"records":[row(n,True),row(n,True)]},{n:"TEST"},[])
if __name__=="__main__":
    unittest.main()
