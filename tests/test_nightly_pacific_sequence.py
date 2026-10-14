"""Clock, duplicate protection, source lineage and awaited overnight execution."""
import copy
import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.nightly_start import decision, WORKFLOW, RUN_TITLE
from scripts.nightly_sequence import completed_source_stage, SOURCE_JOBS, SOURCE_TAILS, WORKFLOW_NAME
from scripts.validate_clinical_snapshot import validate

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github/workflows'
REPO = 'pdufa/pdufa-command-center'


def read(name):
    return (WORKFLOWS / name).read_text(encoding='utf-8')


def job(text, name):
    match = re.search(r'(?m)^  ' + re.escape(name) + r':\s*$', text)
    if match is None:
        raise AssertionError('Missing job ' + name)
    next_job = re.search(r'(?m)^  [a-z][a-z0-9_-]*:\s*$', text[match.end():])
    return text[match.start():match.end() + next_job.start() if next_job else len(text)]


def clock(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class PacificAdmissionTests(unittest.TestCase):
    def test_daylight_standard_and_wrong_offset_slots(self):
        for at, cron, expected in (
            ('2026-10-15T04:00:00Z', '0 4 * * *', True),
            ('2026-01-15T05:00:00Z', '0 5 * * *', True),
            ('2026-10-15T05:00:00Z', '0 5 * * *', False),
            ('2026-01-15T05:00:00Z', '0 4 * * *', False),
            ('2026-10-15T06:00:00Z', '0 4 * * *', True),
            ('2026-10-15T07:45:00Z', '0 4 * * *', True),
            ('2026-10-15T09:59:00Z', '0 4 * * *', True),
            ('2026-10-15T10:00:00Z', '0 4 * * *', False),
            ('2026-10-15T13:00:00Z', '0 4 * * *', False),
        ):
            with self.subTest(at=at, cron=cron):
                result = decision('schedule', cron, [], now=clock(at))
                self.assertEqual(result['run'], expected)
                self.assertEqual(result['night_date_pacific'], at[:10].replace('-15', '-14'))

    def test_recovery_crons_start_a_missed_night(self):
        for at, cron in (('2026-10-15T07:05:00Z', '5 7 * * *'),
                         ('2026-10-15T08:35:00Z', '35 8 * * *'),
                         ('2026-01-15T09:05:00Z', '5 9 * * *')):
            with self.subTest(at=at):
                self.assertTrue(decision('schedule', cron, [], now=clock(at))['run'])
        self.assertFalse(decision('schedule', '5 7 * * *', [], now=clock('2026-10-15T04:30:00Z'))['run'])

    def test_dst_fall_back_uses_the_offset_at_that_nights_start(self):
        # The 9 PM start was PDT; by this retry Los Angeles has switched to PST.
        result = decision('schedule', '0 4 * * *', [], now=clock('2026-11-01T09:30:00Z'))
        self.assertTrue(result['run'])
        self.assertEqual(result['night_date_pacific'], '2026-10-31')

    def test_only_actual_full_runs_suppress_a_night(self):
        now = clock('2026-10-15T08:00:00Z')
        run = dict(id=7, path=WORKFLOW, head_branch='main', event='workflow_dispatch',
                   display_title=RUN_TITLE, created_at='2026-10-15T04:01:00Z',
                   status='completed', conclusion='success')
        for status in ('queued', 'in_progress', 'completed'):
            for conclusion in ('success', 'failure'):
                with self.subTest(status=status, conclusion=conclusion):
                    self.assertFalse(decision('schedule', '5 8 * * *',
                                     [{**run, 'status': status, 'conclusion': conclusion}], now=now)['run'])
        for change in ({'path': '.github/workflows/pdufa-nightly-clinical.yml'},
                       {'display_title': 'VALIDATE — PDUFA overnight'},
                       {'event': 'push'}, {'head_branch': 'repair-branch'},
                       {'created_at': '2026-10-14T04:01:00Z'}):
            with self.subTest(change=change):
                self.assertTrue(decision('schedule', '5 8 * * *', [{**run, **change}], now=now)['run'])
        self.assertFalse(decision('schedule', '5 8 * * *', [{**run, 'status': 'in_progress',
                         'created_at': '2026-10-14T04:01:00Z'}], now=now)['run'])
        self.assertFalse(decision('schedule', '5 8 * * *', [{**run, 'created_at': 'bad'}], now=now)['run'])

    def test_manual_start_and_scheduler_edit_gates(self):
        now = clock('2026-10-14T23:00:00Z')
        self.assertTrue(decision('workflow_dispatch', '', [], now=now)['run'])
        self.assertFalse(decision('push', '', [], now=now)['run'])
        self.assertTrue(decision('push', '', [], now=clock('2026-10-15T04:30:00Z'))['run'])


class SourceStageTests(unittest.TestCase):
    def setUp(self):
        self.run = dict(id=42, name=RUN_TITLE, display_title=RUN_TITLE, path=WORKFLOW, head_branch='main',
                        head_repository={'full_name': REPO}, status='in_progress')
        self.jobs = [dict(name='sources / ' + name, status='completed', conclusion='success',
                         completed_at='2026-10-15T10:00:00Z') for name in SOURCE_JOBS + SOURCE_TAILS]

    def context(self, conclusion='success'):
        return completed_source_stage(self.run, self.jobs, current_run_id=42,
                                      conclusion=conclusion, repository=REPO)

    def test_active_parent_reports_only_its_completed_source_stage(self):
        result = self.context()
        self.assertEqual(result['stage'], 'sources')
        self.assertEqual(result['parent_status'], 'in_progress')
        self.assertFalse(result['needs_attention'])

    def test_running_feed_missing_source_and_failed_job_cannot_pass(self):
        for change in ('running_feed', 'missing_source', 'failed_job', 'duplicate_source'):
            with self.subTest(change=change):
                before = copy.deepcopy(self.jobs)
                if change == 'running_feed': self.jobs[-1]['status'] = 'in_progress'
                if change == 'missing_source': self.jobs.pop(0)
                if change == 'failed_job': self.jobs[0]['conclusion'] = 'failure'
                if change == 'duplicate_source': self.jobs.append(dict(self.jobs[0]))
                with self.assertRaises(ValueError): self.context()
                self.jobs = before
        self.jobs[0]['conclusion'] = 'failure'
        self.assertTrue(self.context('failure')['needs_attention'])

    def test_untrusted_or_other_parent_rejected(self):
        for change in ({'id': 43}, {'path': 'other.yml'}, {'head_branch': 'feature'},
                       {'head_repository': {'full_name': 'other/fork'}}, {'status': 'completed'}):
            with self.subTest(change=change):
                original = self.run
                self.run = {**self.run, **change}
                with self.assertRaises(ValueError): self.context()
                self.run = original

    def test_prior_clinical_or_scoring_failure_is_visible_during_error_check(self):
        self.jobs.append(dict(name='clinical / PDUFA #2 PIPELINE', id=3,
                              status='completed', conclusion='failure'))
        result = self.context()
        self.assertTrue(result['needs_attention'])
        self.assertEqual(result['failed_parent_jobs'][0]['id'], 3)


class ClinicalPublicationTests(unittest.TestCase):
    def test_partial_failed_stale_and_mismatched_data_are_not_published(self):
        now = clock('2026-10-15T06:00:00Z')
        state = dict(status='COMPLETE', complete=True, finished_at='2026-10-15T05:59:00Z', stored_trials=1)
        report = dict(scan='3', status='PARTIAL', collector_status='COMPLETE',
                      collector_exit_code=0, full_coverage_verified=False,
                      created_at_utc='2026-10-15T06:00:00Z')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'data').mkdir(); (root / 'reports').mkdir()
            (root / 'data/phase_pipeline.csv').write_text('nct_id\nNCT00000001\n')
            def check(s=state, r=report):
                (root/'data/phase_pipeline_state.json').write_text(json.dumps(s))
                (root/'reports/nightly-clinical-3.json').write_text(json.dumps(r))
                return validate('3', root=root, now=now)
            self.assertEqual(check()['status'], 'PARTIAL')
            for changed in ({'status': 'PARTIAL', 'complete': False}, {'status': 'FAILED'},
                            {'finished_at': '2026-10-14T05:59:00Z'}, {'stored_trials': 2}):
                with self.subTest(changed=changed), self.assertRaises(ValueError): check({**state, **changed})
            for changed in ({'scan': '2'}, {'collector_exit_code': 1},
                            {'full_coverage_verified': True}, {'status': 'FAILED'}):
                with self.subTest(changed=changed), self.assertRaises(ValueError): check(r={**report, **changed})


class AwaitedWorkflowTests(unittest.TestCase):
    def test_one_whole_sequence_lock_and_no_dispatch_handoffs(self):
        sequence = read('pdufa-overnight-sequential.yml')
        self.assertIn('pdufa-complete-overnight-sequence-', sequence)
        self.assertIn('cancel-in-progress: false', sequence)
        stages = ['validate', 'clinical', 'report', 'sources', 'scoring-and-repair']
        for previous, current in zip(stages, stages[1:]):
            part = job(sequence, current)
            self.assertIn('needs: ' + previous, part)
            self.assertIn('uses: ./.github/workflows/', part)
            if current != 'clinical': self.assertIn('always()', part)
        self.assertIn('include_gem: true', job(sequence, 'clinical'))
        self.assertNotIn('/dispatches', sequence)
        final = job(sequence, 'result')
        for stage in stages: self.assertIn(stage, final)
        self.assertIn("item['result'] != 'success'", final)

    def test_clinical_publication_and_both_gem_jobs_finish_before_report(self):
        clinical = read('pdufa-nightly-clinical.yml')
        for previous, current in [('scan2','scan3'),('scan3','scan4'),
                                  ('scan4','gem_block'),('gem_block','gem_financing')]:
            self.assertIn('needs: '+previous, job(clinical,current))
            self.assertIn('always()', job(clinical,current))
        for scan in '234':
            part = job(clinical, 'scan'+scan)
            self.assertIn('ref: main', part)
            self.assertIn('validate_clinical_snapshot.py --scan '+scan, part)
            self.assertLess(part.index('Publish completed clinical snapshot'), part.index('Archive scan results'))
        for name in ('pdufa-nightly-clinical.yml','pdufa-nightly-report.yml',
                     'pdufa-nightly-missing-sources.yml','pdufa-nightly-scoring-then-repair.yml',
                     'gem-research-quality.yml','gem-financing-full-coverage.yml'):
            self.assertIn('\n  workflow_call:', read(name))
            self.assertNotIn('\n  schedule:', read(name))

    def test_all_sources_publication_feed_scoring_and_repair_are_serial(self):
        source = read('pdufa-nightly-missing-sources.yml')
        self.assertNotIn('\n  push:', source)
        expected = ['fda','sec','financial','market','issuer']
        for first,second in zip(expected,expected[1:]):
            self.assertIn('needs: source_'+first, job(source,'source_'+second))
        self.assertIn('needs: reconcile', job(source,'publish-source-report'))
        self.assertIn('needs: publish-source-report', job(source,'refresh-prephase3'))
        self.assertNotIn('ref: ${{ github.sha }}',source)
        scoring = read('pdufa-nightly-scoring-then-repair.yml')
        self.assertIn('completed_source_stage(', scoring)
        self.assertIn('needs: scoring', job(scoring,'error-check'))
        self.assertIn('needs: [scoring, error-check]', job(scoring,'safe-repair'))

    def test_all_control_uses_same_sequence_instead_of_parallel_gem_dispatch(self):
        control=read('pdufa-scan-control.yml')
        self.assertIn('"pdufa-overnight-sequential.yml" if scan == "ALL"',control)
        self.assertIn("inputs.scan == 'ALL' && inputs.action == 'VERIFY_ALL'",control)
        scheduler=read('pdufa-nightly-pacific-start.yml')
        self.assertIn('actions/workflows/pdufa-overnight-sequential.yml/runs?',scheduler)
        self.assertIn('pdufa-overnight-sequential.yml/dispatches',scheduler)
        self.assertNotIn('pdufa-nightly-clinical.yml/dispatches',scheduler)


if __name__ == '__main__':
    unittest.main()
