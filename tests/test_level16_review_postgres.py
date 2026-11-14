"""Real PostgreSQL permissions/transaction tests in a newly created test database.

Set LEVEL16_TEST_DATABASE_URL to a disposable PostgreSQL cluster admin URL and
LEVEL16_TEST_ALLOW_DISPOSABLE=1. No DATABASE_URL fallback and no existing tables
are migrated. CI supplies a fresh PostgreSQL service container.
"""
import copy
import json
import os
import sys
import threading
import importlib.util
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from test_level16_review_events import (
    ROOT, SyntheticEvidenceProvider, SyntheticIdentityProvider, binding, command, policy,
)
from app.level16_review_events import ReviewEventService


@unittest.skipUnless(os.getenv('LEVEL16_TEST_ALLOW_DISPOSABLE') == '1' and os.getenv('LEVEL16_TEST_DATABASE_URL'),
                     'Disposable PostgreSQL integration cluster not explicitly provided')
class ReviewPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bootstrap = create_engine(os.environ['LEVEL16_TEST_DATABASE_URL'], isolation_level='AUTOCOMMIT')
        cls.dbname = 'level16_test_' + uuid4().hex
        cls.runtime_role = 'level16_test_' + uuid4().hex
        cls.bootstrap = bootstrap
        with bootstrap.connect() as c:
            # Avoid ever reusing or mutating an existing review schema/role.
            if c.execute(text("SELECT 1 FROM pg_roles WHERE rolname='pdufa_level16_writer'")).scalar():
                raise RuntimeError('Fresh disposable cluster required; review writer role already exists')
            c.exec_driver_sql('CREATE DATABASE ' + cls.dbname)
        cls.owner = create_engine(bootstrap.url.set(database=cls.dbname))
        try:
            with cls.owner.connect() as c:
                raw = c.connection.driver_connection
                raw.autocommit = True
                raw.execute((ROOT / 'new-platform/backend/migrations/20261113_level16_review_events.sql').read_text(encoding='utf-8'))
                raw.autocommit = False  # Restore transactional owner connections after explicit DDL.
            with bootstrap.connect() as c:
                c.exec_driver_sql('CREATE ROLE ' + cls.runtime_role + " LOGIN PASSWORD 'synthetic-test-only' NOSUPERUSER NOCREATEDB NOCREATEROLE")
                c.exec_driver_sql('GRANT pdufa_level16_writer TO ' + cls.runtime_role)
            cls.runtime = create_engine(bootstrap.url.set(database=cls.dbname, username=cls.runtime_role,
                                                          password='synthetic-test-only'), pool_size=5)
        except Exception:
            cls.cleanup()
            raise
        cls.addClassCleanup(cls.cleanup)

    @classmethod
    def cleanup(cls):
        if hasattr(cls, 'runtime'): cls.runtime.dispose()
        if hasattr(cls, 'owner'): cls.owner.dispose()
        with cls.bootstrap.connect() as c:
            c.exec_driver_sql('DROP DATABASE IF EXISTS ' + cls.dbname + ' WITH (FORCE)')
            c.exec_driver_sql('DROP ROLE IF EXISTS ' + cls.runtime_role)
            c.exec_driver_sql('DROP ROLE IF EXISTS pdufa_level16_writer')
        cls.bootstrap.dispose()

    def setUp(self):
        self.stream = str(uuid4())
        self.evidence = SyntheticEvidenceProvider()
        self.service = ReviewEventService(self.runtime, identity_provider=SyntheticIdentityProvider(), evidence_provider=self.evidence)
        with self.owner.begin() as c:
            for role in (policy.SOURCE_VERIFIER, policy.CLINICAL_REVIEWER, policy.INDEPENDENT_CHALLENGER, policy.REVIEW_ADMIN):
                c.execute(text('''INSERT INTO level16_review.reviewer_grants VALUES ('synthetic-test',:role,:role,true)
                    ON CONFLICT(issuer,subject,role) DO UPDATE SET enabled=true'''), {'role': role})
            c.execute(text("INSERT INTO level16_review.reviewer_grants VALUES('synthetic-test','SOURCE_SUBMITTER','SOURCE_VERIFIER',true) ON CONFLICT DO NOTHING"))
            c.execute(text('INSERT INTO level16_review.streams VALUES (:id,CAST(:binding AS jsonb))'),
                      {'id': self.stream, 'binding': json.dumps(self.evidence.binding)})

    def append(self, state='SOURCE_SUBMITTED', token='synthetic-source-token', **changes):
        history = self.service.history(token, self.stream)['events']
        cmd = command(history, state, streamId=self.stream, binding=self.evidence.binding, **changes)
        return self.service.append(token, cmd)

    def through(self, count):
        tokens = {policy.SOURCE_VERIFIER: 'synthetic-source-token', policy.CLINICAL_REVIEWER: 'synthetic-clinical-token',
                  policy.INDEPENDENT_CHALLENGER: 'synthetic-challenge-token', policy.REVIEW_ADMIN: 'synthetic-admin-token'}
        for status in policy.STAGES[:count]:
            self.append(status, 'synthetic-submitter-token' if status == 'SOURCE_SUBMITTED' else tokens[policy.ROLES[status]])

    def test_full_lifecycle_durable_history_and_server_fields(self):
        self.through(9)
        fresh = ReviewEventService(self.runtime, identity_provider=SyntheticIdentityProvider(), evidence_provider=self.evidence)
        history = fresh.history('synthetic-admin-token', self.stream)
        self.assertEqual([e['status'] for e in history['events']], list(policy.STAGES))
        self.assertEqual([e['version'] for e in history['events']], list(range(1, 10)))
        self.assertTrue(all(e['serverTimestamp'] and e['eventVersion'] == 1 for e in history['events']))
        self.assertIsNone(history['approvalProbability'])
        self.assertIsNone(history['fdaOutcomeJudgment'])
        self.assertEqual(history['events'][2]['sourceChecks'], dict.fromkeys(policy.SOURCE_CHECKS, True))

    def test_unauthorized_forged_and_role_escalation(self):
        for token in ('forged', 'Bearer not-a-verified-token', 'synthetic-ungranted-token', 'synthetic-clinical-token'):
            with self.subTest(token=token), self.assertRaises(policy.ReviewDenied): self.append(token=token)
        for key in ('reviewerId', 'authorizedRole', 'reviewerIdentityClaim', 'approvalProbability'):
            with self.subTest(key=key), self.assertRaises(ValueError): self.append(**{key: policy.REVIEW_ADMIN})
        self.assertEqual(self.service.history('synthetic-source-token', self.stream)['events'], [])

    def test_revoked_authorization_is_rechecked(self):
        with self.owner.begin() as c:
            c.execute(text("UPDATE level16_review.reviewer_grants SET enabled=false WHERE subject='SOURCE_VERIFIER'"))
        with self.assertRaises(policy.ReviewDenied): self.append()

    def test_wrong_nct_application_phase_cutoff_digest_or_version(self):
        for key, value in (('nct', 'NCT05031780'), ('applicationCycleId', 'invented'), ('phases', ['PHASE3']),
                           ('cutoffDate', '2026-11-12'), ('documentSha256', 'b' * 64), ('evidenceVersion', 2),
                           ('documentId', 'wrong-doc'), ('indication', 'different population')):
            changed = binding(**{key: value})
            if key == 'applicationCycleId': changed['applicationIdentityVerified'] = True
            with self.subTest(key=key), self.assertRaises((ValueError, policy.ReviewConflict)):
                self.service.append('synthetic-source-token', command(streamId=self.stream, binding=changed))

    def test_current_evidence_changes_block_stale_stream(self):
        self.evidence.binding['evidenceVersion'] = 2
        with self.assertRaises(policy.ReviewConflict): self.append()

    def test_unmapped_application_is_not_invented(self):
        self.evidence.binding = binding(nct='NCT05031780', applicationCycleId='fabricated', applicationIdentityVerified=True)
        # Bind the exact canonical company so the crosswalk restriction is tested.
        roster = json.loads((ROOT / 'new-platform/frontend/data/p3PostDataActive.json').read_text())
        trial = next(r for r in roster['records'] if r['nct'] == 'NCT05031780')
        self.evidence.binding.update(company=trial['company'], ticker=trial['ticker'])
        with self.owner.begin() as c:
            c.execute(text('INSERT INTO level16_review.streams VALUES (:id,CAST(:binding AS jsonb))'),
                      {'id': str(uuid4()), 'binding': json.dumps(self.evidence.binding)})
        with self.assertRaises(policy.ReviewConflict): self.service._binding(self.stream, self.evidence.binding)

    def test_hash_alone_and_incomplete_source_checks_never_authenticate(self):
        self.through(2)
        for checks in ({'originalDocument': True}, dict.fromkeys(policy.SOURCE_CHECKS, False)):
            self.evidence.checks = checks
            with self.assertRaises(policy.ReviewDenied): self.append('SOURCE_AUTHENTICATED')
        self.assertEqual(len(self.service.history('synthetic-source-token', self.stream)['events']), 2)

    def test_source_authentication_is_not_scientific_completion(self):
        self.through(3)
        with self.assertRaises(policy.ReviewConflict): self.append('SCIENTIFIC_REVIEW_COMPLETED', 'synthetic-clinical-token')
        self.assertEqual(self.service.history('synthetic-source-token', self.stream)['events'][-1]['status'], 'SOURCE_AUTHENTICATED')

    def test_duplicate_event_id_rejected_across_streams(self):
        first = self.append()
        second_stream = str(uuid4())
        with self.owner.begin() as c:
            c.execute(text('INSERT INTO level16_review.streams VALUES (:id,CAST(:binding AS jsonb))'),
                      {'id': second_stream, 'binding': json.dumps(self.evidence.binding)})
        with self.assertRaises(policy.ReviewConflict):
            self.service.append('synthetic-source-token', command(streamId=second_stream, eventId=first['eventId']))

    def test_concurrent_updates_only_one_commits(self):
        gate = threading.Barrier(2)
        def append_one(_):
            cmd = command(streamId=self.stream)
            gate.wait(timeout=10)
            try:
                self.service.append('synthetic-source-token', cmd)
                return 'appended'
            except policy.ReviewConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(append_one, range(2)))
        self.assertCountEqual(results, ['appended', 'conflict'])
        self.assertEqual(len(self.service.history('synthetic-source-token', self.stream)['events']), 1)

    def test_correction_preserves_original_bytes_and_predecessor(self):
        first = self.append()
        saved = copy.deepcopy(first)
        corrected = self.append(action='CORRECTION', findings=['Corrected synthetic finding'])
        history = self.service.history('synthetic-source-token', self.stream)['events']
        self.assertEqual(history[0], saved)
        self.assertEqual(corrected['previousEventId'], first['eventId'])
        self.assertEqual(corrected['version'], 2)
        self.assertEqual(corrected['status'], first['status'])

    def test_runtime_cannot_update_delete_truncate_history_or_escalate_grants(self):
        self.append()
        statements = (
            "UPDATE level16_review.events SET status='FINAL_ADJUDICATED'",
            'DELETE FROM level16_review.events', 'TRUNCATE level16_review.events',
            'UPDATE level16_review.streams SET stream_id=stream_id',
            'DELETE FROM level16_review.streams', 'TRUNCATE level16_review.streams',
            "UPDATE level16_review.reviewer_grants SET enabled=true",
            "UPDATE level16_review.reviewer_grants SET issuer='forged'",
            "INSERT INTO level16_review.reviewer_grants VALUES('x','x','REVIEW_ADMIN',true)",
            'ALTER TABLE level16_review.events DISABLE TRIGGER ALL',
        )
        for statement in statements:
            with self.subTest(statement=statement), self.assertRaises(DBAPIError):
                with self.runtime.begin() as c: c.exec_driver_sql(statement)
        # Even owner DML cannot silently change immutable history; the DBA can
        # still deliberately disable guards, so backups/separation remain required.
        for statement in statements[:3]:
            with self.assertRaises(DBAPIError):
                with self.owner.begin() as c: c.exec_driver_sql(statement)

    def test_self_challenge_and_self_approval_even_when_multirole_granted(self):
        with self.owner.begin() as c:
            for role in (policy.INDEPENDENT_CHALLENGER, policy.REVIEW_ADMIN):
                c.execute(text("INSERT INTO level16_review.reviewer_grants VALUES('synthetic-test','CLINICAL_REVIEWER',:role,true) ON CONFLICT DO NOTHING"), {'role': role})
        self.through(5)
        with self.assertRaises(policy.ReviewDenied): self.append('INDEPENDENT_CHALLENGE_PENDING', 'synthetic-clinical-token')
        self.append('INDEPENDENT_CHALLENGE_PENDING', 'synthetic-challenge-token')
        self.append('INDEPENDENT_CHALLENGE_COMPLETED', 'synthetic-challenge-token')
        with self.assertRaises(policy.ReviewDenied): self.append('FINAL_ADJUDICATION_PENDING', 'synthetic-clinical-token')

    def test_postgres_owner_credentials_fail_closed(self):
        service = ReviewEventService(self.owner, identity_provider=SyntheticIdentityProvider(), evidence_provider=self.evidence)
        with self.assertRaises(policy.ReviewUnavailable): service.append('synthetic-source-token', command(streamId=self.stream))

    def test_engine_preview_readback_requires_authorization_and_exact_history(self):
        self.through(9)
        self.evidence.current_stream = lambda nct, level, connection: self.stream if (nct, level) == ('NCT05507203', 3) else None
        reader = lambda nct, level: self.service.projection('synthetic-admin-token', nct, level)
        def load(name):
            spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/medical' / (name + '.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        engine, preview = load('phase_first_levels_1_6'), load('render_level16_focus_preview')
        inputs = [json.loads(path.read_text(encoding='utf-8')) for path in (engine.ROSTER_PATH, engine.APPLICATIONS_PATH, engine.DEFINITION_PATH)]
        report = engine.build(inputs[0], inputs[1], {'results': {}}, inputs[2], trusted_review_reader=reader)
        self.assertEqual(report['focusTrialCount'], 32)
        self.assertEqual(report['mappedTrialCount'], 29)
        self.assertEqual(report['provisionalApplicationCycleCount'], 23)
        self.assertEqual(report['unmappedTrialCount'], 3)
        self.assertEqual(report['scientificallyAdjudicatedLevels'], 1)
        self.assertEqual(report['independentlyReviewedTrialCount'], 1)
        self.assertEqual(report['originalSourcesIndependentlyAuthenticated'], 1)
        self.assertEqual(report['calibratedFdaPredictions'], 0)
        for trial in report['trials']:
            for level in trial['levels']:
                self.assertIsNone(level['approvalProbability'])
        with self.assertRaises(ValueError): preview.render(report)
        html = preview.render(report, trusted_review_reader=reader)
        self.assertIn('Independently adjudicated finding', html)
        self.assertIn('Append-only review-event history', html)
        self.assertIn('NOT_MAPPED_APPLICATION_CYCLE', html)
        report['trials'][0]['levels'][2]['reviewWorkflow']['findings'] = ['Forged scientific statement']
        with self.assertRaises(ValueError): preview.render(report, trusted_review_reader=reader)

    def test_final_correction_invalidates_completion_until_full_review_repeats(self):
        self.through(9)
        self.evidence.current_stream = lambda nct, level, connection: self.stream
        original = self.service.projection('synthetic-admin-token', 'NCT05507203', 3)
        self.assertTrue(original['independentlyAdjudicated'])
        self.append('FINAL_ADJUDICATED', 'synthetic-admin-token', action='CORRECTION', findings=['Corrected findings pending repeated independent review'])
        corrected = self.service.projection('synthetic-admin-token', 'NCT05507203', 3)
        self.assertFalse(corrected['independentlyAdjudicated'])
        self.assertEqual(corrected['reviewStatus'], 'CORRECTION_REQUIRES_REVIEW')
        self.assertEqual(corrected['history'][:9], original['history'])
        with self.assertRaises(policy.ReviewConflict): self.append('FINAL_ADJUDICATED', 'synthetic-admin-token')
        self.append('SOURCE_AUTHENTICATION_PENDING', 'synthetic-source-token')

    def test_projection_requires_source_provider_and_does_not_promote_source_only_events(self):
        self.through(3)
        self.evidence.current_stream = lambda nct, level, connection: self.stream
        projection = self.service.projection('synthetic-admin-token', 'NCT05507203', 3)
        self.assertEqual(projection['originalDocumentAuthenticationStatus'], 'SOURCE_AUTHENTICATED')
        self.assertFalse(projection['independentlyAdjudicated'])
        self.assertEqual(projection['clinicalReviewStatus'], 'NOT_COMPLETED')
        self.assertEqual(projection['independentChallengeStatus'], 'NOT_COMPLETED')
        with self.assertRaises(policy.ReviewConflict): self.service.projection('synthetic-admin-token', 'NCT05031780', 3)
        service = ReviewEventService(self.runtime, identity_provider=SyntheticIdentityProvider())
        with self.assertRaises(policy.ReviewUnavailable): service.projection('synthetic-admin-token', 'NCT05507203', 3)

    def test_self_authentication_and_clinical_review_rejected(self):
        self.append()
        self.append('SOURCE_AUTHENTICATION_PENDING')
        with self.assertRaises(policy.ReviewDenied): self.append('SOURCE_AUTHENTICATED')
        with self.owner.begin() as c:
            c.execute(text("INSERT INTO level16_review.reviewer_grants VALUES('synthetic-test','SOURCE_VERIFIER','CLINICAL_REVIEWER',true) ON CONFLICT DO NOTHING"))
        # A separately identified submitter-token identity can authenticate this
        # test stream because SOURCE_VERIFIER submitted it (test-only fixture).
        self.append('SOURCE_AUTHENTICATED', 'synthetic-submitter-token')
        with self.assertRaises(policy.ReviewDenied): self.append('SCIENTIFIC_REVIEW_PENDING')

    def test_database_trigger_rejects_stage_skips_even_without_service_policy(self):
        self.append()
        with self.assertRaises(DBAPIError):
            with self.runtime.begin() as c:
                c.execute(text('''INSERT INTO level16_review.events
                    (event_id,stream_id,ordinal,previous_event_id,reviewer_issuer,reviewer_id,authorized_role,
                     binding,action,status,findings,reasons,contradictory_evidence,limitations,blockers)
                    SELECT :new,stream_id,2,event_id,'synthetic-test','REVIEW_ADMIN','REVIEW_ADMIN',binding,
                     'TRANSITION','FINAL_ADJUDICATED',findings,reasons,contradictory_evidence,limitations,blockers
                    FROM level16_review.events WHERE stream_id=:stream'''), {'new': str(uuid4()), 'stream': self.stream})


if __name__ == '__main__': unittest.main()
