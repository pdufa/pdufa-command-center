"""Offline regression tests for owner-approved, perpetual PDUFA worker follow-on."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import windows_local_agent_followon as F

SPEC = importlib.util.spec_from_file_location(
    "pdufa_continuous_followon_driver", ROOT / "scripts/windows_local_agent_continuous.py"
)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ContinuousFollowonTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        for attr, value in {
            "DATA": self.home / "data",
            "WORKTREES": self.home / "worktrees",
            "STATE_FILE": self.home / "data/ledger.json",
            "HEARTBEAT": self.home / "data/heartbeat.json",
            "STOP_FILE": self.home / "data/STOP",
            "LOCK_FILE": self.home / "data/RUNNING.lock",
        }.items():
            p = patch.object(M, attr, value)
            p.start()
            self.addCleanup(p.stop)
        self.levels = M.manifest()
        self.state = M.initial_ledger(self.levels)

    def finish_initial_queue(self):
        for n in M.LEVELS:
            row = self.state["tasks"][str(n)]
            row["status"] = "DRAFT_PR_CREATED"
            row["attempts"] = 1
            row["draft_pr"] = (
                "https://github.com/pdufa/pdufa-command-center/pull/" + str(1100 + n)
            )

    def test_followon_is_a_distinct_17_stage_queue_without_rewriting_old_drafts(self):
        self.finish_initial_queue()
        before = json.loads(json.dumps(self.state["tasks"]))
        self.assertTrue(F.ensure_jobs(self.state))
        self.assertFalse(F.ensure_jobs(self.state))
        self.assertEqual(self.state["tasks"], before)
        self.assertEqual(F.counts(self.state)["pending"], 17)
        self.assertEqual(F.select_job(self.state), 4)
        self.assertEqual(F.counts(self.state)["completed"], 0)
        self.assertEqual(self.state["completed_scientific_levels"], 0)

    def test_finished_jobs_remain_finished_across_ledger_restart(self):
        F.ensure_jobs(self.state)
        row = self.state["validation_jobs"]["4"]
        row.update(status="DRAFT_PR_CREATED", attempts=1,
                   draft_pr="https://github.com/pdufa/pdufa-command-center/pull/2001")
        M.save_ledger(self.state)
        loaded = M.load_ledger(self.levels)
        self.assertFalse(F.ensure_jobs(loaded))
        self.assertEqual(F.select_job(loaded), 5)
        self.assertEqual(F.counts(loaded)["completed"], 1)
        self.assertFalse(loaded["validation_jobs"]["4"]["scientific_stage_complete"])

    def test_corrupt_backlog_fail_closed(self):
        F.ensure_jobs(self.state)
        self.state["validation_jobs"]["4"]["kind"] = "AUTO_MERGE"
        with self.assertRaises(ValueError):
            F.ensure_jobs(self.state)
        self.assertEqual(self.state["completed_scientific_levels"], 0)

    def test_interrupted_followon_is_retried_at_most_twice(self):
        F.ensure_jobs(self.state)
        row = self.state["validation_jobs"]["4"]
        row.update(status="RUNNING", attempts=1)
        self.assertEqual(F.select_job(self.state), 4)
        self.assertEqual(row["status"], "PENDING")
        row.update(status="RUNNING", attempts=2)
        self.assertEqual(F.select_job(self.state), 5)
        self.assertEqual(row["status"], "BLOCKED")

    def test_trusted_metadata_source_is_valid_python_without_prediction(self):
        source, tests = F.render(7, self.levels[6]["name"], M.SCOPES[7])
        ast.parse(source)
        ast.parse(tests)
        scope = {}
        exec(compile(source, "<trusted-validation-template>", "exec"), scope)
        result = scope["inspect_metadata"]({
            "nct": "NCT00000001", "trial_phase": 1,
            "knowledge_cutoff": "2026-01-01", "source_metadata": {},
        })
        self.assertEqual(set(result["missing_receipts"]), set(M.SCOPES[7]))
        self.assertFalse(result["source_facts_independently_verified"])
        self.assertFalse(result["scientific_stage_complete"])
        self.assertIsNone(result["approval_probability"])
        self.assertIsNone(result["clinical_score"])

    def test_generated_offline_synthetic_tests_run_cleanly(self):
        source, tests = F.render(4, self.levels[3]["name"], M.SCOPES[4])
        out, checks = F.paths(4)
        root = self.home / "isolated"
        (root / out).parent.mkdir(parents=True)
        (root / checks).parent.mkdir(parents=True)
        (root / out).write_text(source, encoding="utf-8")
        (root / checks).write_text(tests, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-B", "-I", "-m", "unittest", "discover",
             "-s", "tests/continuous_provenance", "-p", Path(checks).name, "-v"],
            cwd=root, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        self.assertIn("Ran 4 tests", result.stderr)

    def test_followon_creates_review_draft_not_scientific_signoff(self):
        F.ensure_jobs(self.state)
        with patch.object(F, "create_review_pr", return_value=(
            "https://github.com/pdufa/pdufa-command-center/pull/2001"
        )) as created:
            self.assertTrue(F.one_attempt(M, self.state, 4, self.levels))
        created.assert_called_once()
        self.assertEqual(self.state["validation_jobs"]["4"]["status"], "DRAFT_PR_CREATED")
        self.assertFalse(self.state["validation_jobs"]["4"]["scientific_stage_complete"])
        self.assertEqual(self.state["completed_scientific_levels"], 0)
        self.assertFalse(self.state["production_modified"])

    def test_worker_advances_to_followon_then_honors_manual_stop(self):
        self.finish_initial_queue()
        M.save_ledger(self.state)
        def fake_next(core, state, level, levels):
            self.assertEqual(level, 4)
            M.STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
            M.STOP_FILE.write_text("STOP REQUESTED\n", encoding="utf-8")
            return False
        with (patch.object(M, "preflight"),
              patch.object(M, "acquire_lock", return_value=1234),
              patch.object(M, "publish_status"),
              patch.object(F, "one_attempt", side_effect=fake_next) as followon_attempt):
            self.assertEqual(M.worker(pilot=False), 0)
        followon_attempt.assert_called_once()
        latest = M.load_ledger(self.levels)
        self.assertEqual(F.counts(latest)["pending"], 17)
        self.assertEqual(M.summarize(latest)["draft_prs_created"], 17)

    def test_exhausted_worker_stays_live_and_idle_instead_of_exiting(self):
        self.finish_initial_queue()
        F.ensure_jobs(self.state)
        for n in M.LEVELS:
            row = self.state["validation_jobs"][str(n)]
            row.update(status="DRAFT_PR_CREATED", attempts=1,
                       draft_pr="https://github.com/pdufa/pdufa-command-center/pull/"
                                + str(2000 + n))
        M.save_ledger(self.state)
        calls = []
        def one_sleep(seconds):
            calls.append(seconds)
            M.STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
            M.STOP_FILE.write_text("STOP REQUESTED\n", encoding="utf-8")
        with (patch.object(M, "preflight"), patch.object(M, "acquire_lock",
                  return_value=1234), patch.object(M, "publish_status"),
              patch.object(M.time, "sleep", side_effect=one_sleep)):
            with redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(M.worker(pilot=False), 0)
        self.assertIn("CONTINUOUS_IDLE", stream.getvalue())
        self.assertEqual(calls, [10])
        h = json.loads(M.HEARTBEAT.read_text(encoding="utf-8"))
        self.assertEqual(h["mode"], "STOPPED")
        self.assertEqual(F.counts(self.state)["pending"], 0)


if __name__ == "__main__":
    unittest.main()
