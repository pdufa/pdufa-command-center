"""MAIN R78: CT.gov registry-history receipt tests. Never simulate a signed SAP."""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"/"scripts"))
from verify_r78_launch_htn_official_registry_history import (
    run,parsed_history,module,fetch_json,LATEST,HISTORY,VERSION_BASE,PRE_COMPLETION_CUTOFF,SAP_SIGNING_CUTOFF
)

def registry(label="week 6",nct="NCT06153693"):
    return {"protocolSection":{
        "identificationModule":{"nctId":nct},
        "statusModule":{"overallStatus":"COMPLETED",
            "primaryCompletionDateStruct":{"date":"2024-12-10","type":"ACTUAL"},
            "completionDateStruct":{"date":"2025-01-24","type":"ACTUAL"}},
        "outcomesModule":{"primaryOutcomes":[{"measure":label,"timeFrame":"6 weeks"}],
                          "secondaryOutcomes":[{"measure":"week-12 bp","timeFrame":"12 weeks"}]}}}

def changes():
    return {"history":{"changes":[
        {"version":0,"date":"2023-12-07","moduleLabels":["Outcome Measures"]},
        {"version":1,"date":"2024-11-12","moduleLabels":["Study Status"]},
        {"version":2,"date":"2025-02-05","moduleLabels":["Outcome Measures"]},
        {"version":3,"date":"2025-03-04","moduleLabels":["Study Status"]},
        {"version":4,"date":"2025-07-21","moduleLabels":["Results"]}
    ]}}

class HistoryReceiptR78(unittest.TestCase):
    def test_exact_registered_version_comparisons_no_sap_lock(self):
        original=registry("original preplanned SBP Week 6")
        v1=registry("original preplanned SBP Week 6")
        v2=registry("updated Week 6 primary")
        def stub(url):
            if url==LATEST:return registry("latest post-readout Week 6")
            if url==HISTORY[0]:return changes()
            if url==VERSION_BASE+"0":return {"studyVersion":0,"study":original}
            if url==VERSION_BASE+"1":return {"studyVersion":1,"study":v1}
            if url==VERSION_BASE+"2":return {"studyVersion":2,"study":v2}
            raise AssertionError("Only original and two pre-signature full versions should be checked: "+url)
        out=run(stub)
        self.assertEqual(out["state"],"OFFICIAL_HISTORICAL_REGISTRY_VERSIONS_READ_RESEARCH_ONLY")
        self.assertEqual(out["historyDatesListed"],5)
        self.assertEqual([x["version"] for x in out["versions"]],[0,1,2])
        self.assertEqual(out["lastVersionAtOrBeforeCompletion"],1)
        self.assertEqual(out["lastVersionAtOrBeforeSapSignature"],2)
        self.assertEqual(out["originalRegisteredPrimaryOutcomeChangedBySapSignature"],True)
        self.assertFalse(out["originalSignedSapAuthenticityConfirmed"])
        self.assertFalse(out["databaseLockDateAuthenticated"])
        self.assertFalse(out["firstTreatmentUnblindingAuthenticated"])
        self.assertFalse(out["preUnblindingOriginalPlanLockProven"])
        self.assertEqual(out["qualifiedIndependentScienceSignatures"],0)
        self.assertEqual(out["independentlyValidatedFDAForecasts"],0)
        self.assertEqual(out["FDAOutcome"],"ABSTAIN")
        self.assertTrue(out["noProductionOrModelTrainingWrites"])

    def test_index_unavailable_returns_false_not_a_missing_history_claim(self):
        def unavailable(url):
            if url==LATEST:return registry()
            raise OSError("offline")
        out=run(unavailable)
        self.assertEqual(out["state"],"REGISTRY_HISTORY_UNVERIFIED")
        self.assertEqual(out["historyDatesListed"],0)
        self.assertEqual(out["registryVersionsAccessible"],0)
        self.assertIsNone(out["originalRegisteredPrimaryOutcomeChangedBySapSignature"])
        self.assertEqual(out["sourceErrors"],["OFFICIAL_HISTORY_INDEX_NOT_AVAILABLE"])
        self.assertEqual(out["FDAOutcome"],"ABSTAIN")

    def test_wrong_trial_and_duplicate_versions_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"CROSS_TRIAL_IDENTITY"):
            module(registry(nct="NCT00000001"))
        with self.assertRaisesRegex(ValueError,"DUPLICATE_HISTORY_VERSION"):
            parsed_history({"changes":[{"version":0,"date":"2024-01-02"},
                                        {"version":0,"date":"2024-02-03"}]})
        with self.assertRaisesRegex(ValueError,"HISTORY_CHANGE_MISSING_NUMBER_OR_DATE"):
            parsed_history({"changes":[{"version":True,"date":"2024-01-01"}]})
        with self.assertRaisesRegex(ValueError,"PROTOCOL_SECTION_NOT_PRESENT"):
            module({"foo":"bar"})

    def test_no_untrusted_http_urls_in_original_registry_request_allowlist(self):
        for u in ["https://example.org/"+ "NCT06153693",
                  "http://clinicaltrials.gov/api/v2/studies/NCT06153693",
                  "https://clinicaltrials.gov/api/int/studies/NCT06153693/history/-1",
                  "https://clinicaltrials.gov/api/int/studies/NCT06153693/history/10000"]:
            with self.assertRaises(ValueError):
                fetch_json(u)

    def test_snapshot_timestamp_boundaries_are_not_a_lock_event(self):
        self.assertEqual(PRE_COMPLETION_CUTOFF,"2025-01-24")
        self.assertEqual(SAP_SIGNING_CUTOFF,"2025-02-13")

if __name__=="__main__":unittest.main()
