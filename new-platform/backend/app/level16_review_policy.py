"""Levels 1–6 review policy. No identity claims or source hashes confer trust."""
from dataclasses import dataclass
from datetime import date
import re
from uuid import UUID

SOURCE_VERIFIER = 'SOURCE_VERIFIER'
CLINICAL_REVIEWER = 'CLINICAL_REVIEWER'
INDEPENDENT_CHALLENGER = 'INDEPENDENT_CHALLENGER'
REVIEW_ADMIN = 'REVIEW_ADMIN'
STAGES = (
    'SOURCE_SUBMITTED', 'SOURCE_AUTHENTICATION_PENDING', 'SOURCE_AUTHENTICATED',
    'SCIENTIFIC_REVIEW_PENDING', 'SCIENTIFIC_REVIEW_COMPLETED',
    'INDEPENDENT_CHALLENGE_PENDING', 'INDEPENDENT_CHALLENGE_COMPLETED',
    'FINAL_ADJUDICATION_PENDING', 'FINAL_ADJUDICATED',
)
EXCEPTIONS = frozenset({'REJECTED', 'CONFLICT_UNRESOLVED', 'ADDITIONAL_EVIDENCE_REQUIRED',
                        'SUPERSEDED_BY_NEW_EVIDENCE', 'NOT_APPLICABLE_AT_CURRENT_PHASE'})
ROLES = dict(zip(STAGES, (SOURCE_VERIFIER,) * 3 + (CLINICAL_REVIEWER,) * 2 +
                 (INDEPENDENT_CHALLENGER,) * 2 + (REVIEW_ADMIN,) * 2))
ROLES.update({state: REVIEW_ADMIN for state in EXCEPTIONS})
SOURCE_CHECKS = ('exactNct', 'phase', 'registryStatus', 'indication', 'population',
                 'sourceOwnership', 'publicationDate', 'retrievalDate',
                 'originalDocument', 'documentVersion', 'protocolVersion', 'cutoff', 'conflicts')
BINDING_KEYS = frozenset({'nct', 'company', 'ticker', 'indication', 'phases', 'registryStatus',
                         'applicationCycleId', 'applicationIdentityVerified', 'level',
                         'documentId', 'documentSha256', 'documentVersion', 'protocolVersion',
                         'cutoffDate', 'sourceUrl', 'publicationDate', 'retrievalDate', 'evidenceVersion'})


class ReviewUnavailable(RuntimeError):
    """Trusted infrastructure is not configured; never fall back to shared keys."""


class ReviewDenied(PermissionError):
    pass


class ReviewConflict(ValueError):
    pass


@dataclass(frozen=True)
class Identity:
    """Only a trusted server-side adapter may return this; never deserialize JSON."""
    issuer: str
    subject: str
    session: object = None


class UnavailableIdentityProvider:
    def authenticate(self, credential):
        raise ReviewUnavailable('Trusted individual reviewer authentication is not connected')


class UnavailableEvidenceProvider:
    def current(self, stream_id, connection):
        raise ReviewUnavailable('Trusted immutable evidence-bundle resolver is not connected')

    def current_stream(self, nct, level, connection):
        raise ReviewUnavailable('Trusted current evidence stream selection is not connected')

    def authentication_checks(self, stream_id, actor, connection):
        raise ReviewUnavailable('Independent original-source authentication is not connected')


def text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4000:
        raise ValueError('Bounded nonblank text required')
    return value


def texts(value, required=False):
    if not isinstance(value, list) or len(value) > 100 or (required and not value):
        raise ValueError('Bounded evidence text list required')
    return [text(item) for item in value]


def validate_binding(binding):
    if not isinstance(binding, dict) or set(binding) != BINDING_KEYS:
        raise ValueError('Exact immutable evidence binding required')
    if not isinstance(binding['nct'], str) or not re.fullmatch(r'NCT[0-9]{8}', binding['nct']):
        raise ValueError('Exact NCT required')
    if type(binding['level']) is not int or not 1 <= binding['level'] <= 6:
        raise ValueError('Level must be 1–6')
    if type(binding['evidenceVersion']) is not int or binding['evidenceVersion'] < 1:
        raise ValueError('Evidence version must be a positive integer')
    for key in ('company', 'ticker', 'indication', 'documentId', 'documentVersion', 'protocolVersion', 'registryStatus'):
        text(binding[key])
    if not isinstance(binding['documentSha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', binding['documentSha256']):
        raise ValueError('Original document SHA-256 required, not sufficient for authentication')
    if binding['applicationIdentityVerified'] is not (binding['applicationCycleId'] is not None):
        raise ValueError('Only independently verified application identities may be bound')
    if binding['applicationCycleId'] is not None:
        text(binding['applicationCycleId'])
    phases = binding['phases']
    if not isinstance(phases, list) or not phases or any(p not in ('EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'NA') for p in phases):
        raise ValueError('Explicit current phase basis required')
    from urllib.parse import urlsplit
    url = urlsplit(text(binding['sourceUrl']))
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('Public original source HTTPS locator required')
    dates = []
    for key in ('publicationDate', 'retrievalDate', 'cutoffDate'):
        value = binding[key]
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            raise ValueError('Evidence dates must be ISO calendar dates')
        dates.append(date.fromisoformat(value))
    if not dates[0] <= dates[1] <= dates[2]:
        raise ValueError('Evidence publication/retrieval must be at or before cutoff')


def validate_command(command):
    keys = {'eventId', 'streamId', 'previousEventId', 'expectedVersion', 'binding',
            'action', 'status', 'findings', 'reasons', 'contradictoryEvidence', 'limitations', 'blockers'}
    if not isinstance(command, dict) or set(command) != keys:
        raise ValueError('Unknown, missing or forbidden reviewer/role/timestamp/prediction fields')
    for key in ('eventId', 'streamId'):
        if not isinstance(command[key], str):
            raise ValueError('Canonical event/stream UUID text required')
        UUID(command[key])
    if command['previousEventId'] is not None:
        if not isinstance(command['previousEventId'], str):
            raise ValueError('Canonical predecessor UUID text required')
        UUID(command['previousEventId'])
    if type(command['expectedVersion']) is not int or command['expectedVersion'] < 0:
        raise ValueError('Expected current stream version required')
    validate_binding(command['binding'])
    if command['action'] not in ('TRANSITION', 'CORRECTION') or command['status'] not in ROLES:
        raise ValueError('Unknown review action/status')
    for key in ('findings', 'reasons', 'limitations'):
        texts(command[key], required=True)
    for key in ('contradictoryEvidence', 'blockers'):
        texts(command[key])
    if command['status'] == 'CONFLICT_UNRESOLVED' and not command['contradictoryEvidence']:
        raise ValueError('Conflicting evidence must be recorded')


def required_role(command, history, identity):
    """Validate progression, optimistic concurrency and independence on locked history."""
    latest = history[-1] if history else None
    if command['expectedVersion'] != len(history) or command['previousEventId'] != (latest['eventId'] if latest else None):
        raise ReviewConflict('Stale predecessor/version; refresh history before appending')
    status = command['status']
    role = ROLES[status]
    if command['action'] == 'CORRECTION':
        if not latest or status != latest['status'] or (identity.issuer, identity.subject) != (latest['reviewerIssuer'], latest['reviewerId']):
            raise ReviewDenied('Corrections must reference the same author/status; never overwrite history')
        role = latest['authorizedRole']
    else:
        previous = latest['status'] if latest else None
        if latest and latest.get('action') == 'CORRECTION':
            if status != 'SOURCE_AUTHENTICATION_PENDING' and status not in EXCEPTIONS:
                raise ReviewConflict('Corrected findings require renewed authentication and independent review')
        elif previous in ('FINAL_ADJUDICATED', 'REJECTED', 'SUPERSEDED_BY_NEW_EVIDENCE', 'NOT_APPLICABLE_AT_CURRENT_PHASE'):
            if status != 'SUPERSEDED_BY_NEW_EVIDENCE' or previous == status:
                raise ReviewConflict('Terminal review requires correction or an explicit supersession')
        elif status in EXCEPTIONS:
            if latest is None:
                raise ReviewConflict('Submit source before recording an exceptional disposition')
        elif previous in ('CONFLICT_UNRESOLVED', 'ADDITIONAL_EVIDENCE_REQUIRED'):
            if status != 'SOURCE_AUTHENTICATION_PENDING':
                raise ReviewConflict('Resolve evidence blockers and repeat authentication/review/challenge')
        elif status != STAGES[0 if previous is None else STAGES.index(previous) + 1]:
            raise ReviewConflict('Required review stages cannot be skipped')
    actor = (identity.issuer, identity.subject)
    submitters = {(e['reviewerIssuer'], e['reviewerId']) for e in history if e['status'] == 'SOURCE_SUBMITTED'}
    source_verifiers = {(e['reviewerIssuer'], e['reviewerId']) for e in history if e['authorizedRole'] == SOURCE_VERIFIER}
    if status == 'SOURCE_AUTHENTICATED' and actor in submitters:
        raise ReviewDenied('Source submitter cannot independently authenticate their own submission')
    if role == CLINICAL_REVIEWER and actor in source_verifiers:
        raise ReviewDenied('Source participant cannot independently complete clinical review of own evidence')
    prior_scientists = {(e['reviewerIssuer'], e['reviewerId']) for e in history
                        if e['authorizedRole'] in (SOURCE_VERIFIER, CLINICAL_REVIEWER)}
    prior_participants = {(e['reviewerIssuer'], e['reviewerId']) for e in history
                          if e['authorizedRole'] != REVIEW_ADMIN}
    if role == INDEPENDENT_CHALLENGER and actor in prior_scientists:
        raise ReviewDenied('Source verifier/scientific reviewer cannot independently challenge own work')
    if status in ('FINAL_ADJUDICATION_PENDING', 'FINAL_ADJUDICATED') and actor in prior_participants:
        raise ReviewDenied('A review participant cannot adjudicate their own assessment')
    if status == 'NOT_APPLICABLE_AT_CURRENT_PHASE' and (
        command['binding']['level'] not in (3, 5) or
        not set(command['binding']['phases']) <= {'EARLY_PHASE1', 'PHASE1', 'PHASE2'}):
        raise ReviewDenied('Phase disposition cannot waive identity or late-phase review')
    if status in ('SCIENTIFIC_REVIEW_COMPLETED', 'INDEPENDENT_CHALLENGE_COMPLETED', 'FINAL_ADJUDICATED') and command['blockers']:
        raise ReviewConflict('Outstanding blockers prevent completion')
    # A conflict cannot be erased merely by submitting an empty list at the next stage.
    # It must be explicitly resolved through the evidence re-authentication path.
    if status in ('SCIENTIFIC_REVIEW_COMPLETED', 'INDEPENDENT_CHALLENGE_COMPLETED', 'FINAL_ADJUDICATED') and command['contradictoryEvidence']:
        raise ReviewConflict('Unresolved contradictory evidence prevents completion')
    return role
