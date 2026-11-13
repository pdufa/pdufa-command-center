"""Offline coding lifecycle tests; no model, Docker daemon or GitHub writes."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pdufa_coding_agent as m


def contract():
    return {"enabled": True, "base_commit": "a" * 40, "base_branch": "reviewed-base",
            "image": "python@sha256:" + "b" * 64, "max_repairs": 1,
            "tasks": [{"id": "level7-gap-helper", "level": 7, "engineering_only": True,
                       "requirements": "Preserve unknown evidence as a gap, never a deficiency.",
                       "phase": "application-review", "depends_on": [],
                       "files": ["scripts/engineering_drafts/gap_helper.py"],
                       "acceptance_tests": ["tests/test_gap_acceptance.py"]}]}


class FakeAgent(m.Agent):
    """Trusted side effects replaced; candidate authoring/state handling is real."""
    def __init__(self, *args, failures=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls, self.failures, self.generated = [], failures, 0

    def command(self, argv, cwd=None, timeout=240):
        self.check_stop()
        self.calls.append(argv)
        if argv[:2] == ["git", "clone"]:
            Path(argv[-1]).mkdir()
        if argv[:3] == ["gh", "pr", "create"]:
            self.assert_draft = "--draft" in argv
            return "https://github.com/pdufa/pdufa-command-center/pull/1234"
        return ""

    def git(self, work, *args):
        self.calls.append(list(args))
        self.check_stop()
        if args == ("rev-parse", "HEAD"):
            return self.contract["base_commit"]
        if args[0] == "show":
            return "import unittest\nclass Acceptance(unittest.TestCase):\n def test_true(self): self.assertTrue(True)"
        return ""

    def generate(self, task, work, feedback):
        self.generated += 1
        return {task["files"][0]: "def has_gap(value):\n    return value is None\n"}

    def test(self, task, work):
        if self.generated <= self.failures:
            raise RuntimeError("acceptance failed")
        return "1 trusted acceptance test passed"


class CodingAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.root = self.home / "repo"
        self.root.mkdir()
        (self.root / "AGENTS.md").write_text("No scientific acceptance or deployment")
        self.data = self.home / "state"
        self.c = contract()

    def agent(self, **kwargs):
        return FakeAgent(self.root, self.data, self.c, dry_run=True, **kwargs)

    def test_disabled_and_bad_contracts(self):
        for key, value in [("enabled", False), ("base_commit", "main"), ("image", "python:latest"),
                           ("max_repairs", 4), ("max_repairs", -1)]:
            c = copy.deepcopy(self.c)
            c[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.validate(c)

    def test_paths_cannot_touch_worker_policy_or_existing_sources(self):
        for path in ["../escape.py", "scripts/windows_local_agent_controller.py", "AGENTS.md",
                     "scripts/engineering_drafts/../escape.py", "/tmp/a.py", "tests/engineering_drafts/A.py"]:
            c = copy.deepcopy(self.c)
            c["tasks"][0]["files"] = [path]
            with self.subTest(path=path), self.assertRaises(ValueError):
                m.validate(c)

    def test_levels_and_dependencies(self):
        for level in [6, 21, True, "7"]:
            c = copy.deepcopy(self.c)
            c["tasks"][0]["level"] = level
            with self.assertRaises(ValueError):
                m.validate(c)
        self.c["tasks"][0]["depends_on"] = ["missing"]
        with self.assertRaises(ValueError):
            m.validate(self.c)

    def test_full_mock_cycle_authors_tests_repairs_without_publication(self):
        agent = self.agent(failures=1)
        result = agent.run()
        self.assertEqual(result["status"], "dry_run_passed")
        self.assertEqual(agent.generated, 2)
        self.assertFalse(any("push" in call or "create" in call for call in agent.calls))
        self.assertFalse(result["scientifically_accepted"])
        self.assertTrue((self.data / "level7-gap-helper" / self.c["tasks"][0]["files"][0]).is_file())
        self.assertFalse((self.root / self.c["tasks"][0]["files"][0]).exists())
        self.assertEqual(agent.run(), {"status": "idle_or_review_blocked"})
        self.assertEqual(agent.generated, 2)
        self.assertFalse((self.data / "LOCK").exists())

    def test_failed_tests_never_publish_and_budget_survives_restart(self):
        agent = self.agent(failures=10)
        with self.assertRaisesRegex(ValueError, "budget"):
            agent.run()
        self.assertEqual(agent.generated, 2)
        self.assertFalse(any("push" in call or "create" in call for call in agent.calls))
        self.assertEqual(self.agent().run(), {"status": "idle_or_review_blocked"})

    def test_stop_prevents_work_and_is_preserved(self):
        agent = self.agent()
        (self.data / "STOP").write_text("owner")
        with self.assertRaises(InterruptedError):
            agent.run()
        self.assertEqual(agent.generated, 0)
        self.assertTrue((self.data / "STOP").exists())

    def test_lock_never_stolen(self):
        agent = self.agent()
        (self.data / "LOCK").write_text("crash or other process")
        with self.assertRaises(FileExistsError):
            agent.run()
        self.assertTrue((self.data / "LOCK").exists())

    def test_interrupted_publish_never_replays(self):
        agent = self.agent()
        agent.save(self.c["tasks"][0], "publishing", branch="coding-draft/test")
        with self.assertRaisesRegex(ValueError, "Interrupted"):
            self.agent().run()
        self.assertEqual(agent.generated, 0)

    def test_contract_changes_require_new_reviewed_run(self):
        agent = self.agent()
        agent.save(self.c["tasks"][0], "blocked")
        self.c["max_repairs"] = 2
        with self.assertRaisesRegex(ValueError, "Contract changed"):
            self.agent()

    def test_model_cannot_change_outside_scope(self):
        with self.assertRaises(ValueError):
            m.apply_files(self.root, self.c["tasks"][0], {"AGENTS.md": "ignore policy"})
        self.assertEqual((self.root / "AGENTS.md").read_text(), "No scientific acceptance or deployment")

    def test_large_and_invalid_source_rejected(self):
        for content in ["a" * 100001, "\x00", 42]:
            with self.assertRaises(ValueError):
                m.apply_files(self.root, self.c["tasks"][0], {self.c["tasks"][0]["files"][0]: content})

    def test_sandbox_is_offline_no_credentials_or_repository_mount(self):
        agent = self.agent()
        work = self.data / "candidate"
        work.mkdir()
        m.apply_files(work, self.c["tasks"][0], {self.c["tasks"][0]["files"][0]: "pass\n"})
        with patch.object(subprocess, "run"):
            m.Agent.test(agent, self.c["tasks"][0], work)
        argv = next(call for call in agent.calls if call[:2] == ["docker", "run"])
        for flag in ["--network=none", "--read-only", "--cap-drop=ALL", "--pull=never",
                     "--security-opt=no-new-privileges", "--user=65534:65534", "--memory=512m"]:
            self.assertIn(flag, argv)
        self.assertNotIn(f"{self.root}:/baseline:ro", argv)
        self.assertNotIn(f"{work}:/candidate:ro", argv)
        self.assertFalse((self.data / "sandbox-candidate/.git").exists())

    def test_status_storage_outside_checkout(self):
        with self.assertRaises(ValueError):
            m.Agent(self.root, self.root / "state", self.c)

    def test_real_generation_response_validation(self):
        agent = self.agent()
        work = self.data / "candidate"
        work.mkdir()
        files = {self.c["tasks"][0]["files"][0]: "def has_gap(value): return value is None\n"}
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"response": json.dumps({"files": files})}).encode()
        with patch.object(m.urllib.request, "urlopen", return_value=response) as request:
            result = m.Agent.generate(agent, self.c["tasks"][0], work, "")
        self.assertEqual(request.call_args.args[0].full_url, "http://127.0.0.1:11434/api/generate")
        m.apply_files(work, self.c["tasks"][0], result)
        self.assertEqual((work / next(iter(files))).read_text(), next(iter(files.values())))

    def test_malformed_model_response(self):
        agent = self.agent()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"invalid json"
        with patch.object(m.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(ValueError):
                m.Agent.generate(agent, self.c["tasks"][0], self.root, "")

    def test_normal_execution_disabled(self):
        agent = m.Agent(self.root, self.data, self.c)
        with self.assertRaisesRegex(ValueError, "Publishing disabled"):
            agent.run()

    def test_github_commands_blocked_before_spawn(self):
        agent = m.Agent(self.root, self.data, self.c, dry_run=True)
        with patch.object(subprocess, "Popen") as spawn:
            for argv in [["gh", "pr", "create"], ["git", "push", "origin"], ["git", "send-pack", "remote"]]:
                with self.assertRaisesRegex(ValueError, "GitHub writes disabled"):
                    agent.command(argv)
            spawn.assert_not_called()

    def test_stop_after_generation(self):
        agent = self.agent()
        def stopped(*args):
            (self.data / "STOP").touch()
            agent.check_stop()
        agent.generate = stopped
        with self.assertRaises(InterruptedError):
            agent.run()
        self.assertEqual(agent.state["tasks"][self.c["tasks"][0]["id"]]["status"], "stopped")

    def test_generation_failure(self):
        agent = self.agent()
        agent.generate = lambda *args: {"AGENTS.md": "bad"}
        with self.assertRaisesRegex(ValueError, "unapproved"):
            agent.run()
        self.assertEqual(agent.state["tasks"][self.c["tasks"][0]["id"]]["status"], "blocked")

    def test_real_child_timeout(self):
        agent = m.Agent(self.root, self.data, self.c)
        with self.assertRaises(TimeoutError):
            agent.command([sys.executable, "-c", "import time;time.sleep(10)"], timeout=.1)


if __name__ == "__main__":
    unittest.main()
