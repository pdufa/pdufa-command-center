"""Strict level sequence tests: no advancement without independent source-linked review."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pdufa_level_completion as B
spec = importlib.util.spec_from_file_location("pdufa_strict", ROOT / "scripts/pdufa_strict_level_runner.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

class SequenceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        home = Path(temp.name)
        for obj, values in [
            (B, {"DATA": home, "LEDGER": home/"level_completion_ledger.json",
                 "HEARTBEAT": home/"heartbeat.json", "LOCK": home/"RUNNING.lock", "STOP": home/"STOP"}),
            (M, {"DATA": home, "SEQUENCE": home/"sequential_level_status.json",
                 "REVIEW_DIR": home/"independent-level-acceptance"})]:
            for key,value in values.items():
                ctx = patch.object(obj,key,value)
                ctx.start();self.addCleanup(ctx.stop)
        self.home=home
        self.plan=B.plan()
        self.state=B.new_ledger(self.plan)
        self.seq=M.new_sequence()

    def test_strict_level4_never_advances_when_all_4_tasks_blocked(self):
        for name in B.STEPS:
            self.state["levels"]["4"]["steps"][name]["status"]="BLOCKED"
        self.assertIsNone(M.candidate(self.state,4))
        self.assertEqual(M.one_cycle(self.seq,self.state,self.plan),"BLOCKED_AWAITING_APPROVED_WORK_OR_REVIEW")
        self.assertEqual(M.level(self.seq),4)
        self.assertEqual(len(self.seq["accepted_levels"]),0)

    def test_task_selection_never_crosses_to_level5(self):
        self.assertEqual(M.candidate(self.state,4),"AUDIT_EXISTING_DRAFTS")
        for name in B.STEPS:
            self.state["levels"]["4"]["steps"][name]["status"]="DONE"
        self.assertIsNone(M.candidate(self.state,4))
        self.assertEqual(M.level(self.seq),4)

    def test_provenance_gates_require_two_real_reviewers(self):
        for name in B.STEPS:
            if name!="INDEPENDENT_REVIEW":
                self.state["levels"]["4"]["steps"][name]["status"]="DONE"
        evidence = self.home/"review-evidence.json"
        evidence.write_text('{"review_notes":"human authored evidence package"}',encoding="utf-8")
        import hashlib
        sha=hashlib.sha256(evidence.read_bytes()).hexdigest()
        reviewdir=self.home/"independent-level-acceptance"
        reviewdir.mkdir()
        urls=[f"https://github.com/pdufa/pdufa-command-center/issues/1096#issuecomment-{i}"
              for i in (1001,1002)]
        payload={"schema_version":1,"level":4,
                 "scientific_review":True,"independent_code_review":True,
                 "all_acceptance_criteria_met":True,
                 "criteria":self.plan["levels"][0]["scientific_acceptance_criteria"],
                 "evidence_file":"review-evidence.json","evidence_sha256":sha,
                 "review_comments":[{"role":"SCIENTIFIC","url":urls[0]},
                                    {"role":"CODE","url":urls[1]}]}
        (reviewdir/"level_04.json").write_text(json.dumps(payload),encoding="utf-8")
        def good(url):
            who="science-expert" if url==urls[0] else "code-expert"
            role="SCIENTIFIC" if url==urls[0] else "CODE"
            return {"user":{"login":who},
                    "body":f"PDUFA-L04-{role}-ACCEPTED SHA256:{sha}"}
        receipt=M.verify_review(self.seq,self.state,self.plan,lookup=good)
        self.assertEqual(receipt["level"],4)
        self.assertEqual(len(receipt["verified_reviewers"]),2)
        bad=lambda url: {"user":{"login":"same-reviewer"},
                          "body":"PDUFA-L04-SCIENTIFIC-ACCEPTED SHA256:"+sha}
        with self.assertRaises(ValueError):
            M.verify_review(self.seq,self.state,self.plan,lookup=bad)
        payload["all_acceptance_criteria_met"]=False
        (reviewdir/"level_04.json").write_text(json.dumps(payload),encoding="utf-8")
        with self.assertRaises(ValueError):
            M.verify_review(self.seq,self.state,self.plan,lookup=good)

    def test_accepted_review_moves_to_level5_only_after_external_receipt(self):
        for name in B.STEPS:
            if name!="INDEPENDENT_REVIEW":
                self.state["levels"]["4"]["steps"][name]["status"]="DONE"
        evidence=self.home/"test.json"
        evidence.write_text('{"verified":true}',encoding="utf-8")
        import hashlib
        sha=hashlib.sha256(evidence.read_bytes()).hexdigest()
        self.seq["last_review_blocker"]=None
        reviewdir=self.home/"independent-level-acceptance"
        reviewdir.mkdir()
        urls=[f"https://github.com/pdufa/pdufa-command-center/issues/1096#issuecomment-{i}"
              for i in (101,102)]
        (reviewdir/"level_04.json").write_text(json.dumps({
            "schema_version":1,"level":4,"scientific_review":True,
            "independent_code_review":True,"all_acceptance_criteria_met":True,
            "criteria":self.plan["levels"][0]["scientific_acceptance_criteria"],
            "evidence_file":"test.json","evidence_sha256":sha,
            "review_comments":[{"role":"SCIENTIFIC","url":urls[0]},
                               {"role":"CODE","url":urls[1]}]
        }),encoding="utf-8")
        def reviewer(url):
            role="SCIENTIFIC" if url==urls[0] else "CODE"
            return {"user":{"login":role.lower()+"-reviewer"},
                    "body":f"PDUFA-L04-{role}-ACCEPTED SHA256:{sha}"}
        self.assertEqual(M.one_cycle(self.seq,self.state,self.plan,lookup=reviewer),
                         "INDEPENDENT_REVIEW_ACCEPTED_NEXT_LEVEL")
        self.assertEqual(M.level(self.seq),5)
        self.assertEqual(M.load_sequence()["active_level"],5)
        self.assertEqual(M.candidate(self.state,5),"AUDIT_EXISTING_DRAFTS")

    def test_monitor_records_current_level_and_no_false_completion(self):
        text=M.monitor_text(self.seq,self.state,None)
        self.assertIn("Current level:** 4",text)
        self.assertIn("Reviewed levels accepted for advancement:** 0/17",text)
        self.assertIn("STRICT LEVEL-BY-LEVEL",text)

    def test_resume_rejects_forged_level_jump(self):
        M.save_sequence(self.seq)
        self.seq["active_level"]=20
        M.save_sequence(self.seq)
        with self.assertRaises(ValueError):
            M.load_sequence()

    def test_stale_running_status_does_not_mutate_during_display(self):
        item=self.state["levels"]["4"]["steps"]["AUDIT_EXISTING_DRAFTS"]
        item.update(status="RUNNING",attempts=1)
        M.monitor_text(self.seq,self.state,"AUDIT_EXISTING_DRAFTS")
        self.assertEqual(item["status"],"RUNNING")
        self.assertEqual(M.candidate(self.state,4,recover=True),"AUDIT_EXISTING_DRAFTS")
        self.assertEqual(item["status"],"PENDING")

if __name__ == "__main__":
    unittest.main()
