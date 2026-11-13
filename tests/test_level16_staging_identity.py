"""Synthetic cryptographic fixtures only: no real issuer, credentials or attestations."""
import sys
import time
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'new-platform/backend'))
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from app.level16_staging_identity import PinnedJwtVerifier
from app.level16_staging import create_staging_app, HarnessApproval
from app.level16_review_policy import ReviewDenied, ReviewUnavailable

IDENTITY_ISSUER = 'https://identity.example.test'
SOURCE_ISSUER = 'https://source.example.test'
IDENTITY_REF = 'SYNTHETIC_TEST_ONLY:identity-not-approved-live'
SOURCE_REF = 'SYNTHETIC_TEST_ONLY:source-not-approved-live'
AUDIENCE = 'level16-synthetic-staging'


def keypair():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    return private, public


def access_claims(subject='synthetic-subject', **changes):
    now = int(time.time())
    result = {'iss': IDENTITY_ISSUER, 'aud': AUDIENCE, 'sub': subject, 'sid': str(uuid4()),
              'jti': str(uuid4()), 'iat': now, 'nbf': now, 'exp': now + 600}
    result.update(changes)
    return result


def sign(private, claims, typ='at+jwt', kid='synthetic-key'):
    return jwt.encode(claims, private, algorithm='RS256', headers={'kid': kid, 'typ': typ})


class StagingIdentityCryptoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private, cls.public = keypair()

    def setUp(self):
        self.verifier = PinnedJwtVerifier(IDENTITY_ISSUER, AUDIENCE, {'synthetic-key': self.public}, approval_reference=IDENTITY_REF)

    def test_valid_signature_issuer_audience_expiry_and_stable_subject(self):
        claims = access_claims()
        actual = self.verifier.decode(sign(self.private, claims), required=('sid',))
        self.assertEqual(actual['sub'], claims['sub'])
        self.assertEqual(actual['iss'], IDENTITY_ISSUER)

    def test_wrong_issuer_audience_expired_future_and_excessive_lifetime(self):
        now = int(time.time())
        for changes in ({'iss': 'https://forged.example.test'}, {'aud': 'other-audience'}, {'aud': [AUDIENCE, 'other']},
                        {'exp': now - 1}, {'nbf': now + 100}, {'iat': now + 100}, {'exp': now + 9000},
                        {'sub': ''}, {'exp': str(now + 500)}):
            with self.subTest(changes=changes), self.assertRaises(ReviewDenied):
                self.verifier.decode(sign(self.private, access_claims(**changes)), required=('sid',))

    def test_forged_signature_unknown_key_and_unsigned_tokens(self):
        foreign, _ = keypair()
        for token in (sign(foreign, access_claims()), sign(self.private, access_claims(), kid='unapproved'),
                      jwt.encode(access_claims(), '', algorithm='none', headers={'typ': 'at+jwt', 'kid': 'synthetic-key'})):
            with self.assertRaises(ReviewDenied): self.verifier.decode(token)

    def test_role_escalation_and_token_controlled_key_urls_rejected(self):
        for key in ('roles', 'role', 'reviewer'):
            with self.assertRaises(ReviewDenied): self.verifier.decode(sign(self.private, access_claims(**{key: 'REVIEW_ADMIN'})))
        token = jwt.encode(access_claims(), self.private, algorithm='RS256',
                           headers={'kid': 'synthetic-key', 'typ': 'at+jwt', 'jku': 'https://forged.example.test/keys'})
        with self.assertRaises(ReviewDenied): self.verifier.decode(token)

    def test_missing_required_claims_and_wrong_token_type(self):
        for key in ('iss', 'aud', 'sub', 'exp', 'iat', 'nbf', 'jti', 'sid'):
            claims = access_claims()
            del claims[key]
            with self.assertRaises(ReviewDenied): self.verifier.decode(sign(self.private, claims), required=('sid',))
        with self.assertRaises(ReviewDenied): self.verifier.decode(sign(self.private, access_claims(), typ='JWT'))

    def test_no_approval_and_no_keys_fail_closed(self):
        for verifier in (PinnedJwtVerifier(IDENTITY_ISSUER, AUDIENCE, {'synthetic-key': self.public}),
                         PinnedJwtVerifier(IDENTITY_ISSUER, AUDIENCE, {}, approval_reference=IDENTITY_REF)):
            with self.assertRaises(ReviewUnavailable): verifier.decode(sign(self.private, access_claims()))

    def test_default_staging_app_has_no_live_reviewer_or_evidence_routes(self):
        with TestClient(create_staging_app()) as client:
            status = client.get('/staging/status').json()
            self.assertEqual(status['status'], 'BLOCKED')
            self.assertFalse(status['liveIntegrationEnabled'])
            for path in ('/staging/levels1-6', '/api/internal/levels1-6/reviews/events', '/staging/evidence/unknown/doc'):
                response = client.get(path)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn('NCT05507203', response.text)
                self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_caller_approval_claim_cannot_activate_live_mode(self):
        for approval in ({'mode': 'APPROVED', 'admin': True}, HarnessApproval('APPROVED_ISOLATED_STAGING', 'invented', 'invented', 'production')):
            with TestClient(create_staging_app(approval=approval)) as client:
                self.assertEqual(client.get('/staging/status').json()['status'], 'BLOCKED')


if __name__ == '__main__': unittest.main()
