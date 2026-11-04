"""Small RAAS source reconciliation tests: no phantom source recoveries."""
import importlib.util
from pathlib import Path
import unittest

SOURCE=Path(__file__).resolve().parents[1]/"scripts/raas_registry_publish_summary.py"
spec=importlib.util.spec_from_file_location("raas_registry_publish_summary", SOURCE)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def trial(nct, posted=False):
    return {"nctId":nct,"sourceSha256":"a"*64,"hasPostedResults":posted,
       "registeredPrimaryOutcomes":[{"measure":"Primary","timeFrame":"Week 12"}],
       "primaryPostedEvidence":[{"analyses":[{"pValue":"0.004"}]}] if posted else [],
       "overallRaasScore":None}

class SummaryTests(unittest.TestCase):
    def test_missing_mirror_not_equivalent_to_missing_public_record(self):
        ncts={"NCT12345678","NCT12345679"}
        records=[trial("NCT12345678",True)]
        src={"schemaVersion":1,"scope":"RAAS_CT_GOV_LIVE_EVIDENCE","cohort":"research",
             "latestAttemptAt":"2026-11-04T16:00:00Z",
             "summary":{"researchTrials":2,"registrySourceRecordsStored":1,"completeRaasScores":0},
             "errors":[{"nctId":"NCT12345679","reason":"NOT_RETURNED_BY_REGISTRY_SEARCH"}],
             "records":records}
        gaps={"scope":"RAAS_MISSING_REGISTRY_BACKFILL",
              "missing":[{"nctId":"NCT12345678"},{"nctId":"NCT12345679"}]}
        a=m.build_summary(src,gaps,ncts)
        self.assertEqual(a["researchTrials"],2)
        self.assertEqual(a["baselineMirrorGapsWithPublicEvidence"],1)
        self.assertEqual(a["baselineMirrorGapsStillWithoutPublicEvidence"],["NCT12345679"])
        self.assertEqual(a["postedRegistryResults"],1)
        self.assertEqual(a["primaryResultsWithReportedPValues"],1)
        self.assertEqual(a["approvedOverallRaasScores"],0)

    def test_duplicate_and_outside_cohort_evidence_fail_closed(self):
        x={"schemaVersion":1,"scope":"RAAS_CT_GOV_LIVE_EVIDENCE",
           "summary":{"researchTrials":1,"registrySourceRecordsStored":2,"completeRaasScores":0},
           "records":[trial("NCT12345678"),trial("NCT12345678")],"errors":[]}
        gaps={"scope":"RAAS_MISSING_REGISTRY_BACKFILL","missing":[]}
        with self.assertRaisesRegex(ValueError,"duplicate"):
            m.build_summary(x,gaps,{"NCT12345678"})
        x["records"]=[trial("NCT99999999")]
        with self.assertRaisesRegex(ValueError,"outside cohort"):
            m.build_summary(x,gaps,{"NCT12345678"})

    def test_never_promote_source_evidence_to_raas_score(self):
        src={"schemaVersion":1,"scope":"RAAS_CT_GOV_LIVE_EVIDENCE",
             "summary":{"researchTrials":1,"registrySourceRecordsStored":1,"completeRaasScores":0},
             "records":[{**trial("NCT12345678"),"overallRaasScore":80}],"errors":[]}
        gaps={"scope":"RAAS_MISSING_REGISTRY_BACKFILL","missing":[]}
        with self.assertRaisesRegex(ValueError,"Unexpected RAAS score"):
            m.build_summary(src,gaps,{"NCT12345678"})

if __name__=="__main__":
    unittest.main()
