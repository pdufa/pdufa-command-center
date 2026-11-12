"""Synthetic offline tests: Level7 must never produce uncalibrated PDUFA predictions."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("level7",ROOT/"scripts/level7_model_validation_readiness.py")
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
NCT="NCT05507203"

def source(**overrides):
    out={
        "url":"https://clinicaltrials.gov/api/v2/studies/"+NCT,
        "sha256":"a"*64,
        "trial_nct":NCT,
        "phase_at_cutoff":"PHASE3",
        "retrieved_at_utc":"2026-11-11T10:00:00Z",
        "publicly_available_at_utc":"2026-11-10T11:00:00Z",
        "source_revision":"CURRENT_STATE_NOT_HISTORICAL_FREEZE",
    }
    out.update(overrides)
    return out

def item(mode="FUTURE_PROSPECTIVE",**overrides):
    out={"nct":NCT,"mode":mode,
         "prediction_cutoff_utc":"2026-11-12T12:00:00Z",
         "evidence_sources":[source()]}
    out.update(overrides)
    return out

def plan(**overrides):
    out={
        "model_version":"v0-prespecified-only",
        "split":{"method":"TEMPORAL_FORWARD_HOLDOUT",
                 "train_end_utc":"2025-12-31T23:59:59Z",
                 "holdout_start_utc":"2026-01-01T00:00:00Z",
                 "outcome_labels_sealed_until_final_evaluation":True},
        "calibration":{"method":"ISOTONIC",
                       "fit_partition":"TRAINING_FOLDS_ONLY"},
        "report_metrics":sorted(M.REQUIRED_METRICS),
        "outcome_label_definition_locked_before_validation":True,
        "independent_validation_review":True,
    }
    out.update(overrides)
    return out

class PredictiveReadinessTests(unittest.TestCase):
    def test_prospective_cutoff_can_be_proven_but_no_prediction(self):
        r=M.audit_input(item())
        self.assertTrue(r["eligible_for_blinded_model_input"])
        self.assertEqual(r["source_count"],1)
        self.assertFalse(r["independently_adjudicated"])
        self.assertIsNone(r["fda_probability"])
        self.assertIsNone(r["prediction"])

    def test_historical_current_registry_not_blind(self):
        r=M.audit_input(item(mode="HISTORICAL_OUTCOME_BLIND"))
        self.assertIn("CURRENT_REGISTRY_USED_AS_HISTORICAL_EVIDENCE",r["review_leads"])
        self.assertFalse(r["eligible_for_blinded_model_input"])

    def test_historical_late_retrieval_fails_unless_freeze_verified(self):
        old=source(source_revision="IMMUTABLE_PRE_CUTOFF_ARCHIVE",
                   publicly_available_at_utc="2025-03-01T00:00:00Z",
                   retrieved_at_utc="2026-11-11T00:00:00Z")
        a=item(mode="HISTORICAL_OUTCOME_BLIND",
               prediction_cutoff_utc="2025-06-01T00:00:00Z",
               evidence_sources=[old])
        r=M.audit_input(a)
        self.assertIn("LATE_RETRIEVAL_WITHOUT_VERIFIED_PRE_CUTOFF_FREEZE",r["review_leads"])
        old["immutable_pre_cutoff_capture_verified"]=True
        self.assertTrue(M.audit_input(a)["eligible_for_blinded_model_input"])

    def test_future_data_after_cutoff_is_leakage(self):
        e=source(publicly_available_at_utc="2026-11-13T00:00:00Z",
                 retrieved_at_utc="2026-11-13T00:00:00Z")
        r=M.audit_input(item(evidence_sources=[e]))
        self.assertIn("SOURCE_PUBLISHED_AFTER_PREDICTION_CUTOFF",r["review_leads"])
        self.assertIn("FUTURE_PROSPECTIVE_SOURCE_RETRIEVED_AFTER_CUTOFF",r["review_leads"])
        self.assertFalse(r["eligible_for_blinded_model_input"])

    def test_direct_and_nested_actual_outcomes_rejected(self):
        a=item(actual_fda_decision="APPROVED")
        self.assertIn("OUTCOME_LABEL_FIELDS_EXPOSED",M.audit_input(a)["review_leads"])
        b=item(features=[{"details":{"actual_outcome":1}}])
        self.assertIn("OUTCOME_LABEL_FIELDS_EXPOSED",M.audit_input(b)["review_leads"])

    def test_unverified_source_sha_url_phase_identity_rejected(self):
        e=source(sha256="bad",url="http://bad.invalid",trial_nct="NCT00000000",
                 phase_at_cutoff=None)
        r=M.audit_input(item(evidence_sources=[e]))
        self.assertEqual(set(r["review_leads"]),
            {"MISSING_EXACT_SOURCE_SHA256","UNVERIFIABLE_PRIMARY_SOURCE_URL",
             "SOURCE_TRIAL_IDENTITY_NOT_PROVEN","PHASE_AT_CUTOFF_UNVERIFIED"})

    def test_invalid_timestamps_and_missing_receipts(self):
        r=M.audit_input(item(evidence_sources=[],
                             prediction_cutoff_utc="not-a-date"))
        self.assertIn("NO_PRIMARY_SOURCE_RECEIPTS",r["review_leads"])
        self.assertIn("INVALID_PREDICTION_CUTOFF",r["review_leads"])
        r=M.audit_input(item(evidence_sources=[source(retrieved_at_utc="2026-11-11")]))
        self.assertIn("SOURCE_ACCESS_OR_PUBLICATION_DATE_UNVERIFIED",r["review_leads"])

    def test_exact_ascii_nct_and_modes_required(self):
        for bad in ["NCT٠٥٥٠٧٢٠٣","NCT123","nct05507203"]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                M.audit_input(item(nct=bad))
        with self.assertRaises(ValueError):
            M.audit_input(item(mode="POST_FDA_OUTCOME_KNOWN"))

    def test_validation_plan_requires_forward_holdout_and_sealed_labels(self):
        self.assertTrue(M.audit_plan(plan())["validation_plan_design_complete"])
        p=plan(split=dict(plan()["split"],holdout_start_utc="2025-01-01T00:00:00Z",
                          outcome_labels_sealed_until_final_evaluation=False))
        audit=M.audit_plan(p)
        self.assertIn("TRAINING_OVERLAPS_FUTURE_HOLDOUT",audit["review_leads"])
        self.assertIn("HOLDOUT_OUTCOMES_NOT_SEALED",audit["review_leads"])

    def test_calibration_never_fit_on_holdout_and_metrics_not_fabricated(self):
        audit=M.audit_plan(plan(calibration={"method":"PLATT",
                                             "fit_partition":"FINAL_HOLDOUT"},
                                report_metrics=["accuracy"]))
        self.assertIn("CALIBRATION_FIT_MUST_EXCLUDE_FINAL_HOLDOUT",audit["review_leads"])
        self.assertIn("PRESPECIFIED_CALIBRATION_METRICS_INCOMPLETE",audit["review_leads"])
        self.assertFalse(audit["metrics_computed"])
        self.assertFalse(audit["calibration_verified"])

    def test_bundle_passes_only_readiness_not_actual_scientific_level(self):
        r=M.audit_bundle({"inputs":[item()],"plan":plan()})
        self.assertEqual(r["input_receipts_gate_passed"],1)
        self.assertTrue(r["ready_for_independent_review"])
        self.assertFalse(r["scientific_level_complete"])
        self.assertFalse(r["uncertainty_calibrated"])
        self.assertFalse(r["model_trained"])
        self.assertFalse(r["fda_predictions_published"])

    def test_duplicate_trial_unknown_bundle_fields_and_size_cap(self):
        with self.assertRaises(ValueError):
            M.audit_bundle({"inputs":[item(),item()],"plan":plan()})
        with self.assertRaises(ValueError):
            M.audit_bundle({"inputs":[item()],"plan":plan(),
                            "actual_fda_decision":"APPROVED"})
        with self.assertRaises(ValueError):
            M.audit_bundle({"inputs":[item() for _ in range(33)],"plan":plan()})

    def test_no_independent_review_no_ready(self):
        r=M.audit_bundle({"inputs":[item()],"plan":plan(independent_validation_review=False)})
        self.assertFalse(r["ready_for_independent_review"])
        self.assertFalse(r["scientific_level_complete"])

if __name__=="__main__":
    unittest.main()
