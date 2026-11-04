"""Strict historical NDA/BLA outcome separation: no hindsight-based accuracy."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "raas_historical_fda_application_outcomes",
    ROOT/"scripts/raas_historical_fda_application_outcomes.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.source=json.loads(mod.SOURCE.read_text(encoding="utf8"))
        self.registry=(json.loads(mod.REGISTRY.read_text(encoding="utf8"))
                       if mod.REGISTRY.exists() else None)

    def test_real_application_outcomes_are_not_validated_predictions(self):
        csv_text,json_text=mod.export(self.source,self.registry)
        rows=list(csv.DictReader(io.StringIO(csv_text)))
        s=json.loads(json_text)
        self.assertEqual(len(rows),2)
        self.assertEqual(s["uniqueApplicationDecisions"],2)
        self.assertEqual(s["linkedTrialNcts"],3)
        self.assertEqual(s["completeResponseLetters"],1)
        self.assertEqual(s["approvals"],1)
        self.assertEqual(s["independentPreActionModelPredictions"],0)
        self.assertIsNone(s["validatedPredictionAccuracy"])
        self.assertTrue(all(r["calibratedPredictionEligible"]=="False"
                            for r in rows))
        achv=next(r for r in rows if r["ticker"]=="ACHV")
        self.assertEqual(achv["linkedNcts"],
                         "NCT04576949;NCT05206370")
        self.assertEqual(achv["actualOutcome"],"COMPLETE_RESPONSE_LETTER")
        self.assertEqual(achv["preActionSourceDate"],"2026-05-12")
        self.assertEqual(achv["pdufaTargetDate"],"2026-06-20")
        self.assertEqual(achv["actualOutcomePublicDate"],"2026-06-22")
        self.assertEqual(achv["actualDecisionDate"],"")
        acad=next(r for r in rows if r["ticker"]=="ACAD")
        self.assertEqual(acad["linkedNcts"],"NCT04181723")
        self.assertEqual(acad["actualOutcome"],"APPROVAL")

    def test_duplicate_nct_across_applications_is_fatal(self):
        modified=copy.deepcopy(self.source)
        modified["records"][1]["trialNcts"]+=["NCT05206370"]
        with self.assertRaisesRegex(ValueError,"CROSS_TRIAL_OR_DOUBLE_COUNT"):
            mod.export(modified,self.registry)

    def test_failed_assumed_forecast_is_forbidden(self):
        modified=copy.deepcopy(self.source)
        modified["records"][0]["predictionIssuedBeforeDecision"]=True
        with self.assertRaisesRegex(ValueError,"PREDICTION_LEAK"):
            mod.export(modified,self.registry)
        modified=copy.deepcopy(self.source)
        modified["records"][0]["calibratedPredictionEligible"]=True
        with self.assertRaisesRegex(ValueError,"PREDICTION_LEAK"):
            mod.export(modified,self.registry)

    def test_outcome_date_cannot_create_an_asof_prior_prediction(self):
        modified=copy.deepcopy(self.source)
        modified["records"][0]["preActionSourceDate"]="2026-07-01"
        with self.assertRaisesRegex(ValueError,"CHRONOLOGY"):
            mod.export(modified,self.registry)
        modified=copy.deepcopy(self.source)
        modified["records"][0]["actualOutcomePublicDate"]="2027-01-01"
        with self.assertRaisesRegex(ValueError,"CHRONOLOGY"):
            mod.export(modified,self.registry)

    def test_trial_identity_reconciliation_with_registry(self):
        if self.registry is None:
            self.skipTest("Registry source snapshot is absent from checkout")
        modified=copy.deepcopy(self.registry)
        for r in modified["records"]:
            if r["nctId"]=="NCT04181723":
                r["ticker"]="WRONG"
        with self.assertRaisesRegex(ValueError,"CROSS_TRIAL_OR_DOUBLE_COUNT"):
            mod.export(self.source,modified)


if __name__=="__main__":
    unittest.main()
