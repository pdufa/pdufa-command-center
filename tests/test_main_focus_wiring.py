"""MAIN nightly scan must await Pipeline and FOCUS evidence stages."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".github" / "workflows"


class MainFocusWiringTests(unittest.TestCase):
    def test_focus_reusable_and_manual(self):
        focus = (ROOT / "stage4-manual-focus-source-review.yml").read_text()
        self.assertIn("  workflow_dispatch:", focus)
        self.assertIn("  workflow_call:", focus)
        self.assertIn("python scripts/stage4_retrieval_coverage_audit.py", focus)
        self.assertNotIn("  schedule:", focus)

    def test_main_waits_for_pipeline_and_focus(self):
        main = (ROOT / "pdufa-overnight-sequential.yml").read_text()
        self.assertIn("  clinical:\n", main)
        self.assertIn("  focus-evidence:\n    needs: sources\n", main)
        self.assertIn("uses: ./.github/workflows/stage4-manual-focus-source-review.yml", main)
        self.assertIn("needs: [sources, focus-evidence]", main)
        self.assertIn("needs.focus-evidence.result == 'success'", main)
        self.assertIn("needs: [validate, clinical, report, sources, focus-evidence, shared-data, scoring-and-repair]", main)
        self.assertIn("github.event_name == 'workflow_dispatch' && !inputs.validate_only", main)
        self.assertNotIn("  schedule:", main)


if __name__ == "__main__":
    unittest.main()
