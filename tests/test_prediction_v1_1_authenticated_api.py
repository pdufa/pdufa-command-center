"""Real RSA JWT + isolated HTTP authorization tests; no production provider."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from research.prediction_v1_1_authenticated_api import create_research_api
from research.prediction_v1_1_oidc_preflight import OIDCConfiguration
from research.prediction_v1_1_oidc_verifier import OIDCVerifier, VerifiedIdentity
from research.prediction_v1_1_principal_directory import PrincipalDirectory
from research.prediction_v1_1_storage_adapter import open_research_evidence_store
from research.prediction_v1_1_integrity_gate import audit_all_research_chains

ISSUER='https://identity.example.test'
AUDIENCE='pdufa-research'
PROGRAM='TEST|NCT00000000'
OTHER='OTHER|NCT00000001'
CATALOG=json.loads((Path(__file__).parents[1]/'research/evidence/prediction_v1_1_field_catalog_draft.json').read_text())
SUBMISSION={'program_id':PROGRAM,'field_id':'TRIAL-001',
            'source_url':'https://clinicaltrials.gov/study/NCT00000000',
            'source_document_sha256':'a'*64,'source_published_at':'2026-01-01T00:00:00Z',
            'observed_at':'2026-01-02T00:00:00Z','evidence_excerpt':'Synthetic test source; no scientific validation',
            'applicability_rationale':'Pivotal test trial','status':'UNVERIFIED'}
REVIEW={'outcome':'APPROVE_PROVENANCE','checks':{'source_bytes':True,'publication_date':True,'identity':True},
        'rationale':'Synthetic independent test review, not actual evidence authentication'}


def account(subject,principal,roles,programs=(PROGRAM,),active=True):
    return {'issuer':ISSUER,'subject':subject,'principal':principal,'roles':list(roles),
            'program_ids':list(programs),'active':active}


class AuthenticatedResearchAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.other_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
        cls.jwk=json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(cls.key.public_key()))
        cls.jwk.update(kid='research-test',alg='RS256',use='sig')

    def setUp(self):
        self.root=tempfile.TemporaryDirectory()
        self.path=Path(self.root.name)/'research.sqlite3'
        self.records=[account('submitter-sub','person-a',('evidence_reader','evidence_submitter','evidence_reviewer')),
                      account('submitter-alias','person-a',('evidence_reviewer',)),
                      account('reviewer-sub','person-b',('evidence_reader','evidence_reviewer')),
                      account('reader-sub','person-c',('evidence_reader',)),
                      account('outsider-sub','person-d',('evidence_reader','evidence_submitter','evidence_reviewer'),(OTHER,)),
                      account('disabled-sub','person-e',('evidence_reader',),active=False)]
        self.directory=PrincipalDirectory(self.records)
        self.verifier=OIDCVerifier(OIDCConfiguration(ISSUER,AUDIENCE,ISSUER+'/jwks'),
                                   jwks_fetcher=lambda _: {'keys':[self.jwk]})
        self.app=create_research_api(verifier=self.verifier,directory=self.directory,
                                    store_path=self.path,catalog=CATALOG)
        self.client=TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.root.cleanup()

    def token(self,subject='submitter-sub',**claims):
        now=datetime.now(timezone.utc)
        payload={'iss':ISSUER,'aud':AUDIENCE,'sub':subject,'iat':now,'nbf':now-timedelta(seconds=1),
                 'exp':now+timedelta(minutes=5)}
        payload.update(claims)
        return jwt.encode(payload,self.key,algorithm='RS256',headers={'kid':'research-test'})

    def headers(self,subject='submitter-sub',**claims):
        return {'Authorization':'Bearer '+self.token(subject,**claims)}

    def submit(self,subject='submitter-sub',payload=None,**claims):
        return self.client.post('/research/v1-1/evidence',json=deepcopy(SUBMISSION if payload is None else payload),
                                headers=self.headers(subject,**claims))

    def review(self,event,subject='reviewer-sub',payload=None,**claims):
        return self.client.post(f'/research/v1-1/reviews/{event}',json=deepcopy(REVIEW if payload is None else payload),
                                headers=self.headers(subject,**claims))

    def counts(self):
        conn=open_research_evidence_store(self.path)
        try:
            return tuple(conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
                         for table in ('evidence_events','evidence_submitter_bindings','review_events'))
        finally:conn.close()

    def test_authenticated_and_denied_responses_are_not_cached(self):
        response=self.client.get('/research/v1-1/evidence/'+PROGRAM, headers=self.headers('reader-sub'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers.get('cache-control'),'private, no-store')
        denied=self.client.get('/research/v1-1/evidence/'+PROGRAM)
        self.assertEqual(denied.status_code,401)
        self.assertEqual(denied.headers.get('cache-control'),'private, no-store')

    def test_unconfigured_factory_fails_closed(self):
        with TestClient(create_research_api()) as client:
            self.assertEqual(client.get('/research/v1-1/evidence/'+PROGRAM).status_code,503)
            self.assertEqual(client.post('/research/v1-1/evidence',json=SUBMISSION).status_code,503)
            self.assertEqual(client.post('/research/v1-1/reviews/1',json=REVIEW).status_code,503)
        self.assertFalse(self.path.exists())

    def test_anonymous_expired_forged_and_wrong_audience_rejected_without_storage(self):
        url='/research/v1-1/evidence/'+PROGRAM
        self.assertEqual(self.client.get(url).status_code,401)
        for token in ('not-a-token', self.token(exp=datetime.now(timezone.utc)-timedelta(minutes=1)),
                      self.token(aud='another-service'), self.token(iss='https://evil.example.test'),
                      jwt.encode({'iss':ISSUER,'aud':AUDIENCE,'sub':'submitter-sub','iat':datetime.now(timezone.utc),
                                  'exp':datetime.now(timezone.utc)+timedelta(minutes=1)},self.other_key,
                                  algorithm='RS256',headers={'kid':'research-test'})):
            response=self.client.get(url,headers={'Authorization':'Bearer '+token})
            self.assertEqual(response.status_code,401,response.text)
        self.assertFalse(self.path.exists())

    def test_server_grants_override_forged_token_roles_programs_and_headers(self):
        forged={'roles':['evidence_submitter','evidence_reviewer'],'program_ids':[PROGRAM],'principal':'person-a'}
        response=self.submit('reader-sub',**forged)
        self.assertEqual(response.status_code,403)
        response=self.client.get('/research/v1-1/evidence/'+PROGRAM,
            headers={**self.headers('outsider-sub',**forged),'x-user-role':'evidence_reader','x-program-id':PROGRAM})
        self.assertEqual(response.status_code,403)
        self.assertFalse(self.path.exists())

    def test_valid_token_is_not_automatic_enrollment_or_activation(self):
        for subject in ('new-unregistered-sub','disabled-sub'):
            self.assertEqual(self.client.get('/research/v1-1/evidence/'+PROGRAM,headers=self.headers(subject)).status_code,403)
        self.assertFalse(self.path.exists())

    def test_submission_binds_server_actor_and_stays_unverified(self):
        response=self.submit(principal='forged-client-principal',roles=['evidence_reviewer'])
        self.assertEqual(response.status_code,201,response.text)
        result=response.json()
        self.assertEqual(result['authenticated_submitter'],'person-a')
        self.assertFalse(result['independently_verified'])
        self.assertEqual(result['readiness'],'NOT_READY')
        self.assertEqual(result['decision'],'ABSTAIN')
        conn=open_research_evidence_store(self.path)
        try:
            payload=json.loads(conn.execute('SELECT payload_json FROM evidence_events').fetchone()[0])
            self.assertEqual(payload['submitted_by_principal'],'person-a')
            self.assertIsNone(payload['reviewer_id'])
            self.assertEqual(conn.execute('SELECT submitter_principal FROM evidence_submitter_bindings').fetchone()[0],'person-a')
            self.assertTrue(audit_all_research_chains(conn)['valid'])
        finally:conn.close()

    def test_client_cannot_select_actor_review_flags_or_status(self):
        for field,value in [('reviewer_id','person-b'),('submitter_principal','person-b'),
                            ('submitted_by_principal','person-b'),('independent_review_confirmed',True),
                            ('roles',['evidence_submitter']),('status','VERIFIED')]:
            changed={**SUBMISSION,field:value}
            response=self.submit(payload=changed)
            self.assertEqual(response.status_code,422,(field,response.text))
        self.assertFalse(self.path.exists())

    def test_cross_program_submit_rejected_before_any_write(self):
        self.assertEqual(self.submit('outsider-sub').status_code,403)
        self.assertEqual(self.submit(payload={**SUBMISSION,'program_id':OTHER}).status_code,403)
        self.assertFalse(self.path.exists())

    def test_independent_review_and_read_preserve_abstention_and_append_only_history(self):
        event=self.submit().json()['event_id']
        response=self.review(event)
        self.assertEqual(response.status_code,201,response.text)
        self.assertFalse(response.json()['independently_verified'])
        self.assertEqual(response.json()['decision'],'ABSTAIN')
        response=self.client.get('/research/v1-1/evidence/'+PROGRAM,headers=self.headers('reviewer-sub'))
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['decision'],'ABSTAIN')
        conn=open_research_evidence_store(self.path)
        try:
            self.assertTrue(audit_all_research_chains(conn)['valid'])
            for sql in ('DELETE FROM evidence_events','DELETE FROM evidence_submitter_bindings','DELETE FROM review_events'):
                with self.assertRaises(sqlite3.DatabaseError):conn.execute(sql)
        finally:conn.close()

    def test_self_review_including_external_identity_alias_is_denied(self):
        event=self.submit().json()['event_id']
        for subject in ('submitter-sub','submitter-alias'):
            self.assertEqual(self.review(event,subject).status_code,403)
        self.assertEqual(self.counts(),(1,1,0))

    def test_cross_program_missing_binding_and_wrong_role_reviews_are_denied(self):
        event=self.submit().json()['event_id']
        for subject in ('outsider-sub','reader-sub'):
            self.assertEqual(self.review(event,subject).status_code,403)
        self.assertEqual(self.review(event+1).status_code,403)
        self.assertEqual(self.counts(),(1,1,0))

    def test_client_review_actor_and_extra_checks_are_rejected(self):
        event=self.submit().json()['event_id']
        for changed in ({**REVIEW,'reviewer_principal':'person-a'},
                        {**REVIEW,'program_id':OTHER},
                        {**REVIEW,'checks':{**REVIEW['checks'],'admin':True}},
                        {**REVIEW,'checks':{**REVIEW['checks'],'identity':1}}):
            self.assertEqual(self.review(event,payload=changed).status_code,422)
        self.assertEqual(self.counts(),(1,1,0))

    def test_binding_failure_rolls_back_the_entire_submission(self):
        with patch('research.prediction_v1_1_authenticated_api.bind_verified_submitter',side_effect=sqlite3.IntegrityError('test failure')):
            self.assertEqual(self.submit().status_code,503)
        self.assertEqual(self.counts(),(0,0,0))

    def test_incomplete_provenance_approval_has_no_review_write(self):
        event=self.submit().json()['event_id']
        response=self.review(event,payload={**REVIEW,'checks':{**REVIEW['checks'],'source_bytes':False}})
        self.assertEqual(response.status_code,422)
        self.assertEqual(self.counts(),(1,1,0))

    def test_review_failure_rolls_back_the_new_review(self):
        from research.prediction_v1_1_review_workflow import record_review
        event=self.submit().json()['event_id']
        def fail_after_append(*args,**kwargs):
            record_review(*args,**kwargs)
            raise RuntimeError('synthetic failure after append')
        with patch('research.prediction_v1_1_authenticated_api.record_review',side_effect=fail_after_append):
            self.assertEqual(self.review(event).status_code,503)
        self.assertEqual(self.counts(),(1,1,0))

    def test_missing_database_and_untrusted_verifier_fail_closed(self):
        for app in (create_research_api(verifier=self.verifier,directory=self.directory,catalog=CATALOG),
                    create_research_api(verifier=lambda token:VerifiedIdentity(ISSUER,'submitter-sub'),
                                        directory=self.directory,catalog=CATALOG,store_path=self.path)):
            with TestClient(app) as client:
                self.assertEqual(client.get('/research/v1-1/evidence/'+PROGRAM,headers=self.headers()).status_code,503)
        self.assertFalse(self.path.exists())
        with self.assertRaises(ValueError):
            create_research_api(program_cutoffs=[])

    def test_rejected_unverified_submission_is_audited_with_server_actor(self):
        response=self.submit(payload={**SUBMISSION,'source_document_sha256':'bad'})
        self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(self.counts(),(1,0,0))
        conn=open_research_evidence_store(self.path)
        try:
            kind,raw=conn.execute('SELECT event_kind,payload_json FROM evidence_events').fetchone()
            self.assertEqual(kind,'REJECTED')
            self.assertEqual(json.loads(raw)['submitted_by_principal'],'person-a')
        finally:conn.close()

    def test_directory_revocation_applies_to_existing_token(self):
        headers=self.headers('reader-sub')
        self.assertEqual(self.client.get('/research/v1-1/evidence/'+PROGRAM,headers=headers).status_code,200)
        self.directory.replace([])
        self.assertEqual(self.client.get('/research/v1-1/evidence/'+PROGRAM,headers=headers).status_code,403)

    def test_tampered_ledger_cannot_be_read_or_written(self):
        event=self.submit().json()['event_id']
        conn=sqlite3.connect(self.path)
        conn.execute('DROP TRIGGER evidence_events_no_update')
        conn.execute("UPDATE evidence_events SET payload_json='{}'")
        conn.commit();conn.close()
        self.assertEqual(self.client.get('/research/v1-1/evidence/'+PROGRAM,headers=self.headers()).status_code,503)
        self.assertEqual(self.submit().status_code,503)
        self.assertEqual(self.review(event).status_code,503)
        conn=sqlite3.connect(self.path)
        try:self.assertEqual(conn.execute('SELECT COUNT(*) FROM evidence_events').fetchone()[0],1)
        finally:conn.close()


class PrincipalDirectoryTests(unittest.TestCase):
    def test_grants_are_copied_and_not_obtained_from_client_objects(self):
        records=[account('subject','canonical-person',('evidence_reader',))]
        directory=PrincipalDirectory(records)
        records[0]['roles'].append('evidence_reviewer')
        principal=directory.resolve(VerifiedIdentity(ISSUER,'subject'))
        self.assertEqual(principal.roles,frozenset({'evidence_reader'}))
        with self.assertRaises(PermissionError):directory.resolve({'issuer':ISSUER,'subject':'subject'})

    def test_bad_grants_duplicate_subject_and_numeric_activation_rejected(self):
        valid=account('subject','person',('evidence_reader',))
        for records in ([valid,valid], [{**valid,'active':1}], [{**valid,'roles':['admin']}],
                        [{**valid,'program_ids':['*']}], [{**valid,'roles':['evidence_reader','evidence_reader']}]):
            with self.assertRaises(ValueError):PrincipalDirectory(records)

    def test_file_loader_is_explicit_versioned_and_rejects_duplicate_fields(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'grants.json'
            path.write_text(json.dumps({'schema_version':'research-principal-directory-v1','accounts':[account('s','p',('evidence_reader',))]}))
            self.assertEqual(PrincipalDirectory.from_file(path).resolve(VerifiedIdentity(ISSUER,'s')).principal,'p')
            path.write_text('{"schema_version":"research-principal-directory-v1","accounts":[],"accounts":[]}')
            with self.assertRaises(ValueError):PrincipalDirectory.from_file(path)


if __name__=='__main__':unittest.main()
