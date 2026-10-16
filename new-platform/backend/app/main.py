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


class WatchTrade(Base):
    __tablename__ = "watch_trade_labels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    trade: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProgramIdentity(Base):
    """Never-recycled integer registry, keyed by immutable Pipeline exact program."""
    __tablename__ = "program_identity"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(15), nullable=False)
    drug: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProgramWatchTrade(Base):
    __tablename__ = "program_watch_trade_labels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watch: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    trade: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


PROGRAM_ID_PATTERN = re.compile(r"^PDUFA-[0-9]{6,}$")


class ProgramWatchTradePayload(BaseModel):
    watch: list[str] = Field(default_factory=list, max_length=500)
    trade: list[str] = Field(default_factory=list, max_length=500)
    version: int = Field(ge=0)

    def canonical(self) -> tuple[list[str], list[str]]:
        watch = sorted(set(self.watch))
        trade = sorted(set(self.trade))
        if (any(not isinstance(v, str) or not PROGRAM_ID_PATTERN.fullmatch(v) for v in watch + trade)
                or len(watch) > 500 or len(trade) > 500
                or set(watch).intersection(trade)):
            raise HTTPException(status_code=422, detail="Invalid or overlapping permanent Program IDs")
        return watch, trade


class WatchTradePayload(BaseModel):
    watch: list[str] = Field(default_factory=list, max_length=500)
    trade: list[str] = Field(default_factory=list, max_length=500)
    version: int = Field(ge=0)

    def canonical(self) -> tuple[list[str], list[str]]:
        watch = sorted(set(t.strip().upper() for t in self.watch))
        trade = sorted(set(t.strip().upper() for t in self.trade))
        if (any(not TICKER_PATTERN.fullmatch(t) for t in watch + trade)
                or set(watch).intersection(trade)):
            raise HTTPException(status_code=422, detail="Invalid or overlapping Watch/Trade tickers")
        return watch, trade


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

def require_writes_enabled() -> None:
    # Opt-in freeze for a database migration. GETs remain usable for validation.
    if os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() in ("1", "true", "yes"):
        raise HTTPException(status_code=503, detail="Checklist writes paused for database migration")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Log only storage readiness, never the database URL or credentials.
    import logging
    logging.getLogger(__name__).warning(
        "PDUFA staging storage mode: %s; postgres_required: %s; persistent database ready: %s",
        "postgresql" if DATABASE_URL.startswith("postgresql+psycopg://") else "sqlite",
        REQUIRE_POSTGRES,
        storage_ready() and DATABASE_URL.startswith("postgresql+psycopg://"),
    )
    if storage_ready():
        Base.metadata.create_all(bind=ENGINE)  # Bootstrap only; replace with reviewed Alembic migrations
    if os.getenv("PDUFA_MIGRATION_COPY_ON_BOOT", "") == "1":
        try:
            from .migrate_snapshot import copy_with_checks
            copy_with_checks(
                ENGINE, os.getenv("PDUFA_MIGRATION_TARGET_DATABASE_URL", ""),
                Base, Checklist,
            )
        except Exception as exc:
            # No credentials or source record values should reach application logs.
            logging.getLogger(__name__).error(
                "PDUFA_DATABASE_COPY_FAILED error_type=%s", type(exc).__name__
            )
            raise RuntimeError("PDUFA migration verification failed; source left unchanged") from None
    logging.getLogger(__name__).warning(
        "PDUFA checklist write freeze active: %s",
        os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() in ("1", "true", "yes"),
    )

    # Lightweight asynchronous read-only smoke check; never delays service
    # readiness and never starts a survey, crawler, scan or trading order.
    import threading
    def verify_published_sources():
        try:
            from .source_workspace import workspace
            published = workspace()
            health = published.get("sourceHealth") or {}
            member_rows = (published.get("members", {}).get("GEM_JR", {}).get("rows", [])
                           + published.get("members", {}).get("GEM", {}).get("rows", []))
            verified_profiles = sum(
                isinstance(row.get("technical"), dict)
                and "tradeCall" in row.get("technical", {})
                for row in member_rows
            )
            market_profiles = sum(
                isinstance(row.get("technical"), dict)
                and row.get("technical", {}).get("close") is not None
                for row in member_rows
            )
            logging.getLogger(__name__).warning(
                "PDUFA_TECHNICAL_CHECK profiles=%d/%d eod_profiles=%d",
                verified_profiles, len(member_rows), market_profiles,
            )
            logging.getLogger(__name__).warning(
                "PDUFA_SOURCE_CHECK state=%s programs=%d gem_jr=%d gem=%d clinical_rows=%d issues=%d payload_bytes=%d",
                health.get("state", "UNKNOWN"),
                len(published.get("pipeline", [])),
                len(published.get("members", {}).get("GEM_JR", {}).get("rows", [])),
                len(published.get("members", {}).get("GEM", {}).get("rows", [])),
                health.get("clinicalRows", 0),
                len(health.get("issues", [])),
                len(__import__("json").dumps(published, separators=(",", ":"), default=str).encode("utf-8")),
            )
        except Exception as exc:
            logging.getLogger(__name__).error(
                "PDUFA_SOURCE_CHECK_FAILED error_type=%s", type(exc).__name__
            )
    threading.Thread(target=verify_published_sources, daemon=True).start()
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


@app.put("/api/checklists/{ticker}/{stage}", dependencies=[Depends(require_internal_key), Depends(require_storage), Depends(require_writes_enabled)])
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


@app.get("/api/workspace", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def read_workspace():
    from .source_workspace import workspace
    from .program_registry import number_workspace
    try:
        return number_workspace(workspace())
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("PDUFA_PROGRAM_REGISTRY_FAILED error_type=%s", type(exc).__name__)
        # Do NOT publish an ephemeral/recomputed number if Neon is unavailable.
        raise HTTPException(status_code=503, detail="Persistent program identification unavailable") from None


@app.get("/api/watch-trade", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def get_watch_trade():
    with Session(ENGINE) as session:
        row = session.get(WatchTrade, 1)
        if row is None:
            return {"watch": [], "trade": [], "version": 0, "updated_at": None}
        return {"watch": row.watch, "trade": row.trade, "version": row.version, "updated_at": row.updated_at}


@app.put("/api/watch-trade", dependencies=[Depends(require_internal_key), Depends(require_storage), Depends(require_writes_enabled)])
def put_watch_trade(payload: WatchTradePayload):
    watch, trade = payload.canonical()
    now = datetime.now(timezone.utc)
    with Session(ENGINE) as session:
        if payload.version == 0:
            session.add(WatchTrade(id=1, watch=watch, trade=trade, version=1, updated_at=now))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(status_code=409, detail="Watch/Trade changed in another session; reload")
            return {"watch": watch, "trade": trade, "version": 1, "updated_at": now}
        result = session.execute(
            update(WatchTrade).where(WatchTrade.id == 1, WatchTrade.version == payload.version)
            .values(watch=watch, trade=trade, version=payload.version + 1, updated_at=now)
        )
        if result.rowcount != 1:
            session.rollback()
            raise HTTPException(status_code=409, detail="Watch/Trade changed in another session; reload")
        session.commit()
        return {"watch": watch, "trade": trade, "version": payload.version + 1, "updated_at": now}


@app.get("/api/program-watch-trade", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def get_program_watch_trade():
    with Session(ENGINE) as session:
        row = session.get(ProgramWatchTrade, 1)
        legacy = session.get(WatchTrade, 1)  # Preserve all pre-migration ticker choices.
        watched = list(row.watch) if row else []
        trading = list(row.trade) if row else []
        ids = [int(label[6:]) for label in watched + trading if PROGRAM_ID_PATTERN.fullmatch(label)]
        identities = session.scalars(select(ProgramIdentity).where(ProgramIdentity.id.in_(ids))).all() if ids else []
        return {
            "watch": watched, "trade": trading, "version": row.version if row else 0,
            "updated_at": row.updated_at if row else None,
            "identities": [{
                "programId": f"PDUFA-{item.id:06d}",
                "id": item.source_key, "ticker": item.ticker, "drug": item.drug,
            } for item in identities],
            "legacy": {
                "watch": list(legacy.watch) if legacy else [],
                "trade": list(legacy.trade) if legacy else [],
            },
        }


@app.put("/api/program-watch-trade", dependencies=[
    Depends(require_internal_key), Depends(require_storage), Depends(require_writes_enabled),
])
def put_program_watch_trade(payload: ProgramWatchTradePayload):
    watch, trade = payload.canonical()
    numbers = {int(x[6:]) for x in watch + trade}
    now = datetime.now(timezone.utc)
    with Session(ENGINE) as session:
        existing = set(session.scalars(
            select(ProgramIdentity.id).where(ProgramIdentity.id.in_(numbers))
        ).all()) if numbers else set()
        if existing != numbers:
            raise HTTPException(status_code=422, detail="Unknown permanent Program ID; refresh Pipeline first")
        if payload.version == 0:
            session.add(ProgramWatchTrade(id=1, watch=watch, trade=trade, version=1, updated_at=now))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(status_code=409, detail="Program W/T conflict; reload")
            return {"watch": watch, "trade": trade, "version": 1, "updated_at": now}
        result = session.execute(
            update(ProgramWatchTrade)
            .where(ProgramWatchTrade.id == 1, ProgramWatchTrade.version == payload.version)
            .values(watch=watch, trade=trade, version=payload.version + 1, updated_at=now)
        )
        if result.rowcount != 1:
            session.rollback()
            raise HTTPException(status_code=409, detail="Program W/T conflict; reload")
        session.commit()
    return {"watch": watch, "trade": trade, "version": payload.version + 1, "updated_at": now}
