"""Isolated PostgreSQL review-event repository and fail-closed HTTP interface.

Not installed into main.py. No automatic DDL, worker imports, schedules or shared
API-key authorization. Identity/evidence adapters are server-side dependencies;
production adapters do not yet exist. Tests inject synthetic adapters explicitly.
"""
from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter, Header, HTTPException, Response
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .level16_review_policy import (
    Identity, ReviewConflict, ReviewDenied, ReviewUnavailable,
    UnavailableIdentityProvider, UnavailableEvidenceProvider,
    SOURCE_CHECKS, required_role, validate_binding, validate_command,
)


def _identity(provider, credential):
    identity = provider.authenticate(credential)
    if type(identity) is not Identity or not identity.issuer or not identity.subject:
        raise ReviewDenied('Verified issuer and stable subject are required')
    return identity


def _event(row):
    return {'eventId': str(row['event_id']), 'streamId': str(row['stream_id']),
            'previousEventId': str(row['previous_event_id']) if row['previous_event_id'] else None,
            'version': row['ordinal'], 'eventVersion': row['event_version'],
            'reviewerIssuer': row['reviewer_issuer'], 'reviewerId': row['reviewer_id'],
            'authorizedRole': row['authorized_role'], 'binding': row['binding'],
            'action': row['action'], 'status': row['status'], 'findings': row['findings'],
            'reasons': row['reasons'], 'contradictoryEvidence': row['contradictory_evidence'],
            'limitations': row['limitations'], 'blockers': row['blockers'],
            'sourceChecks': row['source_checks'], 'serverTimestamp': row['recorded_at'].isoformat()}


class ReviewEventService:
    def __init__(self, engine=None, *, identity_provider=None, evidence_provider=None):
        self.engine = engine
        self.identity_provider = identity_provider or UnavailableIdentityProvider()
        self.evidence_provider = evidence_provider or UnavailableEvidenceProvider()

    def _storage(self, connection):
        # Never permit owner/superuser credentials for the review runtime. The
        # migration is a separate DBA task; runtime cannot migrate/disable guards.
        safe = connection.execute(text("""SELECT NOT r.rolsuper AND NOT r.rolcreaterole
            AND NOT login_role.rolsuper AND NOT login_role.rolcreaterole
            AND NOT r.rolbypassrls AND NOT login_role.rolbypassrls
            AND NOT pg_has_role(session_user,n.nspowner,'MEMBER')
            AND NOT pg_has_role(current_user,n.nspowner,'MEMBER')
            AND pg_has_role(current_user,'pdufa_level16_writer','MEMBER')
            AND NOT has_table_privilege(current_user,'level16_review.events','UPDATE,DELETE,TRUNCATE')
            AND NOT has_table_privilege(current_user,'level16_review.streams','INSERT,DELETE,TRUNCATE')
            AND NOT has_column_privilege(current_user,'level16_review.reviewer_grants','enabled','UPDATE')
            FROM pg_roles r CROSS JOIN pg_namespace n CROSS JOIN pg_roles login_role
            WHERE r.rolname=current_user AND login_role.rolname=session_user AND n.nspname='level16_review'""")).scalar()
        guards = connection.execute(text("""SELECT count(*) FROM pg_trigger t
            JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='level16_review' AND t.tgenabled='O' AND NOT t.tgisinternal
            AND t.tgname IN ('immutable_events','no_truncate_events','immutable_streams',
                            'no_truncate_streams','verify_event','immutable_grant_identity')""")).scalar()
        if safe is not True or guards != 6:
            raise ReviewUnavailable('Restricted review writer role and all database guards are required')

    def _engine(self):
        if self.engine is None or self.engine.dialect.name != 'postgresql':
            raise ReviewUnavailable('Migrated PostgreSQL required; no ephemeral fallback or automatic migration')
        return self.engine

    def _grants(self, connection, identity):
        authorize = getattr(self.identity_provider, 'authorize_in_transaction', None)
        if authorize is not None:
            authorize(identity, connection)
        rows = connection.execute(text('''SELECT role FROM level16_review.reviewer_grants
            WHERE issuer=:issuer AND subject=:subject AND enabled FOR SHARE'''),
            {'issuer': identity.issuer, 'subject': identity.subject}).scalars().all()
        if not rows:
            raise ReviewDenied('No active server-managed reviewer authorization')
        return set(rows)

    def _binding(self, stream_id, stored, connection=None):
        current = self.evidence_provider.current(stream_id, connection)
        validate_binding(current)
        if current != stored:
            raise ReviewConflict('Evidence version, cutoff or trial/application binding is stale')
        # Reuse canonical FOCUS and provisional crosswalk as restrictions, never
        # as proof of scientific/application identity. A provider must independently
        # establish phase/indication and any application it claims verified.
        root = Path(__file__).resolve().parents[2]
        roster = json.loads((root / 'frontend/data/p3PostDataActive.json').read_text(encoding='utf-8'))
        trials = {r['nct']: r for r in roster['records']}
        trial = trials.get(current['nct'])
        if trial is None or any(current[key] != trial[key] for key in ('company', 'ticker')):
            raise ReviewConflict('Evidence does not match canonical FOCUS company/NCT')
        apps = json.loads((Path(__file__).parent / 'data/focus_application_snapshot.json').read_text(encoding='utf-8'))
        cycles = {c['cycleId'] for r in apps['records'] if r['nct'] == current['nct']
                  for c in r['candidateApplications']}
        if current['applicationCycleId'] is not None and current['applicationCycleId'] not in cycles:
            raise ReviewConflict('Application is outside exact-NCT crosswalk; never invent missing mappings')
        return current

    def history(self, credential, stream_id):
        from uuid import UUID
        UUID(stream_id)
        actor = _identity(self.identity_provider, credential)
        with self._engine().begin() as connection:
            self._storage(connection)
            self._grants(connection, actor)
            binding = connection.execute(text('SELECT binding FROM level16_review.streams WHERE stream_id=:stream'),
                                         {'stream': stream_id}).scalar_one_or_none()
            if binding is None:
                raise ReviewConflict('Unknown evidence stream')
            rows = connection.execute(text('SELECT * FROM level16_review.events WHERE stream_id=:stream ORDER BY ordinal'),
                                      {'stream': stream_id}).mappings().all()
            # Old streams remain readable after evidence changes. They must not
            # be applied as current assessments without _binding validation.
            return {'streamId': stream_id, 'binding': binding, 'events': [_event(r) for r in rows],
                    'approvalProbability': None, 'fdaOutcomeJudgment': None, 'prospectiveBlindAssessment': False}

    def projection(self, credential, nct, level):
        """Server-only reader for phase-first engine/preview; never trust JSON exports.

        Current stream selection is a trusted evidence-provider responsibility.
        Absence of a configured provider fails closed. Re-reading history checks
        active grants and immutable current evidence binding on every projection.
        """
        actor = _identity(self.identity_provider, credential)
        with self._engine().begin() as connection:
            self._storage(connection)
            self._grants(connection, actor)
            stream_id = self.evidence_provider.current_stream(nct, level, connection)
            if stream_id is None:
                return None
            stored = connection.execute(text('SELECT binding FROM level16_review.streams WHERE stream_id=:stream FOR UPDATE'),
                                        {'stream': stream_id}).scalar_one_or_none()
            if stored is None:
                raise ReviewConflict('Current review stream is missing')
            current = self._binding(stream_id, stored, connection)
            if current['nct'] != nct or current['level'] != level:
                raise ReviewConflict('Current stream selection crossed trial/level identity')
            events = [_event(r) for r in connection.execute(text(
                'SELECT * FROM level16_review.events WHERE stream_id=:stream ORDER BY ordinal'), {'stream': stream_id}).mappings()]
            from .level16_review_policy import STAGES
            latest = events[-1] if events else None
            status = latest['status'] if latest else 'NO_REVIEW_EVENTS'
            if latest and latest['action'] == 'CORRECTION':
                status = 'CORRECTION_REQUIRES_REVIEW'
            stage = STAGES.index(status) if status in STAGES else -1
            result = {
                'status': 'AUTHORIZED_DATABASE_READBACK', 'binding': current,
                'sourceCollectionStatus': 'SOURCE_SUBMITTED' if events else 'NO_REVIEW_EVENTS',
                'originalDocumentAuthenticationStatus': 'SOURCE_AUTHENTICATED' if stage >= 2 else 'NOT_AUTHENTICATED',
                'reviewerAuthorizationStatus': 'SERVER_AUTHORIZED_EVENTS' if events else 'NO_AUTHORIZED_EVENTS',
                'clinicalReviewStatus': 'SCIENTIFIC_REVIEW_COMPLETED' if stage >= 4 else 'NOT_COMPLETED',
                'independentChallengeStatus': 'INDEPENDENT_CHALLENGE_COMPLETED' if stage >= 6 else 'NOT_COMPLETED',
                'reviewStatus': status, 'independentlyAdjudicated': stage == 8, 'prospectiveBlindAssessment': False,
                'findings': latest['findings'] if latest else [], 'reasons': latest['reasons'] if latest else [],
                'contradictoryEvidence': latest['contradictoryEvidence'] if latest else [],
                'limitations': latest['limitations'] if latest else [],
                'blockers': (latest['blockers'] if latest else []) + ([] if stage == 8 else ['FINAL_INDEPENDENT_ADJUDICATION_REQUIRED']),
                'history': events,
            }
            describe = getattr(self.evidence_provider, 'provenance', None)
            if describe is not None:
                result['originalEvidenceProvenance'] = describe(stream_id, connection)
            return result

    def append(self, credential, command):
        # Authenticate before processing any caller-supplied reviewer claims.
        actor = _identity(self.identity_provider, credential)
        validate_command(command)
        try:
            with self._engine().begin() as connection:
                self._storage(connection)
                grants = self._grants(connection, actor)
                stored = connection.execute(text('''SELECT binding FROM level16_review.streams
                    WHERE stream_id=:stream FOR UPDATE'''), {'stream': command['streamId']}).scalar_one_or_none()
                if stored is None:
                    raise ReviewConflict('Evidence stream must be registered by a separate authorized process')
                current = self._binding(command['streamId'], stored, connection)
                if command['binding'] != current:
                    raise ReviewConflict('Request is bound to stale or different trial/application evidence')
                history = [_event(r) for r in connection.execute(text('''SELECT * FROM level16_review.events
                    WHERE stream_id=:stream ORDER BY ordinal'''), {'stream': command['streamId']}).mappings()]
                role = required_role(command, history, actor)
                if role not in grants:
                    raise ReviewDenied('Required reviewer role is not granted by server')
                checks = {}
                if command['status'] == 'SOURCE_AUTHENTICATED':
                    checks = self.evidence_provider.authentication_checks(command['streamId'], actor, connection)
                    if not isinstance(checks, dict) or set(checks) != set(SOURCE_CHECKS) or any(v is not True for v in checks.values()):
                        raise ReviewDenied('Independent original-source checks incomplete; checksum equality is insufficient')
                params = {'event': command['eventId'], 'stream': command['streamId'],
                          'ordinal': command['expectedVersion'] + 1, 'previous': command['previousEventId'],
                          'issuer': actor.issuer, 'subject': actor.subject, 'role': role,
                          'binding': json.dumps(current), 'action': command['action'], 'status': command['status'],
                          'checks': json.dumps(checks)}
                for key in ('findings', 'reasons', 'contradictoryEvidence', 'limitations', 'blockers'):
                    params[key] = json.dumps(command[key])
                row = connection.execute(text('''INSERT INTO level16_review.events
                    (event_id,stream_id,ordinal,previous_event_id,reviewer_issuer,reviewer_id,authorized_role,
                     binding,action,status,findings,reasons,contradictory_evidence,limitations,blockers,source_checks)
                    VALUES (:event,:stream,:ordinal,:previous,:issuer,:subject,:role,
                     CAST(:binding AS jsonb),:action,:status,CAST(:findings AS jsonb),CAST(:reasons AS jsonb),
                     CAST(:contradictoryEvidence AS jsonb),CAST(:limitations AS jsonb),CAST(:blockers AS jsonb),CAST(:checks AS jsonb))
                    RETURNING *'''), params).mappings().one()
                return _event(row)
        except ReviewDenied:
            audit = getattr(self.identity_provider, 'audit_denial', None)
            if audit is not None:
                audit(actor)
            raise
        except DBAPIError as exc:
            # Includes duplicate event IDs, concurrent branch attempts, revoked
            # grants and constraint failures. Never leak SQL, documents or DSNs.
            raise ReviewConflict('Database rejected review event; refresh immutable history') from None


def build_router(service=None):
    """Permission-controlled, UNMOUNTED interface. No shared-key fallback."""
    router = APIRouter(prefix='/api/internal/levels1-6/reviews')
    service = service or ReviewEventService()

    def call(function, *args):
        try:
            return function(*args)
        except ReviewUnavailable as exc:
            raise HTTPException(503, str(exc)) from None
        except ReviewDenied as exc:
            raise HTTPException(403, str(exc)) from None
        except (ReviewConflict, ValueError, TypeError) as exc:
            raise HTTPException(409, 'Invalid/stale review request; no event appended') from None
        except DBAPIError:
            raise HTTPException(503, 'Review storage unavailable; no event appended') from None

    @router.post('/events')
    def append_event(command: dict, response: Response, authorization: str | None = Header(default=None)):
        response.headers['Cache-Control'] = 'no-store'
        return call(service.append, authorization, command)

    @router.get('/{stream_id}/history')
    def history(stream_id: str, response: Response, authorization: str | None = Header(default=None)):
        response.headers['Cache-Control'] = 'no-store'
        return call(service.history, authorization, stream_id)

    return router
