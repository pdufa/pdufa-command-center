"""Cycle-correct RAAS V2 nightly original-goal queue; source findings not predictions."""
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_v2_prospective_source_readiness as v2


class OriginalGoalQueueSafetyTests(unittest.TestCase):
    def test_source_findings_are_joined_without_promoting_to_approved_fda_predictions(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        self.assertEqual(r["sourceQueueCount"],36)
        self.assertEqual(r["issuerSourceReviewedFutureDeadlineLeads"],15)
        self.assertEqual(r["sourceDocumentedFirstGoalStillFuture"],11)
        self.assertEqual(r["knownRevisedDeadlineExcludedFromOriginalGoalCount"],4)
        self.assertEqual(r["unreviewedLegacyDeadlineLeads"],21)
        self.assertEqual(r["unexcludedLegacyDeadlineLeadsNotIndependentlyVerified"],32)
        self.assertEqual(r["independentlyCertifiedOriginalGoalRecords"],0)
        self.assertEqual(r["readyForThreeWayProspectiveFreeze"],0)
        self.assertEqual(r["verifiedProspectiveForecasts"],0)
        self.assertEqual(r["approvedRAASMetricCalibrations"],0)
        self.assertIsNone(r["independentlyVerifiedThreeWayAccuracyPct"])
        for case in r["blockedSourceItems"]:
            self.assertFalse(case["independentlyVerifiedApplicationCycle"])
            self.assertFalse(case["V2ForecastEligible"])
            self.assertFalse(case["immutablePreactionThreeWayProbabilityVector"])

    def test_capr_revised_november_goal_cannot_be_used_as_upcoming_original_fda_decision(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        indexed={x["ticker"]:x for x in r["blockedSourceItems"]
                 if x["ticker"] in {"CYTK","SMMT","CAPR","ANAB"}}
        self.assertTrue(indexed["CAPR"]["issuerSourceFound"])
        self.assertEqual(indexed["CAPR"]["firstGoalForThisCycleIssuerReported"],"2026-08-22")
        self.assertEqual(indexed["CAPR"]["legacyGoalDateUnverified"],"2026-11-22")
        self.assertTrue(indexed["CAPR"]["knownRevisedGoalNotOriginalPrediction"])
        self.assertEqual(indexed["CAPR"]["applicationClassIssuerReported"],
                         "REVISED_BLA_TARGET_AFTER_FORMAL_EXTENSION")
        self.assertEqual(indexed["CAPR"]["sourceResearchStatus"],
                         "REVISED_GOAL_MUST_NOT_COUNT_AS_FUTURE_ORIGINAL_DEADLINE")
        self.assertTrue(indexed["CAPR"]["issuerSourceLink"].startswith("https://"))
        self.assertEqual(indexed["CYTK"]["applicationClassIssuerReported"],"SUPPLEMENTAL_NDA")
        self.assertEqual(indexed["SMMT"]["applicationClassIssuerReported"],"ORIGINAL_BLA_REPORTED")
        self.assertEqual(indexed["ANAB"]["applicationClassIssuerReported"],
                         "LICENSED_THIRD_PARTY_BLA_SPONSOR")

    def test_three_more_publicly_extended_deadlines_are_excluded_without_three_way_forecasts(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        case={x["researchCaseKey"]:x for x in r["blockedSourceItems"]}
        for key,first,revised in (
            ("SVRA|MOLBREEVI_PAP_20261122","2026-08-22","2026-11-22"),
            ("RELUTRIGINE_DEE_US_20261227","2026-09-27","2026-12-27"),
            ("ZANZALINTINIB_CRC_US_20261203","2026-12-03","2027-03-03"),
        ):
            x=case[key]
            self.assertTrue(x["issuerSourceFound"])
            self.assertTrue(x["knownRevisedGoalNotOriginalPrediction"])
            self.assertEqual(x["firstGoalForThisCycleIssuerReported"],first)
            self.assertEqual(x["currentIssuerReportedRevisedGoalDate"],revised)
            self.assertFalse(x["independentlyVerifiedApplicationCycle"])
            self.assertFalse(x["V2ForecastEligible"])
            self.assertFalse(x["immutablePreactionThreeWayProbabilityVector"])
        self.assertEqual(case["ZANZALINTINIB_CRC_US_20261203"]["legacyGoalDateUnverified"],"2026-12-03")
        self.assertEqual(case["ZANZALINTINIB_CRC_US_20261203"]["sourceResearchStatus"],
                         "FORMAL_EXTENSION_KNOWN_ORIGINAL_DATE_NO_LONGER_UNRESOLVED")
        self.assertEqual(r["additionalFormallyExtendedSourceLeadsCount"],3)
        self.assertEqual(r["sourceDocumentedFirstGoalStillFuture"],11)

    def test_false_extension_source_or_promotion_is_rejected(self):
        from copy import deepcopy
        import raas_fda_decision_accuracy_audit as audit
        source=audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-top8-2026-source-intake.json")
        legacy=audit.csv_rows(ROOT/"data/fda_directional_100pct_freezes.csv")
        for field,value in (
            ("formalExtensionAnnouncementDate","2026-12-31"),
            ("eligibleForV2OriginalGoalPrediction",True),
            ("revisedGoalDate","2026-08-22"),
        ):
            changed=deepcopy(source)
            changed["additionalFormalRevisionCases"][0][field]=value
            with self.assertRaises(ValueError):
                v2.validate_additional_formal_extensions(
                    changed,legacy,"2026-11-03T23:59:59Z")

    def test_four_additional_issuer_original_goals_and_two_phase2_cases_never_promote(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        by={x["researchCaseKey"]:x for x in r["blockedSourceItems"]}
        cases={
          "COGT|BEZUCLASTINIB_GIST_20261130":("2026-11-30","PHASE_3_REPORTED_PEAK"),
          "ANITOCEL_RRMM_US_20261223":("2026-12-23","PIVOTAL_PHASE_2_REPORTED_IMMAGINE1"),
          "MR107A02_ACUTEPAIN_US_20261227":("2026-12-27","PHASE_NOT_INDEPENDENTLY_VERIFIED"),
          "BEZUCLASTINIB_NONADVSM_US_20261230":("2026-12-30","PIVOTAL_PHASE_2_REPORTED_SUMMIT"),
        }
        for key,(goal,phase) in cases.items():
            x=by[key]
            self.assertTrue(x["issuerSourceFound"])
            self.assertEqual(x["legacyGoalDateUnverified"],goal)
            self.assertEqual(x["pivotalPhaseIssuerResearch"],phase)
            self.assertFalse(x["approvedPipelinePhase3Qualification"])
            self.assertFalse(x["knownRevisedGoalNotOriginalPrediction"])
            self.assertFalse(x["V2ForecastEligible"])
            self.assertFalse(x["immutablePreactionThreeWayProbabilityVector"])
        self.assertEqual(r["additionalOriginalGoalIssuerSourcesCount"],4)
        self.assertEqual(len(r["phase2PivotalOriginalGoalSourceCases"]),2)
        self.assertTrue(r["issuerDocumentedGistAndNonAdvSMRemainSeparate"])

    def test_bad_new_source_identity_or_future_publication_fails_closed(self):
        from copy import deepcopy
        import raas_fda_decision_accuracy_audit as audit
        original=audit.load_json(ROOT/"new-platform/frontend/data/raas-v2-top8-2026-source-intake.json")
        old=audit.csv_rows(ROOT/"data/fda_directional_100pct_freezes.csv")
        for field,bad in (
            ("issuerReportedFirstGoalDate","2026-12-01"),
            ("sourcePublicationDate","2026-11-20"),
            ("pivotalPhaseEvidence","PIVOTAL_PHASE_2_REPORTED_SUMMIT"),
            ("approvedPipelinePhase3Qualification",True),
            ("applicationNumberIndependentlyVerified",True),
            ("ticker","GILD"),
        ):
            modified=deepcopy(original)
            modified["additionalOriginalGoalIssuerSourceCases"][0][field]=bad
            with self.assertRaises(ValueError):
                v2.validate_additional_original_goal_sources(
                    modified,old,"2026-11-03T23:59:59Z")
        modified=deepcopy(original)
        modified["additionalOriginalGoalIssuerSourceCases"][3]["legacyCaseKey"]=(
            modified["additionalOriginalGoalIssuerSourceCases"][0]["legacyCaseKey"])
        with self.assertRaises(ValueError):
            v2.validate_additional_original_goal_sources(
                modified,old,"2026-11-03T23:59:59Z")

    def test_source_record_lapses_with_matured_legacy_dates(self):
        r=v2.execute("2026-11-18T23:59:59Z")
        self.assertEqual(r["issuerSourceReviewedFutureDeadlineLeads"],13)
        self.assertEqual(r["knownRevisedDeadlineExcludedFromOriginalGoalCount"],4)
        self.assertTrue(all(x["legacyGoalDateUnverified"]>"2026-11-18"
                            for x in r["blockedSourceItems"]))
        r=v2.execute("2028-01-02T23:59:59Z")
        self.assertEqual(r["sourceQueueCount"],0)
        self.assertEqual(r["issuerSourceReviewedFutureDeadlineLeads"],0)
        self.assertEqual(r["knownRevisedDeadlineExcludedFromOriginalGoalCount"],0)

    def test_dated_csv_exposes_source_type_and_revised_goal_exclusion(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        with TemporaryDirectory() as d:
            p=Path(d)/"review.json"
            c=Path(d)/"review.csv"
            v2.export(r,p,c)
            with c.open(newline="") as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),36)
            capr=next(x for x in rows if x["ticker"]=="CAPR")
            self.assertEqual(capr["firstGoalForThisCycleIssuerReported"],"2026-08-22")
            self.assertEqual(capr["knownRevisedGoalNotOriginalPrediction"],"True")
            self.assertEqual(capr["independentlyVerifiedApplicationCycle"],"False")
            self.assertEqual(json.loads(p.read_text())["approvedRAASMetricCalibrations"],0)

if __name__=="__main__":
    unittest.main()
