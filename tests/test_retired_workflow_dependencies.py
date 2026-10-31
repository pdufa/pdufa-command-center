"""Retired interfaces cannot schedule scans, require Cloud, or authorize repairs."""
import hashlib
from datetime import datetime, timezone
import re
from pathlib import Path
import unittest

from scripts.adhoc_alert_check import WORKFLOWS
from scripts.nightly_start import decision, WORKFLOW, RUN_TITLE
from scripts.pdufa_auto_repair import decide, RERUN_ALLOWLIST

ROOT = Path(__file__).resolve().parents[1]
RETIRED = (
    'pdufa-complete-verification-repair-20261014.yml',
    'pdufa-sequential-verification-repair-20261014.yml',
    'pdufa-gmail-recovery-20261016.yml',
    'pdufa-inbox-failure-regression.yml',
    'prephase3-acceptance.yml',
)


class RetiredWorkflowDependencies(unittest.TestCase):
    def test_old_operators_are_preserved_outside_registered_workflows(self):
        for name in RETIRED:
            with self.subTest(name=name):
                self.assertFalse((ROOT / '.github/workflows' / name).exists())
                content = (ROOT / '.github/retired-workflows' / name).read_text()
                self.assertIn('name:', content)
                self.assertIn('jobs:', content)

    def test_registered_workflows_never_dispatch_removed_jobs_or_browser_cloud(self):
        forbidden = ('gem-research-quality.yml/dispatches', 'inputs[gem_action]',
                     'node scripts/live_streamlit_audit.cjs',
                     'node scripts/gem_potential_live_audit.cjs',
                     'node scripts/prephase3_live_acceptance.cjs',
                     'node scripts/adhoc_button_live_acceptance.cjs')
        for file in (ROOT / '.github/workflows').glob('*.yml'):
            for token in forbidden:
                self.assertNotIn(token, file.read_text(), str(file))

    def test_monitor_checks_current_clinical_and_every_source_stage(self):
        self.assertIn('pdufa-nightly-clinical.yml', WORKFLOWS)
        self.assertIn('pdufa-nightly-missing-sources.yml', WORKFLOWS)
        self.assertIn('pdufa-overnight-sequential.yml', WORKFLOWS)
        for name in WORKFLOWS:
            self.assertTrue((ROOT / '.github/workflows' / name).exists(), name)
            self.assertNotRegex(name, r'gem|streamlit|prephase3-acceptance')
        source = (ROOT / '.github/workflows/pdufa-nightly-missing-sources.yml').read_text()
        for family in ('fda', 'sec', 'financial', 'market', 'issuer'):
            self.assertIn('  source_' + family + ':', source)

    def test_retired_failure_cannot_rerun_or_repair(self):
        for name in ('Streamlit setup and dashboard tests', 'Live Streamlit Cloud Browser Audit',
                     'PRE PHASE 3 Live Acceptance', 'PIPELINE Early Clinical Live Acceptance'):
            self.assertNotIn(name, RERUN_ALLOWLIST)
            run = dict(name=name, status='completed', conclusion='failure', run_attempt=1,
                       head_branch='main', head_sha='a' * 40, event='push')
            action, _ = decide(run, [{'conclusion': 'failure'}], 'HTTP 503 Service Unavailable',
                               'a' * 40, {}, datetime.now(timezone.utc))
            self.assertEqual(action, 'skip')

    def test_current_and_historical_full_chains_prevent_overlap(self):
        now = datetime(2026, 10, 31, 5, tzinfo=timezone.utc)
        for title in (RUN_TITLE, 'ALL + GEM — PDUFA overnight'):
            for status in ('in_progress', 'completed'):
                run = dict(path=WORKFLOW, head_branch='main', event='workflow_dispatch',
                           display_title=title, created_at='2026-10-31T03:10:00Z',
                           status=status, conclusion='success', id=42)
                with self.subTest(title=title, status=status):
                    result = decision('schedule', '0 3 * * *', [run], now=now)
                    self.assertFalse(result['run'])
                    self.assertIn('42', result['reason'])

    def test_unrelated_old_label_does_not_suppress_missing_night(self):
        run = dict(path='other.yml', head_branch='main', event='workflow_dispatch',
                   display_title='ALL + GEM — PDUFA overnight', created_at='2026-10-31T03:10:00Z',
                   status='completed', id=42)
        self.assertTrue(decision('schedule', '0 3 * * *', [run],
                                now=datetime(2026, 10, 31, 5, tzinfo=timezone.utc))['run'])

    def test_executable_dispatch_regression_is_in_overnight_validation(self):
        source = (ROOT / '.github/workflows/pdufa-overnight-sequential.yml').read_text()
        self.assertIn("-p 'test_nightly_dispatch_shell.py'", source)
        self.assertIn("-p 'test_retired_workflow_dependencies.py'", source)


if __name__ == '__main__':
    unittest.main()
