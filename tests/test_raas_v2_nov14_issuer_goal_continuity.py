"""Date-scoped issuer goal reiterations must never certify FDA current cycles."""
import csv
from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_v2_prospective_source_readiness as v2
import raas_fda_decision_accuracy_audit as audit

ASOF="2026-11-03T23:59:59Z"
DOC=ROOT/"new-platform/frontend/data/raas-v2-nov14-issuer-goal-continuity.json"
LEGACY=ROOT/"data/fda_directional_100pct_freezes.csv"


def fixture():
    return audit.load_json(DOC),audit.csv_rows(LEGACY)


class Nov14IssuerContinuityTests(unittest.TestCase):
    def test_later_company_sources_repeat_nov14_not_independent_fda_cycle(self):
        data,legacy=fixture()
        rows=v2.validate_nov14_issuer_goal_continuity(data,legacy,ASOF)
        self.assertEqual(len(rows),2)
        by={x["ticker"]:x for x in rows}
        self.assertEqual(by["CYTK"]["issuerContinuityDocumentDate"],"2026-08-06")
        self.assertEqual(by["CYTK"]["issuerReportedActualSubmissionPeriod"],"2026-01")
        self.assertEqual(by["CYTK"]["firstSelectedPublicApplicationUpdateDate"],"2026-02-24")
        self.assertFalse(by["CYTK"]["issuerSourceClockIsActualSubmissionDate"])
        self.assertEqual(by["SMMT"]["issuerContinuityDocumentDate"],"2026-09-15")
        self.assertEqual(by["CYTK"]["firstSelectedPublicApplicationUpdateType"],"SUBMISSION_PUBLIC_DISCLOSURE")
        self.assertEqual(by["SMMT"]["firstSelectedPublicApplicationUpdateType"],"FDA_ACCEPTANCE_PUBLIC_DISCLOSURE")
        self.assertEqual(by["SMMT"]["issuerReportedActualSubmissionPeriod"],"2025-Q4")
        self.assertTrue(all(x["sourceIsPublicByAuditAsOf"] for x in rows))
        self.assertTrue(all(x["documentAtItsDateRepeatsNov14Goal"] for x in rows))
        self.assertTrue(all(x["issuerGoalEvidenceOlderThan30DaysAtAudit"] for x in rows))
        self.assertTrue(all(x["daysSinceIssuerGoalReiteration"]>30 for x in rows))
        self.assertTrue(all(not x["currentlyIndependentlyCertifiedUnrevisedFdaDeadline"]
                           and not x["currentFDAApplicationNumberIndependentlyVerified"]
                           and not x["prospectivelyFrozenThreeWayForecast"] for x in rows))

    def test_not_yet_published_later_document_never_leaks_into_past(self):
        data,legacy=fixture()
        by={x["ticker"]:x for x in v2.validate_nov14_issuer_goal_continuity(
            data,legacy,"2026-07-01T12:00:00Z")}
        for x in by.values():
            self.assertFalse(x["sourceIsPublicByAuditAsOf"])
            self.assertIsNone(x["daysSinceIssuerGoalReiteration"])
            self.assertFalse(x["issuerGoalEvidenceOlderThan30DaysAtAudit"])
        by={x["ticker"]:x for x in v2.validate_nov14_issuer_goal_continuity(
            data,legacy,"2026-08-07T12:00:00Z")}
        self.assertTrue(by["CYTK"]["sourceIsPublicByAuditAsOf"])
        self.assertFalse(by["SMMT"]["sourceIsPublicByAuditAsOf"])
        by={x["ticker"]:x for x in v2.validate_nov14_issuer_goal_continuity(
            data,legacy,"2026-09-16T12:00:00Z")}
        self.assertTrue(by["SMMT"]["sourceIsPublicByAuditAsOf"])

    def test_nightly_report_exports_correct_clocks_and_blocks_forecasts(self):
        report=v2.execute(ASOF)
        self.assertEqual(len(report["nov14DatedIssuerGoalContinuityChecks"]),2)
        self.assertEqual(report["nov14DatedIssuerSourcesPublicByAsOfCount"],2)
        self.assertEqual(report["nov14IssuerSourcesOlderThan30DaysCount"],2)
        self.assertEqual(report["nov14IndependentlyCertifiedNoLaterFdaGoalRevisions"],0)
        self.assertEqual(report["readyForThreeWayProspectiveFreeze"],0)
        self.assertEqual(report["verifiedProspectiveForecasts"],0)
        rows={x["researchCaseKey"]:x for x in report["blockedSourceItems"]}
        cy=rows["CYTK|MYQORZO_HCM_20261114"]
        sm=rows["SMMT|IVONESCIMAB_20261114"]
        self.assertEqual(cy["issuerActualOriginalSubmissionPeriodNotPressDate"],"2026-01")
        self.assertEqual(sm["issuerActualOriginalSubmissionPeriodNotPressDate"],"2025-Q4")
        self.assertEqual(cy["mostRecentLocatedIssuerGoalContinuityDocumentDate"],"2026-08-06")
        self.assertEqual(sm["mostRecentLocatedIssuerGoalContinuityDocumentDate"],"2026-09-15")
        self.assertFalse(cy["issuerGoalReiterationConfirmsNoLaterFDAExtension"])
        self.assertFalse(sm["issuerGoalReiterationConfirmsNoLaterFDAExtension"])
        self.assertFalse(cy["V2ForecastEligible"])
        self.assertFalse(sm["V2ForecastEligible"])
        with TemporaryDirectory() as td:
            v2.export(report,Path(td)/"report.json",Path(td)/"review.csv")
            with (Path(td)/"review.csv").open(newline="") as f:
                csv_rows={r["researchCaseKey"]:r for r in csv.DictReader(f)}
            self.assertEqual(csv_rows["CYTK|MYQORZO_HCM_20261114"][
                "issuerActualOriginalSubmissionPeriodNotPressDate"],"2026-01")
            self.assertEqual(csv_rows["SMMT|IVONESCIMAB_20261114"][
                "issuerGoalReiterationConfirmsNoLaterFDAExtension"],"False")

    def test_fake_later_goal_source_or_fda_confirmation_fails_closed(self):
        data,legacy=fixture()
        for i,field,value in (
            (0,"issuerPublicSourceDate","2026-07-28"),
            (0,"issuerReportedActualApplicationSubmissionMonth","2026-02"),
            (0,"firstSelectedIssuerPublicApplicationUpdateDate","2026-01-12"),
            (0,"issuerPublicSourceUrl","https://invalid.test"),
            (0,"fdaParentNdaKnown","219084"),
            (1,"reportedGoalDate","2026-12-14"),
            (1,"issuerPublicSourceDate","2026-11-20"),
            (1,"pendingBlaNumberVerified",True),
            (1,"firstSelectedIssuerPublicApplicationUpdateType","SUBMISSION_PUBLIC_DISCLOSURE"),
            (1,"absenceOfLaterGoalChangeIndependentlyEstablished",True),
            (1,"immutablePredecisionThreeWayForecastMade",True),
            (1,"strictMarketCapPipelineQualificationEstablished",True),
        ):
            modified=deepcopy(data)
            modified["records"][i][field]=value
            with self.subTest(ticker=modified["records"][i]["ticker"],
                              field=field),self.assertRaises(ValueError):
                v2.validate_nov14_issuer_goal_continuity(modified,legacy,ASOF)
        modified=deepcopy(data)
        modified["records"][1]["researchCaseKey"]=modified["records"][0][
            "researchCaseKey"]
        with self.assertRaises(ValueError):
            v2.validate_nov14_issuer_goal_continuity(modified,legacy,ASOF)


if __name__=="__main__":
    unittest.main()
