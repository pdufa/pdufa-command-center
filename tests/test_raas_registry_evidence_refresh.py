"""Offline validation for the official RAAS registry data collector."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("registry",ROOT/"scripts/raas_registry_evidence_refresh.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
BASE=json.loads((ROOT/"new-platform/frontend/data/raas-registry-evidence-census.json").read_text())
STAMP="2026-11-04T17:10:00Z"

def sample(nct,results=False):
    result={
      "protocolSection":{
        "identificationModule":{"nctId":nct},
        "statusModule":{"overallStatus":"COMPLETED",
             "lastUpdatePostDateStruct":{"date":"2026-11-01"}},
        "designModule":{"enrollmentInfo":{"count":175}},
        "outcomesModule":{"primaryOutcomes":[{"measure":"Change from baseline"}],
                          "secondaryOutcomes":[]}},
      "hasResults":results
    }
    if results:
        result["resultsSection"]={"outcomeMeasuresModule":{
            "outcomeMeasures":[{"analyses":[{"pValue":"0.02"}]}]}}
    return result

class RegistryTests(unittest.TestCase):
    def test_manifest(self):
        rows=mod.validate_manifest(BASE)
        self.assertEqual(len(rows),762)
        self.assertGreaterEqual(BASE["counts"]["cachedRegistry"],727)
        self.assertEqual(BASE["counts"]["cachedRegistry"]+BASE["counts"]["missingRegistry"],762)
        self.assertLessEqual(BASE["counts"]["postedResults"],762)
        self.assertLessEqual(BASE["counts"]["resultAnalyses"],762)
        self.assertTrue(all(x["approvedRaasScore"] is None for x in rows))
        self.assertTrue(all(x["issuerReadoutStage"] is None for x in rows))
    def test_source_identity_and_result_flags(self):
        x=mod.extract_study(sample("NCT12345678",True),"NCT12345678",STAMP)
        self.assertEqual(x["analysisCount"],1)
        self.assertTrue(x["hasPostedResults"])
        self.assertIsNone(x["approvedRaasScore"])
        self.assertIsNone(x["issuerReadoutStage"])
        with self.assertRaises(ValueError):
            mod.extract_study(sample("NCT12345678"),"NCT87654321",STAMP)
    def test_all_trials_and_failed_batch_retention(self):
        all_rows=mod.refresh(BASE,fetcher=lambda ids:[sample(i) for i in ids],captured_at=STAMP)
        self.assertEqual(all_rows["counts"]["livePrimaryRegistry"],762)
        self.assertEqual(all_rows["counts"]["apiBatchesSucceeded"],20)
        self.assertTrue(all(x["approvedRaasScore"] is None for x in all_rows["records"]))
        missing_id=BASE["records"][0]["nctId"]
        def partial(ids):
            if missing_id in ids:raise RuntimeError("Unavailable")
            return [sample(i) for i in ids]
        partial_rows=mod.refresh(BASE,fetcher=partial,captured_at=STAMP)
        old=BASE["records"][0]
        fresh=partial_rows["records"][0]
        self.assertEqual(old["capturedAt"],fresh["capturedAt"])
        self.assertEqual(partial_rows["counts"]["apiBatchesFailed"],1)

if __name__=="__main__":
    unittest.main()
