"""Primary contemporaneous 2026 FDA goal evidence intake never certifies V2 forecast."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_v2_prospective_source_readiness as v2
import raas_fda_decision_accuracy_audit as audit

SOURCE=ROOT/"new-platform/frontend/data/raas-v2-top8-2026-source-intake.json"
LEGACY=ROOT/"data/fda_directional_100pct_freezes.csv"
ASOF="2026-11-03T23:59:59Z"

def fixture():
    return audit.load_json(SOURCE),audit.csv_rows(LEGACY)

class V2IssuerGoalsTests(unittest.TestCase):
    def test_eight_original_issuer_public_goal_publications_research_only(self):
        source,legacy=fixture()
        rows=v2.validate_top8_source_intake(source,legacy,ASOF)
        self.assertEqual(len(rows),8)
        self.assertEqual({x["ticker"] for x in rows},
                         {"CYTK","SMMT","CAPR","BBIO","VRTX","ANAB","CORT","MLYS"})
        self.assertTrue(all(x["issuerSourceLocatedAtAudit"] is True and
                            x["firstPublicGoalDateForThisCycleIndependentlyCertified"] is False and
                            x["immutableThreeClassForecastVerified"] is False and
                            x["eligibleForApprovedPredictiveAccuracy"] is False
                            for x in rows))
        self.assertTrue(all(x["issuerGoalSourcePublicationDate"]<"2026-11-03"
                            for x in rows))

    def test_supplemental_and_resubmission_cycles_are_kept_separate(self):
        src,legacy=fixture()
        d={x["ticker"]:x for x in v2.validate_top8_source_intake(src,legacy,ASOF)}
        self.assertEqual(d["CYTK"]["applicationType"],"SUPPLEMENTAL_NDA")
        self.assertEqual(d["CORT"]["applicationType"],"NDA_RESUBMISSION_AFTER_PRIOR_CRL")
        self.assertEqual(d["SMMT"]["applicationType"],"ORIGINAL_BLA_REPORTED")
        self.assertEqual(d["BBIO"]["applicationType"],"ORIGINAL_NDA_REPORTED")

    def test_capr_august_original_goal_is_not_a_november_first_cycle(self):
        src,legacy=fixture()
        d={x["ticker"]:x for x in v2.validate_top8_source_intake(src,legacy,ASOF)}
        c=d["CAPR"]
        self.assertEqual(c["firstReportedReviewCycleGoalDate"],"2026-08-22")
        self.assertEqual(c["issuerPublishedCurrentGoalDate"],"2026-11-22")
        self.assertTrue(c["originalGoalAlreadyPassedBeforeAudit"])
        self.assertEqual(c["formalGoalRevision"]["firstPublicDate"],"2026-08-24")
        self.assertNotEqual(c["applicationType"],"ORIGINAL_BLA_REPORTED")

    def test_anab_is_not_the_vanda_licensed_fda_sponsor(self):
        src,legacy=fixture()
        d={x["ticker"]:x for x in v2.validate_top8_source_intake(src,legacy,ASOF)}
        self.assertEqual(d["ANAB"]["clinicalApplicantOrSponsor"],"Vanda Pharmaceuticals")
        self.assertIn("AnaptysBio",d["ANAB"]["publicStockExposure"])
        self.assertNotEqual(d["ANAB"]["clinicalApplicantOrSponsor"],d["ANAB"]["publicStockExposure"])

    def test_stage0_report_enriched_but_not_three_way_scored(self):
        r=v2.execute(ASOF)
        self.assertEqual(r["issuerPublishedGoalSourceLeadsCount"],11)
        self.assertEqual(r["additionalFormallyExtendedSourceLeadsCount"],3)
        self.assertEqual(r["independentlyCertifiedOriginalGoalRecords"],0)
        self.assertEqual(len(r["caseCycleAndSponsorSourceChecks"]),8)
        self.assertTrue(r["sourceIntakeStillExcludedFromApprovedFDAAccuracy"])
        self.assertEqual(r["sourceQueueCount"],36)
        self.assertEqual(r["readyForThreeWayProspectiveFreeze"],0)
        self.assertEqual(r["verifiedProspectiveForecasts"],0)
        self.assertEqual(r["approvedRAASMetricCalibrations"],0)
        self.assertEqual(r["clinicalReviewCycleRisks"]["supplemental"],1)
        self.assertEqual(r["clinicalReviewCycleRisks"]["previouslyExtendedOriginalGoalAlreadyPassed"],1)
        self.assertIsNone(r["independentlyVerifiedThreeWayAccuracyPct"])

    def test_bad_future_source_or_wrong_goal_fails(self):
        s,l=fixture()
        d=deepcopy(s)
        d["records"][0]["sourcePublicationDate"]="2026-11-08"
        with self.assertRaisesRegex(ValueError,"TOP8_ISSUER_PUBLICATION_OR_DATE_INVALID"):
            v2.validate_top8_source_intake(d,l,ASOF)
        d=deepcopy(s)
        d["records"][0]["legacyGoalDate"]="2026-11-15"
        with self.assertRaisesRegex(ValueError,"TOP8_LEGACY_OR_APPLICATION_IDENTITY_MISMATCH"):
            v2.validate_top8_source_intake(d,l,ASOF)
        d=deepcopy(s)
        d["records"][0]["prospectivelyFrozenThreeWayProbabilities"]=True
        with self.assertRaisesRegex(ValueError,"TOP8_UNJUSTIFIED_APPROVAL_OR_INDEPENDENCE"):
            v2.validate_top8_source_intake(d,l,ASOF)

    def test_capr_revision_and_anab_rights_fail_closed(self):
        s,l=fixture()
        d=deepcopy(s)
        next(x for x in d["records"] if x["ticker"]=="CAPR")["firstCycleGoalDate"]="2026-11-22"
        with self.assertRaisesRegex(ValueError,"TOP8_CAPR_ORIGINAL_GOAL_EXTENSION_INVALID"):
            v2.validate_top8_source_intake(d,l,ASOF)
        d=deepcopy(s)
        next(x for x in d["records"] if x["ticker"]=="ANAB")["clinicalSponsor"]="AnaptysBio"
        with self.assertRaisesRegex(ValueError,"TOP8_ANAB_LICENSED_SPONSOR_NOT_RECONCILED"):
            v2.validate_top8_source_intake(d,l,ASOF)

    def test_missing_source_is_not_approved(self):
        s,l=fixture()
        d=deepcopy(s)
        d["records"][1]["sourceDocumentLocated"]=False
        with self.assertRaisesRegex(ValueError,"TOP8_UNJUSTIFIED_APPROVAL_OR_INDEPENDENCE"):
            v2.validate_top8_source_intake(d,l,ASOF)
        d=deepcopy(s)
        d["records"].pop()
        with self.assertRaisesRegex(ValueError,"TOP8_SOURCE_GATES_OR_SCHEMA_INVALID"):
            v2.validate_top8_source_intake(d,l,ASOF)

if __name__=="__main__":
    unittest.main()
