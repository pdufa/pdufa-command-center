"""Two November 14 research dossiers cross-check clinical trials, not FDA outcomes."""
from copy import deepcopy
from pathlib import Path
import csv
import json
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_v2_prospective_source_readiness as v2
import raas_fda_decision_accuracy_audit as audit

ASOF="2026-11-03T23:59:59Z"
def fixtures():
    return (
        audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-nov14-review-cycle-triangulation.json"),
        audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-top8-2026-source-intake.json"),
        audit.csv_rows(ROOT/"data/fda_directional_100pct_freezes.csv")
    )


class Nov14RegistryCrossSourceTests(unittest.TestCase):
    def test_distinct_snda_vs_original_bla_study_and_fda_parent_not_current(self):
        doc,source,legacy=fixtures()
        rows=v2.validate_nov14_trial_registry_triangulation(doc,source,legacy,ASOF)
        self.assertEqual(len(rows),2)
        by={x["ticker"]:x for x in rows}
        self.assertEqual(by["CYTK"]["clinicalTrialsGovId"],"NCT05767346")
        self.assertEqual(by["SMMT"]["clinicalTrialsGovId"],"NCT06396065")
        self.assertEqual(by["CYTK"]["fdaApprovedParentNdaNumber"],"219083")
        self.assertIsNone(by["SMMT"]["fdaApprovedParentNdaNumber"])
        self.assertEqual(by["CYTK"]["applicationClass"],"SUPPLEMENTAL_NDA")
        self.assertEqual(by["SMMT"]["applicationClass"],"ORIGINAL_BLA_REPORTED")
        for x in rows:
            self.assertEqual(x["clinicalTrialsGovPhase"],"PHASE_3")
            self.assertTrue(x["trialPhaseAndSponsorCrossChecked"])
            self.assertFalse(x["fdaCurrentCycleApplicationOrSupplementNumberVerified"])
            self.assertFalse(x["fdaOriginalGoalAndExtensionsIndependentlyCertified"])
            self.assertFalse(x["independentPreDecisionThreeWayForecastExists"])
            self.assertFalse(x["qualifiesForStrictPhase3MarketCapPipeline"])

    def test_nightly_report_has_registry_fields_without_prediction_promotion(self):
        report=v2.execute(ASOF)
        self.assertEqual(report["issuerPublishedGoalSourceLeadsCount"],15)
        self.assertEqual(report["nov14ThirdPartyRegistryPhase3CrossCheckedCount"],2)
        self.assertEqual(report["nov14ThirdPartyRegistryUpcomingCaseCount"],2)
        self.assertEqual(report["nov14ExactCurrentFDAReviewCyclesIndependentlyCertified"],0)
        self.assertEqual(report["nov14FrozenThreeWayPredictionsIndependentlyVerified"],0)
        self.assertEqual(report["readyForThreeWayProspectiveFreeze"],0)
        self.assertEqual(report["approvedRAASMetricCalibrations"],0)
        by={x["researchCaseKey"]:x for x in report["blockedSourceItems"]}
        for key,nct in (
            ("CYTK|MYQORZO_HCM_20261114","NCT05767346"),
            ("SMMT|IVONESCIMAB_20261114","NCT06396065"),
        ):
            r=by[key]
            self.assertEqual(r["clinicalTrialsGovNctId"],nct)
            self.assertTrue(r["thirdPartyClinicalTrialPhase3CrossChecked"])
            self.assertFalse(r["fdaCurrentReviewApplicationOrSupplementNumberVerified"])
            self.assertFalse(r["V2ForecastEligible"])
            self.assertFalse(r["immutablePreactionThreeWayProbabilityVector"])
        with TemporaryDirectory() as d:
            out=Path(d)
            v2.export(report,out/"audit.json",out/"audit.csv")
            with (out/"audit.csv").open(newline="") as f:
                rows={r["researchCaseKey"]:r for r in csv.DictReader(f)}
            self.assertEqual(rows["CYTK|MYQORZO_HCM_20261114"]["FDAApprovedParentOriginalNdaNumber"],"219083")
            self.assertEqual(rows["SMMT|IVONESCIMAB_20261114"]["clinicalTrialsGovNctId"],"NCT06396065")

    def test_corrupt_trial_identity_approval_or_wrong_parent_fails(self):
        doc,source,legacy=fixtures()
        for i,field,bad in (
            (0,"clinicalTrialsGovId","NCT06396065"),
            (0,"clinicalTrialsGovPhase","PHASE_2"),
            (0,"usFDAParentOriginalNdaNumber","219084"),
            (0,"currentSupplementSequenceIndependentlyVerified",True),
            (1,"currentBlaNumberIndependentlyVerified",True),
            (1,"exactCurrentFDAReviewCycleIndependentlyCertified",True),
            (1,"independentlyVerifiedThreeWayForecast",True),
            (0,"approvedPipelineMarketCapAndPhase3Qualification",True),
            (0,"issuerSourcePublicationDate","2026-11-04"),
            (1,"clinicalTrialsGovRecordLastUpdatePosted","2026-11-30"),
        ):
            changed=deepcopy(doc)
            changed["records"][i][field]=bad
            with self.subTest(case=i,field=field),self.assertRaises(ValueError):
                v2.validate_nov14_trial_registry_triangulation(changed,source,legacy,ASOF)
        changed=deepcopy(doc)
        changed["records"][1]["researchCaseKey"]=changed["records"][0]["researchCaseKey"]
        with self.assertRaises(ValueError):
            v2.validate_nov14_trial_registry_triangulation(changed,source,legacy,ASOF)

    def test_matured_nov14_goals_no_longer_upcoming_even_if_registry_remains_historical(self):
        report=v2.execute("2026-11-18T23:59:59Z")
        self.assertEqual(report["nov14ThirdPartyRegistryPhase3CrossCheckedCount"],2)
        self.assertEqual(report["nov14ThirdPartyRegistryUpcomingCaseCount"],0)
        self.assertEqual(report["verifiedProspectiveForecasts"],0)


if __name__=="__main__":
    unittest.main()
