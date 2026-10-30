"""Real RSA signature/security regressions; no live provider or credentials."""
import base64
from copy import deepcopy
from dataclasses import fields
from datetime import datetime, timezone
from email.message import Message
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from jwt.algorithms import RSAAlgorithm

from research.prediction_v1_1_oidc_preflight import OIDCConfiguration
from research.prediction_v1_1_oidc_verifier import (
    OIDCVerifier, VerifiedIdentity, AuthenticationError, CACHE_SECONDS,
    MAX_JWKS_BYTES, _NoRedirects, _fetch_jwks,
)

CONFIG = OIDCConfiguration('https://identity.example.org/', 'pdufa-research-api',
                           'https://identity.example.org/jwks.json')


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


class OIDCVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.weak = rsa.generate_private_key(public_exponent=65537, key_size=1024)

    def setUp(self):
        now = int(datetime.now(timezone.utc).timestamp())
        self.claims = {'iss': CONFIG.issuer, 'aud': CONFIG.audience, 'sub': 'provider|alice',
                       'iat': now - 5, 'nbf': now - 5, 'exp': now + 300}
        self.jwk = self.jwk_for(self.key, 'key-one')
        self.calls = []
        self.document = {'keys': [self.jwk]}
        self.verifier = OIDCVerifier(CONFIG, jwks_fetcher=self.fetch)

    def jwk_for(self, private, kid):
        value = json.loads(RSAAlgorithm.to_jwk(private.public_key()))
        return {**value, 'kid': kid, 'alg': 'RS256', 'use': 'sig', 'key_ops': ['verify']}

    def fetch(self, uri):
        self.calls.append(uri)
        return deepcopy(self.document)

    def token(self, *, claims=None, headers=None, key=None, algorithm='RS256'):
        return jwt.encode(self.claims if claims is None else claims,
                          self.key if key is None else key, algorithm=algorithm,
                          headers={'kid': 'key-one', **(headers or {})})

    def assert_denied(self, token):
        with self.assertRaises(AuthenticationError):
            self.verifier.verify_token(token)

    def test_real_signature_yields_only_verified_issuer_and_subject(self):
        claims = {**self.claims, 'roles': ['admin'], 'program_ids': ['ALL'], 'is_authenticated': True}
        identity = self.verifier.verify_token(self.token(claims=claims))
        self.assertEqual(identity, VerifiedIdentity(CONFIG.issuer, 'provider|alice'))
        self.assertEqual({f.name for f in fields(identity)}, {'issuer', 'subject'})
        self.assertEqual(self.calls, [CONFIG.jwks_uri])

    def test_audience_array_can_include_exact_api_audience(self):
        claims = {**self.claims, 'aud': [CONFIG.audience, 'other-accepted-service']}
        self.assertEqual(self.verifier.verify_token(self.token(claims=claims)).subject, self.claims['sub'])

    def test_required_claims_are_not_optional(self):
        for claim in ('exp', 'iat', 'iss', 'aud', 'sub'):
            with self.subTest(claim=claim):
                claims = dict(self.claims); del claims[claim]
                self.assert_denied(self.token(claims=claims))

    def test_wrong_issuer_or_audience_is_denied_without_key_fetch(self):
        for field, value in [('iss', 'https://attacker.example/'), ('aud', 'wrong'),
                             ('aud', []), ('aud', [CONFIG.audience, CONFIG.audience]),
                             ('aud', [CONFIG.audience, 1])]:
            with self.subTest(field=field, value=value):
                self.assert_denied(self.token(claims={**self.claims, field: value}))
        self.assertEqual(self.calls, [])

    def test_expired_future_issued_and_future_not_before_tokens_are_denied(self):
        now = int(datetime.now(timezone.utc).timestamp())
        for changes in ({'exp': now - 1, 'iat': now - 10, 'nbf': now - 10},
                        {'iat': now + 50}, {'nbf': now + 50},
                        {'exp': self.claims['iat']}, {'nbf': self.claims['exp']}):
            with self.subTest(changes=changes):
                self.assert_denied(self.token(claims={**self.claims, **changes}))

    def test_cached_key_never_caches_token_expiration_acceptance(self):
        self.verifier.verify_token(self.token())
        now = int(datetime.now(timezone.utc).timestamp())
        expired = {**self.claims, 'exp': now - 1, 'iat': now - 10, 'nbf': now - 10}
        self.assert_denied(self.token(claims=expired))
        self.assertEqual(len(self.calls), 1)

    def test_boolean_string_and_float_timestamp_claims_are_rejected(self):
        for field in ('exp', 'iat', 'nbf'):
            for value in (True, False, '1234567890', 1.5, None):
                with self.subTest(field=field, value=value):
                    self.assert_denied(self.token(claims={**self.claims, field: value}))

    def test_subject_must_be_canonical_nonempty_text(self):
        for value in ('', ' ', ' padded ', 'line\nfeed', 'a' * 257, 123, None):
            with self.subTest(value=value):
                self.assert_denied(self.token(claims={**self.claims, 'sub': value}))

    def test_forged_signature_and_payload_tampering_are_denied(self):
        self.assert_denied(self.token(key=self.other))
        token = self.token().split('.')
        token[1] = b64(json.dumps({**self.claims, 'sub': 'provider|admin'}).encode())
        self.assert_denied('.'.join(token))

    def test_none_hs256_and_wrong_rsa_algorithm_are_denied_before_key_fetch(self):
        self.assert_denied(self.token(key='', algorithm='none'))
        self.assert_denied(self.token(key=b'a-sufficiently-long-untrusted-secret', algorithm='HS256'))
        self.assert_denied(self.token(algorithm='RS512'))
        self.assertEqual(self.calls, [])

    def test_header_key_urls_inline_keys_and_unsupported_critical_extensions_are_denied(self):
        for field, value in [('jku', 'https://attacker.example/keys'), ('jwk', self.jwk),
                             ('x5u', 'https://attacker.example/cert'), ('x5c', ['cert']),
                             ('crit', []), ('b64', True), ('typ', 'unexpected')]:
            with self.subTest(field=field):
                self.assert_denied(self.signed_raw({'alg': 'RS256', 'kid': 'key-one', field: value}, self.claims))
        self.assertEqual(self.calls, [])

    def test_missing_and_malformed_kid_are_denied(self):
        for kid in (None, '', 'a b', '../../keys', 'a' * 129, 1):
            with self.subTest(kid=kid):
                self.assert_denied(self.token(headers={'kid': kid}) if isinstance(kid, str)
                                   else self.signed_raw({'alg': 'RS256', 'kid': kid}, self.claims))

    def signed_raw(self, header, claims):
        header = header if isinstance(header, bytes) else json.dumps(header).encode()
        claims = claims if isinstance(claims, bytes) else json.dumps(claims).encode()
        message = (b64(header) + '.' + b64(claims)).encode()
        signature = self.key.sign(message, padding.PKCS1v15(), hashes.SHA256())
        return message.decode() + '.' + b64(signature)

    def test_signed_duplicate_json_claims_and_headers_are_denied(self):
        claims = json.dumps(self.claims)[:-1] + ',"sub":"provider|forged"}'
        self.assert_denied(self.signed_raw({'alg': 'RS256', 'kid': 'key-one'}, claims.encode()))
        header = b'{"alg":"RS256","kid":"other","kid":"key-one"}'
        self.assert_denied(self.signed_raw(header, self.claims))

    def test_malformed_oversized_noncompact_and_unsigned_inputs_are_denied(self):
        for value in (None, b'token', '', 'x' * 16385, 'a.b', 'a.b.', 'a.b.c.d', 'a .b.c', '{}.e30.sig'):
            with self.subTest(value=str(value)[:30]):
                self.assert_denied(value)

    def test_unknown_kid_is_not_fetched_from_any_token_pointer(self):
        self.assert_denied(self.token(headers={'kid': 'unknown'}))
        self.assertEqual(self.calls, [CONFIG.jwks_uri])
        self.assertEqual(self.verifier.verify_token(self.token()).subject, self.claims['sub'])

    def test_unknown_kid_refresh_is_throttled_while_valid_cache_is_fresh(self):
        with patch('research.prediction_v1_1_oidc_verifier.time.monotonic', return_value=10):
            self.verifier.verify_token(self.token())
            for kid in ('unknown-one', 'unknown-two', 'unknown-three'):
                self.assert_denied(self.token(headers={'kid': kid}))
        self.assertEqual(len(self.calls), 1)

    def test_key_rotation_refreshes_only_pinned_jwks_and_removes_old_key(self):
        next_jwk = self.jwk_for(self.other, 'key-two')
        with patch('research.prediction_v1_1_oidc_verifier.time.monotonic', return_value=10):
            self.verifier.verify_token(self.token())
        self.document = {'keys': [next_jwk]}
        with patch('research.prediction_v1_1_oidc_verifier.time.monotonic', return_value=16):
            identity = self.verifier.verify_token(self.token(key=self.other, headers={'kid': 'key-two'}))
            self.assertEqual(identity.subject, self.claims['sub'])
            self.assert_denied(self.token())
        self.assertEqual(self.calls, [CONFIG.jwks_uri, CONFIG.jwks_uri])

    def test_failed_expired_cache_refresh_does_not_serve_stale_key(self):
        with patch('research.prediction_v1_1_oidc_verifier.time.monotonic', return_value=10):
            self.verifier.verify_token(self.token())
        self.verifier._fetch = lambda _: (_ for _ in ()).throw(OSError('unavailable'))
        with patch('research.prediction_v1_1_oidc_verifier.time.monotonic', return_value=11 + CACHE_SECONDS):
            self.assert_denied(self.token())
        self.assertEqual(self.verifier._keys, {})

    def test_failed_fetch_is_throttled_without_a_cache_and_retries_after_cooldown(self):
        calls = []
        def unavailable(uri):
            calls.append(uri)
            raise OSError('offline')
        verifier = OIDCVerifier(CONFIG, jwks_fetcher=unavailable)
        with patch('research.prediction_v1_1_oidc_verifier.time.monotonic', return_value=10):
            for _ in range(3):
                with self.assertRaises(AuthenticationError): verifier.verify_token(self.token())
        self.assertEqual(calls, [CONFIG.jwks_uri])
        with patch('research.prediction_v1_1_oidc_verifier.time.monotonic', return_value=16):
            with self.assertRaises(AuthenticationError): verifier.verify_token(self.token())
        self.assertEqual(calls, [CONFIG.jwks_uri, CONFIG.jwks_uri])

    def test_key_usage_algorithm_private_fields_and_size_are_validated(self):
        invalid = [dict(self.jwk, alg='HS256'), dict(self.jwk, use='enc'),
                   dict(self.jwk, key_ops=['sign']), dict(self.jwk, d='private'),
                   self.jwk_for(self.weak, 'key-one'), dict(self.jwk, n='bad'),
                   dict(self.jwk, e='Aw')]
        for row in invalid:
            with self.subTest(fields=row.keys()):
                self.document = {'keys': [row]}
                self.verifier = OIDCVerifier(CONFIG, jwks_fetcher=self.fetch)
                self.assert_denied(self.token())

    def test_optional_jwk_alg_and_use_metadata_do_not_weaken_fixed_algorithm(self):
        row = dict(self.jwk)
        for name in ('alg', 'use', 'key_ops'):
            del row[name]
        self.document = {'keys': [row]}
        self.assertEqual(self.verifier.verify_token(self.token()).issuer, CONFIG.issuer)

    def test_duplicate_kid_and_malformed_jwks_fail_closed(self):
        invalid = [None, {}, {'keys': []}, {'keys': [self.jwk, self.jwk]},
                   {'keys': [self.jwk] * 33}, {'keys': ['not-a-key']},
                   {'keys': [dict(self.jwk, kid='bad key')]},
                   {'keys': [self.jwk], 'oversized': 'x' * MAX_JWKS_BYTES}]
        for document in invalid:
            with self.subTest(document=str(document)[:30]):
                self.document = document
                self.verifier = OIDCVerifier(CONFIG, jwks_fetcher=self.fetch)
                self.assert_denied(self.token())

    def test_network_or_tls_fetch_failure_rejects_identity(self):
        verifier = OIDCVerifier(CONFIG, jwks_fetcher=lambda _: (_ for _ in ()).throw(OSError('private detail')))
        with self.assertRaisesRegex(AuthenticationError, '^Identity signing keys unavailable$'):
            verifier.verify_token(self.token())


class DefaultJWKSFetchTests(unittest.TestCase):
    def response(self, data=b'{"keys": []}', content_type='application/json', length=None, status=200):
        class Response:
            headers = Message()
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, limit):
                self.read_limit = limit
                return data[:limit]
        result = Response(); result.status = status
        result.headers['Content-Type'] = content_type
        if length is not None: result.headers['Content-Length'] = length
        return result

    def fetch_response(self, response):
        with patch('research.prediction_v1_1_oidc_verifier.build_opener') as factory:
            factory.return_value.open.return_value = response
            value = _fetch_jwks(CONFIG.jwks_uri)
            args, kwargs = factory.return_value.open.call_args
            self.assertEqual(args[0].full_url, CONFIG.jwks_uri)
            self.assertEqual(kwargs['timeout'], 5)
            return value

    def test_https_fetch_uses_fixed_uri_bounded_read_and_timeout(self):
        response = self.response()
        self.assertEqual(self.fetch_response(response), {'keys': []})
        self.assertEqual(response.read_limit, MAX_JWKS_BYTES + 1)

    def test_response_size_content_type_status_and_duplicate_members_are_checked(self):
        for response in (self.response(length=str(MAX_JWKS_BYTES + 1)),
                         self.response(data=b'x' * (MAX_JWKS_BYTES + 1)),
                         self.response(content_type='text/html'), self.response(status=302),
                         self.response(data=b'{"keys": [],"keys": []}'),
                         self.response(data=b'{"keys": [],"number": NaN}')):
            with self.subTest(headers=response.headers):
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    self.fetch_response(response)

    def test_redirect_handler_never_follows_redirect(self):
        with self.assertRaises(HTTPError):
            _NoRedirects().redirect_request(type('Request', (), {'full_url': CONFIG.jwks_uri})(),
                                            None, 302, 'Moved', Message(), 'https://attacker.example/keys')


if __name__ == '__main__':
    unittest.main()
