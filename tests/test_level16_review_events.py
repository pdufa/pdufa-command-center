"""Policy/HTTP tests use synthetic identities, never a production auth provider."""
import copy
import sys
import unittest
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'new-platform/backend'))
from app import level16_review_policy as policy
from app.level16_review_events import ReviewEventService, build_router
from fastapi import FastAPI
from fastapi.testclient import TestClient


def binding(**changes):
    result = dict(nct='NCT05507203', company='Abivax S.A.', ticker='ABVX', indication='Synthetic test population',
                  phases=['PHASE2'], registryStatus='RECRUITING', applicationCycleId=None,
                  applicationIdentityVerified=False, level=3, documentId='synthetic-document',
                  documentSha256='a' * 64, documentVersion='Synthetic v1', protocolVersion='Synthetic p1',
                  cutoffDate='2026-11-13', sourceUrl='https://example.org/synthetic',
                  publicationDate='2026-11-01', retrievalDate='2026-11-02', evidenceVersion=1)
    result.update(changes)
    return result


def command(history=None, status='SOURCE_SUBMITTED', **changes):
    history = history or []
    result = dict(eventId=str(uuid4()), streamId=str(uuid4()), previousEventId=history[-1]['eventId'] if history else None,
                  expectedVersion=len(history), binding=binding(), action='TRANSITION', status=status,
                  findings=['Synthetic findings; not actual clinical evidence'], reasons=['Synthetic supporting reasons'],
                  contradictoryEvidence=[], limitations=['Synthetic test only; no actual verified medical review'], blockers=[])
    result.update(changes)
    return result


def history_through(count):
    return [dict(eventId=str(uuid4()), status=state, reviewerIssuer='synthetic-test',
                 reviewerId='SOURCE_SUBMITTER' if state == 'SOURCE_SUBMITTED' else policy.ROLES[state], authorizedRole=policy.ROLES[state]) for state in policy.STAGES[:count]]


class SyntheticIdentityProvider:
    """Server-injected test fixture; NEVER usable in the production interface."""
    def authenticate(self, token):
        identities = {'synthetic-source-token': policy.SOURCE_VERIFIER,
                      'synthetic-submitter-token': 'SOURCE_SUBMITTER',
                      'synthetic-clinical-token': policy.CLINICAL_REVIEWER,
                      'synthetic-challenge-token': policy.INDEPENDENT_CHALLENGER,
                      'synthetic-admin-token': policy.REVIEW_ADMIN,
                      'synthetic-ungranted-token': 'UNGRANTED'}
        if token not in identities:
            raise policy.ReviewDenied('Synthetic identity provider rejected token')
        return policy.Identity('synthetic-test', identities[token])


class SyntheticEvidenceProvider:
    def __init__(self, value=None):
        self.binding = value or binding()
        self.checks = dict.fromkeys(policy.SOURCE_CHECKS, True)

    def current(self, stream, connection):
        return copy.deepcopy(self.binding)

    def authentication_checks(self, stream, actor, connection):
        return copy.deepcopy(self.checks)


class ReviewPolicyTests(unittest.TestCase):
    def test_all_stages_and_roles(self):
        for count, state in enumerate(policy.STAGES):
            history = history_through(count)
            cmd = command(history, state)
            policy.validate_command(cmd)
            role = policy.ROLES[state]
            self.assertEqual(policy.required_role(cmd, history, policy.Identity('synthetic-test', role)), role)

    def test_no_stage_skips(self):
        for count in range(len(policy.STAGES)):
            for state in policy.STAGES:
                if state == policy.STAGES[count]:
                    continue
                history = history_through(count)
                with self.subTest(count=count, state=state), self.assertRaises(policy.ReviewConflict):
                    policy.required_role(command(history, state), history, policy.Identity('issuer', 'other'))

    def test_self_challenge_and_own_final_adjudication_denied(self):
        for state, count in (('INDEPENDENT_CHALLENGE_PENDING', 5), ('INDEPENDENT_CHALLENGE_COMPLETED', 6),
                             ('FINAL_ADJUDICATION_PENDING', 7), ('FINAL_ADJUDICATED', 8)):
            history = history_through(count)
            actor = policy.Identity('synthetic-test', policy.CLINICAL_REVIEWER)
            with self.subTest(state=state), self.assertRaises(policy.ReviewDenied):
                policy.required_role(command(history, state), history, actor)

    def test_source_submitter_cannot_authenticate_or_clinically_review_own_evidence(self):
        history = history_through(2)
        with self.assertRaises(policy.ReviewDenied):
            policy.required_role(command(history, 'SOURCE_AUTHENTICATED'), history, policy.Identity('synthetic-test', 'SOURCE_SUBMITTER'))
        history = history_through(3)
        with self.assertRaises(policy.ReviewDenied):
            policy.required_role(command(history, 'SCIENTIFIC_REVIEW_PENDING'), history, policy.Identity('synthetic-test', policy.SOURCE_VERIFIER))

    def test_stale_predecessor_and_version(self):
        history = history_through(1)
        for changes in ({'expectedVersion': 0}, {'previousEventId': str(uuid4())}):
            with self.assertRaises(policy.ReviewConflict):
                policy.required_role(command(history, policy.STAGES[1], **changes), history, policy.Identity('i', 's'))

    def test_corrections_append_same_author_status_only(self):
        history = history_through(5)
        cmd = command(history, policy.STAGES[4], action='CORRECTION')
        self.assertEqual(policy.required_role(cmd, history, policy.Identity('synthetic-test', policy.CLINICAL_REVIEWER)), policy.CLINICAL_REVIEWER)
        with self.assertRaises(policy.ReviewDenied):
            policy.required_role(cmd, history, policy.Identity('synthetic-test', 'different'))

    def test_corrected_completed_findings_require_new_review_cycle(self):
        history = history_through(9)
        history[-1]['action'] = 'CORRECTION'
        with self.assertRaises(policy.ReviewConflict):
            policy.required_role(command(history, 'FINAL_ADJUDICATED'), history, policy.Identity('i', 'a'))
        self.assertEqual(policy.required_role(command(history, 'SOURCE_AUTHENTICATION_PENDING'), history,
                                             policy.Identity('i', 'source')), policy.SOURCE_VERIFIER)

    def test_conflicts_and_missing_evidence_block_completion(self):
        history = history_through(4)
        for changes in ({'blockers': ['Missing phase-appropriate evidence']}, {'contradictoryEvidence': ['Unresolved clinical contradiction']}):
            with self.assertRaises(policy.ReviewConflict):
                policy.required_role(command(history, policy.STAGES[4], **changes), history, policy.Identity('i', 's'))
        cmd = command(history, 'CONFLICT_UNRESOLVED')
        with self.assertRaises(ValueError): policy.validate_command(cmd)
        cmd['contradictoryEvidence'] = ['Registry/protocol conflict']
        policy.validate_command(cmd)
        self.assertEqual(policy.required_role(cmd, history, policy.Identity('i', 'admin')), policy.REVIEW_ADMIN)

    def test_exception_resolution_restarts_authentication(self):
        for state in ('CONFLICT_UNRESOLVED', 'ADDITIONAL_EVIDENCE_REQUIRED'):
            history = history_through(4) + [dict(eventId=str(uuid4()), status=state, reviewerIssuer='i', reviewerId='a', authorizedRole=policy.REVIEW_ADMIN)]
            for target in ('SOURCE_AUTHENTICATION_PENDING', 'FINAL_ADJUDICATED'):
                cmd = command(history, target)
                if target == 'SOURCE_AUTHENTICATION_PENDING':
                    policy.required_role(cmd, history, policy.Identity('i', 'v'))
                else:
                    with self.assertRaises(policy.ReviewConflict): policy.required_role(cmd, history, policy.Identity('i', 'v'))

    def test_early_phase_applicability_does_not_waive_provenance(self):
        history = history_through(1)
        for level in range(1, 7):
            for phase in ('PHASE1', 'PHASE2', 'PHASE3', 'PHASE4'):
                cmd = command(history, 'NOT_APPLICABLE_AT_CURRENT_PHASE', binding=binding(level=level, phases=[phase]))
                if level in (3, 5) and phase in ('PHASE1', 'PHASE2'):
                    policy.required_role(cmd, history, policy.Identity('i', 'admin'))
                else:
                    with self.assertRaises(policy.ReviewDenied): policy.required_role(cmd, history, policy.Identity('i', 'admin'))

    def test_caller_authorization_timestamp_and_prediction_fields_rejected(self):
        for key in ('reviewerId', 'authorizedRole', 'reviewer', 'tokenVerified', 'serverTimestamp', 'eventVersion', 'approvalProbability', 'fdaOutcomeJudgment'):
            with self.subTest(key=key), self.assertRaises(ValueError): policy.validate_command(command(**{key: 'invented'}))

    def test_missing_phase_invalid_cutoff_and_false_application_verification(self):
        for changes in ({'phases': []}, {'cutoffDate': '2026-11-01'}, {'applicationCycleId': 'invented'},
                        {'applicationIdentityVerified': True}, {'level': True}, {'documentVersion': ''}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): policy.validate_binding(binding(**changes))

    def test_default_http_fails_closed_for_every_unverified_credential(self):
        app = FastAPI()
        app.include_router(build_router())
        with TestClient(app) as client:
            for credential in ('Bearer forged.jwt.token', 'shared-internal-key', 'arbitrary-name', ''):
                response = client.post('/api/internal/levels1-6/reviews/events', json=command(), headers={'Authorization': credential})
                self.assertEqual(response.status_code, 503)
            response = client.get('/api/internal/levels1-6/reviews/' + str(uuid4()) + '/history')
            self.assertEqual(response.status_code, 503)

    def test_offline_json_cannot_forge_authorization_or_history(self):
        import importlib.util
        def load(name):
            spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/medical' / (name + '.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        import json
        engine, preview = load('phase_first_levels_1_6'), load('render_level16_focus_preview')
        r, a, d = [json.loads(p.read_text(encoding='utf-8')) for p in (engine.ROSTER_PATH, engine.APPLICATIONS_PATH, engine.DEFINITION_PATH)]
        report = engine.build(r, a, {'results': {}}, d)
        for key, value in (('originalDocumentAuthenticationStatus', 'SOURCE_AUTHENTICATED'),
                           ('reviewerAuthorizationStatus', 'SERVER_AUTHORIZED_EVENTS'),
                           ('independentChallengeStatus', 'INDEPENDENT_CHALLENGE_COMPLETED'),
                           ('history', [{'eventId': 'invented'}])):
            forged = copy.deepcopy(report)
            forged['trials'][0]['levels'][0]['reviewWorkflow'][key] = value
            with self.assertRaises(ValueError): preview.render(forged)
        report['scientificallyAdjudicatedLevels'] = 192
        with self.assertRaises(ValueError): preview.render(report)

    def test_json_identity_from_adapter_is_not_a_verified_principal(self):
        class BadAdapter:
            def authenticate(self, token): return {'issuer': 'invented', 'subject': 'forged', 'role': 'REVIEW_ADMIN'}
        with self.assertRaises(policy.ReviewDenied):
            ReviewEventService(identity_provider=BadAdapter()).append('fake', command())

    def test_no_postgres_fallback_even_with_synthetic_identity(self):
        from sqlalchemy import create_engine
        for engine in (None, create_engine('sqlite://')):
            service = ReviewEventService(engine, identity_provider=SyntheticIdentityProvider())
            with self.assertRaises(policy.ReviewUnavailable): service.append('synthetic-source-token', command())


if __name__ == '__main__': unittest.main()
