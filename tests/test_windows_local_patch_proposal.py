"""Safety gates for an AI-proposed Level 1 patch; never execute generated code."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "windows_local_agent_patch_proposal.py"
SPEC = importlib.util.spec_from_file_location("windows_local_patch_proposal", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

GOOD = (
    "if any(ch.isspace() for ch in url) or parsed.fragment:\n"
    "    raise ValueError('Malformed source URL')"
)


class PatchProposalGuardTests(unittest.TestCase):
    def test_bounded_whitespace_and_fragment_guard_accepted(self):
        guard = MODULE.review_guard(GOOD)
        self.assertEqual(
            guard, "    if any(ch.isspace() for ch in url) or parsed.fragment:\n"
                   "        raise ValueError('Malformed source URL')\n"
        )

    def test_unapproved_semantic_guard_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.review_guard(
                "if parsed.fragment:\n    raise ValueError('Malformed source URL')"
            )

    def test_import_and_side_effect_rejected(self):
        for bad in (
            "import os\n" + GOOD,
            "if any(ch.isspace() for ch in url) or parsed.fragment:\n"
            "    print('unexpected')",
            "if any(ch.isspace() for ch in url) or parsed.fragment:\n"
            "    raise SystemExit('stop')",
            "if any(ch.isspace() for ch in url) or parsed.fragment:\n"
            "    raise ValueError('x'); open('file', 'w')",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    MODULE.review_guard(bad)

    def test_only_short_error_message_accepted(self):
        with self.assertRaises(ValueError):
            MODULE.review_guard(
                "if any(ch.isspace() for ch in url) or parsed.fragment:\n"
                "    raise ValueError('" + "x" * 121 + "')"
            )


if __name__ == "__main__":
    unittest.main()
