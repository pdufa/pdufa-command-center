"""Level5 all-four checkpoint implementation integration, without falsifying science."""
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

class Level5IntegrationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data=Path(tmp.name)
        for obj,values in [
            (B,{"DATA":self.data,"LEDGER":self.data/"level_completion_ledger.json"}),
            (E,{"STATE":self.data/"engineering_lane_ledger.json"})]:
            for key,value in values.items():
                p=patch.object(obj,key,value)
                p.start();self.addCleanup(p.stop)
        self.manifest=B.plan()

    def test_level5_scope_is_registered_but_not_science_complete(self):
        row=self.manifest["levels"][1]
        self.assertEqual(row["implementation_draft_pr"],1161)
        self.assertIn("challenge inventory",row["implementation_scope"])
        self.assertFalse(row["completed_scientific_level"])
        self.assertTrue(all(not flag for flag in self.manifest["safety"].values()))

    def test_32_readonly_lead_candidates_exact_ncts(self):
        ncts,doc=B.verified_level5_candidate_ids()
        self.assertEqual(len(ncts),32)
        self.assertEqual(len(set(ncts)),32)
        self.assertEqual(doc["asOf"],"2026-11-11")
        self.assertFalse(doc["canonical_focus_verified"])
        self.assertTrue(all(n.startswith("NCT") and len(n)==11 for n in ncts))

    def test_real_sources_required_for_level5_source_checkpoint(self):
        ncts,_=B.verified_level5_candidate_ids()
        batch={"retrieved":32,"total":32,
               "reports":[{"nct":n,"scientific_stage_complete":False} for n in ncts]}
        with patch("level5_contradictory_evidence.process_ncts",return_value=batch):
            evidence=B.execute(5,"COLLECT_ORIGINAL_SOURCE",self.manifest)
        self.assertEqual(evidence["retrieved_original_source_count"],32)
        self.assertEqual(evidence["unavailable_or_invalid_count"],0)
        self.assertFalse(evidence["current_canonical_focus_verified"])
        self.assertFalse(evidence["negative_evidence_adjudicated"])
        path=self.data/"level5/dated-source-challenge-inventory.json"
        self.assertEqual(len(json.loads(path.read_text())["reports"]),32)
        with patch("level5_contradictory_evidence.process_ncts",
                   return_value={**batch,"retrieved":31}):
            with self.assertRaisesRegex(RuntimeError,"LEVEL5_SOURCE_RETRIEVAL_PARTIAL"):
                B.execute(5,"COLLECT_ORIGINAL_SOURCE",self.manifest)

    def test_explicit_level5_source_code_and_review_pr(self):
        with patch.object(B,"confirmed_level5_pr",return_value={"pr_number":1161}):
            self.assertEqual(B.execute(5,"IMPLEMENT_FUNCTIONAL_GATES",self.manifest)[
                "implementation_pr"]["pr_number"],1161)
            self.assertEqual(B.execute(5,"PREPARE_REVIEW_PR",self.manifest)[
                "implementation_pr"]["pr_number"],1161)

    def test_level5_only_reopens_if_regressions_and_retirement_pass(self):
        replies=[
            subprocess.CompletedProcess([],0,"","Ran 8 tests in 0.1s"),
            subprocess.CompletedProcess([],0,"PASS","")
        ]
        with patch.object(B,"cmd",side_effect=replies):
            evidence=B.execute(5,"RUN_REGRESSION_TESTS",self.manifest)
        self.assertEqual(evidence["tests"],[
            {"suite":"level5_source_challenge","passed":8},
            {"suite":"permanent_retirement","passed":True}])
        with patch.object(B,"cmd",side_effect=[
            subprocess.CompletedProcess([],1,"","FAIL")]):
            with self.assertRaisesRegex(RuntimeError,"LEVEL5_REGRESSION_OR_RETIREMENT_FAILED"):
                B.execute(5,"RUN_REGRESSION_TESTS",self.manifest)

    def test_level8_still_fails_without_actual_code(self):
        for step in ("COLLECT_ORIGINAL_SOURCE","IMPLEMENT_FUNCTIONAL_GATES",
                     "RUN_REGRESSION_TESTS","PREPARE_REVIEW_PR"):
            with self.subTest(step=step), self.assertRaises(RuntimeError):
                B.execute(8,step,self.manifest)
        self.assertIsNone(E.engineering_evidence(B.new_ledger(self.manifest),
                                                  self.manifest,8,verify_remote=False))

if __name__=="__main__":
    unittest.main()
