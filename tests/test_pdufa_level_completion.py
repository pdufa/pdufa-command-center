"""Offline persistent Level 4-20 completion queue acceptance/restart tests."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("completion_worker", ROOT / "scripts/pdufa_level_completion.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)

class CompletionTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.home = Path(t.name)
        for attr, value in {
            "DATA": self.home, "LEDGER": self.home / "level_completion_ledger.json",
            "HEARTBEAT": self.home / "heartbeat.json",
            "LOCK": self.home / "RUNNING.lock", "STOP": self.home / "STOP",
        }.items():
            target = patch.object(M, attr, value)
            target.start()
            self.addCleanup(target.stop)
        self.plan = M.plan()
        self.state = M.new_ledger(self.plan)

    def test_17_levels_and_102_steps_have_no_false_scientific_signoff(self):
        self.assertEqual([x["level"] for x in self.plan["levels"]], list(range(4, 21)))
        self.assertEqual(M.counts(self.state)["tasks_total"], 102)
        self.assertEqual(M.counts(self.state)["scientifically_completed_levels"], 0)
        self.assertEqual(M.next_step(self.state), (4, "AUDIT_EXISTING_DRAFTS"))
        self.assertTrue(all(x["scientific_complete"] is False
                            for x in self.state["levels"].values()))

    def test_interrupted_task_preserves_progress_and_retries_bounded(self):
        first = self.state["levels"]["4"]["steps"]["AUDIT_EXISTING_DRAFTS"]
        first.update(status="DONE", attempts=1, evidence={"result": "SUCCESS"})
        step = self.state["levels"]["4"]["steps"]["COLLECT_ORIGINAL_SOURCE"]
        step.update(status="RUNNING", attempts=1)
        M.save(self.state)
        state = M.load(self.plan)
        self.assertEqual(M.next_step(state), (4, "COLLECT_ORIGINAL_SOURCE"))
        self.assertEqual(state["levels"]["4"]["steps"]["AUDIT_EXISTING_DRAFTS"]["evidence"],
                         {"result": "SUCCESS"})
        step = state["levels"]["4"]["steps"]["COLLECT_ORIGINAL_SOURCE"]
        step["status"] = "RUNNING"
        step["attempts"] = 2
        self.assertEqual(M.next_step(state), (4, "IMPLEMENT_FUNCTIONAL_GATES"))
        self.assertEqual(step["status"], "BLOCKED")

    def test_approved_draft_audit_is_not_a_scientific_completion(self):
        with patch.object(M, "confirmed_pr", side_effect=lambda n: {"pr_number": n}):
            result = M.execute(4, "AUDIT_EXISTING_DRAFTS", self.plan)
        self.assertEqual(len(result["drafts"]), 2)
        self.assertTrue(result["scientific_review_required"])
        self.assertFalse(self.state["levels"]["4"]["scientific_complete"])

    def test_missing_level5_implementation_is_recorded_and_does_not_block_other_levels(self):
        step = self.state["levels"]["5"]["steps"]["IMPLEMENT_FUNCTIONAL_GATES"]
        with patch.object(M, "execute", side_effect=RuntimeError("DOMAIN_IMPLEMENTATION_NOT_APPROVED")):
            for s in M.STEPS:
                self.state["levels"]["4"]["steps"][s]["status"] = "BLOCKED"
            for s in M.STEPS[:2]:
                self.state["levels"]["5"]["steps"][s]["status"] = "DONE"
            self.assertTrue(M.once(self.state, self.plan))
        self.assertEqual(step["status"], "BLOCKED")
        self.assertEqual(step["blocker"], "DOMAIN_IMPLEMENTATION_NOT_APPROVED")
        self.assertEqual(M.next_step(self.state), (5, "RUN_REGRESSION_TESTS"))

    def test_source_unavailable_does_not_forge_evidence(self):
        for s in M.STEPS[:1]:
            self.state["levels"]["4"]["steps"][s]["status"] = "DONE"
        with patch.object(M, "execute", side_effect=TimeoutError("registry unavailable")):
            M.once(self.state, self.plan)
            M.once(self.state, self.plan)
        row = self.state["levels"]["4"]["steps"]["COLLECT_ORIGINAL_SOURCE"]
        self.assertEqual(row["status"], "BLOCKED")
        self.assertFalse(row["evidence"]["scientific_signoff"])
        self.assertEqual(M.next_step(self.state), (4, "IMPLEMENT_FUNCTIONAL_GATES"))

    def test_level4_dated_roster_batch_retains_original_source_review_gate(self):
        self.state["levels"]["4"]["steps"]["AUDIT_EXISTING_DRAFTS"]["status"] = "DONE"
        source = self.home / "new-platform/frontend/data/p3PostDataActive.json"
        source.parent.mkdir(parents=True)
        source.write_text(json.dumps({"asOf": "2026-11-10", "records": [
            {"nct": "NCT05507203"}, {"nct": "NCT05507216"}
        ]}), encoding="utf-8")
        batch = {"retrieved": 1, "total": 2, "reports": [
            {"nct": "NCT05507203", "scientific_stage_complete": False},
            {"nct": "NCT05507216", "status": "SOURCE_RETRIEVAL_OR_VALIDATION_BLOCKED"}]}
        with patch.object(M, "ROOT", self.home), patch(
                "level4_scientific_evidence.process_ncts", return_value=batch) as fetch:
            M.once(self.state, self.plan)
        fetch.assert_called_once_with(["NCT05507203", "NCT05507216"])
        row = self.state["levels"]["4"]["steps"]["COLLECT_ORIGINAL_SOURCE"]
        self.assertEqual(row["status"], "DONE")
        self.assertEqual(row["evidence"]["retrieved_original_source_count"], 1)
        self.assertEqual(row["evidence"]["unavailable_or_invalid_count"], 1)
        self.assertEqual(row["evidence"]["snapshot_as_of"], "2026-11-10")
        self.assertFalse(row["evidence"]["current_canonical_focus_verified"])
        self.assertFalse(row["evidence"]["independently_reviewed"])
        self.assertFalse(self.state["levels"]["4"]["scientific_complete"])
        self.assertTrue((self.home / "level4/dated-focus-source-inventory.json").exists())

    def test_reviews_are_not_automatically_approved(self):
        for s in M.STEPS[:-1]:
            self.state["levels"]["4"]["steps"][s]["status"] = "DONE"
        self.assertTrue(M.once(self.state, self.plan))
        row = self.state["levels"]["4"]["steps"]["INDEPENDENT_REVIEW"]
        self.assertEqual(row["blocker"], "PDUFA_LEVEL_ASSESSMENTS_NOT_AVAILABLE")
        self.assertEqual(row["status"], "BLOCKED")
        self.assertEqual(M.next_step(self.state), (5, "AUDIT_EXISTING_DRAFTS"))
        self.assertEqual(M.counts(self.state)["scientifically_completed_levels"], 0)

    def test_regression_test_count_and_retirement_guard(self):
        fake = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="Ran 6 tests in 0.01s"),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="PASS", stderr=""),
        ]
        with patch.object(M, "cmd", side_effect=fake):
            result = M.execute(4, "RUN_REGRESSION_TESTS", self.plan)
        self.assertEqual(result["tests"][0]["passed"], 6)
        self.assertEqual(result["tests"][1]["passed"], True)

    def test_monitor_includes_current_task_last_checkpoint_and_blockers(self):
        self.state["active"] = {"level": 4, "task": "COLLECT_ORIGINAL_SOURCE"}
        self.state["levels"]["4"]["steps"]["AUDIT_EXISTING_DRAFTS"]["status"] = "DONE"
        self.state["levels"]["5"]["steps"]["IMPLEMENT_FUNCTIONAL_GATES"].update(
            status="BLOCKED", blocker="DOMAIN_IMPLEMENTATION_NOT_APPROVED")
        message = M.public_status(self.state)
        self.assertIn("L4 COLLECT_ORIGINAL_SOURCE", message)
        self.assertIn("L04 AUDIT_EXISTING_DRAFTS", message)
        self.assertIn("L05 IMPLEMENT_FUNCTIONAL_GATES", message)
        self.assertIn("Scientific levels independently completed:** 0/17", message)
        self.assertIn("Next approved action:", message)

    def test_persisted_completion_ledger_does_not_rewrite_old_engineering_ledger(self):
        old = self.home / "ledger.json"
        old.write_text('{"completed_scientific_levels":0}', encoding="utf-8")
        M.save(self.state)
        self.assertEqual(json.loads(old.read_text()), {"completed_scientific_levels": 0})
        self.assertEqual(M.load(self.plan)["queue_id"], "PDUFA_LEVEL_COMPLETION_V1")
        self.state["levels"]["4"]["scientific_complete"] = True
        M.save(self.state)
        with self.assertRaises(ValueError):
            M.load(self.plan)

if __name__ == "__main__":
    unittest.main()
