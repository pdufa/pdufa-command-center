"""RAAS FDA three-way prediction accuracy tests: synthetic math, real legacy guards."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import math
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import raas_fda_decision_accuracy_audit as audit


def fixture():
    p=audit.load_json(ROOT/"data/raas_fda_three_way_protocol.json")
    r=audit.load_json(ROOT/"data/raas_fda_three_way_eligible_cases.json")
    f=audit.load_json(ROOT/"data/raas_fda_three_way_frozen_forecasts.json")
    o=audit.load_json(ROOT/"data/raas_fda_three_way_outcomes.json")
    for feed in (r,f,o):
        feed["sourceAsOf"]="2027-07-01"
    c=["CYCLE_A","CYCLE_B","CYCLE_C","CYCLE_D"]
    classes=("PASS","CRL","EXTENSION","PASS")
    for i,k in enumerate(c):
        r["records"].append({
            "caseId":k,"ticker":"XYZ","applicationId":"NDA"+str(200000+i),
            "reviewCycle":1,"issuerProgramFamilyId":"ISSUER_FAMILY_"+str(i),
            "originalPdufaGoalDate":"2027-06-01","goalFirstPublicAtDate":"2026-10-30",
            "goalFirstPublicSourceUrl":"https://www.fda.gov/drugs/approval-"+str(i),
            "registeredAtUTC":"2027-01-01T00:00:00Z",
        })
        actual=classes[i]
        o["records"].append({
            "caseId":k,"actualClass":actual,
            "dispositionDate":"2027-03-01" if actual=="EXTENSION" else "2027-05-01",
            "firstPublicOutcomeAtUTC":"2027-03-02T00:00:00Z" if actual=="EXTENSION" else "2027-05-02T00:00:00Z",
            "officialFdaSourceUrl":"https://www.fda.gov/drugs/decision-"+str(i),
            "independentFDAReviewerVerified":True,
            "formalFDAExtensionDocumented":actual=="EXTENSION",
        })
        state="ABSTAIN" if i==3 else "PREDICTED"
        prob={c:0.1 for c in audit.CLASSES}
        prob[actual]=0.8
        f["records"].append({
            "caseId":k,"frozenAtUTC":"2027-01-03T14:00:00Z",
            "asOfDate":"2027-01-03","modelVersion":"RAAS-FDA-FROZEN-1",
            "immutableReceiptUrl":"https://github.com/pdufa/pdufa-command-center/commit/example-"+str(i),
            "receiptIndependentlyVerified":True,
            "publicEvidence":[{"url":"https://www.fda.gov/drugs/evidence-"+str(i),
                               "firstPublicDate":"2027-01-02"}],
            "status":state,
            "probabilities":None if state=="ABSTAIN" else prob,
            "predictedClass":None if state=="ABSTAIN" else actual,
            "abstainReason":"Source missing" if state=="ABSTAIN" else None
        })
    return p,r,f,o


class ThreeWayTests(unittest.TestCase):
    def test_empty_real_ledger_reports_null_accuracy_not_fake_zero(self):
        report=audit.execute()
        self.assertEqual(report["status"],"BENCHMARK_INSTALLED_NO_VALIDATED_THREE_WAY_ACCURACY")
        self.assertEqual(report["approvedFDAOutcomeAccuracyPct"],None)
        self.assertEqual(report["threeWayProspective"]["verifiedFDAAccuracyPct"],None)
        self.assertEqual(report["threeWayProspective"]["frozenThreeClassPredictions"],0)
        self.assertEqual(report["threeWayProspective"]["registeredEligibleCycleCount"],0)
        self.assertEqual(report["threeWayProspective"]["independentGatesPassed"],0)
        self.assertEqual(report["threeWayProspective"]["approvedRAASMetrics"],0)

    def test_original_146_rows_worse_than_simple_always_approve_diagnostic(self):
        r=audit.execute()
        s=r["historicalBinaryRetrospective"]
        self.assertEqual(s["cases"],146)
        self.assertEqual(s["approved"],106)
        self.assertEqual(s["CRL"],40)
        self.assertEqual(s["extensionCases"],0)
        self.assertEqual(s["legacyRetrospectiveCorrect"],102)
        self.assertEqual(s["legacyRetrospectiveAccuracyPct"],69.86)
        self.assertEqual(s["alwaysApproveAccuracyPct"],72.6)
        self.assertLess(s["legacyVsAlwaysApprovePctPoints"],0)
        self.assertEqual(s["publicDirectionalCallsWithoutCertifiedThreeWayFreeze"],13)
        self.assertEqual(r["historicalReviewQueue"][0]["validationStatus"],
                         "RETROSPECTIVE_ONLY_NOT_THREE_WAY_FROZEN")
        self.assertFalse(s["independentlyValidated"])

    def test_old_404_frozen_binary_versions_not_inflated_into_404_independent_cases(self):
        r=audit.execute()
        old=r["olderFrozenBinaryDirections"]
        self.assertEqual(old["rowsAcrossRepeatedVersions"],404)
        self.assertEqual(old["latestV1_9ProspectivelyEligibleUniqueCases"],40)
        self.assertEqual(old["certifiedThreeClassProbabilities"],0)
        self.assertEqual(old["portedToThreeWayLedger"],0)

    def test_three_class_metrics_correct_without_claim_of_independent_validation(self):
        inp=fixture()
        cases,preds,outcomes=audit.parse_prospective(*inp)
        self.assertEqual(len(cases),4)
        self.assertEqual(len(preds),4)
        self.assertEqual(len(outcomes),4)
        r=audit.prospective_audit(*inp,asof="2027-07-01T00:00:00Z")
        self.assertEqual(r["coveredScoredCases"],3)
        self.assertEqual(r["abstained"],1)
        self.assertIsNone(r["verifiedFDAAccuracyPct"])
        self.assertFalse(r["approvedModel"])
        m=r["mathMetrics"]
        self.assertEqual(m["accuracy"],1)
        self.assertEqual(m["balancedAccuracy"],1)
        self.assertEqual(m["multiclassBrier"],0.06)
        self.assertAlmostEqual(m["logLoss"],-math.log(0.8),places=5)
        self.assertAlmostEqual(m["expectedCalibrationError"],0.2,places=5)
        self.assertEqual(m["alwaysPASSBaselineAccuracy"],1/3 if False else round(1/3,5))
        self.assertEqual(m["coverage"],0.75)
        self.assertEqual(m["confusion"]["EXTENSION"]["EXTENSION"],1)
        self.assertFalse(m["modelValidated"])

    def test_no_extension_truth_means_balanced_threeway_accuracy_not_defined(self):
        m=audit.score_three_way([
            ({"PASS":0.7,"CRL":0.2,"EXTENSION":0.1},"PASS"),
            ({"PASS":0.2,"CRL":0.7,"EXTENSION":0.1},"CRL"),
        ],2)
        self.assertEqual(m["accuracy"],1)
        self.assertIsNone(m["balancedAccuracy"])
        self.assertIsNone(m["perClassRecall"]["EXTENSION"])

    def test_no_covered_forecasts_means_not_zero_accuracy(self):
        m=audit.score_three_way([],7)
        self.assertEqual(m["covered"],0)
        self.assertEqual(m["abstentionsAndUnverified"],7)
        self.assertIsNone(m["accuracy"])
        self.assertIsNone(m["logLoss"])
        self.assertIsNone(m["multiclassBrier"])
        self.assertEqual(m["coverage"],0)

    def test_hindsight_frozen_prediction_after_FDA_action_rejected(self):
        p,r,f,o=fixture()
        f["records"][2]["frozenAtUTC"]="2027-04-03T14:00:00Z"
        f["records"][2]["asOfDate"]="2027-04-03"
        f["records"][2]["publicEvidence"][0]["firstPublicDate"]="2027-04-02"
        with self.assertRaisesRegex(ValueError,"PREDICTION_AFTER_FDA_OUTCOME"):
            audit.parse_prospective(p,r,f,o)

    def test_same_day_unverified_evidence_cannot_be_backdated_into_frozen_prediction(self):
        p,r,f,o=fixture()
        f["records"][0]["publicEvidence"][0]["firstPublicDate"]="2027-01-03"
        with self.assertRaisesRegex(ValueError,"FUTURE_PUBLIC_EVIDENCE_LEAKAGE"):
            audit.parse_prospective(p,r,f,o)

    def test_adaptive_thresholds_cannot_approve_protocol(self):
        p,r,f,o=fixture()
        p["minAdjudicatedProspectivePrograms"]=1
        with self.assertRaisesRegex(ValueError,"LOWERED_VALIDATION_THRESHOLD"):
            audit.parse_prospective(p,r,f,o)
        p["minAdjudicatedProspectivePrograms"]=30
        p["minProgramsPerClass"]=1
        with self.assertRaisesRegex(ValueError,"LOWERED_VALIDATION_THRESHOLD"):
            audit.parse_prospective(p,r,f,o)

    def test_duplicate_program_family_cannot_fake_more_holdout_cases(self):
        p,r,f,o=fixture()
        r["records"][1]["issuerProgramFamilyId"]=r["records"][0]["issuerProgramFamilyId"]
        with self.assertRaisesRegex(ValueError,"DUPLICATE_PROGRAM_OR_REVIEW_CYCLE"):
            audit.parse_prospective(p,r,f,o)

    def test_malformed_probs_and_argmax_fail_closed(self):
        p,r,f,o=fixture()
        for bad in ({"PASS":0.8,"CRL":0.4,"EXTENSION":-0.2},
                    {"PASS":0.8,"CRL":0.2},
                    {"PASS":float("nan"),"CRL":0.1,"EXTENSION":0.9}):
            g=deepcopy(f)
            g["records"][0]["probabilities"]=bad
            with self.assertRaisesRegex(ValueError,"THREE_"):
                audit.parse_prospective(p,r,g,o)
        g=deepcopy(f)
        g["records"][0]["predictedClass"]="CRL"
        with self.assertRaisesRegex(ValueError,"PREDICTION_ARGMAX_INCONSISTENT"):
            audit.parse_prospective(p,r,g,o)

    def test_formal_extension_requires_fda_primary_source_and_label(self):
        p,r,f,o=fixture()
        g=deepcopy(o)
        g["records"][2]["formalFDAExtensionDocumented"]=False
        with self.assertRaisesRegex(ValueError,"EXTENSION_OR_FDA_PRIMARY_SOURCE_MISSING"):
            audit.parse_prospective(p,r,f,g)
        g=deepcopy(o)
        g["records"][2]["officialFdaSourceUrl"]="https://www.sec.gov/filing"
        with self.assertRaisesRegex(ValueError,"EXTENSION_OR_FDA_PRIMARY_SOURCE_MISSING"):
            audit.parse_prospective(p,r,f,g)

    def test_unreviewed_outcome_and_unverified_receipt_not_scored(self):
        p,r,f,o=fixture()
        o["records"][1]["independentFDAReviewerVerified"]=False
        f["records"][2]["receiptIndependentlyVerified"]=False
        r=audit.prospective_audit(p,r,f,o,"2027-07-01T00:00:00Z")
        self.assertEqual(r["unverifiedOutcomes"],1)
        self.assertEqual(r["unverifiedFreezeReceipts"],1)
        self.assertEqual(r["coveredScoredCases"],1)
        self.assertEqual(r["mathMetrics"]["coverage"],round(1/3,5))
        self.assertIsNone(r["mathMetrics"]["balancedAccuracy"])

    def test_pending_outcome_kept_distinct_from_abstention(self):
        p,r,f,o=fixture()
        o["records"].pop()
        report=audit.prospective_audit(p,r,f,o,"2027-07-01T00:00:00Z")
        self.assertEqual(report["pendingOutcomes"],1)
        self.assertEqual(report["abstained"],0)
        self.assertEqual(report["coveredScoredCases"],3)
        self.assertEqual(report["mathMetrics"]["coverage"],1)

    def test_reports_can_export_consistent_queue_without_unlocking_strategy(self):
        from tempfile import TemporaryDirectory
        r=audit.execute()
        with TemporaryDirectory() as td:
            out=Path(td)/"report.json"
            queue=Path(td)/"queue.csv"
            audit.export(r,out,queue)
            parsed=json.loads(out.read_text())
            self.assertEqual(parsed["approvedBestPredictiveModel"],None)
            self.assertEqual(len(audit.csv_rows(queue)),146)
            self.assertEqual(parsed["approvedFDAOutcomeAccuracyPct"],None)


if __name__=="__main__":
    unittest.main()
