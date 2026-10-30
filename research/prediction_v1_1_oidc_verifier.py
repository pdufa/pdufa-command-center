"""Cryptographic identity verification for the isolated research API.

RS256 and a server-pinned issuer/audience/JWKS URI are the only supported
profile. Verification yields only issuer + subject. Token roles and program
claims are deliberately unavailable to authorization code. This module neither
configures a live provider nor mounts or changes production authentication.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import re
import threading
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm

from research.prediction_v1_1_oidc_preflight import validate_oidc_configuration

MAX_TOKEN_BYTES = 16 * 1024
MAX_JWKS_BYTES = 128 * 1024
MAX_JWKS_KEYS = 32
CACHE_SECONDS = 300
UNKNOWN_KID_REFRESH_SECONDS = 5
_KID = re.compile(r'[A-Za-z0-9_.:-]{1,128}\Z')
_SEGMENT = re.compile(r'[A-Za-z0-9_-]+\Z')


class AuthenticationError(PermissionError):
    """The caller has not supplied a cryptographically accepted identity."""


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    issuer: str
    subject: str


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise HTTPError(request.full_url, code, 'JWKS redirects are not allowed', headers, fp)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON member')
        result[key] = value
    return result


def _json(raw):
    return json.loads(raw, object_pairs_hook=_unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def _segment(raw):
    if not _SEGMENT.fullmatch(raw):
        raise ValueError('invalid JWT encoding')
    decoded = base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4))
    # Reject noncanonical encodings and duplicate header/claim members before
    # letting the signature library parse the same bytes.
    if base64.urlsafe_b64encode(decoded).decode().rstrip('=') != raw:
        raise ValueError('noncanonical JWT encoding')
    value = _json(decoded)
    if not isinstance(value, dict):
        raise ValueError('JWT header and claims must be objects')
    return value


def _fetch_jwks(uri):
    """Read only the configured HTTPS URI with system TLS verification.

    urllib uses the environment's configured proxy and trusted CA chain. It is
    never given a token-supplied URL; redirects are rejected rather than followed.
    """
    request = Request(uri, headers={'Accept': 'application/json, application/jwk-set+json',
                                    'User-Agent': 'PDUFA-Research-OIDC/1'})
    with build_opener(_NoRedirects()).open(request, timeout=5) as response:
        if response.status != 200:
            raise ValueError('JWKS HTTP failure')
        if response.headers.get_content_type() not in ('application/json', 'application/jwk-set+json'):
            raise ValueError('JWKS JSON content type required')
        declared = response.headers.get('Content-Length')
        if declared is not None and (not declared.isdecimal() or int(declared) > MAX_JWKS_BYTES):
            raise ValueError('JWKS size limit')
        raw = response.read(MAX_JWKS_BYTES + 1)
    if not raw or len(raw) > MAX_JWKS_BYTES:
        raise ValueError('JWKS size limit')
    return _json(raw)


def _signing_keys(document):
    if not isinstance(document, dict) or not isinstance(document.get('keys'), list):
        raise ValueError('JWKS key list required')
    rows = document['keys']
    if not 1 <= len(rows) <= MAX_JWKS_KEYS:
        raise ValueError('JWKS key count limit')
    # Apply the size bound to injected server fetchers as well as HTTPS input.
    if len(json.dumps(document, allow_nan=False).encode()) > MAX_JWKS_BYTES:
        raise ValueError('JWKS size limit')
    seen, accepted = set(), {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('kid'), str) or not _KID.fullmatch(row['kid']):
            raise ValueError('unique bounded signing key identity required')
        kid = row['kid']
        if kid in seen:
            raise ValueError('duplicate signing key identity')
        seen.add(kid)
        if row.get('kty') != 'RSA' or row.get('alg', 'RS256') != 'RS256' or row.get('use', 'sig') != 'sig':
            continue
        if 'key_ops' in row and row['key_ops'] != ['verify']:
            continue
        if any(field in row for field in ('d', 'p', 'q', 'dp', 'dq', 'qi', 'oth', 'k')):
            raise ValueError('private or symmetric key material is not a public signing key')
        if (not isinstance(row.get('n'), str) or len(row['n']) > 1400
                or not isinstance(row.get('e'), str) or len(row['e']) > 8):
            raise ValueError('bounded RSA public parameters required')
        public = RSAAlgorithm.from_jwk(json.dumps(row))
        if not isinstance(public, RSAPublicKey) or not 2048 <= public.key_size <= 8192:
            raise ValueError('RSA signing key size outside research security profile')
        if public.public_numbers().e != 65537:
            raise ValueError('RSA signing exponent outside research security profile')
        accepted[kid] = public
    if not accepted:
        raise ValueError('no acceptable RS256 signing keys')
    return accepted


class OIDCVerifier:
    """Verify one explicitly configured provider; no role claims cross this boundary.

    JWKS keys expire after five minutes. Unknown kids can trigger bounded refresh
    for rotation, but never cause retrieval of token-supplied URLs. Failed refresh
    invalidates the cache: no stale signing keys are served after an error.
    """
    def __init__(self, config, *, jwks_fetcher=None):
        self.config = validate_oidc_configuration(config)
        if jwks_fetcher is not None and not callable(jwks_fetcher):
            raise ValueError('server JWKS fetcher must be callable')
        self._fetch = _fetch_jwks if jwks_fetcher is None else jwks_fetcher
        self._keys = {}
        self._expires_at = 0.0
        self._last_refresh = None
        self._lock = threading.Lock()

    def _key(self, kid):
        with self._lock:
            now = time.monotonic()
            if now < self._expires_at and kid in self._keys:
                return self._keys[kid]
            if (self._last_refresh is not None
                    and now - self._last_refresh < UNKNOWN_KID_REFRESH_SECONDS):
                # Rate-limit failed initial/expired fetches too. Otherwise an
                # outage plus forged tokens could cause one network fetch per
                # request after the cache has been cleared.
                message = ('Identity signing keys unavailable' if not self._keys
                           else 'Bearer token is not accepted')
                raise AuthenticationError(message)
            self._last_refresh = now
            try:
                keys = _signing_keys(self._fetch(self.config.jwks_uri))
            except Exception as exc:
                # Fetcher errors, malformed keys and TLS/network failures all
                # fail closed without disclosing key data or response bodies.
                self._keys, self._expires_at = {}, 0.0
                raise AuthenticationError('Identity signing keys unavailable') from exc
            self._keys = keys
            self._expires_at = now + CACHE_SECONDS
            if kid not in keys:
                raise AuthenticationError('Bearer token is not accepted')
            return keys[kid]

    def verify_token(self, token):
        try:
            if (not isinstance(token, str) or not 0 < len(token) <= MAX_TOKEN_BYTES
                    or any(character.isspace() for character in token)):
                raise ValueError('bounded compact JWT required')
            parts = token.split('.')
            if len(parts) != 3 or not parts[2] or not _SEGMENT.fullmatch(parts[2]):
                raise ValueError('signed compact JWT required')
            header, claims = _segment(parts[0]), _segment(parts[1])
            if (header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str)
                    or not _KID.fullmatch(header['kid'])
                    or any(field in header for field in ('jku', 'jwk', 'x5u', 'x5c', 'crit', 'b64'))
                    or header.get('typ', 'JWT') not in ('JWT', 'at+jwt')):
                raise ValueError('fixed RS256 signing profile required')
            for field in ('iat', 'exp'):
                if type(claims.get(field)) is not int or claims[field] < 0:
                    raise ValueError('required integer timestamp claim')
            if claims['iat'] >= claims['exp']:
                raise ValueError('invalid token lifetime')
            if 'nbf' in claims and (type(claims['nbf']) is not int or not 0 <= claims['nbf'] < claims['exp']):
                raise ValueError('invalid not-before claim')
            subject = claims.get('sub')
            if (not isinstance(subject, str) or not subject or len(subject) > 256
                    or subject != subject.strip() or any(ord(c) < 32 or ord(c) == 127 for c in subject)):
                raise ValueError('canonical nonempty subject required')
            # Avoid issuer/audience mismatches inducing network access. The same
            # claims are cryptographically verified again by jwt.decode below.
            audience = claims.get('aud')
            if claims.get('iss') != self.config.issuer:
                raise ValueError('wrong issuer')
            if isinstance(audience, str):
                if audience != self.config.audience:
                    raise ValueError('wrong audience')
            elif (not isinstance(audience, list) or not audience
                    or any(not isinstance(a, str) or not a or a != a.strip() for a in audience)
                    or len(set(audience)) != len(audience) or self.config.audience not in audience):
                raise ValueError('wrong audience')
            public_key = self._key(header['kid'])
            verified = jwt.decode(token, public_key, algorithms=['RS256'],
                                  issuer=self.config.issuer, audience=self.config.audience,
                                  options={'require': ['iss', 'aud', 'sub', 'iat', 'exp'],
                                           'verify_signature': True, 'verify_exp': True,
                                           'verify_iat': True, 'verify_nbf': True,
                                           'verify_iss': True, 'verify_aud': True,
                                           'verify_sub': True}, leeway=0)
            return VerifiedIdentity(issuer=verified['iss'], subject=verified['sub'])
        except AuthenticationError:
            raise
        except Exception as exc:
            raise AuthenticationError('Bearer token is not accepted') from exc
