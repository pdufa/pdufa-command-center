"""Offline integration receipts for Level6 worker engineering-only progress."""
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

class Level6IntegrationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        for obj,values in [
            (B,{"DATA":self.home,"LEDGER":self.home/"level_completion_ledger.json"}),
            (E,{"STATE":self.home/"engineering_lane_ledger.json"})]:
            for key,value in values.items():
                p=patch.object(obj,key,value)
                p.start()
                self.addCleanup(p.stop)
        self.manifest=B.plan()
        self.state=B.new_ledger(self.manifest)

    def test_scope_approved_for_engineering_only_and_next_levels_not_approved(self):
        row=self.manifest["levels"][2]
        self.assertEqual(row["level"],6)
        self.assertEqual(row["implementation_draft_pr"],1163)
        self.assertIn("gap inventory",row["implementation_scope"])
        self.assertFalse(row["completed_scientific_level"])
        self.assertTrue(all(x["implementation_draft_pr"] is None
                            for x in self.manifest["levels"][4:]))
        self.assertTrue(all(v is False for v in self.manifest["safety"].values()))

    def test_32_live_registry_receipts_needed_not_preclinical_or_fda_invented(self):
        ncts,roster=B.verified_level5_candidate_ids()
        report={"retrieved":32,"total":32,"reports":[{"nct":n} for n in ncts]}
        with patch("level6_cross_disciplinary_inventory.process_ncts",return_value=report):
            evidence=B.execute(6,"COLLECT_ORIGINAL_SOURCE",self.manifest)
        self.assertEqual(evidence["retrieved_original_source_count"],32)
        self.assertEqual(evidence["snapshot_as_of"],"2026-11-11")
        self.assertEqual(evidence["source_git_blob_sha1"],roster["source_git_blob_sha1"])
        self.assertEqual(evidence["preclinical_primary_sources_verified"],0)
        self.assertEqual(evidence["regulatory_primary_sources_verified"],0)
        self.assertFalse(evidence["cross_domain_scientific_integration_complete"])
        with patch("level6_cross_disciplinary_inventory.process_ncts",
                   return_value=dict(report,retrieved=31)):
            with self.assertRaisesRegex(RuntimeError,"LEVEL6_SOURCE_RETRIEVAL_PARTIAL"):
                B.execute(6,"COLLECT_ORIGINAL_SOURCE",self.manifest)

    def test_9_real_regressions_and_retired_guard(self):
        ok=[subprocess.CompletedProcess([],0,"","Ran 9 tests in 0.2s"),
            subprocess.CompletedProcess([],0,"PASS","")]
        with patch.object(B,"cmd",side_effect=ok):
            result=B.execute(6,"RUN_REGRESSION_TESTS",self.manifest)
        self.assertEqual(result["tests"],[
            {"suite":"level6_cross_domain_source_gaps","passed":9},
            {"suite":"permanent_retirement","passed":True}])
        with patch.object(B,"cmd",side_effect=[subprocess.CompletedProcess([],1,"","FAIL")]):
            with self.assertRaisesRegex(RuntimeError,"LEVEL6_REGRESSION_OR_RETIREMENT_FAILED"):
                B.execute(6,"RUN_REGRESSION_TESTS",self.manifest)

    def test_pr1163_is_draft_and_correct_branch(self):
        correct={"number":1163,"state":"OPEN","isDraft":True,
                 "baseRefName":"automation/level5-checkpoints-one-command-20261112",
                 "headRefName":"feature/level6-cross-disciplinary-evidence-20261112",
                 "url":"https://github.com/pdufa/pdufa-command-center/pull/1163"}
        with patch.object(B,"cmd",return_value=subprocess.CompletedProcess(
                [],0,json.dumps(correct),"")):
            self.assertEqual(B.confirmed_level6_pr()["pr_number"],1163)
        wrong=dict(correct,isDraft=False)
        with patch.object(B,"cmd",return_value=subprocess.CompletedProcess(
                [],0,json.dumps(wrong),"")):
            with self.assertRaisesRegex(RuntimeError,"NOT_APPROVED_DRAFT"):
                B.confirmed_level6_pr()

    def test_old_four_blockers_rearmed_once_without_touching_science_or_level5(self):
        before5=json.dumps(self.state["levels"]["5"],sort_keys=True)
        prior={}
        for step,code in E.LEVEL5_REARMABLE.items():
            row=self.state["levels"]["6"]["steps"][step]
            row.update(status="BLOCKED",attempts=2,blocker=code,
                       evidence={"scientific_signoff":False,"last_attempt_utc":"2026-11-12T18:11Z"})
            prior[step]=code
        with patch.object(B,"confirmed_level6_pr",return_value={"pr_number":1163}):
            self.assertTrue(E.rearm_level6_after_real_implementation(self.state,self.manifest))
            self.assertFalse(E.rearm_level6_after_real_implementation(self.state,self.manifest))
        doc=json.loads((self.home/"level6/prior-placeholder-blockers.json").read_text())
        self.assertEqual(set(doc["restored_steps"]),set(prior))
        self.assertEqual(json.dumps(self.state["levels"]["5"],sort_keys=True),before5)
        self.assertFalse(self.state["levels"]["6"]["scientific_complete"])
        for step in prior:
            row=self.state["levels"]["6"]["steps"][step]
            self.assertEqual(row["status"],"PENDING")
            self.assertEqual(row["attempts"],0)

    def test_new_source_failure_is_not_cleared(self):
        row=self.state["levels"]["6"]["steps"]["COLLECT_ORIGINAL_SOURCE"]
        row.update(status="BLOCKED",attempts=2,blocker="LEVEL6_SOURCE_RETRIEVAL_PARTIAL")
        with patch.object(B,"confirmed_level6_pr",return_value={"pr_number":1163}):
            self.assertFalse(E.rearm_level6_after_real_implementation(self.state,self.manifest))
        self.assertEqual(row["blocker"],"LEVEL6_SOURCE_RETRIEVAL_PARTIAL")

    def test_level6_engineering_receipts_require_all_real_parts(self):
        steps=self.state["levels"]["6"]["steps"]
        for step in E.STEPS:
            steps[step].update(status="DONE",attempts=1,evidence={"scientific_signoff":False})
        src=steps["COLLECT_ORIGINAL_SOURCE"]["evidence"]
        src.update(snapshot_nct_count=32,retrieved_original_source_count=32,
                   unavailable_or_invalid_count=0,
                   source_git_blob_sha1="b1b79b632ff6a87d6533f6135d4204cb5931e23c",
                   preclinical_primary_sources_verified=0,regulatory_primary_sources_verified=0,
                   cross_domain_scientific_integration_complete=False,
                   current_canonical_focus_verified=False,independently_reviewed=False)
        steps["IMPLEMENT_FUNCTIONAL_GATES"]["evidence"]["implementation_pr"]={"pr_number":1163}
        steps["PREPARE_REVIEW_PR"]["evidence"]["implementation_pr"]={"pr_number":1163}
        steps["RUN_REGRESSION_TESTS"]["evidence"]["tests"]=[
            {"suite":"level6_cross_domain_source_gaps","passed":9},
            {"suite":"permanent_retirement","passed":True}]
        self.assertIsNotNone(E.engineering_evidence(self.state,self.manifest,6,verify_remote=False))
        src["retrieved_original_source_count"]=31
        self.assertIsNone(E.engineering_evidence(self.state,self.manifest,6,verify_remote=False))
        src["retrieved_original_source_count"]=32
        src["cross_domain_scientific_integration_complete"]=True
        self.assertIsNone(E.engineering_evidence(self.state,self.manifest,6,verify_remote=False))

    def test_later_scientific_level_never_passed_by_engineering_evidence(self):
        self.assertIsNone(E.engineering_evidence(self.state,self.manifest,7,verify_remote=False))
        self.assertEqual(self.state["levels"]["6"]["scientific_complete"],False)
        self.assertEqual(self.state["levels"]["7"]["scientific_complete"],False)

if __name__=="__main__":
    unittest.main()
