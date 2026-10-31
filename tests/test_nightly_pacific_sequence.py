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
            ('2026-10-15T03:00:00Z', '0 3 * * *', True),   # 8 PM PDT
            ('2026-10-15T04:00:00Z', '0 4 * * *', False),  # wrong DST primary slot
            ('2026-01-15T03:00:00Z', '0 3 * * *', False),  # too early in PST
            ('2026-01-15T04:00:00Z', '0 4 * * *', True),   # 8 PM PST
            ('2026-01-15T06:00:00Z', '0 6 * * *', False),  # retired 10 PM PST slot
            ('2026-10-15T06:00:00Z', '0 6 * * *', False),
            ('2026-10-15T09:59:00Z', '0 3 * * *', True),
            ('2026-10-15T10:00:00Z', '0 3 * * *', True),  # delayed schedule safely catches up
        ):
            with self.subTest(at=at, cron=cron):
                result = decision('schedule', cron, [], now=clock(at))
                self.assertEqual(result['run'], expected)

        scheduler = read('pdufa-nightly-pacific-start.yml')
        self.assertIn('name: PDUFA Daily 8:00 PM Pacific Start', scheduler)
        for minute in ('0', '15', '30'):
            for hour in ('3', '4'):
                self.assertIn(f"cron: '{minute} {hour} * * *'", scheduler)
        self.assertNotIn("cron: '0 6 * * *'", scheduler)

    def test_recovery_crons_start_a_missed_night(self):
        for at, cron in (('2026-10-15T07:05:00Z', '5 7 * * *'),
                         ('2026-10-15T08:35:00Z', '35 8 * * *'),
                         ('2026-01-15T09:05:00Z', '5 9 * * *')):
            with self.subTest(at=at):
                self.assertTrue(decision('schedule', cron, [], now=clock(at))['run'])
        self.assertFalse(decision('schedule', '5 7 * * *', [], now=clock('2026-10-15T03:30:00Z'))['run'])

    def test_frequent_recovery_sweep_is_dst_safe_and_deduplicates(self):
        sweep = '3-53/10 3-10 * * *'
        scheduler = read('pdufa-nightly-pacific-start.yml')
        self.assertIn(f"cron: '{sweep}'", scheduler)
        for when, expected in (
            ('2026-10-16T04:03:00Z', True),   # 9:03 PM PDT
            ('2026-01-16T05:03:00Z', True),   # 9:03 PM PST
            ('2026-01-16T06:03:00Z', True),   # 10:03 PM PST
            ('2026-10-16T09:53:00Z', True),   # 2:53 AM PDT recovery
            ('2026-10-16T10:03:00Z', True),   # 3:03 AM PDT: delayed recovery
            ('2026-01-16T10:53:00Z', True),   # 2:53 AM PST recovery
            ('2026-10-16T16:43:00Z', True),  # late GitHub tick at 9:43 AM PDT
        ):
            with self.subTest(when=when):
                self.assertEqual(
                    decision('schedule', sweep, [], now=clock(when))['run'],
                    expected,
                )
        prior = dict(id=33, path=WORKFLOW, head_branch='main',
                     event='workflow_dispatch', display_title=RUN_TITLE,
                     created_at='2026-10-16T05:02:00Z',
                     status='completed', conclusion='success')
        self.assertFalse(decision('schedule', sweep, [prior],
                         now=clock('2026-10-16T05:13:00Z'))['run'])

    def test_daytime_catchup_does_not_duplicate_any_recorded_nightly_chain(self):
        sweep = '3-53/10 3-10 * * *'
        # A delayed scheduled job the following morning must recover the
        # missing *previous* night, not start an unrelated daytime scan.
        late = clock('2026-10-16T16:43:00Z')  # 9:43 AM PDT
        missing = decision('schedule', sweep, [], now=late)
        self.assertTrue(missing['run'])
        self.assertEqual(missing['night_date_pacific'], '2026-10-15')
        self.assertIn('RECOVERY of missed 2026-10-15', missing['reason'])

        prior = dict(id=181, path=WORKFLOW, head_branch='main',
                     event='workflow_dispatch', display_title=RUN_TITLE,
                     created_at='2026-10-16T04:25:00Z',
                     status='completed', conclusion='success')
        self.assertFalse(decision('schedule', sweep, [prior], now=late)['run'])
        self.assertFalse(decision('schedule', sweep,
                         [{**prior,'status':'in_progress'}],now=late)['run'])
        # A prior night must not suppress the next night's new scan.
        next_night = clock('2026-10-17T04:13:00Z')
        self.assertTrue(decision('schedule', sweep, [prior], now=next_night)['run'])

    def test_late_recovery_only_accepts_known_scheduler_crons(self):
        late = clock('2026-10-16T16:43:00Z')
        for cron in ('', '1 15 * * *', '0 6 * * *'):
            with self.subTest(cron=cron):
                self.assertFalse(decision('schedule',cron,[],now=late)['run'])
        # Human and source edits during daytime should not launch the chain.
        self.assertFalse(decision('push','',[],now=late)['run'])

    def test_dst_fall_back_uses_the_offset_at_that_nights_start(self):
        # The 8 PM start was PDT; by this retry Los Angeles has switched to PST.
        result = decision('schedule', '0 3 * * *', [], now=clock('2026-11-01T09:30:00Z'))
        self.assertTrue(result['run'])
        self.assertEqual(result['night_date_pacific'], '2026-10-31')

    def test_only_actual_full_runs_suppress_a_night(self):
        now = clock('2026-10-15T08:00:00Z')
        run = dict(id=7, path=WORKFLOW, head_branch='main', event='workflow_dispatch',
                   display_title=RUN_TITLE, created_at='2026-10-15T05:01:00Z',
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
        self.assertFalse(decision('push', '', [], now=clock('2026-10-15T02:59:00Z'))['run'])
        self.assertTrue(decision('push', '', [], now=clock('2026-10-15T03:30:00Z'))['run'])
        # Operator can recover a missed 8 PM launch at 9:30 PM Pacific.
        late_push = clock('2026-10-15T04:30:00Z')
        self.assertTrue(decision('push', '', [], now=late_push)['run'])
        already = dict(id=1234, path=WORKFLOW, head_branch='main',
                       event='workflow_dispatch', display_title=RUN_TITLE,
                       status='in_progress', created_at='2026-10-15T03:10:00Z')
        self.assertFalse(decision('push', '', [already], now=late_push)['run'])



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
        stages = ['validate', 'clinical', 'report', 'sources', 'shared-data', 'scoring-and-repair']
        for previous, current in zip(stages, stages[1:]):
            part = job(sequence, current)
            needs = re.search(r'(?m)^    needs: (.+)$', part)
            self.assertIsNotNone(needs)
            dependencies = needs.group(1).strip('[]').replace(' ', '').split(',')
            self.assertIn(previous, dependencies)
            self.assertIn('uses: ./.github/workflows/', part)
            if current != 'clinical': self.assertIn('always()', part)
        self.assertNotIn('include_gem:', job(sequence, 'clinical'))
        self.assertNotIn('/dispatches', sequence)
        final = job(sequence, 'result')
        for stage in stages: self.assertIn(stage, final)
        self.assertIn("item['result'] != 'success'", final)

    def test_clinical_pool_pipeline_and_phase3_results_without_gem_jobs(self):
        clinical = read('pdufa-nightly-clinical.yml')
        self.assertNotIn('  scan3:', clinical)
        self.assertNotIn('  scan4:', clinical)
        self.assertIn("options: ['ALL', 'PIPELINE', 'PHASE3_RESULTS']", clinical)
        pipeline = job(clinical, 'pipeline')
        phase3 = job(clinical, 'phase3_results')
        self.assertIn('ref: main', pipeline)
        self.assertIn('ref: main', phase3)
        for scan in ('2', '3'):
            self.assertIn('validate_clinical_snapshot.py --scan ' + scan, pipeline)
            self.assertIn('nightly-clinical-' + scan, pipeline)
        self.assertLess(pipeline.index('--scan 2'), pipeline.index('--scan 3'))
        self.assertIn('needs: pipeline', phase3)
        self.assertIn("needs.pipeline.result == 'success'", phase3)
        self.assertIn('validate_clinical_snapshot.py --scan 4', phase3)
        self.assertNotIn('  gem_block:', clinical)
        self.assertNotIn('  gem_financing:', clinical)
        self.assertNotIn('gem_stage_membership', clinical)
        for name in ('pdufa-nightly-clinical.yml','pdufa-nightly-report.yml',
                     'pdufa-nightly-missing-sources.yml','pdufa-nightly-scoring-then-repair.yml'):
            self.assertIn('\n  workflow_call:', read(name))
            self.assertNotIn('\n  schedule:', read(name))

    def test_all_sources_publication_feed_scoring_and_repair_are_serial(self):
        source = read('pdufa-nightly-missing-sources.yml')
        self.assertNotIn('\n  push:', source)
        expected = ['fda','sec','financial','market','issuer']
        for first,second in zip(expected,expected[1:]):
            self.assertIn('needs: source_'+first, job(source,'source_'+second))
        self.assertIn('needs: reconcile', job(source,'publish-source-report'))
        eod = job(source, 'refresh-step7-market-eod')
        self.assertIn('needs: publish-source-report', eod)
        self.assertIn('scripts/step7_market_refresh.py', eod)
        self.assertIn('data/step7_market_status.csv data/step7_market_status.json', eod)
        self.assertIn('needs: refresh-step7-market-eod', job(source,'refresh-prephase3'))
        self.assertIn('Refresh validated PIPELINE early-clinical feed after sources / publish', (ROOT / 'scripts/nightly_sequence.py').read_text())
        self.assertNotIn('ref: ${{ github.sha }}',source)
        scoring = read('pdufa-nightly-scoring-then-repair.yml')
        self.assertIn('completed_source_stage(', scoring)
        self.assertIn('needs: scoring', job(scoring,'error-check'))
        self.assertIn('needs: [scoring, error-check]', job(scoring,'safe-repair'))

    def test_all_control_uses_same_sequence_without_gem_dispatch(self):
        control=read('pdufa-scan-control.yml')
        self.assertIn('"pdufa-overnight-sequential.yml" if scan == "ALL"',control)
        self.assertIn("options: [ALL, PIPELINE, PHASE3_RESULTS]", control)
        self.assertNotIn("gem-research-quality.yml/dispatches", control)
        self.assertNotIn("GEM_JR", control)
        scheduler=read('pdufa-nightly-pacific-start.yml')
        self.assertIn('actions/workflows/pdufa-overnight-sequential.yml/runs?',scheduler)
        self.assertIn('pdufa-overnight-sequential.yml/dispatches',scheduler)
        self.assertNotIn('pdufa-nightly-clinical.yml/dispatches',scheduler)


class DatedArchiveTests(unittest.TestCase):
    def test_archive_is_awaited_after_the_full_sequence(self):
        sequence = read('pdufa-overnight-sequential.yml')
        archive = job(sequence, 'archive')
        self.assertIn('needs: result', archive)
        self.assertIn('always()', archive)
        self.assertIn("github.event_name == 'workflow_dispatch'", archive)
        self.assertIn('scripts/pdufa_daily_results.py', archive)
        self.assertIn('night_date_pacific:', sequence)
        self.assertIn('GUARDED_NIGHT:', archive)
        self.assertIn('--night-date-pacific "$GUARDED_NIGHT"', archive)
        self.assertIn('inputs[night_date_pacific]', read('pdufa-nightly-pacific-start.yml'))
        self.assertIn('git push origin HEAD:main', archive)
        self.assertNotIn('dispatches', archive)

    def test_archived_start_delay_uses_guarded_pacific_night_even_after_midnight(self):
        from scripts import pdufa_daily_results as daily
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            unavailable = Path(directory) / "no-nightly-report.json"
            with patch.object(daily, "REPORT", unavailable):
                at_815 = daily.record(
                    501, "2026-10-31T03:15:44Z", "success", "2026-10-30")
                self.assertEqual(at_815["date_pacific"], "2026-10-30")
                self.assertEqual(at_815["start_delay_minutes"], 15)
                self.assertEqual(at_815["scan_night_source"], "GUARDED_SCHEDULER_INPUT")
                self.assertEqual(at_815["scheduled_8pm_pacific_utc"],
                                 "2026-10-31T03:00:00+00:00")
                late = daily.record(
                    502, "2026-10-31T09:05:00Z", "success", "2026-10-30")
                self.assertEqual(late["date_pacific"], "2026-10-30")
                self.assertEqual(late["start_delay_minutes"], 365)
                standard_time = daily.record(
                    503, "2026-11-02T04:15:00Z", "success", "2026-11-01")
                self.assertEqual(standard_time["start_delay_minutes"], 15)
                self.assertEqual(standard_time["scheduled_8pm_pacific_utc"],
                                 "2026-11-02T04:00:00+00:00")
                with self.assertRaises(ValueError):
                    daily.record(504, "2026-10-31T03:15:44Z", "success", "2026-10-31")
                with self.assertRaises(ValueError):
                    daily.record(505, "2026-10-31T03:15:44Z", "success", "2026-10-28")
                with self.assertRaises(ValueError):
                    daily.record(506, "2026-10-30T20:15:44", "success", "2026-10-30")


    def test_same_night_changes_and_saved_membership_not_confused_with_new(self):
        from scripts import pdufa_daily_results as daily
        from unittest.mock import patch
        run_id = 39895404578
        report = {
            'latest_run_id': run_id,
            'latest_run_started_at_utc': '2026-10-23T03:30:41Z',
            'status': 'PARTIAL',
            'scans': [{'scan': '2', 'run_id': run_id,
                       'collector_status': 'COMPLETE',
                       'changed_trials_this_execution': 49,
                       'metrics': {'tracked_trials_total': 11594}}],
        }
        membership = {'stages': {
            'GEM_JR': {'last_complete_snapshot': '2026-10-22',
                       'entries': {'j1': {'status': 'ACTIVE', 'periods': []}}},
            'GEM': {'last_complete_snapshot': '2026-10-22',
                    'entries': {'g1': {'status': 'ACTIVE', 'periods': []}}},
        }}
        source = {'latest_run_id': str(run_id), 'findings_due': 1121,
                  'findings_verified': 995, 'findings_unresolved': 23,
                  'findings_unavailable': 93, 'findings_not_applicable': 10,
                  'full_coverage_verified': False}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'report.json').write_text(json.dumps(report))
            (root / 'members.json').write_text(json.dumps(membership))
            (root / 'sources.json').write_text(json.dumps(source))
            with (patch.object(daily, 'REPORT', root / 'report.json'),
                  patch.object(daily, 'MEMBERSHIP', root / 'members.json'),
                  patch.object(daily, 'SOURCES', root / 'sources.json')):
                entry = daily.record(run_id, '2026-10-23T03:30:41Z', 'success')
                self.assertEqual(entry['date_pacific'], '2026-10-22')
                self.assertEqual(entry['status'], 'PARTIAL')
                self.assertEqual(entry['sections']['master']['total'], 11594)
                self.assertEqual(entry['sections']['master']['updated'], 49)
                self.assertIsNone(entry['sections']['master']['new'])
                self.assertEqual(entry['sections']['gem_jr']['new'], 0)
                self.assertEqual(entry['sections']['gem']['new'], 0)
                self.assertIsNone(entry['sections']['pipeline']['total'])
                self.assertIsNone(entry['sections']['designations']['total'])
                self.assertTrue(any('995 of 1121' in note for note in entry['notes']))
                self.assertIsNone(daily.same_run_trial_inventory(report, run_id + 1))


    def test_same_run_source_conflicts_are_reconciled_and_fail_closed(self):
        from scripts import pdufa_daily_results as daily
        from unittest.mock import patch
        data = {
            'latest_run_id': '40263199452',
            'findings_due': 1121,
            'findings_verified': 995,
            'findings_unresolved': 21,
            'findings_conflicted': 2,
            'findings_unavailable': 93,
            'findings_not_applicable': 10,
            'full_coverage_verified': False,
            'missing_required_source_families': ['SEC', 'FINANCIAL'],
        }
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / 'source.json'
            def note(source=data, run=40263199452):
                source_path.write_text(json.dumps(source), encoding='utf-8')
                with patch.object(daily, 'SOURCES', source_path):
                    return daily.same_run_source_note(run)

            valid = note()
            self.assertIn('995 of 1121 verified', valid)
            self.assertIn('21 unresolved, 2 conflicted, 93 unavailable', valid)
            self.assertIn('10 not applicable', valid)
            self.assertIn('Full coverage verified: no', valid)
            self.assertIsNone(note(run=40263199453))

            # The old note silently hid two conflicts. Now a missing field
            # cannot masquerade as a reconciled complete source audit.
            missing_conflicts = {k: v for k, v in data.items()
                                 if k != 'findings_conflicted'}
            self.assertIn('counts withheld', note(missing_conflicts))
            self.assertIn('do not reconcile', note({**data, 'findings_due': 1122}))
            self.assertIn('counts withheld', note({**data, 'findings_conflicted': -1}))
            self.assertIn('counts withheld', note({**data, 'findings_conflicted': True}))
            self.assertIn('counts withheld', note({**data, 'findings_conflicted': '2'}))
            self.assertIn('Full coverage verified: no', note({
                **data, 'full_coverage_verified': True}))

            # Legacy reports without the new category are still accepted
            # when the four reported categories account for every source.
            legacy = {**data, 'findings_unresolved': 23}
            del legacy['findings_conflicted']
            self.assertIn('0 conflicted', note(legacy))
            self.assertNotIn('counts withheld', note(legacy))




if __name__ == '__main__':
    unittest.main()
