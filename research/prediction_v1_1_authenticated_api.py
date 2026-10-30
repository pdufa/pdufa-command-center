"""Isolated authenticated research API factory, deliberately not production-mounted.

No provider, directory, catalog or storage is configured implicitly. Valid JWT
identity never supplies roles/programs: the server-owned directory does that.
Approval records provenance review only, never scientific/prediction readiness.
"""
from __future__ import annotations
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import sqlite3
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Path as APIPath
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from research.prediction_v1_1_audit_ledger import append_submission
from research.prediction_v1_1_authorization import authorize_research_read
from research.prediction_v1_1_integrity_gate import audit_all_research_chains
from research.prediction_v1_1_oidc_verifier import OIDCVerifier, AuthenticationError
from research.prediction_v1_1_principal_directory import PrincipalDirectory
from research.prediction_v1_1_read_service import read_program_evidence
from research.prediction_v1_1_review_workflow import record_review
from research.prediction_v1_1_storage_adapter import open_research_evidence_store
from research.prediction_v1_1_submitter_binding import bind_verified_submitter


class EvidenceSubmission(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    program_id: str = Field(min_length=1, max_length=1000)
    field_id: str = Field(min_length=1, max_length=200)
    source_url: str | None = Field(max_length=4000)
    source_document_sha256: str | None = Field(max_length=64)
    source_published_at: str | None = Field(max_length=100)
    observed_at: str = Field(min_length=1, max_length=100)
    evidence_excerpt: str = Field(max_length=20000)
    applicability_rationale: str = Field(max_length=10000)
    status: Literal['UNVERIFIED', 'MISSING', 'NOT_APPLICABLE']


class ReviewChecks(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    source_bytes: bool
    publication_date: bool
    identity: bool


class EvidenceReview(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    outcome: Literal['APPROVE_PROVENANCE', 'REJECT_PROVENANCE', 'REQUEST_MORE_EVIDENCE']
    checks: ReviewChecks
    rationale: str = Field(min_length=1, max_length=10000)


class _InTransaction:
    """Keep existing helpers' nested `with conn` inside one locked transaction.

    Only execute/context methods are exposed: helper commits cannot accidentally
    separate accepted submission from its authenticated submitter binding.
    The real outer connection owns commit/rollback, including integrity checks.
    """
    def __init__(self, conn):
        self.conn = conn

    def execute(self, *args, **kwargs):
        return self.conn.execute(*args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _integrity(conn):
    if not audit_all_research_chains(conn)['valid']:
        raise RuntimeError('research audit integrity unavailable')


@contextmanager
def _write_transaction(conn):
    conn.execute('BEGIN IMMEDIATE')
    try:
        _integrity(conn)
        yield _InTransaction(conn)
        _integrity(conn)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def create_research_api(*, verifier=None, directory=None, store_path=None,
                        catalog=None, program_cutoffs=None):
    """Construct an isolated app using explicit server-owned dependencies only.

    Mounting/deployment and a real identity provider remain operator decisions.
    The default factory serves no research data and accepts no writes.
    """
    app = FastAPI(title='PDUFA isolated research evidence API', docs_url=None,
                  redoc_url=None, openapi_url=None)
    @app.middleware('http')
    async def private_research_response(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'private, no-store'
        return response

    configured = (isinstance(verifier, OIDCVerifier) and isinstance(directory, PrincipalDirectory)
                  and isinstance(store_path, (str, Path)) and bool(str(store_path).strip())
                  and isinstance(catalog, dict) and isinstance(catalog.get('fields'), list))
    trusted_catalog = deepcopy(catalog) if isinstance(catalog, dict) else None
    cutoffs = deepcopy({} if program_cutoffs is None else program_cutoffs)
    if not isinstance(cutoffs, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in cutoffs.items()):
        raise ValueError('server-controlled program cutoff map required')

    def identity(authorization: str | None = Header(default=None)):
        if not configured:
            raise HTTPException(503, 'Research identity, directory, catalog or storage is not configured')
        if (not isinstance(authorization, str) or not authorization.startswith('Bearer ')
                or not 0 < len(authorization[7:]) <= 16384 or any(c.isspace() for c in authorization[7:])):
            raise HTTPException(401, 'Valid bearer authentication required', headers={'WWW-Authenticate': 'Bearer'})
        try:
            external = verifier.verify_token(authorization[7:])
        except AuthenticationError:
            raise HTTPException(401, 'Valid bearer authentication required', headers={'WWW-Authenticate': 'Bearer'}) from None
        try:
            return directory.resolve(external)
        except PermissionError:
            raise HTTPException(403, 'Research account access denied') from None

    @contextmanager
    def database():
        conn = None
        try:
            conn = open_research_evidence_store(store_path)
            yield conn
        except (RuntimeError, sqlite3.DatabaseError, OSError, ValueError):
            raise HTTPException(503, 'Research evidence integrity or storage unavailable') from None
        finally:
            if conn is not None:
                conn.close()

    @app.get('/research/v1-1/evidence/{program_id:path}')
    def read(program_id: str, principal=Depends(identity)):
        try:
            authorize_research_read(principal, program_id)
        except PermissionError:
            raise HTTPException(403, 'Research evidence access denied') from None
        with database() as conn:
            return read_program_evidence(conn, trusted_catalog, principal, program_id)

    @app.post('/research/v1-1/evidence')
    def submit(payload: EvidenceSubmission, principal=Depends(identity)):
        if 'evidence_submitter' not in principal.roles or payload.program_id not in principal.program_ids:
            raise HTTPException(403, 'Research submission access denied')
        record = payload.model_dump()
        record.update(reviewer_id=None, reviewed_at=None, independent_review_confirmed=False,
                      submitted_by_principal=principal.principal)
        with database() as conn:
            try:
                with _write_transaction(conn) as tx:
                    result = append_submission(tx, record, trusted_catalog, cutoffs.get(payload.program_id))
                    if result['receipt']['accepted']:
                        bind_verified_submitter(tx, result['event_id'], principal)
            except PermissionError:
                raise HTTPException(403, 'Research submission access denied') from None
        result.update(readiness='NOT_READY', authenticated_submitter=principal.principal)
        return JSONResponse(status_code=201 if result['receipt']['accepted'] else 422, content=result)

    @app.post('/research/v1-1/reviews/{evidence_event_id}')
    def review(payload: EvidenceReview, evidence_event_id: int = APIPath(gt=0), principal=Depends(identity)):
        if 'evidence_reviewer' not in principal.roles:
            raise HTTPException(403, 'Independent review access denied')
        with database() as conn:
            try:
                with _write_transaction(conn) as tx:
                    result = record_review(tx, evidence_event_id=evidence_event_id,
                                           reviewer_principal=principal.principal,
                                           outcome=payload.outcome, checks=payload.checks.model_dump(),
                                           rationale=payload.rationale, trusted_identity=principal)
            except PermissionError:
                raise HTTPException(403, 'Independent review access denied') from None
            except ValueError:
                raise HTTPException(422, 'Invalid independent review') from None
        return JSONResponse(status_code=201, content=result)

    return app
