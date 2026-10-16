"""Isolated prototype API. No jobs, trading orders, or source Streamlit mutations."""
from __future__ import annotations

import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

# Render supplies postgres:// or postgresql://; SQLAlchemy 2 uses psycopg (v3) explicitly.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./checklists_dev.sqlite3")
REQUIRE_POSTGRES = os.getenv("PDUFA_REQUIRE_POSTGRES", "").lower() in ("1", "true", "yes")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgres://"):]
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]
ENGINE = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
ALLOWED_STAGES = {"PIPELINE", "GEM_JR", "GEM"}
TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,14}$")


class Base(DeclarativeBase):
    pass


class Checklist(Base):
    __tablename__ = "checklists"

    ticker: Mapped[str] = mapped_column(String(15), primary_key=True)
    stage: Mapped[str] = mapped_column(String(12), primary_key=True)
    selections: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChecklistPayload(BaseModel):
    selections: dict[str, bool] = Field(default_factory=dict)
    notes: str = Field(default="", max_length=4000)
    version: int = Field(ge=0)

    # Prevent unintended huge unbounded state uploads.
    def validate_size(self) -> None:
        if len(self.selections) > 150 or any(len(k) > 100 for k in self.selections):
            raise HTTPException(status_code=422, detail="Checklist size limit exceeded")


def validate_location(ticker: str, stage: str) -> tuple[str, str]:
    ticker = ticker.upper()
    stage = stage.upper()
    if not TICKER_PATTERN.fullmatch(ticker) or stage not in ALLOWED_STAGES:
        raise HTTPException(status_code=422, detail="Invalid ticker or stage")
    return ticker, stage


def require_internal_key(
    x_pdufa_internal_key: Annotated[str | None, Header()] = None,
) -> None:
    expected = os.getenv("PDUFA_INTERNAL_API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API not configured")
    if not x_pdufa_internal_key or not secrets.compare_digest(expected, x_pdufa_internal_key):
        raise HTTPException(status_code=401, detail="Unauthorized")


def storage_ready() -> bool:
    # Hosted staging must NEVER silently save ticker data to ephemeral SQLite.
    return not REQUIRE_POSTGRES or DATABASE_URL.startswith("postgresql+psycopg://")


def require_storage() -> None:
    if not storage_ready():
        raise HTTPException(
            status_code=503,
            detail="Persistent PostgreSQL is not connected. Set DATABASE_URL in Render first.",
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log only storage readiness, never the database URL or credentials.
    import logging
    logging.getLogger(__name__).warning(
        "PDUFA staging storage mode: %s; persistent database ready: %s",
        "postgresql" if DATABASE_URL.startswith("postgresql+psycopg://") else "sqlite",
        storage_ready() and DATABASE_URL.startswith("postgresql+psycopg://"),
    )
    if storage_ready():
        Base.metadata.create_all(bind=ENGINE)  # Bootstrap only; replace with reviewed Alembic migrations
    yield


app = FastAPI(title="PDUFA New Platform Setup API", lifespan=lifespan)


@app.get("/health")
def health():
    # An HTTP 200 permits configuration inspection without claiming DB readiness.
    return {
        "status": "ok" if storage_ready() else "waiting_for_database",
        "service": "pdufa-new-backend",
        "storage_ready": storage_ready(),
        "storage_kind": "postgresql" if DATABASE_URL.startswith("postgresql+psycopg://") else "sqlite",
        "production_scans_enabled": False,
    }


@app.get("/api/checklists/{ticker}/{stage}", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def read_checklist(ticker: str, stage: str):
    ticker, stage = validate_location(ticker, stage)
    with Session(ENGINE) as session:
        item = session.get(Checklist, (ticker, stage))
        if not item:
            return {"ticker": ticker, "stage": stage, "selections": {}, "notes": "", "version": 0, "updated_at": None}
        return {
            "ticker": ticker, "stage": stage, "selections": item.selections,
            "notes": item.notes, "version": item.version, "updated_at": item.updated_at,
        }


@app.put("/api/checklists/{ticker}/{stage}", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def save_checklist(ticker: str, stage: str, payload: ChecklistPayload):
    ticker, stage = validate_location(ticker, stage)
    payload.validate_size()
    now = datetime.now(timezone.utc)
    with Session(ENGINE) as session:
        if payload.version == 0:
            session.add(Checklist(
                ticker=ticker, stage=stage, selections=payload.selections,
                notes=payload.notes, version=1, updated_at=now,
            ))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(status_code=409, detail="Version conflict; reload this checklist")
            return {"saved": True, "version": 1, "updated_at": now}
        result = session.execute(
            update(Checklist)
            .where(Checklist.ticker == ticker, Checklist.stage == stage, Checklist.version == payload.version)
            .values(selections=payload.selections, notes=payload.notes,
                    version=payload.version + 1, updated_at=now)
        )
        if result.rowcount != 1:
            session.rollback()
            raise HTTPException(status_code=409, detail="Version conflict; reload this checklist")
        session.commit()
    return {"saved": True, "version": payload.version + 1, "updated_at": now}
