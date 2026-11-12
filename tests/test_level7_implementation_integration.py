"""Level7 genuine engineering-only integration; never a calibrated FDA predictor."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import pdufa_level_completion as B
import pdufa_engineering_review_lanes as E

class Level7IntegrationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        for obj,values in [
            (B,{"DATA":self.home,"LEDGER":self.home/"level_completion_ledger.json"}),
            (E,{"STATE":self.home/"engineering_lane_ledger.json"})]:
            for key,value in values.items():
                q=patch.object(obj,key,value)
                q.start()
                self.addCleanup(q.stop)
        self.manifest=B.plan()
        self.state=B.new_ledger(self.manifest)
        self.level6=self.home/"level6/d a".replace("d a","dated-cross-domain-source-gap-inventory.json")
        self.level6.parent.mkdir(parents=True,exist_ok=True)
        self.level6.write_text(json.dumps({"level":6,"total":32,"retrieved":32,
                                          "reports":[]}),encoding="utf-8")

    def test_level7_scope_readiness_and_future_untouched(self):
        row=self.manifest["levels"][3]
        self.assertEqual(row["implementation_draft_pr"],1169)
        self.assertIn("evidence-gap inventory",row["implementation_scope"])
        self.assertFalse(row["completed_scientific_level"])
        self.assertTrue(all(v is False for v in self.manifest["safety"].values()))
        self.assertTrue(all(x["implementation_draft_pr"] is None
                            for x in self.manifest["levels"][4:]))

    def test_source_checkpoint_reuses_actual_level6_receipts(self):
        ncts,roster=B.verified_level5_candidate_ids()
        saved={"total":32,"original_registry_receipts_audited":32,
               "exact_nct_identity_matched":32,
               "source_roster_git_blob_sha1":roster["source_git_blob_sha1"]}
        with patch("level7_source_readiness_inventory.inventory",return_value=saved) as run:
            receipt=B.execute(7,"COLLECT_ORIGINAL_SOURCE",self.manifest)
        self.assertEqual(run.call_args.kwargs["ncts"],ncts)
        self.assertEqual(receipt["original_registry_receipts_audited"],32)
        self.assertFalse(receipt["predictive_model_trained"])
        self.assertFalse(receipt["calibration_evidence_verified"])
        self.assertFalse(receipt["approval_probabilities_generated"])
        self.assertFalse(receipt["current_canonical_focus_verified"])
        self.assertTrue((self.home/"level7/model-validation-source-and-timing-gaps.json").exists())

    def test_missing_prior_receipts_blocks_source_instead_of_approving(self):
        self.level6.unlink()
        with self.assertRaisesRegex(RuntimeError,"LEVEL7_PRIOR_SOURCE_RECEIPTS_NOT_AVAILABLE"):
            B.execute(7,"COLLECT_ORIGINAL_SOURCE",self.manifest)

    def test_review_pr_verified_against_exact_branch_and_base(self):
        correct={"number":1169,"state":"OPEN","isDraft":True,
                 "baseRefName":"automation/predictive-preflight-all-levels-20261112",
                 "headRefName":"automation/level7-engineering-readiness-20261112",
                 "url":"https://github.com/pdufa/pdufa-command-center/pull/1169"}
        with patch.object(B,"cmd",return_value=subprocess.CompletedProcess(
            [],0,json.dumps(correct),"")):
            self.assertEqual(B.confirmed_level7_pr()["pr_number"],1169)
        with patch.object(B,"cmd",return_value=subprocess.CompletedProcess(
            [],0,json.dumps(dict(correct,isDraft=False)),"")):
            with self.assertRaisesRegex(RuntimeError,"NOT_APPROVED_DRAFT"):
                B.confirmed_level7_pr()

    def test_code_and_pr_check_does_not_approve_science(self):
        with patch.object(B,"confirmed_level7_pr",return_value={"pr_number":1169}):
            gates=B.execute(7,"IMPLEMENT_FUNCTIONAL_GATES",self.manifest)
            pr=B.execute(7,"PREPARE_REVIEW_PR",self.manifest)
        self.assertFalse(gates["trained_model"])
        self.assertFalse(gates["probability_calibrated"])
        self.assertEqual(pr["implementation_pr"]["pr_number"],1169)

    def test_25_offline_regressions_and_retired_guard(self):
        responses=[
            subprocess.CompletedProcess([],0,"","Ran 13 tests in 0.2s"),
            subprocess.CompletedProcess([],0,"","Ran 12 tests in 0.2s"),
            subprocess.CompletedProcess([],0,"PASS",""),
        ]
        with patch.object(B,"cmd",side_effect=responses):
            receipt=B.execute(7,"RUN_REGRESSION_TESTS",self.manifest)
        self.assertEqual(receipt["tests"],[
            {"suite":"level7_temporal_model_readiness","passed":13},
            {"suite":"level7_source_gap_inventory","passed":12},
            {"suite":"permanent_retirement","passed":True},
        ])
        self.assertFalse(receipt["model_validated"])
        with patch.object(B,"cmd",side_effect=[
            subprocess.CompletedProcess([],1,"","FAIL")]):
            with self.assertRaisesRegex(RuntimeError,"LEVEL7_REGRESSION_OR_RETIREMENT_FAILED"):
                B.execute(7,"RUN_REGRESSION_TESTS",self.manifest)

    def test_only_four_known_placeholder_blockers_rearmed_once(self):
        before6=json.dumps(self.state["levels"]["6"],sort_keys=True)
        for step,code in E.LEVEL5_REARMABLE.items():
            self.state["levels"]["7"]["steps"][step].update(
                status="BLOCKED",attempts=2,blocker=code,
                evidence={"last_attempt_utc":"2026-11-12T21:24:48Z"})
        with patch.object(B,"confirmed_level7_pr",return_value={"pr_number":1169}):
            self.assertTrue(E.rearm_level7_after_real_implementation(self.state,self.manifest))
            self.assertFalse(E.rearm_level7_after_real_implementation(self.state,self.manifest))
        receipt=json.loads((self.home/"level7/approved-retry-receipt.json").read_text())
        self.assertFalse(receipt["scientific_level_completed"])
        self.assertEqual(json.dumps(self.state["levels"]["6"],sort_keys=True),before6)
        self.assertFalse(self.state["levels"]["7"]["scientific_complete"])
        for step in E.LEVEL5_REARMABLE:
            self.assertEqual(self.state["levels"]["7"]["steps"][step]["status"],"PENDING")

    def test_unrecognized_source_failure_is_not_silently_cleared(self):
        self.state["levels"]["7"]["steps"]["COLLECT_ORIGINAL_SOURCE"].update(
            status="BLOCKED",attempts=2,blocker="LEVEL7_PRIOR_SOURCE_RECEIPTS_NOT_AVAILABLE")
        with patch.object(B,"confirmed_level7_pr",return_value={"pr_number":1169}):
            self.assertFalse(E.rearm_level7_after_real_implementation(self.state,self.manifest))
        self.assertEqual(
            self.state["levels"]["7"]["steps"]["COLLECT_ORIGINAL_SOURCE"]["blocker"],
            "LEVEL7_PRIOR_SOURCE_RECEIPTS_NOT_AVAILABLE")

    def test_evidence_acceptance_requires_three_real_suites_and_32_receipts(self):
        steps=self.state["levels"]["7"]["steps"]
        for step in E.STEPS:
            steps[step].update(status="DONE",attempts=1,
                               evidence={"scientific_signoff":False})
        src=steps["COLLECT_ORIGINAL_SOURCE"]["evidence"]
        src.update(snapshot_nct_count=32,original_registry_receipts_audited=32,
                   exact_nct_identity_matched=32,
                   source_roster_git_blob_sha1="b1b79b632ff6a87d6533f6135d4204cb5931e23c",
                   source_publication_dates_independently_verified=0,
                   historical_pre_cutoff_source_freezes_verified=0,
                   outcome_blind_historical_validations_performed=0,
                   predictive_model_trained=False,calibration_evidence_verified=False,
                   approval_probabilities_generated=False,
                   current_canonical_focus_verified=False,independently_reviewed=False)
        steps["IMPLEMENT_FUNCTIONAL_GATES"]["evidence"].update(
            implementation_pr={"pr_number":1169},trained_model=False,
            probability_calibrated=False)
        steps["PREPARE_REVIEW_PR"]["evidence"]["implementation_pr"]={"pr_number":1169}
        steps["RUN_REGRESSION_TESTS"]["evidence"]["tests"]=[
            {"suite":"level7_temporal_model_readiness","passed":13},
            {"suite":"level7_source_gap_inventory","passed":12},
            {"suite":"permanent_retirement","passed":True}]
        self.assertIsNotNone(E.engineering_evidence(
            self.state,self.manifest,7,verify_remote=False))
        src["original_registry_receipts_audited"]=31
        self.assertIsNone(E.engineering_evidence(
            self.state,self.manifest,7,verify_remote=False))
        src["original_registry_receipts_audited"]=32
        src["predictive_model_trained"]=True
        self.assertIsNone(E.engineering_evidence(
            self.state,self.manifest,7,verify_remote=False))

if __name__=="__main__":
    unittest.main()
