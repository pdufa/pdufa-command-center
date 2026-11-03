"""Near-term RAAS V2 FDA original-goal source classification, not trading or model validation."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_fda_decision_accuracy_audit as audit
import raas_v2_prospective_source_readiness as v2

SOURCE=ROOT/"new-platform/frontend/data/raas-v2-upcoming-2026-cycle-source-research.json"


def inputs():
    data=ROOT/"data"
    return {
        "old_rows":audit.csv_rows(data/"fda_directional_100pct_freezes.csv"),
        "archive":audit.load_json(ROOT/"new-platform/frontend/data/raas-2025-nine-archived-goal-original-source-triage.json"),
        "protocol":audit.load_json(data/"raas_fda_three_way_protocol.json"),
        "roster":audit.load_json(data/"raas_fda_three_way_eligible_cases.json"),
        "forecasts":audit.load_json(data/"raas_fda_three_way_frozen_forecasts.json"),
        "outcomes":audit.load_json(data/"raas_fda_three_way_outcomes.json"),
        "near_term":audit.load_json(SOURCE),
        "as_of":"2026-11-03T23:59:59Z",
    }


class CandidateCycleReviewTests(unittest.TestCase):
    def test_three_near_term_source_leads_are_not_independent_model_labels(self):
        r=v2.compile_report(**inputs())
        self.assertEqual(r["sourceQueueCount"],36)
        self.assertEqual(r["nearTermIssuerGoalSourceReviewed"],3)
        self.assertEqual(r["revisedGoalResearchCasesNotFutureOriginalGoals"],1)
        self.assertEqual(r["issuerDocumentedFutureOriginalGoalCases"],2)
        self.assertEqual(r["issuerDocumentedSupplementalFutureGoals"],1)
        self.assertEqual(r["remainingLegacyGoalCasesWithoutIssuerSourceReview"],33)
        self.assertTrue(r["nearTermSourceDocumentedOnlyNotIndependentlyVerified"])
        self.assertEqual(r["readyForThreeWayProspectiveFreeze"],0)
        self.assertEqual(r["verifiedProspectiveForecasts"],0)
        self.assertIsNone(r["independentlyVerifiedThreeWayAccuracyPct"])
        self.assertEqual(r["approvedRAASMetricCalibrations"],0)

    def test_original_review_cycle_and_application_type_distinctions(self):
        report=v2.compile_report(**inputs())
        indexed={r["ticker"]:r for r in report["blockedSourceItems"]
                 if r["ticker"] in ("CYTK","SMMT","CAPR")}
        self.assertEqual(len(indexed),3)
        for ticker in indexed:
            self.assertTrue(indexed[ticker]["issuerOriginalGoalDocumentUrl"].startswith("https://"))
            self.assertFalse(indexed[ticker]["V2ForecastEligible"])
            self.assertFalse(indexed[ticker]["originalGoalPrimarySourceVerified"])
            self.assertFalse(indexed[ticker]["independentlyVerifiedFDAOriginalGoalOutcome"])
            self.assertFalse(indexed[ticker]["immutablePreactionThreeWayProbabilityVector"])
        self.assertEqual(indexed["CYTK"]["issuerApplicationTypeResearch"],"SUPPLEMENTAL_NDA")
        self.assertEqual(indexed["SMMT"]["issuerApplicationTypeResearch"],"BLA_INITIAL_ACCEPTANCE")
        self.assertEqual(indexed["CAPR"]["issuerApplicationTypeResearch"],"BLA_CLASS_2_RESUBMISSION")
        self.assertEqual(indexed["CAPR"]["originalCycleGoalResearchDate"],"2026-08-22")
        self.assertEqual(indexed["CAPR"]["legacyGoalDateUnverified"],"2026-11-22")
        self.assertTrue(indexed["CAPR"]["revisedPdufaGoalMisclassifiedAsOriginal"])
        self.assertTrue(indexed["CAPR"]["originalCycleGoalAlreadyPassed"])
        self.assertFalse(indexed["CAPR"]["futureOriginalGoalResearchEligible"])
        self.assertEqual(indexed["CAPR"]["revisionFirstPublicDisclosure"],"2026-08-24")
        self.assertFalse(indexed["CYTK"]["revisedPdufaGoalMisclassifiedAsOriginal"])
        self.assertTrue(indexed["CYTK"]["futureOriginalGoalResearchEligible"])
        self.assertTrue(indexed["SMMT"]["futureOriginalGoalResearchEligible"])

    def test_no_hindsight_source_when_asof_predates_issuer_disclosure(self):
        d=inputs()
        d["as_of"]="2026-01-01T23:59:59Z"
        report=v2.compile_report(**d)
        self.assertEqual(report["nearTermIssuerGoalSourceReviewed"],0)
        self.assertEqual(report["revisedGoalResearchCasesNotFutureOriginalGoals"],0)
        self.assertEqual(report["issuerDocumentedFutureOriginalGoalCases"],0)

    def test_deny_hidden_promotions_and_invented_cycle_dates(self):
        d=inputs()
        d["near_term"]["verifiedProspectiveFDADecisionForecasts"]=2
        with self.assertRaisesRegex(ValueError,"NEAR_TERM_SOURCE_SCOPE_OR_APPROVAL_INVALID"):
            v2.compile_report(**d)
        d=inputs()
        d["near_term"]["records"][2]["firstAnnouncedGoalForThisReviewCycle"]="2026-11-22"
        with self.assertRaisesRegex(ValueError,"NEAR_TERM_REVISED_GOAL_INVALID"):
            v2.compile_report(**d)
        d=inputs()
        d["near_term"]["records"][1]["legacyGoalDate"]="2026-12-14"
        with self.assertRaisesRegex(ValueError,"NEAR_TERM_FINDING_WRONG_CASE_OR_GOAL"):
            v2.compile_report(**d)

    def test_source_clock_and_review_type_fail_closed(self):
        d=inputs()
        d["near_term"]["records"][0]["goalFirstObservedPublicDate"]="2026-11-14"
        with self.assertRaisesRegex(ValueError,"NEAR_TERM_PUBLIC_SOURCE_TIME_INVALID"):
            v2.compile_report(**d)
        d=inputs()
        d["near_term"]["records"][1]["issuerDocumentedApplicationClass"]="ORIGINAL_NDA_APPROVED"
        with self.assertRaisesRegex(ValueError,"NEAR_TERM_UNVERIFIED_CYCLE_PROMOTION"):
            v2.compile_report(**d)

if __name__=="__main__":
    unittest.main()
