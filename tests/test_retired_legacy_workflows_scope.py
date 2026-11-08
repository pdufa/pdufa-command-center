"""Ensure retired pipelines cannot recreate obsolete trial lists."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FILES=(
    ".github/workflows/pdufa-pipeline-research-sync.yml",
    "archives/raas/workflows/raas-clinical-evidence-collector.yml.disabled",
)

class RetiredLegacyWorkflows(unittest.TestCase):
    def test_no_automatic_trigger_or_source_publishing(self):
        for name in FILES:
            with self.subTest(name=name):
                src=(ROOT/name).read_text()
                self.assertIn("workflow_dispatch:",src)
                self.assertIn("RETIRED",src)
                self.assertNotIn("schedule:",src)
                self.assertNotIn("cron:",src)
                self.assertNotIn("pull_request:",src)
                self.assertNotIn("push:",src)
                self.assertNotIn("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON",src)
                self.assertNotIn("scripts/raas_collect_registry_evidence.py",src)
                self.assertNotIn("scripts/sync_pipeline_research.py",src)

if __name__=="__main__":
    unittest.main()
