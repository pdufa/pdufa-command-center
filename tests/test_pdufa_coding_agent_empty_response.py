import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pdufa_coding_agent as m

APPROVED = "scripts/engineering_drafts/gap_helper.py"


class EmptyModelResponseTests(unittest.TestCase):
    def test_empty_source_is_rejected(self):
        task = {
            "id": "fixture-gap-helper",
            "level": 7,
            "engineering_only": True,
            "requirements": "Implement has_gap(value).",
            "phase": "engineering-fixture",
            "depends_on": [],
            "files": [APPROVED],
            "acceptance_tests": ["tests/test_gap_acceptance.py"],
        }

        contract = {
            "enabled": True,
            "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "base_branch": "local-only",
            "image": "python@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90",
            "max_repairs": 1,
            "tasks": [task],
        }

        payload = json.dumps({
            "response": json.dumps({
                "files": {APPROVED: ""}
            })
        }).encode()

        fake_response = MagicMock()
        fake_response.read.return_value = payload
        fake_response.__enter__.return_value = fake_response

        with tempfile.TemporaryDirectory() as tmp:
            agent = m.Agent(
                ROOT, Path(tmp), contract, dry_run=True
            )

            with patch.object(
                m.urllib.request,
                "urlopen",
                return_value=fake_response
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "empty source"
                ):
                    agent.generate(task, ROOT, "")


if __name__ == "__main__":
    unittest.main()
