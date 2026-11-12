"""Engineering lane advances approved slices, not independent scientific acceptance."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import pdufa_level_completion as B
import pdufa_strict_level_runner as S
spec=importlib.util.spec_from_file_location("engine",ROOT/"scripts/pdufa_engineering_review_lanes.py")
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

class EngineeringLanes(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home=Path(temp.name)
        for obj,d in [
            (B,{"DATA":home,"LEDGER":home/"level_completion_ledger.json",
                "HEARTBEAT":home/"heartbeat.json","LOCK":home/"RUNNING.lock",
                "STOP":home/"STOP"}),
            (S,{"DATA":home,"SEQUENCE":home/"sequential_level_status.json",
                "REVIEW_DIR":home/"independent-level-acceptance"}),
            (M,{"STATE":home/"engineering_lane_ledger.json",
                "HEARTBEAT":home/"heartbeat.json"})]:
            for k,v in d.items():
                p=patch.object(obj,k,v)
                p.start();self.addCleanup(p.stop)
        self.home=home
        self.manifest=B.plan()
        self.state=B.new_ledger(self.manifest)
        self.eng=M.initial()
        self.sci=S.new_sequence()
        S.save_sequence(self.sci)
        p=patch.object(M,"heartbeat")
        p.start();self.addCleanup(p.stop)
        p=patch.object(M,"publish",return_value=True)
        p.start();self.addCleanup(p.stop)

    def fill_level4(self):
        for key in M.STEPS:
            row=self.state["levels"]["4"]["steps"][key]
            row.update(status="DONE",attempts=1,evidence={
                "scientific_signoff":False,"observed_at_utc":"2026-11-12T15:00:00+00:00"
            })
        s=self.state["levels"]["4"]["steps"]
        s["COLLECT_ORIGINAL_SOURCE"]["evidence"].update(
            retrieved_original_source_count=29,snapshot_nct_count=29,
            unavailable_or_invalid_count=0,current_canonical_focus_verified=False,
            independently_reviewed=False)
        s["IMPLEMENT_FUNCTIONAL_GATES"]["evidence"]["implementation_pr"]={"pr_number":1156}
        s["PREPARE_REVIEW_PR"]["evidence"]["implementation_pr"]={"pr_number":1156}
        s["RUN_REGRESSION_TESTS"]["evidence"]["tests"]=[
            {"suite":"level4_original_source","passed":6},
            {"suite":"permanent_retirement","passed":True}
        ]

    def test_current_level4_eng_slice_advances_to_5_without_sci_review(self):
        self.fill_level4()
        self.assertIsNotNone(M.engineering_evidence(self.state,self.manifest,4,verify_remote=False))
        self.assertEqual(M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False),
                         "ENGINEERING_SCOPE_ACCEPTED_ADVANCE_NEXT")
        self.assertEqual(M.first_uncompleted(self.eng),5)
        self.assertEqual(len(self.eng["engineering_completed_levels"]),1)
        self.assertEqual(len(S.load_sequence()["accepted_levels"]),0)
        self.assertFalse(self.eng["engineering_completed_levels"][0]["scientifically_complete"])
        self.assertEqual(M.load(self.state,self.manifest)["mode"],
                         "ENGINEERING_ADVANCE_REVIEW_SEPARATE")
        self.assertEqual(self.state["levels"]["4"]["steps"]["INDEPENDENT_REVIEW"]["status"],
                         "PENDING")

    def test_missing_stage4_source_or_test_wont_advance(self):
        self.fill_level4()
        self.state["levels"]["4"]["steps"]["COLLECT_ORIGINAL_SOURCE"]["evidence"][
            "retrieved_original_source_count"]=28
        self.assertIsNone(M.engineering_evidence(self.state,self.manifest,4,verify_remote=False))
        self.assertEqual(M.first_uncompleted(self.eng),4)
        self.state["levels"]["4"]["steps"]["COLLECT_ORIGINAL_SOURCE"]["evidence"][
            "retrieved_original_source_count"]=29
        self.state["levels"]["4"]["steps"]["RUN_REGRESSION_TESTS"]["evidence"]["tests"][0]["passed"]=0
        self.assertIsNone(M.engineering_evidence(self.state,self.manifest,4,verify_remote=False))

    def test_no_level5_approval_without_real_domain_implementation(self):
        self.fill_level4()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        for step in M.STEPS:
            self.state["levels"]["5"]["steps"][step].update(
                status="DONE",attempts=1,evidence={"scientific_signoff":False})
        self.assertIsNone(M.engineering_evidence(self.state,self.manifest,5,verify_remote=False))
        self.assertEqual(M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False),
                         "BLOCKED_AWAITING_IMPLEMENTATION_OR_SOURCE")
        self.assertEqual(M.first_uncompleted(self.eng),5)

    def test_engineering_acceptance_hash_cannot_be_forged_by_edit(self):
        self.fill_level4()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        self.state["levels"]["4"]["steps"]["RUN_REGRESSION_TESTS"]["evidence"]["tests"][0][
            "passed"]=7
        with self.assertRaises(ValueError):
            M.load(self.state,self.manifest)

    def test_scientific_review_later_independent_of_level5_engineering(self):
        self.fill_level4()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        approve={"level":4,"review_evidence_sha256":"f"*64,
                 "verified_reviewers":["scientific-reviewer","code-reviewer"],
                 "verified_utc":"2026-11-12T16:00:00+00:00",
                 "review_comment_urls":[
                    "https://github.com/pdufa/pdufa-command-center/issues/1096#issuecomment-10",
                    "https://github.com/pdufa/pdufa-command-center/issues/1096#issuecomment-11"]}
        with patch.object(S,"verify_review",return_value=approve):
            sci,block=M.review_sync(self.state,self.manifest)
        self.assertIsNone(block)
        self.assertEqual(len(sci["accepted_levels"]),1)
        self.assertEqual(len(S.load_sequence()["accepted_levels"]),1)
        self.assertEqual(M.first_uncompleted(self.eng),5)

    def test_level5_runs_approved_audit_but_blocks_on_missing_domain_source(self):
        self.fill_level4()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        with patch.object(B,"execute",return_value={"result":"AUDITED"}):
            self.assertEqual(M.cycle(self.eng,self.state,self.manifest,
                                     check_review=False,remote=False),
                             "ENGINEERING_CHECKPOINT_ATTEMPTED")
        self.assertEqual(self.state["levels"]["5"]["steps"]["AUDIT_EXISTING_DRAFTS"]["status"],
                         "DONE")
        with patch.object(B,"execute",side_effect=RuntimeError("DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED")):
            M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        self.assertEqual(self.state["levels"]["5"]["steps"]["COLLECT_ORIGINAL_SOURCE"]["status"],
                         "BLOCKED")
        self.assertEqual(M.first_uncompleted(self.eng),5)

    def test_legacy_science_ledger_remains_unchanged_when_engineering_moves(self):
        self.fill_level4()
        old=S.load_sequence()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        self.assertEqual(S.load_sequence(),old)
        text=M.monitor(self.eng,old,self.state)
        self.assertIn("Engineering implementation slices completed:** 1/17",text)
        self.assertIn("Independent scientific levels reviewed:** 0/17",text)
        self.assertIn("registry evidence inventory",text)

    def test_reject_corrupt_engineering_progress_ledger(self):
        self.fill_level4()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        raw=json.loads(M.STATE.read_text(encoding="utf-8"))
        raw["engineering_completed_levels"][0]["level"]=7
        M.STATE.write_text(json.dumps(raw),encoding="utf-8")
        with self.assertRaises(ValueError):
            M.load(self.state,self.manifest)

    def test_only_old_level5_placeholder_blockers_rearmed_one_time(self):
        self.fill_level4()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        prior=S.load_sequence()
        mapping=dict(M.LEVEL5_REARMABLE)
        for step,code in mapping.items():
            self.state["levels"]["5"]["steps"][step].update(
                status="BLOCKED",blocker=code,attempts=2,
                evidence={"scientific_signoff":False,"last_attempt_utc":"2026-11-12T15:37:21Z"})
        self.state["levels"]["6"]["steps"]["COLLECT_ORIGINAL_SOURCE"].update(
            status="BLOCKED",blocker="DOMAIN_SOURCE_COLLECTION_NOT_REVIEWED",attempts=2)
        with patch.object(B,"confirmed_level5_pr",return_value={"pr_number":1161}):
            self.assertTrue(M.rearm_level5_after_real_implementation(self.state,self.manifest))
            self.assertFalse(M.rearm_level5_after_real_implementation(self.state,self.manifest))
        self.assertTrue((self.home/"level5/prior-placeholder-blockers.json").exists())
        self.assertTrue((self.home/"level5/approved-retry-receipt.json").exists())
        for step,code in mapping.items():
            item=self.state["levels"]["5"]["steps"][step]
            self.assertEqual(item["status"],"PENDING")
            self.assertEqual(item["attempts"],0)
            self.assertIsNone(item["blocker"])
        self.assertEqual(self.state["levels"]["6"]["steps"]["COLLECT_ORIGINAL_SOURCE"]["status"],
                         "BLOCKED")
        self.assertEqual(S.load_sequence(),prior)

    def test_actual_level5_test_failure_cannot_be_hidden_by_rearm(self):
        self.state["levels"]["5"]["steps"]["RUN_REGRESSION_TESTS"].update(
            status="BLOCKED",blocker="LEVEL5_REGRESSION_OR_RETIREMENT_FAILED",attempts=2)
        with patch.object(B,"confirmed_level5_pr",return_value={"pr_number":1161}):
            self.assertFalse(M.rearm_level5_after_real_implementation(self.state,self.manifest))
        self.assertEqual(self.state["levels"]["5"]["steps"]["RUN_REGRESSION_TESTS"]["status"],
                         "BLOCKED")
        self.assertFalse((self.home/"level5/approved-retry-receipt.json").exists())

    def test_level5_engineering_scope_proven_by_32_receipts_eight_tests_and_pr(self):
        self.fill_level4()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        for step in M.STEPS:
            self.state["levels"]["5"]["steps"][step].update(
                status="DONE",attempts=1,evidence={"scientific_signoff":False})
        source=self.state["levels"]["5"]["steps"]["COLLECT_ORIGINAL_SOURCE"]["evidence"]
        source.update(snapshot_nct_count=32,retrieved_original_source_count=32,
                      unavailable_or_invalid_count=0,
                      source_git_blob_sha1="b1b79b632ff6a87d6533f6135d4204cb5931e23c",
                      current_canonical_focus_verified=False,independently_reviewed=False,
                      negative_evidence_adjudicated=False)
        self.state["levels"]["5"]["steps"]["IMPLEMENT_FUNCTIONAL_GATES"][
            "evidence"]["implementation_pr"]={"pr_number":1161}
        self.state["levels"]["5"]["steps"]["PREPARE_REVIEW_PR"][
            "evidence"]["implementation_pr"]={"pr_number":1161}
        self.state["levels"]["5"]["steps"]["RUN_REGRESSION_TESTS"]["evidence"]["tests"]=[
            {"suite":"level5_source_challenge","passed":8},
            {"suite":"permanent_retirement","passed":True}]
        self.assertIsNotNone(M.engineering_evidence(self.state,self.manifest,5,verify_remote=False))
        self.assertEqual(M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False),
                         "ENGINEERING_SCOPE_ACCEPTED_ADVANCE_NEXT")
        self.assertEqual(M.first_uncompleted(self.eng),6)
        self.assertEqual(len(S.load_sequence()["accepted_levels"]),0)
        self.assertFalse(self.eng["engineering_completed_levels"][1]["scientifically_complete"])

    def test_incomplete_32_study_source_cannot_advance_level5(self):
        self.fill_level4()
        M.cycle(self.eng,self.state,self.manifest,check_review=False,remote=False)
        for step in M.STEPS:
            self.state["levels"]["5"]["steps"][step].update(
                status="DONE",attempts=1,evidence={"scientific_signoff":False})
        self.state["levels"]["5"]["steps"]["COLLECT_ORIGINAL_SOURCE"]["evidence"].update(
            snapshot_nct_count=32,retrieved_original_source_count=31,
            source_git_blob_sha1="b1b79b632ff6a87d6533f6135d4204cb5931e23c",
            unavailable_or_invalid_count=1,current_canonical_focus_verified=False,
            independently_reviewed=False,negative_evidence_adjudicated=False)
        self.assertIsNone(M.engineering_evidence(self.state,self.manifest,5,verify_remote=False))

if __name__=="__main__":
    unittest.main()
