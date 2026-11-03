"""RAAS V2 prospective source readiness: explicit research-only regression."""
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import csv
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_v2_prospective_source_readiness as v2
import raas_fda_decision_accuracy_audit as audit


def fixture(asof="2026-11-03T23:59:59Z"):
    return dict(
        old_rows=audit.csv_rows(ROOT/"data/fda_directional_100pct_freezes.csv"),
        archive=audit.load_json(ROOT/"new-platform/frontend/data/raas-2025-nine-archived-goal-original-source-triage.json"),
        protocol=audit.load_json(ROOT/"data/raas_fda_three_way_protocol.json"),
        roster=audit.load_json(ROOT/"data/raas_fda_three_way_eligible_cases.json"),
        forecasts=audit.load_json(ROOT/"data/raas_fda_three_way_frozen_forecasts.json"),
        outcomes=audit.load_json(ROOT/"data/raas_fda_three_way_outcomes.json"),
        as_of=asof,
    )


class V2SourceReadinessTests(unittest.TestCase):
    def test_v2_candidate_does_not_upgrade_active_foundation_v1_model(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        self.assertEqual(r["scope"],v2.SCOPE)
        self.assertEqual(r["version"],"V2_RESEARCH_CANDIDATE_STAGE_0")
        self.assertEqual(r["status"],"RESEARCH_V2_CANDIDATE_NOT_AN_APPROVED_MODEL")
        self.assertEqual(r["modelVersionStillActive"],"2026-11-02-foundation-v1")
        self.assertIsNone(r["independentlyVerifiedThreeWayAccuracyPct"])
        self.assertFalse(r["issuerDisjointHoldoutVerified"])
        self.assertFalse(r["originalGoalCensusVerified"])
        self.assertEqual(r["approvedRAASMetricCalibrations"],0)
        self.assertEqual(r["readyForThreeWayProspectiveFreeze"],0)
        self.assertEqual(r["verifiedProspectiveForecasts"],0)

    def test_original_36_future_legacy_binary_events_are_source_leads_only(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        self.assertEqual(r["sourceQueueCount"],36)
        self.assertEqual(r["archived2025OriginalGoalReviewCount"],9)
        self.assertEqual(r["archived2025FormalExtensionLeads"],2)
        self.assertEqual(r["sourceQueueCount"],sum(r["byPriority"].values()))
        self.assertLessEqual(r["distinctLegacyIssuerTickers"],36)
        self.assertTrue(all(x["V2ForecastEligible"] is False
                            and x["immutablePreactionThreeWayProbabilityVector"] is False
                            and x["approvedRAASMetricGrade"] is False
                            and x["originalGoalPrimarySourceVerified"] is False
                            and x["researchStatus"]=="SOURCE_REVIEW_ONLY_NOT_THREE_WAY_PREDICTION"
                            for x in r["blockedSourceItems"]))
        self.assertEqual(len({x["researchCaseKey"] for x in r["blockedSourceItems"]}),36)
        self.assertEqual(r["blockedSourceItems"][0]["calendarDaysUntilLegacyGoal"],11)
        self.assertEqual(r["blockedSourceItems"][0]["priority"],"PRIORITY_WITHIN_30_DAYS")
        self.assertEqual(r["blockedSourceItems"][0]["legacyGoalDateUnverified"],"2026-11-14")

    def test_same_issuer_is_not_automatically_independent(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        counts={}
        for x in r["blockedSourceItems"]:
            counts[x["ticker"]]=counts.get(x["ticker"],0)+1
        self.assertEqual(r["distinctLegacyIssuerTickers"],len(counts))
        self.assertEqual(r["multipleLegacyEventsSameIssuer"],
                         {k:v for k,v in sorted(counts.items()) if v>1})

    def test_asof_recurring_queue_expires_goal_dates_instead_of_inventing_results(self):
        r=v2.execute("2026-11-18T23:59:59Z")
        self.assertLess(r["sourceQueueCount"],36)
        self.assertNotIn("2026-11-14",
                         [x["legacyGoalDateUnverified"] for x in r["blockedSourceItems"]])
        self.assertEqual(r["verifiedProspectiveForecasts"],0)
        self.assertIsNone(r["independentlyVerifiedThreeWayAccuracyPct"])

    def test_future_horizon_clears_legacy_leads(self):
        r=v2.execute("2028-01-02T23:59:59Z")
        self.assertEqual(r["sourceQueueCount"],0)
        self.assertEqual(r["distinctLegacyIssuerTickers"],0)
        self.assertEqual(r["archived2025OriginalGoalReviewCount"],9)
        self.assertEqual(r["readyForThreeWayProspectiveFreeze"],0)

    def test_urgent_priorities_explicit_no_false_probability(self):
        self.assertEqual(v2.priority(3),"URGENT_WITHIN_7_DAYS")
        self.assertEqual(v2.priority(8),"PRIORITY_WITHIN_30_DAYS")
        self.assertEqual(v2.priority(30),"PRIORITY_WITHIN_30_DAYS")
        self.assertEqual(v2.priority(45),"PENDING_MORE_THAN_30_DAYS")
        self.assertEqual(v2.priority(-1),"PAST_UNVERIFIED_GOAL_INVESTIGATE_OUTCOME")
        with self.assertRaisesRegex(ValueError,"DAYS_UNTIL_NOT_INTEGER"):
            v2.priority(2.5)

    def test_archived_2025_formal_extensions_do_not_count_as_future_forecasts(self):
        r=v2.execute("2026-11-03T23:59:59Z")
        ext=[x for x in r["archived2025GoalResearch"] if x["revisedGoalDate"]]
        self.assertEqual(len(ext),2)
        d={x["ticker"]:x for x in ext}
        self.assertEqual(d["ETON"]["originalGoalDate"],"2025-02-28")
        self.assertEqual(d["ETON"]["revisedGoalDate"],"2025-05-28")
        self.assertEqual(d["BCRX"]["originalGoalDate"],"2025-09-12")
        self.assertEqual(d["BCRX"]["revisedGoalDate"],"2025-12-12")
        self.assertFalse(any(x["independentlyVerifiedThreeWayOutcome"]
                             for x in r["archived2025GoalResearch"]))

    def test_fail_closed_if_archive_tries_to_claim_independent_outcomes(self):
        d=fixture()
        d["archive"]["independentlyAdjudicatedFDAThreeWayOutcomes"]=2
        with self.assertRaisesRegex(ValueError,"ARCHIVE_APPROVAL_OR_SOURCE_SCHEMA_INVALID"):
            v2.compile_report(**d)
        d=fixture()
        d["archive"]["records"][0]["eligibleForFDAProspectiveAccuracy"]=True
        with self.assertRaisesRegex(ValueError,"ARCHIVE_INDEPENDENT_ADJUDICATION_NOT_ESTABLISHED"):
            v2.compile_report(**d)

    def test_fail_closed_on_duplicate_old_directional_case_id(self):
        d=fixture()
        d["old_rows"].append(deepcopy([x for x in d["old_rows"]
                                      if x["model_version"]=="FDA-DIRECTIONAL-100-V1.9" and
                                      x["pdufa_date"]>"2026-11-03"][0]))
        with self.assertRaisesRegex(ValueError,"DUPLICATE_FUTURE_REVIEW_SOURCE_LEAD"):
            v2.compile_report(**d)

    def test_export_never_authorizes_calibration_or_three_way_forecast(self):
        report=v2.execute("2026-11-03T23:59:59Z")
        with TemporaryDirectory() as td:
            j=Path(td)/"readiness.json"
            c=Path(td)/"readiness.csv"
            v2.export(report,j,c)
            out=json.loads(j.read_text())
            self.assertIsNone(out["independentlyVerifiedThreeWayAccuracyPct"])
            with c.open(newline="") as fh:
                rows=list(csv.DictReader(fh))
            self.assertEqual(len(rows),36)
            self.assertEqual(rows[0]["researchStatus"],
                             "SOURCE_REVIEW_ONLY_NOT_THREE_WAY_PREDICTION")
        forged=deepcopy(report)
        forged["approvedRAASMetricCalibrations"]=60
        with TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"EXPORT_CANNOT_APPROVE_MODEL"):
                v2.export(forged,Path(td)/"fake.json",Path(td)/"fake.csv")


if __name__=="__main__":
    unittest.main()
