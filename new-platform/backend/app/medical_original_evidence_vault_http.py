"""Explicitly opted-in, isolated-only ORIGINAL source evidence HTTP vault.

This API is never installed on default settings, never proxied by the dashboard,
and is not a substitute for an independent qualified scientific reviewer.
Only small non-PHI, legally authorized original research sources are acceptable.
"""
from __future__ import annotations
import base64
import binascii
import json
import os
import secrets
import threading

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import medical_original_evidence_vault as vault

ENABLED = ("1", "true", "yes")
ISOLATED_SERVICE = "srv-dbntrkpsrm7s73aec3lg"
LIMIT_JSON_BYTES = 2_850_000
RIGHTS = "I_HAVE_THE_RIGHT_TO_STORE_THIS_PUBLIC_RESEARCH_DOCUMENT"
ROLES = ("read", "write")
_INIT_LOCK = threading.Lock()
_INITIALIZED = False


def feature_enabled() -> bool:
    return (os.getenv("PDUFA_ORIGINAL_EVIDENCE_VAULT_ENABLED", "").lower() in ENABLED
            and os.getenv("PDUFA_MEDICAL_PREVIEW_ENABLED", "").lower() in ENABLED
            and os.getenv("RENDER_SERVICE_ID", "") == ISOLATED_SERVICE
            and os.getenv("PDUFA_REQUIRE_POSTGRES", "").lower() in ENABLED)


def credentials_valid() -> bool:
    r = os.getenv("PDUFA_EVIDENCE_VAULT_READ_KEY", "")
    w = os.getenv("PDUFA_EVIDENCE_VAULT_WRITE_KEY", "")
    return (len(r) >= 32 and len(w) >= 32 and r.isascii() and w.isascii()
            and not secrets.compare_digest(r, w))


def require_role(request: Request, role: str) -> None:
    if not feature_enabled():
        raise HTTPException(503, "Isolated original evidence vault is disabled")
    if not credentials_valid():
        raise HTTPException(503, "Separate evidence reviewer credentials are not configured")
    if request.headers.get("origin") is not None:
        raise HTTPException(403, "Browser-origin storage requests are not supported")
    offered = request.headers.get("x-pdufa-evidence-key", "")
    target = os.getenv("PDUFA_EVIDENCE_VAULT_" + role.upper() + "_KEY", "")
    if not offered or not secrets.compare_digest(offered, target):
        raise HTTPException(401, "Evidence vault role authorization required")


def _initialize(engine, require_storage) -> None:
    global _INITIALIZED
    require_storage()
    if engine.dialect.name != "postgresql":
        raise HTTPException(503, "Durable isolated PostgreSQL is required")
    with _INIT_LOCK:
        if not _INITIALIZED:
            try:
                vault.initialize(engine)
            except Exception:
                raise HTTPException(503, "Isolated evidence storage is unavailable") from None
            _INITIALIZED = True


async def _bounded_payload(request: Request) -> dict:
    if not (request.headers.get("content-type", "").lower().startswith("application/json")):
        raise HTTPException(415, "JSON-only private original evidence upload")
    declared = request.headers.get("content-length")
    if declared and (not declared.isdecimal() or int(declared) > LIMIT_JSON_BYTES):
        raise HTTPException(413, "Original evidence exceeds encrypted storage limit")
    chunks=[]
    size=0
    async for chunk in request.stream():
        size += len(chunk)
        if size > LIMIT_JSON_BYTES:
            raise HTTPException(413, "Original evidence exceeds encrypted storage limit")
        chunks.append(chunk)
    try:
        result=json.loads(b"".join(chunks))
    except (ValueError,UnicodeDecodeError):
        raise HTTPException(400,"Invalid original evidence JSON metadata") from None
    if not isinstance(result, dict) or set(result) != {
       "metadata","originalBytesBase64","rightsAttestation"
    }:
        raise HTTPException(422,"Original source upload requires exact fields")
    if result["rightsAttestation"] != RIGHTS:
        raise HTTPException(422,"Original research document storage rights must be attested")
    if not isinstance(result["originalBytesBase64"],str):
        raise HTTPException(422,"Original evidence bytes must be base64")
    return result


def install_routes(app, engine_provider, require_storage) -> None:
    """Install only on a backend whose startup gate selects the isolated canary."""
    if not feature_enabled():
        return
    router=APIRouter(prefix="/api/internal/medical-original-evidence-vault")

    @router.post("/NCT06081894", status_code=201)
    async def upload(request: Request):
        require_role(request,"write")
        payload=await _bounded_payload(request)
        try:
            raw=base64.b64decode(payload["originalBytesBase64"],validate=True)
        except (ValueError,binascii.Error):
            raise HTTPException(422,"Original bytes base64 encoding invalid") from None
        if len(raw)>vault.MAX_DOCUMENT_BYTES:
            raise HTTPException(413,"Original source exceeds encrypted size limit")
        officer=request.headers.get("x-pdufa-evidence-officer","")
        engine=engine_provider()
        _initialize(engine,require_storage)
        try:
            key=vault.parse_encryption_key(os.getenv("PDUFA_EVIDENCE_ENCRYPTION_KEY_B64"))
            receipt=vault.deposit(engine,metadata=payload["metadata"],original_bytes=raw,
                                  uploaded_by=officer,encryption_key=key)
        except vault.VaultError:
            raise HTTPException(422,"Source evidence did not pass isolated original-byte integrity checks") from None
        return JSONResponse(receipt,status_code=201,headers={"Cache-Control":"no-store"})

    @router.get("/NCT06081894")
    def list_receipts(request: Request):
        require_role(request,"read")
        engine=engine_provider()
        _initialize(engine,require_storage)
        try:
            entries=vault.list_receipts(engine,nct=vault.EXACT_NCT)
        except Exception:
            raise HTTPException(503,"Original evidence metadata unavailable") from None
        return JSONResponse({
            "nct":vault.EXACT_NCT,"receipts":entries,
            "publicSourceOnly":True,
            "originalBytesExposed":False,
            "clinicalGradeEventsWritten":0,
            "reviewerSignoff":False,
            "fdaPrediction":"ABSTAIN",
        },headers={"Cache-Control":"private, no-store"})

    app.include_router(router)
