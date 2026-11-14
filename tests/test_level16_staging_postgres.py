"""End-to-end staging tests: ephemeral signed synthetic identities and evidence.

No real token, private key, clinical document or source attestation is committed.
Uses the existing disposable PostgreSQL fixture, never application DATABASE_URL.
"""
import copy
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from fastapi.testclient import TestClient

import test_level16_review_postgres as prior
from test_level16_review_events import binding, command, policy, ROOT
from test_level16_staging_identity import (
    IDENTITY_ISSUER, SOURCE_ISSUER, IDENTITY_REF, SOURCE_REF, AUDIENCE,
    keypair, access_claims, sign,
)
from app.level16_review_events import ReviewEventService
from app.level16_staging_identity import PinnedJwtVerifier, StagingIdentityProvider, REALM
from app.level16_staging_evidence import TransactionalEvidenceResolver, digest_json
from app.level16_staging import HarnessApproval, create_staging_app


@unittest.skipUnless(os.getenv('LEVEL16_TEST_ALLOW_DISPOSABLE') == '1' and os.getenv('LEVEL16_TEST_DATABASE_URL'),
                     'Disposable PostgreSQL cluster not explicitly provided')
class StagingPostgresTests(unittest.TestCase):
    cleanup = classmethod(prior.ReviewPostgresTests.cleanup.__func__)

    @classmethod
    def setUpClass(cls):
        prior.ReviewPostgresTests.setUpClass.__func__(cls)
        with cls.owner.connect() as c:
            raw = c.connection.driver_connection
            raw.autocommit = True
            raw.execute((ROOT / 'new-platform/backend/migrations/20261113_level16_staging_evidence.sql').read_text(encoding='utf-8'))
            raw.autocommit = False  # Restore transactional owner connections after explicit DDL.
        cls.private, cls.public = keypair()
        cls.source_private, cls.source_public = keypair()

    def setUp(self):
        self.people, self.claims, self.tokens = {}, {}, {}
        with self.owner.connect() as c:
            self.version_base = c.execute(text("SELECT COALESCE(max((binding->>'evidenceVersion')::integer),0) FROM level16_review.streams")).scalar() + 100
        self.issuer_verifier = PinnedJwtVerifier(IDENTITY_ISSUER, AUDIENCE, {'synthetic-key': self.public}, approval_reference=IDENTITY_REF)
        self.source_verifier = PinnedJwtVerifier(SOURCE_ISSUER, AUDIENCE, {'synthetic-key': self.source_public},
                                                 approval_reference=SOURCE_REF, max_lifetime=3600)
        self.identity = StagingIdentityProvider(self.runtime, self.issuer_verifier)
        self.evidence = TransactionalEvidenceResolver(self.source_verifier)
        self.service = ReviewEventService(self.runtime, identity_provider=self.identity, evidence_provider=self.evidence)
        with self.owner.begin() as c:
            for name, role in (('submitter', policy.SOURCE_VERIFIER), ('verifier', policy.SOURCE_VERIFIER),
                               ('clinical', policy.CLINICAL_REVIEWER), ('challenger', policy.INDEPENDENT_CHALLENGER),
                               ('admin', policy.REVIEW_ADMIN), ('ungranted', None)):
                person = str(uuid4())
                claims = access_claims('SYNTHETIC_TEST_ONLY:' + name + ':' + uuid4().hex)
                self.people[name], self.claims[name] = person, claims
                self.tokens[name] = 'Bearer ' + sign(self.private, claims)
                self.provision_account(c, claims, person)
                if role:
                    c.execute(text('INSERT INTO level16_review.reviewer_grants VALUES (:issuer,:person,:role,true)'),
                              {'issuer': REALM, 'person': person, 'role': role})
        self.stream, self.binding, self.manifest = self.provision()
        self.approval = HarnessApproval('SYNTHETIC_TEST_ONLY', IDENTITY_REF, SOURCE_REF, self.dbname)
        self.app = create_staging_app(approval=self.approval, service=self.service)

    def provision_account(self, c, claims, person):
        c.execute(text('INSERT INTO level16_review.identity_accounts VALUES (:issuer,:subject,CAST(:person AS uuid))'),
                  {'issuer': claims['iss'], 'subject': claims['sub'], 'person': person})
        c.execute(text('''INSERT INTO level16_review.identity_sessions
            (token_issuer,session_id,token_subject,valid_after,expires_at) VALUES
            (:issuer,:sid,:subject,to_timestamp(:iat)-interval '1 second',to_timestamp(:exp)+interval '1 hour')'''),
                  {'issuer': claims['iss'], 'sid': claims['sid'], 'subject': claims['sub'], 'iat': claims['iat'], 'exp': claims['exp']})

    def provision(self, *, version=1, binding_changes=None, manifest_changes=None,
                  bytes_override=None, attestation_changes=None, foreign_signature=False, amendment=False, activate=True, missing_bytes=False):
        stream, document = str(uuid4()), 'synthetic-document-' + uuid4().hex
        data = ('SYNTHETIC_TEST_ONLY_NOT_CLINICAL_EVIDENCE NCT05507203 ' + document).encode()
        b = binding(documentId=document, documentSha256=hashlib.sha256(data).hexdigest(), evidenceVersion=self.version_base + version,
                    **(binding_changes or {}))
        manifest = {'schemaVersion': 1, 'binding': b, 'provenance': {'sourceUrl': b['sourceUrl'], 'publisher': 'SYNTHETIC_TEST_ONLY',
                     'retrievalMethod': 'Synthetic in-memory fixture, not a retrieval', 'publicAccess': True},
                    'amendments': [], 'historicalOutcomeExposed': False, 'purpose': 'CURRENT_SCIENTIFIC_REVIEW'}
        documents = [(document, b['documentSha256'], None if missing_bytes else (data if bytes_override is None else bytes_override))]
        if amendment:
            amendment_bytes = b'SYNTHETIC_AMENDMENT_ONLY_NCT05507203'
            amend = dict(b, documentId='synthetic-amendment-' + uuid4().hex,
                         documentSha256=hashlib.sha256(amendment_bytes).hexdigest(), documentVersion='Synthetic amendment v2')
            manifest['amendments'] = [amend]
            documents.append((amend['documentId'], amend['documentSha256'], amendment_bytes))
        manifest.update(manifest_changes or {})
        claims = access_claims(self.people['verifier'], iss=SOURCE_ISSUER, exp=int(time.time()) + 1800,
                              streamId=stream, manifestDigest=digest_json(manifest), reviewerIssuer=REALM,
                              checks=dict.fromkeys(policy.SOURCE_CHECKS, True))
        claims.pop('sid')
        claims.update(attestation_changes or {})
        signed = sign(self.private if foreign_signature else self.source_private, claims, 'level16-source-attestation+jwt')
        with self.owner.begin() as c:
            c.execute(text('INSERT INTO level16_review.streams VALUES (:stream,CAST(:binding AS jsonb))'),
                      {'stream': stream, 'binding': json.dumps(b)})
            for ident, digest, original in documents:
                c.execute(text('INSERT INTO level16_review.original_documents VALUES (:id,:sha,:original)'),
                          {'id': ident, 'sha': digest, 'original': original})
            c.execute(text('INSERT INTO level16_review.evidence_bundles VALUES (:stream,CAST(:manifest AS jsonb),:ids,:signed)'),
                      {'stream': stream, 'manifest': json.dumps(manifest), 'ids': [d[0] for d in documents], 'signed': signed})
            for person in self.people.values():
                c.execute(text('INSERT INTO level16_review.evidence_access VALUES (:issuer,:person,:stream,true)'),
                          {'issuer': REALM, 'person': person, 'stream': stream})
            if activate:
                c.execute(text('''INSERT INTO level16_review.current_evidence_versions VALUES (:nct,:level,:stream,1)
                    ON CONFLICT(nct,level) DO UPDATE SET stream_id=EXCLUDED.stream_id,generation=current_evidence_versions.generation+1'''),
                          {'nct': b['nct'], 'level': b['level'], 'stream': stream})
        return stream, b, manifest

    def history(self, who='admin', stream=None):
        return self.service.history(self.tokens[who], stream or self.stream)['events']

    def append(self, state='SOURCE_SUBMITTED', who='submitter', **changes):
        return self.service.append(self.tokens[who], command(self.history(who), state,
                                   streamId=self.stream, binding=self.binding, **changes))

    def through(self, count=9):
        who = ['submitter', 'verifier', 'verifier', 'clinical', 'clinical', 'challenger', 'challenger', 'admin', 'admin']
        for i, state in enumerate(policy.STAGES[:count]): self.append(state, who[i])

    def test_real_signature_sessions_original_bytes_and_full_independent_lifecycle(self):
        self.through()
        projection = self.service.projection(self.tokens['admin'], self.binding['nct'], self.binding['level'])
        self.assertTrue(projection['independentlyAdjudicated'])
        self.assertEqual(len(projection['history']), 9)
        self.assertEqual(len({e['reviewerId'] for e in projection['history']}), 5)
        self.assertFalse(projection['prospectiveBlindAssessment'])
        self.assertIsNone(self.service.history(self.tokens['admin'], self.stream)['approvalProbability'])
        with self.owner.connect() as c:
            rows = c.execute(text("SELECT decision FROM level16_review.authorization_audit")).scalars().all()
        self.assertIn('AUTHENTICATED', rows)
        self.assertIn('AUTHORIZED', rows)

    def test_protected_http_event_api_uses_signed_individual_sessions_and_full_lifecycle(self):
        who=['submitter','verifier','verifier','clinical','clinical','challenger','challenger','admin','admin']
        with TestClient(self.app) as client:
            endpoint='/api/internal/levels1-6/reviews/events'
            forged=command(streamId=self.stream,binding=self.binding,reviewerId='invented')
            self.assertEqual(client.post(endpoint,json=forged,headers={'Authorization':self.tokens['submitter']}).status_code,409)
            for index,state in enumerate(policy.STAGES):
                cmd=command(self.history(),state,streamId=self.stream,binding=self.binding)
                response=client.post(endpoint,json=cmd,headers={'Authorization':self.tokens[who[index]]})
                self.assertEqual(response.status_code,200,response.text[:300])
                self.assertEqual(response.json()['reviewerId'],self.people[who[index]])
                self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual(client.post(endpoint,json=cmd,headers={'Authorization':self.tokens['admin']}).status_code,409)
            history=client.get('/api/internal/levels1-6/reviews/'+self.stream+'/history',headers={'Authorization':self.tokens['admin']})
            self.assertEqual(history.status_code,200)
            self.assertEqual(len(history.json()['events']),9)
            self.assertIsNone(history.json()['approvalProbability'])

    def test_interface_access_is_protected_and_all_32_focus_records_preserved(self):
        self.through()
        with TestClient(self.app) as client:
            for token in ('shared-dashboard-password', 'Bearer forged', ''):
                response = client.get('/staging/levels1-6', headers={'Authorization': token})
                self.assertEqual(response.status_code, 403)
                self.assertNotIn('NCT05507203', response.text)
            response = client.get('/staging/levels1-6', headers={'Authorization': self.tokens['admin']})
            self.assertEqual(response.status_code, 200, response.text[:300])
            self.assertIn('SYNTHETIC TEST HARNESS', response.text)
            self.assertIn('Independently adjudicated finding', response.text)
            self.assertIn('Source attestation authority:', response.text)
            self.assertIn('https://source.example.test', response.text)
            for nct in ('NCT05031780','NCT06747468','NCT06553768'): self.assertIn(nct, response.text)
            self.assertIn('NOT_MAPPED_APPLICATION_CYCLE', response.text)
            self.assertIn('ORIGINAL_EVIDENCE_NOT_PROVISIONED', response.text)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertIn("frame-ancestors 'none'", response.headers['content-security-policy'])
            self.assertFalse(client.get('/staging/status').json()['liveIntegrationEnabled'])

    def test_protected_original_document_download_and_evidence_access_revocation(self):
        path = '/staging/evidence/' + self.stream + '/' + self.binding['documentId']
        with TestClient(self.app) as client:
            self.assertEqual(client.get(path).status_code, 403)
            response = client.get(path, headers={'Authorization': self.tokens['clinical']})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(hashlib.sha256(response.content).hexdigest(), self.binding['documentSha256'])
            self.assertIn('attachment', response.headers['content-disposition'])
            with self.owner.begin() as c:
                c.execute(text('UPDATE level16_review.evidence_access SET enabled=false WHERE subject=:person'), {'person': self.people['clinical']})
            self.assertEqual(client.get(path, headers={'Authorization': self.tokens['clinical']}).status_code, 403)

    def test_revoked_session_and_token_are_rejected(self):
        with self.owner.begin() as c:
            c.execute(text('UPDATE level16_review.identity_sessions SET revoked_at=clock_timestamp() WHERE session_id=:sid'), {'sid': self.claims['clinical']['sid']})
            c.execute(text('INSERT INTO level16_review.revoked_tokens(token_issuer,token_id,session_id) VALUES (:issuer,:jti,:sid)'),
                      {'issuer': IDENTITY_ISSUER, 'jti': self.claims['challenger']['jti'], 'sid': self.claims['challenger']['sid']})
        for who in ('clinical','challenger'):
            with self.assertRaises(policy.ReviewDenied): self.identity.authenticate(self.tokens[who])
        with self.owner.connect() as c:
            self.assertGreater(c.execute(text("SELECT count(*) FROM level16_review.authorization_audit WHERE decision='DENIED'")).scalar(), 0)

    def test_valid_after_session_invalidation_and_mid_request_revocation(self):
        actor = self.identity.authenticate(self.tokens['admin'])
        with self.owner.begin() as c:
            c.execute(text('UPDATE level16_review.identity_sessions SET valid_after=clock_timestamp()+interval \'1 second\' WHERE session_id=:sid'), {'sid': self.claims['admin']['sid']})
        with self.assertRaises(policy.ReviewDenied):
            with self.runtime.begin() as c: self.identity.authorize_in_transaction(actor, c)

    def test_signed_but_ungranted_or_claimed_roles_do_not_authorize(self):
        with self.assertRaises(policy.ReviewDenied): self.identity.authenticate(self.tokens['ungranted'])
        claimed = dict(self.claims['clinical'], roles=['REVIEW_ADMIN'])
        with self.assertRaises(policy.ReviewDenied): self.identity.authenticate('Bearer ' + sign(self.private, claimed))
        with self.assertRaises(policy.ReviewDenied): self.append(who='clinical')

    def test_alias_account_for_same_person_cannot_independently_challenge(self):
        self.through(5)
        claims = access_claims('SYNTHETIC_TEST_ONLY:second-account-same-person')
        with self.owner.begin() as c:
            self.provision_account(c, claims, self.people['clinical'])
            c.execute(text('INSERT INTO level16_review.reviewer_grants VALUES (:issuer,:person,\'INDEPENDENT_CHALLENGER\',true)'),
                      {'issuer': REALM, 'person': self.people['clinical']})
        token = 'Bearer ' + sign(self.private, claims)
        same = self.identity.authenticate(token)
        self.assertEqual(same.subject, self.people['clinical'])
        with self.assertRaises(policy.ReviewDenied):
            self.service.append(token, command(self.history(), 'INDEPENDENT_CHALLENGE_PENDING', streamId=self.stream, binding=self.binding))

    def test_missing_or_modified_original_bytes_are_rejected(self):
        for index, changes in enumerate(({'bytes_override':b''}, {'bytes_override':b'MODIFIED_SYNTHETIC_BYTES'}, {'missing_bytes':True})):
            stream, b, _ = self.provision(version=index+2, **changes)
            with self.assertRaises(policy.ReviewConflict):
                self.service.append(self.tokens['submitter'], command(streamId=stream, binding=b))

    def test_source_attestation_signature_binding_and_verifier_authorization(self):
        variants = ({'foreign_signature': True}, {'attestation_changes': {'manifestDigest': '0' * 64}},
                    {'attestation_changes': {'sub': self.people['clinical']}},
                    {'attestation_changes': {'exp': int(time.time())-1}},
                    {'attestation_changes': {'checks': {'originalDocument': True}}})
        for i, changes in enumerate(variants):
            stream, b, _ = self.provision(version=i+2, **changes)
            with self.subTest(changes=changes), self.assertRaises((policy.ReviewDenied,policy.ReviewConflict)):
                self.service.append(self.tokens['submitter'], command(streamId=stream, binding=b))

    def test_cutoff_wrong_nct_and_cross_application_amendments(self):
        for i, changes in enumerate(({'cutoffDate':'2026-11-01'}, {'cutoffDate':(datetime.now(timezone.utc).date()+timedelta(days=1)).isoformat()}, {'nct':'NCT99999999'},
                                      {'applicationCycleId':'invented','applicationIdentityVerified':True})):
            stream, b, _ = self.provision(version=i+2, binding_changes=changes)
            with self.assertRaises((policy.ReviewConflict, ValueError)):
                self.service.append(self.tokens['submitter'], command(streamId=stream, binding=b))

    def test_amendments_require_their_own_original_bytes_and_cutoff(self):
        stream, b, manifest = self.provision(version=2, amendment=True)
        result = self.service.append(self.tokens['submitter'], command(streamId=stream, binding=b))
        self.assertEqual(result['binding']['evidenceVersion'], self.binding['evidenceVersion']+1)
        # An extra amendment pointing into another application cannot borrow
        # the primary original bytes or an approved source-attestation issuer.
        amend = dict(b, documentId='synthetic-cross-application', applicationCycleId='invented', applicationIdentityVerified=True)
        stream, b, _ = self.provision(version=3, manifest_changes={'amendments':[amend]})
        with self.assertRaises((policy.ReviewConflict,ValueError)):
            self.service.append(self.tokens['submitter'], command(streamId=stream, binding=b))

    def test_historical_outcome_archive_flags_rejected(self):
        for i, changes in enumerate(({'historicalOutcomeExposed':True}, {'purpose':'OUTCOME_AWARE_ARCHIVE'})):
            stream,b,_ = self.provision(version=i+2, manifest_changes=changes)
            with self.assertRaises(policy.ReviewConflict): self.service.append(self.tokens['submitter'], command(streamId=stream,binding=b))

    def test_new_evidence_invalidates_current_completion_preserving_old_history(self):
        self.through()
        original = copy.deepcopy(self.history())
        new_stream,new_binding,_ = self.provision(version=2)
        projection = self.service.projection(self.tokens['admin'],new_binding['nct'],new_binding['level'])
        self.assertFalse(projection['independentlyAdjudicated'])
        self.assertEqual(projection['history'],[])
        self.assertEqual(projection['binding']['evidenceVersion'],self.binding['evidenceVersion']+1)
        self.assertEqual(self.history(),original)
        with self.assertRaises(policy.ReviewConflict): self.append('FINAL_ADJUDICATED','admin',action='CORRECTION')

    def test_concurrent_events_only_one_commits_and_history_is_append_only(self):
        gate=Barrier(2)
        def append(_):
            cmd=command(streamId=self.stream,binding=self.binding)
            gate.wait(timeout=10)
            try:
                self.service.append(self.tokens['submitter'],cmd)
                return 'accepted'
            except policy.ReviewConflict:
                return 'conflict'
        with ThreadPoolExecutor(max_workers=2) as pool: result=list(pool.map(append,range(2)))
        self.assertCountEqual(result,['accepted','conflict'])
        for statement in ('DELETE FROM level16_review.events','TRUNCATE level16_review.authorization_audit',
                          'UPDATE level16_review.original_documents SET original_bytes=NULL',
                          'UPDATE level16_review.identity_accounts SET person_id=gen_random_uuid()',
                          'UPDATE level16_review.current_evidence_versions SET generation=100',
                          'UPDATE level16_review.identity_sessions SET revoked_at=NULL'):
            with self.assertRaises(DBAPIError):
                with self.runtime.begin() as c: c.exec_driver_sql(statement)

    def test_owner_cannot_silently_delete_current_index_or_original_evidence(self):
        for statement in ('DELETE FROM level16_review.current_evidence_versions',
                          'TRUNCATE level16_review.current_evidence_versions',
                          'DELETE FROM level16_review.original_documents',
                          'DELETE FROM level16_review.evidence_bundles'):
            with self.assertRaises(DBAPIError):
                with self.owner.begin() as c: c.exec_driver_sql(statement)

    def test_missing_staging_guards_fail_closed(self):
        with self.owner.begin() as c:
            c.exec_driver_sql('ALTER TABLE level16_review.evidence_bundles DISABLE TRIGGER immutable_staging_row')
        try:
            with self.assertRaises(policy.ReviewUnavailable): self.append()
        finally:
            with self.owner.begin() as c:
                c.exec_driver_sql('ALTER TABLE level16_review.evidence_bundles ENABLE TRIGGER immutable_staging_row')

    def test_raw_database_access_without_person_context_cannot_read_evidence(self):
        with self.runtime.begin() as c:
            self.assertEqual(c.execute(text('SELECT count(*) FROM level16_review.original_documents')).scalar(),0)
            self.assertEqual(c.execute(text('SELECT count(*) FROM level16_review.events')).scalar(),0)

    def test_all_six_levels_report_separate_readiness_without_future_phase3_requirements(self):
        from app.level16_staging import _module
        initial_stream, initial_binding = self.stream, self.binding
        for level in range(1,7):
            if level != 3:
                self.stream,self.binding,_ = self.provision(version=1,binding_changes={'level':level})
            else:
                self.stream,self.binding = initial_stream,initial_binding
            self.through()
        engine,preview = _module('phase_first_levels_1_6'),_module('render_level16_focus_preview')
        roster,apps,definition = [json.loads(p.read_text(encoding='utf-8')) for p in (engine.ROSTER_PATH,engine.APPLICATIONS_PATH,engine.DEFINITION_PATH)]
        reader = lambda nct,level: self.service.projection(self.tokens['admin'],nct,level)
        report = engine.build(roster,apps,{'results':{}},definition,trusted_review_reader=reader)
        self.assertEqual((report['focusTrialCount'],report['mappedTrialCount'],report['provisionalApplicationCycleCount'],report['unmappedTrialCount']),(32,29,23,3))
        self.assertEqual(report['scientificallyAdjudicatedLevels'],6) # synthetic fixture only
        levels=next(t for t in report['trials'] if t['nct']==initial_binding['nct'])['levels']
        for item in levels:
            self.assertEqual(item['evidenceVerificationStatus'],'SOURCE_AUTHENTICATED')
            self.assertEqual(item['automatedTestStatus'],'NOT_EXECUTED_BY_REPORT')
            self.assertIsNone(item['approvalProbability'])
            self.assertIsNone(item['score'])
            self.assertEqual(item['verifiedPhaseBasis'],['PHASE2'])
        self.assertEqual(levels[2]['pivotalReadoutRequirement'],'NOT_YET_EXPECTED_AT_EARLIER_PHASE')
        self.assertEqual(levels[4]['pivotalSAPRequirement'],'NOT_YET_EXPECTED_AT_EARLIER_PHASE')
        self.assertIn('NOT_YET_EXPECTED_AT_EARLIER_PHASE',preview.render(report,trusted_review_reader=reader))

    def test_alias_of_challenger_cannot_finally_adjudicate(self):
        self.through(7)
        claims=access_claims('SYNTHETIC_TEST_ONLY:challenger-alias-'+uuid4().hex)
        with self.owner.begin() as c:
            self.provision_account(c,claims,self.people['challenger'])
            c.execute(text("INSERT INTO level16_review.reviewer_grants VALUES(:issuer,:person,'REVIEW_ADMIN',true)"),
                      {'issuer':REALM,'person':self.people['challenger']})
        with self.assertRaises(policy.ReviewDenied):
            self.service.append('Bearer '+sign(self.private,claims),command(self.history(),'FINAL_ADJUDICATION_PENDING',streamId=self.stream,binding=self.binding))

    def test_current_evidence_index_is_locked_during_review_append(self):
        next_stream,_,_ = self.provision(version=2,activate=False)
        locked,release=Event(),Event()
        original_current=self.evidence.current
        def blocked_current(stream,connection):
            result=original_current(stream,connection)
            locked.set()
            if not release.wait(timeout=10): raise RuntimeError('Test release timeout')
            return result
        self.evidence.current=blocked_current
        def write():
            return self.service.append(self.tokens['submitter'],command(streamId=self.stream,binding=self.binding))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(write)
            try:
                self.assertTrue(locked.wait(timeout=10))
                with self.assertRaises(DBAPIError):
                    with self.owner.begin() as c:
                        self.assertFalse(c.connection.driver_connection.autocommit)
                        c.exec_driver_sql("SET LOCAL lock_timeout='100ms'")
                        c.execute(text("UPDATE level16_review.current_evidence_versions SET stream_id=:stream,generation=generation+1 WHERE nct=:nct AND level=:level"),
                                  {'stream':next_stream,'nct':self.binding['nct'],'level':self.binding['level']})
            finally:
                release.set()
            self.assertEqual(future.result(timeout=10)['status'],'SOURCE_SUBMITTED')
        self.evidence.current=original_current
        with self.owner.begin() as c:
            c.execute(text("UPDATE level16_review.current_evidence_versions SET stream_id=:stream,generation=generation+1 WHERE nct=:nct AND level=:level"),
                      {'stream':next_stream,'nct':self.binding['nct'],'level':self.binding['level']})
        with self.assertRaises(policy.ReviewConflict): self.append('SOURCE_AUTHENTICATION_PENDING','verifier')

    def test_source_only_cannot_complete_assessment_or_ignore_contradictions(self):
        self.through(3)
        projection=self.service.projection(self.tokens['admin'],self.binding['nct'],self.binding['level'])
        self.assertFalse(projection['independentlyAdjudicated'])
        self.assertEqual(projection['clinicalReviewStatus'],'NOT_COMPLETED')
        self.append('SCIENTIFIC_REVIEW_PENDING','clinical')
        with self.assertRaises(policy.ReviewConflict):
            self.append('SCIENTIFIC_REVIEW_COMPLETED','clinical',contradictoryEvidence=['Synthetic unresolved clinical contradiction'])


if __name__=='__main__': unittest.main()
