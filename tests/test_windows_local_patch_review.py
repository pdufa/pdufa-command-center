"""Unit tests for the read-only Level 1 AI patch review gate.

Synthetic examples only. No generated code is imported or executed.
"""
import difflib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "windows_local_agent_patch_review.py"
SPEC = importlib.util.spec_from_file_location("level1_patch_review", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

ORIGINAL = (
    "from urllib.parse import urlparse\n"
    "\n"
    "def validate(url):\n"
    "    parsed = urlparse(url)\n"
    "    if parsed.scheme != 'https':\n"
    "        raise ValueError('HTTPS required')\n"
    "    return parsed.hostname\n"
)
GUARD = (
    "    if any(ch.isspace() for ch in url) or parsed.fragment:\n"
    "        raise ValueError('Invalid URL fragment or whitespace')\n"
)


def document(original, proposed):
    diff = "".join(difflib.unified_diff(
        original.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile="a/" + MODULE.TARGET,
        tofile="b/" + MODULE.TARGET,
    ))
    return MODULE.HEADER + diff


class LevelOnePatchReviewTests(unittest.TestCase):
    def test_exact_two_line_url_guard_passes_static_review(self):
        candidate = ORIGINAL.replace(
            MODULE.ANCHOR, MODULE.ANCHOR + GUARD, 1
        )
        result = MODULE.check_proposal(ORIGINAL, document(ORIGINAL, candidate))
        self.assertEqual(result, GUARD)

    def test_wrong_semantics_rejected(self):
        wrong = (
            "    if parsed.fragment:\n"
            "        raise ValueError('Invalid source URL')\n"
        )
        candidate = ORIGINAL.replace(
            MODULE.ANCHOR, MODULE.ANCHOR + wrong, 1
        )
        with self.assertRaises(ValueError):
            MODULE.check_proposal(ORIGINAL, document(ORIGINAL, candidate))

    def test_extra_changes_or_deletions_rejected(self):
        candidate = ORIGINAL.replace(
            MODULE.ANCHOR, MODULE.ANCHOR + GUARD, 1
        ).replace("HTTPS required", "change existing behavior")
        with self.assertRaises(ValueError):
            MODULE.check_proposal(ORIGINAL, document(ORIGINAL, candidate))

    def test_wrong_file_header_rejected(self):
        candidate = ORIGINAL.replace(
            MODULE.ANCHOR, MODULE.ANCHOR + GUARD, 1
        )
        doc = document(ORIGINAL, candidate).replace(
            "a/" + MODULE.TARGET, "a/unapproved-source.py"
        )
        with self.assertRaises(ValueError):
            MODULE.check_proposal(ORIGINAL, doc)

    def test_missing_review_header_rejected(self):
        candidate = ORIGINAL.replace(
            MODULE.ANCHOR, MODULE.ANCHOR + GUARD, 1
        )
        doc = document(ORIGINAL, candidate).replace(MODULE.HEADER, "", 1)
        with self.assertRaises(ValueError):
            MODULE.check_proposal(ORIGINAL, doc)

    def test_changed_baseline_rejected(self):
        candidate = ORIGINAL.replace(
            MODULE.ANCHOR, MODULE.ANCHOR + GUARD, 1
        )
        doc = document(ORIGINAL, candidate)
        with self.assertRaises(ValueError):
            MODULE.check_proposal(ORIGINAL + "# newer source\n", doc)


if __name__ == "__main__":
    unittest.main()
