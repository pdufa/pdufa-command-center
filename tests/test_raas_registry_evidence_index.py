"""RAAS primary-source research index tests: no missing-as-zero or invented results."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "raas_registry_evidence_index",ROOT/"scripts/raas_registry_evidence_index.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def sample(nct="NCT12345678", posted=False):
    return {
      "nctId":nct,"ticker":"TEST","sourceUrl":"https://clinicaltrials.gov/study/"+nct,
      "sourceSha256":"a"*64,"overallRaasScore":None,
      "evidenceState":"POSTED_RESULTS_UNGRADED" if posted else "PROTOCOL_ONLY",
      "hasPostedResults":posted,
      "fetchedAt":"2026-11-04T16:00:00Z",
      "registryStatus":"COMPLETED",
      "registeredPhases":["PHASE3"],
      "registeredConditions":["Test disease"],
      "registeredInterventions":["Drug A"],
      "registeredPrimaryOutcomes":[{"measure":"Primary clinical endpoint","timeFrame":"Week 12"}],
      "postedPrimaryOutcomeCount":1 if posted else 0,
      "postedOtherOutcomeCount":0,
      "primaryPostedEvidence":[{"title":"Primary clinical endpoint",
        "timeFrame":"Week 12","unit":"points",
        "analysesCount":1,"analyses":[{"pValue":"0.02"}]}] if posted else [],
      "seriousAdverseEventTermCount":3 if posted else 0
    }

class IndexTests(unittest.TestCase):
    def payload(self,records):
        return {"schemaVersion":1,"scope":"RAAS_CT_GOV_LIVE_EVIDENCE",
          "latestAttemptAt":"2026-11-04T16:00:00Z",
          "summary":{"registrySourceRecordsStored":len(records),
                     "hasPostedRegistryResults":sum(x["hasPostedResults"] for x in records)},
          "records":records}

    def test_complete_exact_nct_registry_index(self):
        xs=[sample(),sample("NCT12345679",True)]
        out=mod.build_index(self.payload(xs),{"NCT12345678":"TEST","NCT12345679":"TEST"})
        self.assertEqual(out["summary"]["researchNcts"],2)
        self.assertEqual(out["summary"]["postedRegistryResults"],1)
        self.assertEqual(out["summary"]["protocolOnly"],1)
        self.assertEqual(out["summary"]["approvedOverallRaasScores"],0)
        self.assertEqual(out["records"][0]["postedPrimaryOutcomeCount"],0)
        self.assertEqual(out["records"][1]["primaryResults"][0]["pValues"],["0.02"])
        self.assertNotIn("score",out["records"][1])

    def test_missing_nct_rejected_never_zero_graded(self):
        with self.assertRaisesRegex(ValueError,"INCOMPLETE_COHORT"):
            mod.build_index(self.payload([sample()]),
                {"NCT12345678":"TEST","NCT12345679":"TEST"})

    def test_wrong_nct_ticker_source_and_fake_grade_rejected(self):
        basic=sample()
        for patch in [
          {"ticker":"FAKE"},
          {"sourceUrl":"https://clinicaltrials.gov/study/NCT99999999"},
          {"overallRaasScore":75},
          {"sourceSha256":"unknown"},
          {"evidenceState":"POSTED_RESULTS_UNGRADED"}
        ]:
            with self.assertRaisesRegex(ValueError,"INDEX"):
                mod.compact_trial({**basic,**patch},"TEST")

    def test_protocol_only_with_unpublished_results_rejected(self):
        wrong=sample()
        wrong["postedPrimaryOutcomeCount"]=1
        with self.assertRaisesRegex(ValueError,"UNPUBLISHED"):
            mod.compact_trial(wrong,"TEST")

    def test_conflicting_source_totals_rejected(self):
        a=sample()
        data=self.payload([a])
        data["summary"]["registrySourceRecordsStored"]=3
        with self.assertRaisesRegex(ValueError,"SUMMARY_MISMATCH"):
            mod.build_index(data,{"NCT12345678":"TEST"})

    def test_duplicate_nct_rejected(self):
        a=sample()
        with self.assertRaisesRegex(ValueError,"DUPLICATE"):
            mod.build_index(self.payload([a,a]),{"NCT12345678":"TEST"})

if __name__=="__main__":
    unittest.main()
