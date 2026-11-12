"""Offline continuous coding-worker orchestration and draft PR safety tests."""
from __future__ import annotations

import ast
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SCRIPT = ROOT / "scripts/windows_local_agent_continuous.py"
SPEC = importlib.util.spec_from_file_location("pdufa_continuous_engine", SCRIPT)
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class ContinuousWorkerSafetyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        for key, value in {
            "DATA": self.home / "data",
            "WORKTREES": self.home / "worktrees",
            "STATE_FILE": self.home / "data/ledger.json",
            "HEARTBEAT": self.home / "data/heartbeat.json",
            "STOP_FILE": self.home / "data/STOP",
            "LOCK_FILE": self.home / "data/RUNNING.lock",
        }.items():
            patcher = patch.object(M, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.levels = M.manifest()
        self.state = M.initial_ledger(self.levels)

    def questions(self):
        return [
            "Which original trial design source was available at the cutoff?",
            "How were the endpoints and analysis protocol described?",
            "Which contradictory sources were independently considered?",
            "What gaps prevent an independent scientific conclusion?",
        ]

    def test_manifest_limits_to_owner_levels_four_through_twenty(self):
        self.assertEqual(M.LEVELS, tuple(range(4, 21)))
        self.assertEqual(len(self.levels), 20)
        self.assertEqual(set(M.SCOPES), set(M.LEVELS))
        self.assertEqual(self.levels[3]["name"], "Experimental and Statistical Validation")

    def test_ledger_initial_state_never_claims_scientific_completion(self):
        counts = M.summarize(self.state)
        self.assertEqual(counts["draft_prs_created"], 0)
        self.assertEqual(counts["pending"], 17)
        self.assertEqual(counts["scientific_stages_complete"], 0)
        self.assertFalse(counts["production_modified"])
        self.assertTrue(all(
            row["scientific_stage_complete"] is False
            for row in self.state["tasks"].values()
        ))

    def test_run_immediately_next_independent_stage_after_draft(self):
        self.assertEqual(M.select_task(self.state), 4)
        self.state["tasks"]["4"]["status"] = "DRAFT_PR_CREATED"
        self.assertEqual(M.select_task(self.state), 5)

    def test_blocked_level_is_skipped_not_automatically_signed_off(self):
        self.state["tasks"]["4"]["status"] = "BLOCKED"
        self.state["tasks"]["4"]["attempts"] = 2
        self.assertEqual(M.select_task(self.state), 5)
        self.assertEqual(M.summarize(self.state)["blocked"], 1)
        self.assertFalse(self.state["tasks"]["4"]["scientific_stage_complete"])

    def test_interrupted_task_retries_only_within_limit(self):
        self.state["tasks"]["4"]["status"] = "RUNNING"
        self.state["tasks"]["4"]["attempts"] = 1
        self.assertEqual(M.select_task(self.state), 4)
        self.assertEqual(self.state["tasks"]["4"]["status"], "PENDING")
        self.state["tasks"]["4"]["status"] = "RUNNING"
        self.state["tasks"]["4"]["attempts"] = 2
        self.assertEqual(M.select_task(self.state), 5)
        self.assertEqual(self.state["tasks"]["4"]["status"], "BLOCKED")

    def test_schema_corruption_fails_closed(self):
        M.save_ledger(self.state)
        self.assertEqual(M.load_ledger(self.levels)["schema_version"], 1)
        modified = M.load_ledger(self.levels)
        modified["completed_scientific_levels"] = 17
        M.atomic_json(M.STATE_FILE, modified)
        with self.assertRaises(ValueError):
            M.load_ledger(self.levels)

    def test_trusted_generated_source_is_review_only(self):
        code, tests = M.render(4, self.levels[3]["name"], M.SCOPES[4], self.questions())
        ast.parse(code)
        ast.parse(tests)
        scope = {}
        exec(compile(code, "<trusted-local-template>", "exec"), scope)
        result = scope["assess"]({"nct": "NCT00000001", "evidence_fields": {}})
        self.assertFalse(result["scientific_stage_complete"])
        self.assertFalse(result["source_facts_independently_verified"])
        self.assertIsNone(result["approval_probability"])
        self.assertIsNone(result["clinical_score"])
        self.assertEqual(set(result["missing_source_fields"]), set(M.SCOPES[4]))
        fully_populated = scope["assess"]({
            "nct": "NCT00000001",
            "evidence_fields": {k: "Unverified link" for k in M.SCOPES[4]},
        })
        self.assertEqual(fully_populated["missing_source_fields"], [])
        self.assertFalse(fully_populated["scientific_stage_complete"])

    def test_generated_tests_execute_on_trusted_template_in_temp_dir(self):
        source, tests = M.render(5, self.levels[4]["name"], M.SCOPES[5], self.questions())
        scripts, checks = M.stage_paths(5)
        root = self.home / "repo"
        (root / scripts).parent.mkdir(parents=True)
        (root / checks).parent.mkdir(parents=True)
        (root / scripts).write_text(source, encoding="utf-8")
        (root / checks).write_text(tests, encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-B", "-I", "-m", "unittest", "discover",
             "-s", "tests/continuous_stage_drafts", "-p", Path(checks).name, "-v"],
            cwd=root, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-1500:])
        self.assertIn("Ran 4 tests", result.stderr)

    def test_model_output_is_json_questions_only(self):
        class Response:
            def __enter__(self):
                return io.BytesIO(json.dumps({
                    "response": json.dumps({"review_questions": self_questions})
                }).encode("utf-8"))
            def __exit__(self, *_):
                return False
        self_questions = self.questions()
        with patch.object(M.urllib.request, "urlopen", return_value=Response()):
            q = M.review_questions(4, self.levels[3]["name"], M.SCOPES[4])
        self.assertEqual(q, self_questions)

    def test_model_malformed_or_unsafe_response_rejected(self):
        bad_samples = [
            json.dumps({"review_questions": ["Short"] * 4}),
            json.dumps({"review_questions": [q + "\nBAD" for q in self.questions()]}),
            json.dumps({"review_questions": [q + "Z" * 500 for q in self.questions()]}),
            "{}",
        ]
        for bad in bad_samples:
            with self.subTest(sample=bad[:25]):
                class Response:
                    def __enter__(self):
                        return io.BytesIO(json.dumps({"response": bad}).encode())
                    def __exit__(self, *_):
                        return False
                with patch.object(M.urllib.request, "urlopen", return_value=Response()):
                    with self.assertRaises(ValueError):
                        M.review_questions(4, "Experimental and Statistical Validation", M.SCOPES[4])

    def test_no_model_generated_source_is_directly_executed(self):
        code, tests = M.render(6, self.levels[5]["name"], M.SCOPES[6], self.questions())
        self.assertNotIn("subprocess", code)
        self.assertNotIn("urllib", code)
        self.assertNotIn("exec(", code)
        self.assertNotIn("eval(", code)
        self.assertNotIn("clinical_signoff = True", code)
        self.assertIn("scientific_stage_complete", code)

    def test_failed_task_retries_twice_then_independent_next_stage(self):
        with (patch.object(M, "review_questions", side_effect=ValueError("MODEL_QUESTIONS_NOT_VALIDATED")),
              patch.object(M, "heartbeat")):
            self.assertFalse(M.one_attempt(self.state, 4, self.levels))
            self.assertEqual(self.state["tasks"]["4"]["status"], "PENDING")
            self.assertFalse(M.one_attempt(self.state, 4, self.levels))
        self.assertEqual(self.state["tasks"]["4"]["status"], "BLOCKED")
        self.assertEqual(self.state["tasks"]["4"]["attempts"], 2)
        self.assertEqual(M.select_task(self.state), 5)

    def test_success_requires_draft_pr_url_to_enter_ledger(self):
        with (patch.object(M, "review_questions", return_value=self.questions()),
              patch.object(M, "create_review_pr", return_value="https://github.com/pdufa/pdufa-command-center/pull/123"),
              patch.object(M, "heartbeat")):
            self.assertTrue(M.one_attempt(self.state, 4, self.levels))
        task = self.state["tasks"]["4"]
        self.assertEqual(task["status"], "DRAFT_PR_CREATED")
        self.assertIn("/pull/123", task["draft_pr"])
        self.assertFalse(task["scientific_stage_complete"])
        self.assertEqual(M.select_task(self.state), 5)

    def test_code_change_pipeline_only_pushes_scoped_branch_and_draft_pr(self):
        calls = []
        source, tests = M.render(4, self.levels[3]["name"], M.SCOPES[4], self.questions())
        paths = M.stage_paths(4)
        def mock_cmd(args, *, cwd=M.ROOT, timeout=180):
            calls.append(tuple(args))
            if args[:3] == ["git", "worktree", "add"]:
                Path(args[5]).mkdir(parents=True, exist_ok=True)
            out = ""
            if args[:4] == ["git", "diff", "--cached", "--name-only"]:
                out = "\n".join(paths) + "\n"
            if args[:4] == ["gh", "pr", "view", args[3]]:
                out = json.dumps({
                    "isDraft": True,
                    "url": "https://github.com/pdufa/pdufa-command-center/pull/999",
                    "baseRefName": "main",
                    "headRefName": args[3],
                })
            err = ""
            if "-m" in args and "unittest" in args:
                err = "Ran 4 tests in 0.001s\nOK"
            return subprocess.CompletedProcess(args, 0, stdout=out, stderr=err)
        with patch.object(M, "cmd", side_effect=mock_cmd):
            url = M.create_review_pr(4, self.levels[3]["name"], source, tests)
        self.assertEqual(url, "https://github.com/pdufa/pdufa-command-center/pull/999")
        self.assertTrue(any(x[:3] == ("gh", "pr", "create") and "--draft" in x for x in calls))
        self.assertTrue(any(x[:3] == ("git", "worktree", "add") for x in calls))
        self.assertFalse(any("merge" in x or "deploy" in x for c in calls for x in c))
        self.assertTrue(all(x.startswith(("scripts/continuous_stage_drafts/", "tests/continuous_stage_drafts/"))
                            for x in paths))

    def test_stop_control_blocks_worker_even_before_pilot(self):
        M.STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
        M.STOP_FILE.write_text("stop", encoding="utf-8")
        self.assertEqual(M.worker(pilot=True), 2)
        self.assertFalse(M.LOCK_FILE.exists())

    def test_real_repo_self_test_is_safe_and_has_no_network(self):
        self.assertEqual(M.self_test(), 0)


if __name__ == "__main__":
    unittest.main()
