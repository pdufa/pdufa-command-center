"""Transactional original-byte resolver with explicit source-authority approval.

No network ingestion or document upload endpoint. Private evidence must be
lawfully obtained and separately provisioned; none is supplied by this module.
Signatures validate an approved attestation, not the scientific truth of a claim.
"""
import hashlib
import json
from uuid import UUID
from datetime import date, datetime, timezone
from sqlalchemy import text

from .level16_review_policy import SOURCE_CHECKS, ReviewConflict, ReviewDenied, ReviewUnavailable, validate_binding
from .level16_staging_identity import transaction_identity, REALM


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class TransactionalEvidenceResolver:
    def __init__(self, attestation_verifier):
        self.attestation_verifier = attestation_verifier

    def _access(self, c, stream):
        actor = transaction_identity(c)
        row = c.execute(text('''SELECT enabled FROM level16_review.evidence_access
            WHERE issuer=:issuer AND subject=:subject AND stream_id=:stream AND enabled FOR SHARE'''),
            {'issuer': actor.issuer, 'subject': actor.subject, 'stream': stream}).first()
        if row is None:
            raise ReviewDenied('No authorized access to this original evidence bundle')
        return actor

    def current_stream(self, nct, level, connection):
        if connection is None:
            raise ReviewUnavailable('Original evidence requires the review transaction')
        transaction_identity(connection)
        row = connection.execute(text('''SELECT stream_id FROM level16_review.current_evidence_versions
            WHERE nct=:nct AND level=:level FOR SHARE'''), {'nct': nct, 'level': level}).first()
        if row is None:
            return None
        stream = str(row.stream_id)
        self._access(connection, stream)
        return stream

    def _document_bytes(self, c, document_id, expected):
        row = c.execute(text('''SELECT sha256,original_bytes FROM level16_review.original_documents
            WHERE document_id=:document FOR SHARE'''), {'document': document_id}).first()
        if row is None or row.original_bytes is None or not len(row.original_bytes):
            raise ReviewConflict('Original document bytes missing or unavailable')
        if len(row.original_bytes) > 64 * 1024 * 1024:
            raise ReviewConflict('Original document exceeds bounded resolver limit')
        data = bytes(row.original_bytes)
        if row.sha256 != expected or hashlib.sha256(data).hexdigest() != expected:
            raise ReviewConflict('Original document digest mismatch')
        return data

    def _resolve(self, stream, c):
        if c is None:
            raise ReviewUnavailable('Original evidence requires the review transaction')
        self._access(c, stream)
        row = c.execute(text('''SELECT s.binding,b.manifest,b.document_ids,b.signed_attestation
            FROM level16_review.streams s JOIN level16_review.evidence_bundles b USING(stream_id)
            WHERE stream_id=:stream FOR SHARE OF b'''), {'stream': stream}).first()
        if row is None:
            raise ReviewConflict('Original evidence manifest unavailable')
        binding, manifest = row.binding, row.manifest
        validate_binding(binding)
        if date.fromisoformat(binding['cutoffDate']) > datetime.now(timezone.utc).date():
            raise ReviewConflict('Future evidence cutoff cannot establish current authentication')
        active = self.current_stream(binding['nct'], binding['level'], c)
        if active != str(stream):
            raise ReviewConflict('Superseded or stale original evidence version')
        if not isinstance(manifest, dict) or set(manifest) != {'schemaVersion', 'binding', 'provenance', 'amendments', 'historicalOutcomeExposed', 'purpose'}:
            raise ReviewConflict('Invalid original evidence manifest')
        if (type(manifest['schemaVersion']) is not int or manifest['schemaVersion'] != 1
                or manifest['binding'] != binding or manifest['historicalOutcomeExposed'] is not False
                or manifest['purpose'] != 'CURRENT_SCIENTIFIC_REVIEW'):
            raise ReviewConflict('Cross-identity/version or historical outcome evidence rejected')
        provenance = manifest['provenance']
        if (not isinstance(provenance, dict) or set(provenance) != {'sourceUrl', 'publisher', 'retrievalMethod', 'publicAccess'}
                or provenance['sourceUrl'] != binding['sourceUrl'] or provenance['publicAccess'] is not True
                or any(not isinstance(provenance[k], str) or not provenance[k].strip() or len(provenance[k]) > 2000
                       for k in ('publisher', 'retrievalMethod'))):
            raise ReviewConflict('Original source ownership/retrieval provenance missing')
        amendments = manifest['amendments']
        if not isinstance(amendments, list) or len(amendments) > 100:
            raise ReviewConflict('Bounded original amendment evidence required')
        documents = {binding['documentId']: binding['documentSha256']}
        for amendment in amendments:
            # Each amendment binds to the same trial/application/cutoff, with its
            # own original bytes, source dates and protocol/document version.
            validate_binding(amendment)
            if any(amendment[k] != binding[k] for k in ('nct', 'company', 'ticker', 'indication', 'phases',
                   'applicationCycleId', 'applicationIdentityVerified', 'level', 'cutoffDate', 'evidenceVersion')):
                raise ReviewConflict('Cross-trial/application amendment rejected')
            if amendment['documentId'] in documents:
                raise ReviewConflict('Duplicate amendment document identifier')
            documents[amendment['documentId']] = amendment['documentSha256']
        if len(row.document_ids) != len(documents) or set(row.document_ids) != set(documents):
            raise ReviewConflict('Document manifest/link mismatch')
        for ident, digest in documents.items():
            self._document_bytes(c, ident, digest)
        claims = self.attestation_verifier.decode(row.signed_attestation,
                    required=('streamId', 'manifestDigest', 'reviewerIssuer'), token_type='level16-source-attestation+jwt')
        if (claims['streamId'] != str(stream) or claims['manifestDigest'] != digest_json(manifest)
                or claims['reviewerIssuer'] != REALM or not isinstance(claims.get('checks'), dict)
                or set(claims['checks']) != set(SOURCE_CHECKS) or any(v is not True for v in claims['checks'].values())):
            raise ReviewDenied('Source attestation does not authenticate exact original evidence/provenance')
        verifier = claims['sub']
        try:
            UUID(verifier)
        except (ValueError,TypeError):
            raise ReviewDenied('Attesting verifier must be a provisioned stable person') from None
        authorized = c.execute(text('''SELECT role FROM level16_review.reviewer_grants
            WHERE issuer=:issuer AND subject=:subject AND role='SOURCE_VERIFIER' AND enabled FOR SHARE'''),
            {'issuer': REALM, 'subject': verifier}).first()
        person_known = c.execute(text('SELECT 1 FROM level16_review.identity_accounts WHERE person_id=CAST(:person AS uuid) LIMIT 1'), {'person': verifier}).first()
        if authorized is None or person_known is None:
            raise ReviewDenied('Attesting verifier has no independently provisioned individual authorization')
        return binding, manifest, claims

    def current(self, stream_id, connection):
        return self._resolve(stream_id, connection)[0]

    def authentication_checks(self, stream_id, actor, connection):
        _, _, claims = self._resolve(stream_id, connection)
        if (actor.issuer, actor.subject) != (claims['reviewerIssuer'], claims['sub']):
            raise ReviewDenied('Source authentication event must belong to the independently attesting verifier')
        return dict.fromkeys(SOURCE_CHECKS, True)

    def provenance(self, stream_id, connection):
        _, manifest, claims = self._resolve(stream_id, connection)
        return {'provenance': manifest['provenance'], 'amendments': manifest['amendments'],
                'attestationAuthority': claims['iss'], 'attestationId': claims['jti'],
                'attestingPerson': claims['sub'], 'attestationIssuedAt': claims['iat'],
                'attestationExpiresAt': claims['exp']}

    def document(self, stream_id, document_id, connection):
        binding, manifest, _ = self._resolve(stream_id, connection)
        documents = {b['documentId']: b['documentSha256'] for b in [binding, *manifest['amendments']]}
        if document_id not in documents:
            raise ReviewDenied('Document is not part of the authorized evidence bundle')
        return self._document_bytes(connection, document_id, documents[document_id])
