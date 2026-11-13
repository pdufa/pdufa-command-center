"""Isolated staging harness. Not imported/mounted by the production application.

Only a disposable synthetic-test mode is supplied. No real identity-provider or
staging deployment has been approved/configured by this code.
"""
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from .level16_review_events import build_router
from .level16_review_policy import ReviewUnavailable, ReviewDenied, ReviewConflict
from .level16_staging_identity import StagingIdentityProvider, check_staging_storage
from .level16_staging_evidence import TransactionalEvidenceResolver


@dataclass(frozen=True)
class HarnessApproval:
    mode: str
    identity_reference: str
    source_authority_reference: str
    isolated_database_name: str


def _module(name):
    path = Path(__file__).resolve().parents[3] / 'scripts/medical' / (name + '.py')
    spec = importlib.util.spec_from_file_location('level16_staging_' + name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def blocked_projection(nct, level, reason, evidence_state='MISSING'):
    return {'status': 'TRUSTED_REVIEW_READBACK_BLOCKED', 'nct': nct, 'level': level,
            'sourceCollectionStatus': 'EVIDENCE_NOT_READY', 'originalDocumentAuthenticationStatus': 'NOT_AUTHENTICATED',
            'reviewerAuthorizationStatus': 'STAGING_ACCESS_AUTHORIZED', 'clinicalReviewStatus': 'NOT_COMPLETED',
            'independentChallengeStatus': 'NOT_COMPLETED', 'independentlyAdjudicated': False,
            'evidenceState': evidence_state, 'history': [], 'blockers': [reason]}


def create_staging_app(*, approval=None, service=None):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    reason = 'No approved individual identity provider, evidence authority or isolated staging configuration'
    enabled = False
    if approval is not None:
        # Intentionally no live enablement path. A server-side approval object is
        # not external authorization; only disposable synthetic infrastructure is supported.
        if (type(approval) is HarnessApproval and approval.mode == 'SYNTHETIC_TEST_ONLY'
                and service is not None and type(service.identity_provider) is StagingIdentityProvider
                and type(service.evidence_provider) is TransactionalEvidenceResolver
                and approval.identity_reference.startswith('SYNTHETIC_TEST_ONLY:')
                and approval.source_authority_reference.startswith('SYNTHETIC_TEST_ONLY:')
                and approval.isolated_database_name.startswith('level16_test_')
                and service.engine is not None and service.engine.url.database == approval.isolated_database_name
                and service.identity_provider.engine is service.engine
                and service.identity_provider.verifier.approval_reference == approval.identity_reference
                and service.evidence_provider.attestation_verifier.approval_reference == approval.source_authority_reference
                and all((urlsplit(v.issuer).hostname or '').endswith('.example.test') for v in (
                    service.identity_provider.verifier, service.evidence_provider.attestation_verifier))):
            with service.engine.begin() as c:
                service._storage(c)
                check_staging_storage(c)
                if c.execute(text('SELECT current_database()')).scalar() != approval.isolated_database_name:
                    raise ReviewUnavailable('Isolated test database identity mismatch')
            enabled = True
    status = {'status': 'SYNTHETIC_TEST_HARNESS_ONLY' if enabled else 'BLOCKED',
              'liveIntegrationEnabled': False, 'actualAuthenticatedSources': 0, 'actualScientificReviews': 0,
              'blockers': [] if enabled else [reason]}

    @app.middleware('http')
    async def protect_response(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        return response

    @app.get('/staging/status')
    def staging_status():
        return status

    if not enabled:
        @app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
        def blocked(path: str):
            raise HTTPException(503, reason)
        return app

    app.include_router(build_router(service))

    def read(nct, level, credential):
        try:
            result = service.projection(credential, nct, level)
            return result if result is not None else blocked_projection(nct, level, 'ORIGINAL_EVIDENCE_NOT_PROVISIONED')
        except ReviewDenied:
            return blocked_projection(nct, level, 'ORIGINAL_EVIDENCE_ACCESS_OR_ATTESTATION_REJECTED', 'UNREVIEWED')
        except (ReviewConflict, ValueError):
            return blocked_projection(nct, level, 'ORIGINAL_EVIDENCE_CONFLICT_OR_VERSION_REJECTED', 'CONFLICTING')

    @app.get('/staging/levels1-6', response_class=HTMLResponse)
    def assessment(authorization: str | None = Header(default=None)):
        try:
            # A denied/expired/revoked token must never receive even roster HTML.
            actor = service.identity_provider.authenticate(authorization)
            with service.engine.begin() as c:
                service._storage(c)
                service._grants(c, actor)
            engine, preview = _module('phase_first_levels_1_6'), _module('render_level16_focus_preview')
            roster, apps, definition = [json.loads(p.read_text(encoding='utf-8')) for p in (
                engine.ROSTER_PATH, engine.APPLICATIONS_PATH, engine.DEFINITION_PATH)]
            reader = lambda nct, level: read(nct, level, authorization)
            report = engine.build(roster, apps, {'results': {}}, definition, trusted_review_reader=reader)
            html = preview.render(report, trusted_review_reader=reader)
            return HTMLResponse(html.replace('<body>', '<body><p>SYNTHETIC TEST HARNESS — NOT REAL CLINICAL ASSESSMENTS</p>'))
        except ReviewDenied:
            raise HTTPException(403, 'Individual reviewer access denied') from None
        except (ReviewConflict, ValueError):
            raise HTTPException(409, 'Evidence changed; refresh the assessment interface') from None
        except (ReviewUnavailable, DBAPIError):
            raise HTTPException(503, 'Staging review infrastructure unavailable') from None

    @app.get('/staging/evidence/{stream_id}/{document_id}')
    def original_document(stream_id: str, document_id: str, authorization: str | None = Header(default=None)):
        try:
            actor = service.identity_provider.authenticate(authorization)
            with service.engine.begin() as c:
                service._storage(c)
                service._grants(c, actor)
                data = service.evidence_provider.document(stream_id, document_id, c)
            return Response(data, media_type='application/octet-stream',
                            headers={'Content-Disposition': 'attachment; filename="original-evidence.bin"'})
        except ReviewDenied:
            raise HTTPException(403, 'Original evidence access denied') from None
        except (ReviewConflict, ValueError):
            raise HTTPException(409, 'Original evidence unavailable or stale') from None
        except (ReviewUnavailable, DBAPIError):
            raise HTTPException(503, 'Staging evidence infrastructure unavailable') from None

    return app
