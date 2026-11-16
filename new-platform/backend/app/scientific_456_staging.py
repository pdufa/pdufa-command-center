"""Standalone, opt-in scientific 456 staging API; no production main/worker imports.

Start only on a separately provisioned backend and database:
  uvicorn app.scientific_456_staging:app --host 0.0.0.0 --port 8000

Never substitute for the main PDUFA service or deploy without owner approval.
"""
from __future__ import annotations

from functools import lru_cache
import os
import re
import secrets
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, Header, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from . import assessment_runtime as runtime

app = FastAPI(title="PDUFA Isolated Scientific 456 Staging", version="0.1.0")
api = APIRouter(prefix="/api/assessment-runtime")


def require_staging_enabled():
    if os.getenv("PDUFA_LEVEL456_BACKEND_ENABLED") != "1":
        raise HTTPException(503, "Scientific 456 staging runtime is disabled")


def require_internal_key(x_pdufa_internal_key: Annotated[str | None, Header()] = None):
    expected = os.getenv("PDUFA_INTERNAL_API_KEY", "")
    if not expected:
        raise HTTPException(503, "Isolated scientific staging key is not configured")
    if not x_pdufa_internal_key or not secrets.compare_digest(x_pdufa_internal_key, expected):
        raise HTTPException(401, "Unauthorized")


@lru_cache(maxsize=1)
def _database_engine():
    """Require a named, physically distinct PostgreSQL database for this service."""
    if os.getenv("PDUFA_REQUIRE_POSTGRES") != "1":
        raise HTTPException(503, "Isolated scientific staging requires PostgreSQL")
    named = os.getenv("PDUFA_LEVEL456_DATABASE_NAME", "")
    if not re.fullmatch(r"[a-z][a-z0-9_]*456[a-z0-9_]*", named):
        raise HTTPException(503, "Unique scientific 456 database name is required")
    raw = os.getenv("DATABASE_URL", "")
    if raw.startswith("postgres://"):
        raw = "postgresql+psycopg://" + raw[len("postgres://"):]
    elif raw.startswith("postgresql://"):
        raw = "postgresql+psycopg://" + raw[len("postgresql://"):]
    try:
        url = make_url(raw)
    except Exception:
        raise HTTPException(503, "Isolated PostgreSQL database URL is not configured") from None
    if url.get_backend_name() != "postgresql" or url.database != named:
        raise HTTPException(503, "Isolated database identity does not match the declared staging database")
    # A dedicated DB/user is the primary isolation boundary. Do not share the
    # production DB with an isolated schema as a substitute for a separate DB.
    return create_engine(url, pool_pre_ping=True)


def isolated_engine():
    require_staging_enabled()
    return _database_engine()


@api.get("/health", include_in_schema=False, dependencies=[Depends(require_staging_enabled)])
def health(db=Depends(isolated_engine)):
    """Read-only readiness probe for isolated staging monitoring.

    An enable flag alone never counts as ready; the staging database must
    accept a SELECT. No trial data, credentials or database name is exposed.
    """
    if not os.getenv("PDUFA_INTERNAL_API_KEY"):
        raise HTTPException(503, "Isolated staging authentication is not configured")
    try:
        with db.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
        if result != 1:
            raise ValueError("Database readiness query did not pass")
    except Exception:
        raise HTTPException(503, "Isolated scientific 456 storage unavailable") from None
    return {"status": "READY", "stagingMode": "SCIENTIFIC_456_ISOLATED_ONLY",
            "fdaModel": "ABSTAIN"}


@api.get("/version")
def version():
    return {
        "engineVersion": runtime.VERSION,
        "scientificContracts": {"SCIENTIFIC_1_6": [4, 5, 6]},
        "levels": [4, 5, 6],
        "stagingMode": "SCIENTIFIC_456_ISOLATED_ONLY",
        "legacy123Separate": True,
        "scientific456Enabled": os.getenv("PDUFA_LEVEL456_BACKEND_ENABLED") == "1",
        "scientificActivation": "RESEARCH_EXECUTION_ONLY",
        "fdaModel": "ABSTAIN",
    }


secured = APIRouter(prefix="/api/assessment-runtime",
                    dependencies=[Depends(require_staging_enabled), Depends(require_internal_key)])


@secured.post("/runs", status_code=202)
def start(request: runtime.RunInput, tasks: BackgroundTasks, db=Depends(isolated_engine)):
    request.checked()
    if request.contract != "SCIENTIFIC_1_6":
        raise HTTPException(422, "Standalone staging accepts only SCIENTIFIC_1_6")
    if os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() in ("1", "true", "yes"):
        raise HTTPException(503, "Isolated scientific assessment writes are paused")
    if request.mode == "BLIND_HISTORICAL":
        runtime.initialize(db)
        try:
            runtime.source_for(db, request)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
    run_id = runtime.create(db, request)
    tasks.add_task(runtime.execute, db, run_id)
    return {"runId": run_id, "nct": request.nct, "status": "QUEUED"}


@secured.get("/runs/{nct}/{run_id}")
def status(nct: str, run_id: str, contract: str, db=Depends(isolated_engine)):
    if contract != "SCIENTIFIC_1_6":
        raise HTTPException(422, "Scientific 456 run contract required")
    return runtime.status(db, nct, run_id, contract)


@secured.get("/history/{nct}")
def history(nct: str, contract: str, level: int | None = None, db=Depends(isolated_engine)):
    if contract != "SCIENTIFIC_1_6":
        raise HTTPException(422, "Scientific 456 history contract required")
    return runtime.history(db, nct, level, contract)


app.include_router(api)
app.include_router(secured)
