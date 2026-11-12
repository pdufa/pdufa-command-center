"""Offline continuous coding-worker orchestration and draft PR safety tests."""
from __future__ import annotations

import ast
from datetime import datetime, timedelta, timezone
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
                    "baseRefName": M.REVIEW_BASE,
                    "headRefName": args[3],
                })
            err = ""
            if "-m" in args and "unittest" in args:
                err = "Ran 4 tests in 0.001s\nOK"
            return subprocess.CompletedProcess(args, 0, stdout=out, stderr=err)
        with patch.object(M, "cmd", side_effect=mock_cmd):
            url = M.create_review_pr(4, self.levels[3]["name"], source, tests)
        self.assertEqual(url, "https://github.com/pdufa/pdufa-command-center/pull/999")
        self.assertTrue(any(x[:3] == ("gh", "pr", "create") and "--draft" in x
                            and x[x.index("--base") + 1] == M.REVIEW_BASE for x in calls))
        self.assertTrue(any(x[:3] == ("git", "fetch", "--no-tags")
                            and "refs/heads/" + M.REVIEW_BASE in x[-1] for x in calls))
        self.assertTrue(any(x[:3] == ("git", "worktree", "add")
                            and x[-1] == "origin/" + M.REVIEW_BASE for x in calls))
        self.assertFalse(any(x[:3] == ("git", "worktree", "add")
                             and x[-1] == "origin/main" for x in calls))
        self.assertTrue(any(x[:3] == ("git", "worktree", "add") for x in calls))
        self.assertFalse(any(c[:3] == ("gh", "pr", "merge") for c in calls))
        self.assertFalse(any(c[:2] == ("git", "merge") for c in calls))
        self.assertFalse(any(c[:2] == ("git", "checkout") and "main" in c for c in calls))
        self.assertFalse(any(c and c[0] in ("vercel", "render", "kubectl") for c in calls))
        self.assertTrue(all(x.startswith(("scripts/continuous_stage_drafts/", "tests/continuous_stage_drafts/"))
                            for x in paths))

    def test_retirement_audit_failure_in_isolated_base_blocks_push_and_pr(self):
        calls = []
        source, tests = M.render(4, self.levels[3]["name"], M.SCOPES[4], self.questions())
        def mock_cmd(args, *, cwd=M.ROOT, timeout=180):
            calls.append(tuple(args))
            if args[:3] == ["git", "worktree", "add"]:
                Path(args[5]).mkdir(parents=True, exist_ok=True)
            if args[:3] == [sys.executable, "-B", "scripts/audit_raas_retirement.py"]:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        with patch.object(M, "cmd", side_effect=mock_cmd):
            with self.assertRaisesRegex(RuntimeError, "REVIEW_BASE_RETIREMENT_POLICY_FAILED"):
                M.create_review_pr(4, self.levels[3]["name"], source, tests)
        self.assertFalse(any(x[:3] == ("gh", "pr", "create") for x in calls))
        self.assertFalse(any("push" in x for x in calls))
        self.assertFalse(any("merge" in x for x in calls))
        self.assertTrue(any(x[:3] == ("git", "worktree", "remove") for x in calls))

    def test_failed_pilot_cleanup_removes_temporary_checkout(self):
        calls = []
        source, tests = M.render(4, self.levels[3]["name"], M.SCOPES[4], self.questions())
        def mock_cmd(args, *, cwd=M.ROOT, timeout=180):
            calls.append(tuple(args))
            if args[:3] == ["git", "worktree", "add"]:
                Path(args[5]).mkdir(parents=True, exist_ok=True)
            if args[:3] == [sys.executable, "-B", "scripts/audit_raas_retirement.py"]:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        with patch.object(M, "cmd", side_effect=mock_cmd):
            with self.assertRaisesRegex(RuntimeError, "REVIEW_BASE_RETIREMENT_POLICY_FAILED"):
                M.create_review_pr(4, self.levels[3]["name"], source, tests)
        self.assertTrue(any(x[:3] == ("git", "worktree", "remove")
                            and "--force" in x for x in calls))
        self.assertFalse(any(x[:3] == ("gh", "pr", "create") for x in calls))

    def test_base_check_runs_clean_audit_without_stage_attempt(self):
        calls = []
        def mock_cmd(args, *, cwd=M.ROOT, timeout=180):
            calls.append(tuple(args))
            if args[:4] == ["git", "worktree", "add", "--detach"]:
                Path(args[4]).mkdir(parents=True, exist_ok=True)
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        with patch.object(M, "cmd", side_effect=mock_cmd):
            M.verify_review_base()
        self.assertTrue(any(x[:4] == ("git", "worktree", "add", "--detach")
                            and x[-1] == "origin/" + M.REVIEW_BASE for x in calls))
        self.assertTrue(any(x[:3] == ("git", "worktree", "remove") for x in calls))
        self.assertFalse(M.STATE_FILE.exists())
        self.assertFalse(any("push" in x or "merge" in x for x in calls))

    def test_base_check_failure_cleans_worktree_without_attempting_pilot(self):
        calls = []
        def mock_cmd(args, *, cwd=M.ROOT, timeout=180):
            calls.append(tuple(args))
            if args[:4] == ["git", "worktree", "add", "--detach"]:
                Path(args[4]).mkdir(parents=True, exist_ok=True)
            if args[:3] == [sys.executable, "-B", "scripts/audit_raas_retirement.py"]:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        with patch.object(M, "cmd", side_effect=mock_cmd):
            with self.assertRaisesRegex(RuntimeError, "REVIEW_BASE_RETIREMENT_POLICY_FAILED"):
                M.verify_review_base()
        self.assertTrue(any(x[:3] == ("git", "worktree", "remove") for x in calls))
        self.assertFalse(M.STATE_FILE.exists())
        self.assertFalse(any(x[:3] == ("gh", "pr", "create") for x in calls))

    def test_stop_control_blocks_worker_even_before_pilot(self):
        M.STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
        M.STOP_FILE.write_text("stop", encoding="utf-8")
        self.assertEqual(M.worker(pilot=True), 2)
        self.assertFalse(M.LOCK_FILE.exists())

    def test_active_worker_lock_blocks_parallel_workers(self):
        M.LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        M.LOCK_FILE.write_text(json.dumps({
            "pid": 12345,
            "started_utc": (datetime.now(timezone.utc) - timedelta(minutes=4)).isoformat(),
        }), encoding="utf-8")
        with patch.object(M, "process_alive", return_value=True):
            with self.assertRaises(FileExistsError):
                M.acquire_lock()
        self.assertTrue(M.LOCK_FILE.exists())

    def test_dead_worker_lock_can_recover_on_windows_restart(self):
        M.LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        M.LOCK_FILE.write_text(json.dumps({
            "pid": 12345,
            "started_utc": (datetime.now(timezone.utc) - timedelta(minutes=4)).isoformat(),
        }), encoding="utf-8")
        with patch.object(M, "process_alive", return_value=False):
            self.assertEqual(M.acquire_lock(), M.os.getpid())
        new_lock = json.loads(M.LOCK_FILE.read_text(encoding="utf-8"))
        self.assertEqual(new_lock["pid"], M.os.getpid())

    def test_pilot_blocker_redacts_diagnostic_output(self):
        self.assertEqual(M.public_blocker({"blocker": "MODEL_QUESTIONS_NOT_VALIDATED"}),
                         "MODEL_QUESTIONS_NOT_VALIDATED")
        self.assertEqual(M.public_blocker({"blocker": "password=not-safe"}),
                         "UNCLASSIFIED_LOCAL_FAILURE")
        self.assertEqual(M.public_blocker({"blocker": None}), "NONE_RECORDED")

    def test_pilot_rejects_stage_five_substitution_when_stage_four_blocked(self):
        self.state["tasks"]["4"]["status"] = "BLOCKED"
        self.state["tasks"]["4"]["attempts"] = 2
        self.state["tasks"]["4"]["blocker"] = "MODEL_QUESTIONS_NOT_VALIDATED"
        M.save_ledger(self.state)
        with (patch.object(M, "preflight"),
              patch.object(M, "acquire_lock", return_value=123),
              patch.object(M, "one_attempt", side_effect=AssertionError("unexpected stage"))):
            self.assertEqual(M.worker(pilot=True), 2)
        current = M.load_ledger(self.levels)
        self.assertEqual(current["tasks"]["5"]["attempts"], 0)
        self.assertEqual(current["tasks"]["4"]["status"], "BLOCKED")

    def test_status_prints_sanitized_blocker_without_raw_secrets(self):
        self.state["tasks"]["4"]["blocker"] = "GITHUB_AUTH_FAILED"
        self.state["tasks"]["4"]["attempts"] = 1
        M.save_ledger(self.state)
        from contextlib import redirect_stdout
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(M.status(), 0)
        self.assertIn("Stage 4 status:", stream.getvalue())
        self.assertIn("blocker: GITHUB_AUTH_FAILED", stream.getvalue())

    def test_real_repo_self_test_is_safe_and_has_no_network(self):
        self.assertEqual(M.self_test(), 0)


if __name__ == "__main__":
    unittest.main()
