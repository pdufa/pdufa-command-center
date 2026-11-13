"""Runtime diagnostics use real isolated files and never repair worker state."""
from __future__ import annotations

import copy
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pdufa_runtime_status as R


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


class RuntimeStatusTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="pdufa-runtime-status-")
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.root = self.directory / "checkout"
        self.data = self.directory / "worker-state"
        self.root.mkdir()
        self.data.mkdir()
        # A complete small release bundle. Code is fingerprinted, never run.
        self.paths = (
            "scripts/pdufa_runtime_status.py",
            "scripts/pdufa_level_completion.py",
            "scripts/pdufa_engineering_review_lanes.py",
            "scripts/pdufa_strict_level_runner.py",
            "scripts/level7_model_validation_readiness.py",
            "scripts/level7_source_readiness_inventory.py",
            "automation/scientific-level-completion-queue.json",
        )
        self.pins = {}
        for path in self.paths:
            raw = ("# isolated release file: " + path + "\n").encode("utf-8")
            if path.endswith(".json"):
                raw = json.dumps({"schema_version": 1, "levels": []}).encode("utf-8")
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
            self.pins[path] = blob(raw)
        self.installer = self.root / "scripts/windows_pdufa_level6_unblock.ps1"
        self.installer.write_text(
            "$files=@(\n" + "\n".join("  '" + x + "'," for x in self.paths)
            + "\n)\n$allowed=@{\n"
            + "\n".join(" '" + x + "'='" + self.pins[x] + "'" for x in self.paths)
            + "\n}\n", encoding="utf-8")
        self.state = {"levels": {"7": {"steps": {
            step: {"status": "PENDING", "attempts": 0, "blocker": None,
                   "evidence": {}}
            for step in ("AUDIT_EXISTING_DRAFTS", "COLLECT_ORIGINAL_SOURCE",
                         "IMPLEMENT_FUNCTIONAL_GATES", "RUN_REGRESSION_TESTS",
                         "PREPARE_REVIEW_PR", "INDEPENDENT_REVIEW")
        }}}}

    def runtime(self, snapshot=None):
        return R.runtime_version(snapshot or R.capture_runtime(self.root), self.root, self.data)

    def diagnosis(self, runtime=None):
        return R.diagnose(self.state, 7, self.root, self.data, runtime or self.runtime())

    def source_receipts(self):
        path = self.data / "level6/dated-cross-domain-source-gap-inventory.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"level": 6, "total": 32, "retrieved": 32,
                                    "reports": []}), encoding="utf-8")
        return path

    def authorization(self, **changes):
        value = {
            "schema_version": 1,
            "repository": "pdufa/pdufa-command-center",
            "release_commit": "a" * 40,
            "installer_path": "scripts/windows_pdufa_level6_unblock.ps1",
            "installer_git_blob_sha1": blob(self.installer.read_bytes()),
            "approved_pr": 1234,
            "approved_base": "main",
            "approval_verified": True,
            "required_checks_verified": True,
            "source_main_commit": "b" * 40,
            "authorization_verified_at_utc": datetime.now(timezone.utc).isoformat(),
            "files": dict(self.pins),
        }
        value.update(changes)
        (self.data / "reviewed-release-authorization.json").write_text(
            json.dumps(value), encoding="utf-8")
        return value

    def release_service(self, *, pr_changes=None, protection=None, checks=0,
                        comparison="ahead", remote_pin=None):
        """Offline responses from the GitHub read endpoints used by the worker."""
        self.release_calls = []
        approved = {"number": 1234, "state": "MERGED", "isDraft": False,
                    "mergedAt": "2026-11-13T05:00:00Z", "baseRefName": "main",
                    "reviewDecision": "APPROVED", "mergeCommit": {"oid": "a" * 40}}
        approved.update(pr_changes or {})
        branch_policy = {"required_pull_request_reviews": {"required_approving_review_count": 1},
                         "required_status_checks": {"contexts": ["runtime-and-release-tests"]}}
        if protection is not None:
            branch_policy = protection
        entries = [{"type": "blob", "path": path, "sha": sha}
                   for path, sha in self.pins.items()]
        entries.append({"type": "blob", "path": "scripts/windows_pdufa_level6_unblock.ps1",
                        "sha": blob(self.installer.read_bytes())})
        if remote_pin:
            entries[0]["sha"] = remote_pin

        def run(argv, *, timeout):
            self.release_calls.append(list(argv))
            self.assertGreater(timeout, 0)
            if argv[:3] == ["gh", "pr", "checks"]:
                return subprocess.CompletedProcess(argv, checks, "", "")
            if argv[:3] == ["gh", "pr", "view"]:
                self.assertEqual(argv[3], "1234", "historical draft IDs need not stay open")
                value = approved
            elif argv[:2] == ["gh", "api"] and argv[2].endswith("/branches/main/protection"):
                value = branch_policy
            elif argv[:2] == ["gh", "api"] and "/compare/" in argv[2]:
                value = {"status": comparison}
            elif argv[:2] == ["gh", "api"] and "/git/trees/" in argv[2]:
                value = {"truncated": False, "tree": entries}
            else:
                self.fail("unexpected network/mutation command: " + repr(argv))
            return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")

        return run

    def test_missing_installation_is_separate_from_missing_source_and_unrun_tests(self):
        (self.root / "scripts/level7_source_readiness_inventory.py").unlink()
        report = self.diagnosis()
        self.assertEqual(report["installation"]["status"], "MISSING_INSTALLATION")
        self.assertIn("scripts/level7_source_readiness_inventory.py",
                      report["installation"]["missing_files"])
        self.assertEqual(report["source_evidence"]["status"], "SOURCE_EVIDENCE_MISSING")
        self.assertEqual(report["tests"]["status"], "NOT_RUN")

    def test_installed_code_does_not_imply_source_or_test_acceptance(self):
        report = self.diagnosis()
        self.assertEqual(report["installation"]["status"], "INSTALLED_FILES_MATCH")
        self.assertEqual(report["source_evidence"]["status"], "SOURCE_EVIDENCE_MISSING")
        self.assertEqual(report["tests"]["status"], "NOT_RUN")
        self.assertFalse(report["scientific_acceptance"])

    def test_source_receipts_are_explicitly_not_scientific_adjudication(self):
        self.source_receipts()
        report = self.diagnosis()
        self.assertEqual(report["source_evidence"]["status"],
                         "SOURCE_RECEIPTS_PRESENT_NOT_ADJUDICATED")
        self.assertFalse(report["scientific_acceptance"])

    def test_malformed_source_evidence_is_not_reported_present(self):
        self.source_receipts().write_text("{broken", encoding="utf-8")
        self.assertEqual(self.diagnosis()["source_evidence"]["status"],
                         "SOURCE_EVIDENCE_INVALID")

    def test_actual_regression_failure_remains_visible_with_installed_code(self):
        self.source_receipts()
        task = self.state["levels"]["7"]["steps"]["RUN_REGRESSION_TESTS"]
        task.update(status="BLOCKED", attempts=2,
                    blocker="LEVEL7_REGRESSION_OR_RETIREMENT_FAILED")
        before = copy.deepcopy(self.state)
        report = self.diagnosis()
        self.assertEqual(report["installation"]["status"], "INSTALLED_FILES_MATCH")
        self.assertEqual(report["tests"]["status"], "REGRESSION_TESTS_FAILED")
        self.assertIn("LEVEL7_REGRESSION_OR_RETIREMENT_FAILED", report["blocker_codes"])
        self.assertEqual(self.state, before, "diagnosis must not clear failures or attempts")

    def test_exhausted_placeholder_is_not_a_failed_regression(self):
        task = self.state["levels"]["7"]["steps"]["RUN_REGRESSION_TESTS"]
        task.update(status="BLOCKED", attempts=2, blocker="DOMAIN_REGRESSION_SUITE_NOT_APPROVED")
        self.assertEqual(self.diagnosis()["tests"]["status"], "NOT_RUN")

    def test_interrupted_attempt_is_not_reported_as_an_actual_test_failure(self):
        task = self.state["levels"]["7"]["steps"]["RUN_REGRESSION_TESTS"]
        task.update(status="BLOCKED", attempts=2, blocker="INTERRUPTED_PREVIOUS_ATTEMPT")
        before = copy.deepcopy(self.state)
        report = self.diagnosis()
        self.assertEqual(report["tests"]["status"], "NOT_RUN")
        self.assertIn("INTERRUPTED_PREVIOUS_ATTEMPT", report["blocker_codes"])
        self.assertEqual(self.state, before)

    def test_test_success_requires_nonempty_successful_results(self):
        task = self.state["levels"]["7"]["steps"]["RUN_REGRESSION_TESTS"]
        task.update(status="DONE", evidence={"tests": []})
        self.assertEqual(self.diagnosis()["tests"]["status"], "REGRESSION_TESTS_FAILED")
        task["evidence"]["tests"] = [{"suite": "readiness", "passed": 0}]
        self.assertNotEqual(self.diagnosis()["tests"]["status"], "PASSED")
        task["evidence"]["tests"] = [{"suite": "readiness", "passed": 25},
                                     {"suite": "permanent_retirement", "passed": True}]
        self.assertEqual(self.diagnosis()["tests"]["status"], "PASSED")
        self.assertFalse(self.diagnosis()["scientific_acceptance"])

    def test_startup_fingerprint_cannot_be_replaced_by_new_disk_version(self):
        snapshot = R.capture_runtime(self.root)
        path = "scripts/pdufa_engineering_review_lanes.py"
        startup = snapshot["startup_files"][path]
        (self.root / path).write_text("# different release\n", encoding="utf-8")
        runtime = self.runtime(snapshot)
        self.assertEqual(runtime["startup_files"][path], startup)
        self.assertNotEqual(runtime["disk_files"][path], startup)
        self.assertIn(path, runtime["disk_changed_since_start"])
        self.assertEqual(self.diagnosis(runtime)["installation"]["status"], "VERSION_MISMATCH")

    def test_matching_local_authorization_reports_identity_without_science_approval(self):
        self.authorization()
        runtime = self.runtime()
        self.assertEqual(runtime["authorization_status"], "FILES_MATCH_LOCAL_AUTHORIZATION")
        self.assertTrue(runtime["files_match_authorization"])
        self.assertEqual(runtime["release_commit"], "a" * 40)
        self.assertFalse(self.diagnosis(runtime)["scientific_acceptance"])

    def test_authorization_booleans_without_complete_files_cannot_claim_release(self):
        self.authorization(files={})
        runtime = self.runtime()
        self.assertFalse(runtime["files_match_authorization"])
        self.assertIsNone(runtime["release_commit"])

    def test_local_receipt_for_other_repository_is_rejected(self):
        self.authorization(repository="other/project")
        runtime = self.runtime()
        self.assertEqual(runtime["authorization_status"], "INVALID")
        self.assertFalse(runtime["files_match_authorization"])
        self.assertIsNone(runtime["release_commit"])

    def test_malformed_authorization_timestamps_do_not_crash_or_claim_release(self):
        for value in (123, [], ["2026-11-13T05:00:00Z"], None):
            with self.subTest(timestamp=value):
                self.authorization(authorization_verified_at_utc=value)
                runtime = self.runtime()
                self.assertEqual(runtime["authorization_status"], "INVALID")
                self.assertFalse(runtime["files_match_authorization"])
                self.assertIsNone(runtime["release_commit"])

    def test_reviewed_release_requires_online_approval_checks_ancestry_and_exact_blobs(self):
        expected = self.authorization()
        run = self.release_service()
        verified = R.verify_reviewed_release(self.root, self.data, run)
        self.assertEqual(verified, expected)
        self.assertTrue(any(call[:3] == ["gh", "pr", "checks"]
                            for call in self.release_calls))
        self.assertTrue(any("/compare/" in call[2] for call in self.release_calls
                            if call[:2] == ["gh", "api"]))
        self.assertTrue(any("/git/trees/" in call[2] for call in self.release_calls
                            if call[:2] == ["gh", "api"]))
        self.assertNotIn("scientific_signoff", verified)

    def test_reviewed_release_refuses_draft_unapproved_or_wrong_commit_pr(self):
        self.authorization()
        for changes in ({"state": "OPEN", "isDraft": True, "mergedAt": None},
                        {"reviewDecision": "REVIEW_REQUIRED"},
                        {"mergeCommit": {"oid": "c" * 40}},
                        {"baseRefName": "feature/unreviewed"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(
                    RuntimeError, "REVIEWED_RELEASE_AUTHORIZATION_INVALID"):
                R.verify_reviewed_release(self.root, self.data,
                                          self.release_service(pr_changes=changes))

    def test_reviewed_release_refuses_failed_ci_unprotected_main_or_unrelated_history(self):
        self.authorization()
        for kwargs in ({"checks": 1}, {"protection": {}},
                       {"protection": {"required_pull_request_reviews": {
                           "required_approving_review_count": 0},
                           "required_status_checks": {"contexts": ["CI"]}}},
                       {"comparison": "diverged"}, {"comparison": "behind"}):
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(
                    RuntimeError, "REVIEWED_RELEASE_AUTHORIZATION_INVALID"):
                R.verify_reviewed_release(self.root, self.data, self.release_service(**kwargs))

    def test_reviewed_release_refuses_remote_or_local_file_drift(self):
        self.authorization()
        with self.assertRaisesRegex(RuntimeError, "REVIEWED_RELEASE_AUTHORIZATION_INVALID"):
            R.verify_reviewed_release(self.root, self.data,
                                      self.release_service(remote_pin="c" * 40))
        (self.root / "scripts/level7_source_readiness_inventory.py").write_text(
            "# unreviewed local change\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "REVIEWED_RELEASE_AUTHORIZATION_INVALID"):
            R.verify_reviewed_release(self.root, self.data, self.release_service())

    def test_forged_local_approval_flags_cannot_replace_independent_remote_review(self):
        self.authorization(approval_verified=True, required_checks_verified=True)
        run = self.release_service(pr_changes={"reviewDecision": "CHANGES_REQUESTED"})
        with self.assertRaisesRegex(RuntimeError, "REVIEWED_RELEASE_AUTHORIZATION_INVALID"):
            R.verify_reviewed_release(self.root, self.data, run)

    def test_reviewed_install_can_verify_closed_historical_pr_without_rewriting_history(self):
        import pdufa_level_completion as B
        plan = self.root / "automation/scientific-level-completion-queue.json"
        plan.write_bytes((ROOT / "automation/scientific-level-completion-queue.json").read_bytes())
        self.pins["automation/scientific-level-completion-queue.json"] = blob(plan.read_bytes())
        # Refresh the synthetic installer's exact reviewed pin-map after changing its plan.
        body = self.installer.read_text(encoding="utf-8")
        key = "automation/scientific-level-completion-queue.json"
        import re
        body = re.sub("'" + re.escape(key) + "'='[a-f0-9]{40}'",
                      "'" + key + "'='" + self.pins[key] + "'", body)
        self.installer.write_text(body, encoding="utf-8")
        self.authorization()
        self.write_status_inputs({"level": 7,
                                  "updated_utc": datetime.now(timezone.utc).isoformat()})
        before = {p.relative_to(self.data): p.read_bytes()
                  for p in self.data.rglob("*") if p.is_file()}
        with patch.object(B, "ROOT", self.root), patch.object(B, "DATA", self.data), \
                patch.object(B, "PLAN", plan), patch.object(B, "cmd", self.release_service()):
            result = B.confirmed_level7_pr()
            self.assertEqual(result["pr_number"], 1169)
            self.assertEqual(result["reviewed_release_commit"], "a" * 40)
            self.assertFalse(result["scientific_signoff"])
            with self.assertRaisesRegex(RuntimeError, "PR_OUTSIDE_REVIEWED_RELEASE_SCOPE"):
                B.confirmed_pr(987654)
        after = {p.relative_to(self.data): p.read_bytes()
                 for p in self.data.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    def test_bad_reviewed_receipt_does_not_fall_back_to_open_draft_checks(self):
        import pdufa_level_completion as B
        self.authorization(files={})
        run = self.release_service()
        with patch.object(B, "ROOT", self.root), patch.object(B, "DATA", self.data), \
                patch.object(B, "cmd", run):
            with self.assertRaisesRegex(RuntimeError, "REVIEWED_RELEASE_AUTHORIZATION_INVALID"):
                B.confirmed_level7_pr()
        self.assertEqual(self.release_calls, [])

    def test_paths_outside_release_root_are_not_trusted_by_authorization(self):
        outside = self.directory / "outside.py"
        outside.write_text("# not in the release root\n", encoding="utf-8")
        pins = dict(self.pins)
        pins["../outside.py"] = blob(outside.read_bytes())
        self.authorization(files=pins)
        runtime = self.runtime()
        self.assertFalse(runtime["files_match_authorization"])
        self.assertIsNone(runtime["release_commit"])

    @unittest.skipUnless(hasattr(Path, "symlink_to"), "symlinks unavailable")
    def test_symlinked_runtime_module_does_not_match_release(self):
        path = self.root / "scripts/level7_model_validation_readiness.py"
        outside = self.directory / "outside.py"
        outside.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(outside)
        except OSError as exc:
            self.skipTest("symlink creation unavailable: " + str(exc))
        self.authorization()
        runtime = self.runtime()
        self.assertFalse(runtime["files_match_authorization"])
        self.assertIsNone(runtime["release_commit"])
        self.assertNotEqual(self.diagnosis(runtime)["installation"]["status"],
                            "INSTALLED_FILES_MATCH")

    def cli(self):
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/pdufa_runtime_status.py"),
             "--root", str(self.root), "--data-dir", str(self.data)],
            text=True, capture_output=True, timeout=30, check=False)

    def write_status_inputs(self, heartbeat):
        (self.data / "heartbeat.json").write_text(json.dumps(heartbeat), encoding="utf-8")
        (self.data / "level_completion_ledger.json").write_text(
            json.dumps(self.state), encoding="utf-8")
        (self.data / "engineering_lane_ledger.json").write_text(json.dumps({
            "schema_version": 1,
            "engineering_completed_levels": [{"level": 4}, {"level": 5}, {"level": 6}],
        }), encoding="utf-8")
        (self.data / "sequential_level_status.json").write_text(
            '{"accepted_levels": [], "mode": "STRICT_LEVEL_BY_LEVEL"}\n', encoding="utf-8")

    def test_cli_legacy_heartbeat_cannot_claim_the_inspectors_new_version(self):
        self.write_status_inputs({"level": 7, "mode": "ENGINEERING_AWAITING_APPROVED_WORK",
                                  "updated_utc": datetime.now(timezone.utc).isoformat()})
        before = {p.relative_to(self.data): p.read_bytes()
                  for p in self.data.rglob("*") if p.is_file()}
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertIn("inspection_version", report)
        self.assertEqual(report["observed_worker"]["status"], "LEGACY_RUNTIME_UNVERIFIED")
        self.assertNotIn("release_commit", report["observed_worker"],
                         "inspection checkout must not impersonate old running worker")
        after = {p.relative_to(self.data): p.read_bytes()
                 for p in self.data.rglob("*") if p.is_file()}
        self.assertEqual(after, before, "read-only status must preserve every worker file")

    def test_cli_missing_worker_state_reports_absence_without_creating_ledgers(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["observed_worker"]["status"], "HEARTBEAT_MISSING")
        self.assertEqual(list(self.data.iterdir()), [])

    def test_cli_invalid_heartbeat_is_reported_without_replacing_it(self):
        heartbeat = self.data / "heartbeat.json"
        heartbeat.write_bytes(b"{partial-write")
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["observed_worker"]["status"],
                         "INVALID_HEARTBEAT")
        self.assertEqual(heartbeat.read_bytes(), b"{partial-write")

    def test_cli_nonstring_heartbeat_timestamps_are_invalid_and_preserved(self):
        for value in (123, [], ["2026-11-13T05:00:00Z"], None):
            with self.subTest(timestamp=value):
                self.write_status_inputs({"level": 7, "updated_utc": value,
                                          "runtime_version": self.runtime()})
                heartbeat = self.data / "heartbeat.json"
                before = heartbeat.read_bytes()
                result = self.cli()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["observed_worker"]["status"],
                                 "INVALID_HEARTBEAT")
                self.assertEqual(heartbeat.read_bytes(), before)

    def test_cli_malformed_nested_ledgers_are_invalid_without_any_rewrite(self):
        self.write_status_inputs({"level": 7,
                                  "updated_utc": datetime.now(timezone.utc).isoformat()})
        ledger = self.data / "level_completion_ledger.json"
        malformed = (
            {"levels": []},
            {"levels": {"7": []}},
            {"levels": {"7": {"steps": []}}},
            {"levels": {"7": {"steps": {"RUN_REGRESSION_TESTS": []}}}},
            {"levels": {"7": {"steps": {"RUN_REGRESSION_TESTS": {
                "status": "DONE", "evidence": []}}}}},
        )
        for value in malformed:
            with self.subTest(ledger=value):
                ledger.write_text(json.dumps(value), encoding="utf-8")
                before = {p.relative_to(self.data): p.read_bytes()
                          for p in self.data.rglob("*") if p.is_file()}
                result = self.cli()
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(result.stdout)
                self.assertEqual(report["ledger_status"], "LEDGER_INVALID")
                self.assertFalse(report["state_modified"])
                after = {p.relative_to(self.data): p.read_bytes()
                         for p in self.data.rglob("*") if p.is_file()}
                self.assertEqual(after, before)

    def test_failed_startup_remote_check_keeps_pulsing_and_preserves_all_ledgers(self):
        import pdufa_engineering_review_lanes as E
        import pdufa_level_completion as B
        self.write_status_inputs({"level": 7,
                                  "updated_utc": datetime.now(timezone.utc).isoformat()})
        previous = {p.relative_to(self.data): p.read_bytes()
                    for p in self.data.rglob("*") if p.is_file() and p.name != "heartbeat.json"}
        engineering = {"engineering_completed_levels": [{"level": 4}, {"level": 5},
                                                         {"level": 6}]}
        scientific = {"accepted_levels": []}

        class OnePulseEvent:
            def __init__(self):
                self.waits = 0
                self.stopped = False

            def wait(self, timeout):
                self.waits += 1
                return self.stopped or self.waits > 1

            def set(self):
                self.stopped = True

        class SynchronousPulseThread:
            def __init__(self, *, target, daemon):
                self.target = target

            def start(self):
                self.target()

            def join(self, *, timeout):
                pass

        with ExitStack() as stack:
            for obj, values in (
                    (B, {"DATA": self.data, "ROOT": self.root, "STOP": self.data / "STOP",
                         "LOCK": self.data / "RUNNING.lock"}),
                    (E, {"HEARTBEAT": self.data / "heartbeat.json",
                         "RUNTIME_START": R.capture_runtime(self.root)})):
                for name, value in values.items():
                    stack.enter_context(patch.object(obj, name, value))
            stack.enter_context(patch.object(B, "acquire_lock"))
            stack.enter_context(patch.object(B, "plan", return_value={}))
            stack.enter_context(patch.object(B, "load", return_value=self.state))
            stack.enter_context(patch.object(E, "load", return_value=engineering))
            stack.enter_context(patch.object(E.strict, "load_sequence", return_value=scientific))
            stack.enter_context(patch.object(E.threading, "Event", OnePulseEvent))
            stack.enter_context(patch.object(E.threading, "Thread", SynchronousPulseThread))
            stack.enter_context(patch.object(E, "rearm_level7_after_real_implementation",
                                            side_effect=RuntimeError("REVIEWED_RELEASE_AUTHORIZATION_INVALID")))
            pulse = stack.enter_context(patch.object(E, "heartbeat", wraps=E.heartbeat))
            cycle = stack.enter_context(patch.object(E, "cycle"))
            with self.assertRaisesRegex(RuntimeError, "REVIEWED_RELEASE_AUTHORIZATION_INVALID"):
                E.run(once=True)
            self.assertEqual([call.args[4] for call in pulse.call_args_list],
                             ["ENGINEERING_STARTING", "ENGINEERING_STARTING",
                              "ENGINEERING_STARTUP_BLOCKED"])
            cycle.assert_not_called()
        heartbeat = json.loads((self.data / "heartbeat.json").read_text(encoding="utf-8"))
        self.assertEqual(heartbeat["mode"], "ENGINEERING_STARTUP_BLOCKED")
        self.assertEqual(heartbeat["startup_blocker"], "REVIEWED_RELEASE_AUTHORIZATION_INVALID")
        self.assertEqual(heartbeat["level"], 7)
        current = {p.relative_to(self.data): p.read_bytes()
                   for p in self.data.rglob("*") if p.is_file() and p.name != "heartbeat.json"}
        self.assertEqual(current, previous)

    def test_cli_distinguishes_running_old_files_from_new_inspection_checkout(self):
        old_runtime = self.runtime()
        path = "scripts/pdufa_level_completion.py"
        replacement = b"# newer reviewed release\n"
        (self.root / path).write_bytes(replacement)
        old_pin = self.pins[path]
        self.pins[path] = blob(replacement)
        self.installer.write_text(self.installer.read_text(encoding="utf-8").replace(
            "'" + path + "'='" + old_pin + "'",
            "'" + path + "'='" + self.pins[path] + "'"), encoding="utf-8")
        self.write_status_inputs({"level": 7,
                                  "updated_utc": datetime.now(timezone.utc).isoformat(),
                                  "runtime_version": old_runtime})
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["observed_worker"]["status"], "RUNTIME_VERSION_MISMATCH")
        self.assertNotEqual(report["inspection_version"]["startup_files"][path],
                            report["observed_worker"]["runtime_version"]["startup_files"][path])

    def test_cli_does_not_treat_old_runtime_heartbeat_as_fresh(self):
        old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        self.write_status_inputs({"level": 7, "updated_utc": old,
                                  "runtime_version": self.runtime()})
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["observed_worker"]["status"],
                         "HEARTBEAT_STALE")


if __name__ == "__main__":
    unittest.main()
