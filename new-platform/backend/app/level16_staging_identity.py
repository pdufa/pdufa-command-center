"""Pinned-key JWT and individual-session adapter; no provider approved by default.

No discovery, token minting, shared-key fallback or client role claims. Live
activation requires separate external approval and isolated infrastructure.
"""
from dataclasses import dataclass
from types import MappingProxyType
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .level16_review_policy import Identity, ReviewDenied, ReviewUnavailable

REALM = 'level16-approved-person'


def check_staging_storage(connection):
    guards = connection.execute(text("""SELECT count(*) FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='level16_review' AND NOT t.tgisinternal AND t.tgenabled='O'
        AND t.tgname IN ('immutable_staging_row','no_truncate_staging','protect_session_keys',
          'protect_access_keys','protect_current_version','no_delete_current_version','no_truncate_current_version',
          'lock_revoked_session','authorization_server_time','require_staging_session')""")).scalar()
    secured = connection.execute(text("""SELECT count(*) FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='level16_review'
        AND c.relname IN ('streams','events','evidence_bundles','original_documents') AND c.relrowsecurity""")).scalar()
    policies = connection.execute(text("""SELECT count(*) FROM pg_policy p
        JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='level16_review' AND p.polname IN ('stream_access','event_access','bundle_access','document_access')""")).scalar()
    if guards != 18 or secured != 4 or policies != 4:
        raise ReviewUnavailable('Staging migration guards and evidence row policies are incomplete')


class PinnedJwtVerifier:
    def __init__(self, issuer, audience, public_keys, *, approval_reference=None, max_lifetime=900):
        self.issuer, self.audience = issuer, audience
        self.approval_reference = approval_reference
        self.max_lifetime = max_lifetime
        keys = {}
        for kid, pem in public_keys.items():
            key = serialization.load_pem_public_key(pem.encode() if isinstance(pem, str) else pem)
            if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
                raise ValueError('Only pinned RSA public keys of at least 2048 bits are supported')
            keys[kid] = key
        self.keys = MappingProxyType(keys)

    def decode(self, token, required=(), token_type='at+jwt'):
        if not self.approval_reference or not self.keys:
            raise ReviewUnavailable('No approved individual issuer/source authority and pinned public keys')
        try:
            if not isinstance(token, str) or not 1 <= len(token) <= 32768:
                raise ValueError('Invalid bounded token')
            header = jwt.get_unverified_header(token)
            if (set(header) != {'alg', 'typ', 'kid'} or header['alg'] != 'RS256'
                    or header['typ'] != token_type or header['kid'] not in self.keys):
                raise ValueError('Unapproved signing header')
            claims = jwt.decode(token, self.keys[header['kid']], algorithms=['RS256'],
                                issuer=self.issuer, audience=self.audience,
                                options={'require': ['iss', 'aud', 'sub', 'exp', 'iat', 'nbf', 'jti', *required],
                                         'strict_aud': True}, leeway=0)
            if any(type(claims[k]) is not int for k in ('exp', 'iat', 'nbf')):
                raise ValueError('Token times must be integer seconds')
            if not claims['nbf'] <= time.time() < claims['exp'] or not 0 < claims['exp'] - claims['iat'] <= self.max_lifetime:
                raise ValueError('Invalid token lifetime')
            for key in ('sub', 'jti', *required):
                if not isinstance(claims[key], str) or not 1 <= len(claims[key]) <= 512:
                    raise ValueError('Stable bounded identity/session required')
            if 'roles' in claims or 'role' in claims or 'reviewer' in claims:
                raise ValueError('Reviewer roles must come from server grants')
            return claims
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise ReviewDenied('Token issuer, audience, signature, type or validity rejected') from None


@dataclass(frozen=True)
class SessionContext:
    issuer: str
    subject: str
    sid: str
    jti: str
    issued_at: int
    expires_at: int


class StagingIdentityProvider:
    def __init__(self, engine, verifier):
        self.engine, self.verifier = engine, verifier

    def _audit(self, connection, decision, reason, actor=None):
        connection.execute(text('''INSERT INTO level16_review.authorization_audit
            (decision,reason,token_issuer,reviewer_id) VALUES (:decision,:reason,:issuer,:person)'''),
            {'decision': decision, 'reason': reason,
             'issuer': actor.session.issuer if actor and actor.session else None,
             'person': actor.subject if actor else None})

    def audit_denial(self, actor=None):
        try:
            with self.engine.begin() as c:
                self._audit(c, 'DENIED', 'REVIEW_APPEND_REJECTED', actor)
        except DBAPIError:
            raise ReviewUnavailable('Durable authorization audit unavailable') from None

    def _session(self, c, context):
        if type(context) is not SessionContext:
            raise ReviewDenied('Verified individual session context required')
        row = c.execute(text('''SELECT a.person_id FROM level16_review.identity_sessions s
            JOIN level16_review.identity_accounts a ON (a.token_issuer,a.token_subject)=(s.token_issuer,s.token_subject)
            WHERE s.token_issuer=:issuer AND s.token_subject=:subject AND s.session_id=:sid
            AND s.revoked_at IS NULL AND s.expires_at>clock_timestamp()
            AND to_timestamp(:iat)>=s.valid_after AND to_timestamp(:exp)<=s.expires_at
            AND to_timestamp(:exp)>clock_timestamp()
            AND NOT EXISTS(SELECT 1 FROM level16_review.revoked_tokens r WHERE r.token_issuer=s.token_issuer AND r.token_id=:jti)
            FOR SHARE OF s'''), {'issuer': context.issuer, 'subject': context.subject, 'sid': context.sid,
                                 'iat': context.issued_at, 'exp': context.expires_at, 'jti': context.jti}).first()
        if row is None:
            raise ReviewDenied('Session expired, revoked, invalidated or unprovisioned')
        return Identity(REALM, str(row.person_id), session=context)

    def authenticate(self, credential):
        actor, rejection, reason = None, None, 'TOKEN_REJECTED'
        try:
            if not isinstance(credential, str) or not credential.startswith('Bearer ') or credential.count(' ') != 1:
                raise ReviewDenied('Individual bearer credential required')
            claims = self.verifier.decode(credential[7:], required=('sid',))
            context = SessionContext(claims['iss'], claims['sub'], claims['sid'], claims['jti'], claims['iat'], claims['exp'])
            reason = 'SESSION_REJECTED'
            with self.engine.begin() as c:
                actor = self._session(c, context)
                reason = 'ROLE_REJECTED'
                grants = c.execute(text('''SELECT role FROM level16_review.reviewer_grants
                    WHERE issuer=:issuer AND subject=:subject AND enabled FOR SHARE'''),
                    {'issuer': actor.issuer, 'subject': actor.subject}).all()
                if not grants:
                    raise ReviewDenied('No server-controlled reviewer grant')
                self._audit(c, 'AUTHENTICATED', 'TOKEN_VALID', actor)
            return actor
        except ReviewDenied as exc:
            rejection = exc
        except DBAPIError:
            raise ReviewUnavailable('Individual session store or authorization audit unavailable') from None
        # Separate transaction retains denial even when the request is rejected.
        try:
            with self.engine.begin() as c:
                self._audit(c, 'DENIED', reason, actor)
        except DBAPIError:
            raise ReviewUnavailable('Durable authorization audit unavailable') from None
        raise rejection

    def authorize_in_transaction(self, actor, connection):
        check_staging_storage(connection)
        try:
            current = self._session(connection, actor.session)
            if (current.issuer, current.subject) != (actor.issuer, actor.subject):
                raise ReviewDenied('Session/person association changed')
        except ReviewDenied:
            self.audit_denial(actor)
            raise
        ctx = actor.session
        values = {'issuer': actor.issuer, 'subject': actor.subject, 'token_issuer': ctx.issuer,
                  'token_subject': ctx.subject, 'session_id': ctx.sid, 'token_id': ctx.jti,
                  'issued_at': str(ctx.issued_at), 'expires_at': str(ctx.expires_at)}
        for key, value in values.items():
            connection.execute(text("SELECT set_config(:key,:value,true)"), {'key': 'level16.' + key, 'value': value})
        self._audit(connection, 'AUTHORIZED', 'ACCESS_VALID', actor)


def transaction_identity(connection):
    """Only a validated adapter session may establish the transaction context."""
    values = connection.execute(text("""SELECT current_setting('level16.issuer',true) AS issuer,
        current_setting('level16.subject',true) AS subject""")).mappings().one()
    if values['issuer'] != REALM or not values['subject']:
        raise ReviewDenied('Authorized evidence transaction required')
    return Identity(values['issuer'], values['subject'])
