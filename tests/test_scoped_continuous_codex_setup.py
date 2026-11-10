"""Regression checks for fail-closed bounded Codex development setup."""
import importlib.util
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path = ROOT / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContinuousCodexSetupTests(unittest.TestCase):
    def test_approved_task_is_explicitly_scoped_and_not_auto_merged(self):
        queue = json.loads((ROOT / ".github/codex/continuous-development-queue.json").read_text())
        self.assertEqual(queue["schemaVersion"], 1)
        self.assertEqual(len(queue["tasks"]), 1)
        select = load("select_continuous_codex_task")
        task = queue["tasks"][0]
        self.assertTrue(select.eligible(task))
        self.assertFalse(select.eligible({**task, "status": "unapproved"}))
        self.assertFalse(select.eligible({**task, "promptFile": "../untrusted.md"}))

    def test_queue_skips_existing_attempt_and_never_retries_same_pr(self):
        select = load("select_continuous_codex_task")
        with TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with patch.dict(os.environ, {"GH_TOKEN": "fake", "GITHUB_OUTPUT": str(output)}), \
                 patch.object(select, "existing_pr", return_value=True):
                select.main()
            self.assertIn("task_id=\n", output.read_text())

    def test_queue_selects_one_work_item_from_checked_in_source(self):
        select = load("select_continuous_codex_task")
        with TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with patch.dict(os.environ, {"GH_TOKEN": "fake", "GITHUB_OUTPUT": str(output)}), \
                 patch.object(select, "existing_pr", return_value=False):
                select.main()
            self.assertIn("task_id=medical-source-gates-01\n", output.read_text())

    def test_patch_scope_rejects_unapproved_and_symlink_paths(self):
        guard = load("check_continuous_codex_patch")
        with patch.object(guard, "run", return_value=" M .github/workflows/ci.yml\n"):
            with self.assertRaisesRegex(ValueError, "unapproved path"):
                guard.validate("medical-source-gates-01")
        with patch.object(guard, "run", return_value=" M new-platform/backend/app/medical_method_projection.py\n"):
            self.assertEqual(guard.validate("medical-source-gates-01"),
                             ["new-platform/backend/app/medical_method_projection.py"])
        with self.assertRaisesRegex(ValueError, "Unknown"):
            guard.validate("invented-task")

    def test_disabled_by_default_and_draft_pr_only(self):
        workflow = (ROOT / ".github/workflows/pdufa-scoped-codex-development.yml").read_text()
        self.assertIn("vars.PDUFA_CONTINUOUS_CODEX_ENABLED == 'true'", workflow)
        self.assertIn("openai/codex-action@v1", workflow)
        self.assertIn("secrets.OPENAI_API_KEY", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("sandbox: workspace-write", workflow)
        self.assertIn("draft: true", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("enable-auto-merge", workflow)


if __name__ == "__main__":
    unittest.main()
