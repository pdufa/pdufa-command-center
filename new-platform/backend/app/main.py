"""Isolated prototype API. No jobs, trading orders, or source Streamlit mutations."""
from __future__ import annotations

import os
import re
import secrets
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, Integer, LargeBinary, String, create_engine, select, update
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
# A quota-blocked persistent database must not crash the web process or
# silently fall back to ephemeral storage / assign replacement program IDs.
_DB_STATE = {"available": False, "reason": "STARTING"}
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


class ProgramChecklist(Base):
    """Notes and checklist state belong to an exact numbered program and stage."""
    __tablename__ = "program_checklists"
    program_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    stage: Mapped[str] = mapped_column(String(12), primary_key=True)
    selections: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
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


class FullTrialRecord(Base):
    """Every ClinicalTrials.gov field, retained losslessly by exact NCT ID."""
    __tablename__ = "full_trial_records"
    nct_id: Mapped[str] = mapped_column(String(11), primary_key=True)
    payload_gzip: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    statistics: Mapped[list] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CandidateAssessmentHistory(Base):
    """Append-only score/evidence changes for one immutable exact program."""
    __tablename__ = "candidate_assessment_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exact_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    program_id: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    model_version: Mapped[str] = mapped_column(String(60), nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FullTrialDownload(Base):
    __tablename__ = "full_trial_download"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    completed_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    missing_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    statistics_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    p_value_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str] = mapped_column(String(300), nullable=False, default="")


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
    if not _DB_STATE["available"]:
        raise HTTPException(status_code=503, detail={
            "error": "Persistent database temporarily unavailable; no data was reset",
            "reason": _DB_STATE["reason"],
            "action": "Restore database quota/access; program IDs and saved selections are preserved.",
        })

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
        try:
            Base.metadata.create_all(bind=ENGINE)  # Bootstrap only; replace with reviewed Alembic migrations
            _DB_STATE.update(available=True, reason="READY")
        except Exception as exc:
            # Neon's free-plan quota can return HTTP 402 while Postgres tables
            # and identities remain intact. Keep the health endpoint available
            # but fail CLOSED for all storage-dependent data and mutations.
            _DB_STATE.update(
                available=False,
                reason=("DATABASE_QUOTA_EXCEEDED"
                        if "quota" in str(exc).lower() else "DATABASE_UNREACHABLE"),
            )
            logging.getLogger(__name__).error(
                "PDUFA_DB_STARTUP_UNAVAILABLE reason=%s error_type=%s; existing data left unchanged",
                _DB_STATE["reason"], type(exc).__name__,
            )
    else:
        _DB_STATE.update(available=False, reason="POSTGRES_NOT_CONFIGURED")
    if os.getenv("PDUFA_MIGRATION_COPY_ON_BOOT", "") == "1" and _DB_STATE["available"]:
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

    # Optional asynchronous source diagnostics; never delay service readiness.
    # Full workspace/index preparation is explicitly enabled below.
    def verify_published_sources():
        try:
            from .alpaca_market_chart import _credentials, _feed, get_alpaca_bars
            alpaca_configured = bool(_credentials())
            logging.getLogger(__name__).warning(
                "PDUFA_ALPACA_CHART_CONFIG status=%s feed=%s provider=ALPACA orders_enabled=False",
                "CONFIGURED" if alpaca_configured else "MISSING_CREDENTIALS", _feed().upper(),
            )
            if alpaca_configured:
                probe = get_alpaca_bars("SPY", "1M")
                logging.getLogger(__name__).warning(
                    "PDUFA_ALPACA_CHART_CHECK status=%s feed=%s daily_bars=%d",
                    probe["status"], probe["feed"], len(probe.get("bars") or []),
                )
            # Isolated-review-only, read-only end-to-end program identity check.
            # Uses the internal DB connection; no public auth bypass or write.
            if os.getenv("PDUFA_ALPACA_REVIEW_SMOKE", "").lower() in ("1", "true", "yes"):
                try:
                    with Session(ENGINE) as review_session:
                        samples = review_session.scalars(
                            select(ProgramIdentity).where(ProgramIdentity.ticker != "")
                            .order_by(ProgramIdentity.id).limit(5)
                        ).all()
                        rows = [(sample.id, sample.ticker, sample.source_key) for sample in samples]
                    if not rows:
                        logging.getLogger(__name__).warning(
                            "PDUFA_ALPACA_PROGRAM_CHECK status=NO_REGISTERED_PROGRAM")
                    else:
                        from .program_market_enrichment import enrich_program_market
                        for program_id, ticker, exact_key in rows:
                            pid = f"PDUFA-{program_id:06d}"
                            try:
                                result = enrich_program_market(pid, exact_key, ticker, "1M")
                                logging.getLogger(__name__).warning(
                                    "PDUFA_ALPACA_PROGRAM_CHECK program_id=%s ticker=%s exact_key_match=%s status=%s bars=%d close_present=%s volume_present=%s",
                                    pid, ticker, result.get("exactKey") == exact_key,
                                    result.get("status"), result.get("barsAvailable", 0),
                                    isinstance(result.get("latestDailyClose"), (int, float)),
                                    isinstance(result.get("latestIexVolume"), (int, float)),
                                )
                            except Exception as program_exc:
                                logging.getLogger(__name__).error(
                                    "PDUFA_ALPACA_PROGRAM_CHECK program_id=%s ticker=%s status=ERROR error_type=%s",
                                    pid, ticker, type(program_exc).__name__,
                                )
                        from .readiness_smoke import check_deployed_program
                        threading.Thread(
                            target=check_deployed_program,
                            args=(f"PDUFA-{rows[0][0]:06d}", rows[0][2]), daemon=True,
                        ).start()
                except Exception as exc:
                    logging.getLogger(__name__).error(
                        "PDUFA_ALPACA_PROGRAM_CHECK status=ERROR error_type=%s",
                        type(exc).__name__,
                    )
            from .source_workspace import workspace
            from .workspace_response import prepared
            published = prepared(workspace())
            # Direct Pipeline-to-WT clinical trial path must work even when a
            # trial never entered GEM JR or GEM. Read-only startup smoke check.
            try:
                trial = next(
                    (r for r in published.get("pipeline", [])
                     if str(r.get("id") or "").startswith("TRIAL|")), None
                )
                if trial:
                    from .wt_research import for_exact_program
                    profile = for_exact_program(trial["id"])
                    tech = profile.get("technical")
                    if not isinstance(tech, dict) or "indicatorModel" not in tech:
                        raise ValueError("Trial indicator calculation unavailable")
                    logging.getLogger(__name__).warning(
                        "WT_TRIAL_INDICATOR_CHECK status=PASS source=%s entry_coverage=%d exit_coverage=%d",
                        profile.get("source"), tech.get("indicatorEntryCoverage", 0),
                        tech.get("indicatorExitCoverage", 0),
                    )
            except Exception as exc:
                logging.getLogger(__name__).error(
                    "WT_TRIAL_INDICATOR_CHECK_FAILED error_type=%s", type(exc).__name__
                )
            logging.getLogger(__name__).warning(
                "PDUFA_IDENTITY_CHECK registered=%d numbered_pipeline=%d",
                published["identityRegistry"]["registeredExactPrograms"],
                sum(bool(r.get("programId")) for r in published["pipeline"]),
            )
            try:
                from .assessment_service import get_index
                get_index()
            except Exception as exc:
                logging.getLogger(__name__).error("CANDIDATE_ASSESSMENTS_BOOTSTRAP error_type=%s", type(exc).__name__)
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
            logged_charts = sum(
                isinstance(row.get("technical"), dict)
                and len(row["technical"].get("chartBars") or []) >= 2
                for row in member_rows
            )
            logging.getLogger(__name__).warning(
                "PDUFA_CHART_SOURCE_CHECK saved_eod_series=%d/%d same_gem_chart_source=True",
                logged_charts, len(member_rows),
            )
            logging.getLogger(__name__).warning(
                "PDUFA_TECHNICAL_CHECK profiles=%d/%d eod_profiles=%d",
                verified_profiles, len(member_rows), market_profiles,
            )
            exact_programs = published["pipeline"]
            same_ids = {r["id"] for r in exact_programs}
            source_parity = health.get("pipelineSourceParity", {})
            if (len(same_ids) != len(exact_programs)
                    or len(exact_programs) != source_parity.get("exactPrograms")
                    or len(exact_programs) != (source_parity.get("clinicalAndResults", 0)
                                               + source_parity.get("regulatoryPrograms", 0))):
                raise ValueError("Published Pipeline IDs or current-stage count mismatch")
            from collections import Counter
            stage_distribution = Counter(r.get("stage", "Unknown") for r in exact_programs)
            logging.getLogger(__name__).warning(
                "PDUFA_PIPELINE_SOURCE_PARITY status=PASS total=%d registered_and_results=%d "
                "regulatory=%d phase3=%d phase3_results=%d unknown=%d",
                len(exact_programs), source_parity["clinicalAndResults"],
                source_parity["regulatoryPrograms"],
                stage_distribution.get("Phase 3", 0),
                stage_distribution.get("Phase 3 Results", 0),
                stage_distribution.get("Unknown", 0),
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
            traceback_entry = exc.__traceback__
            while traceback_entry and traceback_entry.tb_next:
                traceback_entry = traceback_entry.tb_next
            logging.getLogger(__name__).error(
                "PDUFA_SOURCE_CHECK_FAILED error_type=%s final_function=%s final_line=%s",
                type(exc).__name__,
                traceback_entry.tb_frame.f_code.co_name if traceback_entry else "UNKNOWN",
                traceback_entry.tb_lineno if traceback_entry else "UNKNOWN",
            )
    # Full source verification can outlive a short-lived API/test instance and
    # retain database work after shutdown. Run this optional diagnostic only
    # when explicitly enabled; normal authenticated reads remain on demand.
    if (_DB_STATE["available"]
            and os.getenv("PDUFA_STARTUP_FULL_SOURCE_VERIFY", "0").lower() in ("1", "true", "yes")):
        threading.Thread(target=verify_published_sources, daemon=True).start()
    if (_DB_STATE["available"] and os.getenv("PDUFA_FULL_TRIAL_DOWNLOAD_BOOTSTRAP") == "1"
            and os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() not in ("1", "true", "yes")):
        from .full_trial_archive import bootstrap
        threading.Thread(target=bootstrap, daemon=True).start()
    from .full_trial_archive import cleanup_retired_zip_exports
    cleanup_retired_zip_exports()
    yield


from .reconciliation_review import ReviewPackage

app = FastAPI(title="PDUFA New Platform Setup API", lifespan=lifespan)


@app.post("/api/reconciliation/validate", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def validate_reconciliation_package(payload: "ReviewPackage"):
    """Authenticated, read-only validation. No identity, preset, or scanner writes."""
    from .reconciliation_review import validate_review_package
    try:
        return validate_review_package(payload, ENGINE, ProgramIdentity)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/health")
def health():
    # An HTTP 200 permits configuration inspection without claiming DB readiness.
    from .full_trial_archive import archive_status
    from .assessment_service import public_status
    return {
        "candidate_assessments": public_status(),
        "status": ("ok" if _DB_STATE["available"] else
                   "waiting_for_database" if _DB_STATE["reason"] == "POSTGRES_NOT_CONFIGURED"
                   else "database_unavailable"),
        "service": "pdufa-new-backend",
        "storage_ready": _DB_STATE["available"],
        "storage_reason": _DB_STATE["reason"],
        "storage_kind": "postgresql" if DATABASE_URL.startswith("postgresql+psycopg://") else "sqlite",
        "production_scans_enabled": False,
        "startup_source_verification_enabled": os.getenv("PDUFA_STARTUP_FULL_SOURCE_VERIFY", "0").lower() in ("1", "true", "yes"),
        "full_trial_download": archive_status(),
    }


@app.get("/api/hop/readiness", dependencies=[Depends(require_internal_key)])
def hop_readiness():
    """Research-only status; no storage dependency and no predictions."""
    from .hop_status import hop_readiness_status
    return hop_readiness_status()


@app.get("/api/candidate-assessments", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def candidate_assessment_index():
    from .assessment_service import get_index
    return get_index()


@app.get("/api/candidate-assessments/detail", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def candidate_assessment_detail(identity: str):
    if len(identity) > 512 or not identity:
        raise HTTPException(status_code=422, detail="An exact program identity is required")
    from .assessment_service import exact_detail
    return exact_detail(identity)


@app.get("/api/pipeline-full-records", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def full_trial_status():
    from .full_trial_archive import archive_status
    return archive_status()


@app.post("/api/pipeline-full-records", dependencies=[Depends(require_internal_key), Depends(require_storage), Depends(require_writes_enabled)])
def start_full_trial_download(refresh: bool = False):
    from .full_trial_archive import start_download
    return start_download(refresh=refresh)


@app.get("/api/pipeline-full-records/rows", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def full_trial_rows(ids: str = ""):
    from .full_trial_archive import record_summaries
    return record_summaries(ids)


@app.get("/api/pipeline-full-records/sort-index", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def full_trial_sort_index():
    from .full_trial_archive import record_sort_index
    return record_sort_index()


@app.get("/api/pipeline-full-records/{nct_id}/view-link", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def full_trial_record_link(nct_id: str):
    from .full_trial_archive import make_record_ticket
    return {"path": make_record_ticket(nct_id)}


@app.get("/downloads/pipeline-trial/{nct_id}/{ticket}")
def view_full_trial_record(nct_id: str, ticket: str):
    from .full_trial_archive import record_response
    return record_response(nct_id, ticket)


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


@app.get("/api/entry-signal/{program_id}", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def read_entry_signal(program_id: str):
    """Calculate entry conditions using a server-resolved exact program identity."""
    if not PROGRAM_ID_PATTERN.fullmatch(program_id):
        raise HTTPException(status_code=422, detail="Invalid Program ID")
    with Session(ENGINE) as session:
        identity = session.get(ProgramIdentity, int(program_id[6:]))
        if identity is None:
            raise HTTPException(status_code=404, detail="Program ID not registered")
        ticker, exact_key = identity.ticker, identity.source_key
    from .alpaca_entry_signal import entry_for_program
    return {"programId": program_id, "exactKey": exact_key,
            **entry_for_program(exact_key, ticker)}


@app.get("/api/alpaca-chart/{program_id}", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def read_alpaca_chart(program_id: str, range: str = "1Y"):
    """Alpaca is the ONLY chart provider: never return synthetic/third-party bars."""
    if not PROGRAM_ID_PATTERN.fullmatch(program_id):
        raise HTTPException(status_code=422, detail="Invalid Program ID")
    if range not in {"1M", "3M", "6M", "1Y", "ALL"}:
        raise HTTPException(status_code=422, detail="Invalid Alpaca chart range")
    with Session(ENGINE) as session:
        row = session.get(ProgramIdentity, int(program_id[6:]))
        if row is None:
            raise HTTPException(status_code=404, detail="Program ID not registered")
        ticker = row.ticker
    from .alpaca_market_chart import get_alpaca_bars
    return {"programId": program_id, "exactKey": row.source_key,
            **get_alpaca_bars(ticker, range)}


@app.get("/api/review/investment-readiness/{program_id}", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def read_program_investment_readiness(program_id: str, identity: str, stage: str = "GEM_JR"):
    """Isolated research review only; no trading or scoring mutations."""
    if os.getenv("PDUFA_ALPACA_REVIEW_SMOKE", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=404, detail="Isolated review disabled")
    if not PROGRAM_ID_PATTERN.fullmatch(program_id) or not identity or len(identity) > 512:
        raise HTTPException(status_code=422, detail="Exact program identity required")
    if stage not in ("GEM_JR", "GEM"):
        raise HTTPException(status_code=422, detail="Invalid research stage")
    with Session(ENGINE) as session:
        registered = session.get(ProgramIdentity, int(program_id[6:]))
        if registered is None or registered.source_key != identity:
            raise HTTPException(status_code=404, detail="Exact program not registered")
    from .assessment_service import exact_detail
    from .assessment_readiness_adapter import readiness_from_existing_assessment
    from .market_evidence_review import market_evidence_review
    record = exact_detail(identity)
    market = market_evidence_review(program_id, identity, {"status": "INSUFFICIENT_EVIDENCE"})
    # No market/financing/catalyst claims are inferred from scoring records.
    return readiness_from_existing_assessment(program_id=program_id, exact_key=identity,
        record=record, market_review=market, stage=stage)


@app.get("/api/program-market-enrichment/{program_id}", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def read_program_market_enrichment(program_id: str, range: str = "1Y"):
    """Read-only market enrichment by immutable program identity."""
    if not PROGRAM_ID_PATTERN.fullmatch(program_id):
        raise HTTPException(status_code=422, detail="Invalid Program ID")
    if range not in {"1M", "3M", "6M", "1Y", "ALL"}:
        raise HTTPException(status_code=422, detail="Invalid Alpaca chart range")
    with Session(ENGINE) as session:
        identity = session.get(ProgramIdentity, int(program_id[6:]))
        if identity is None:
            raise HTTPException(status_code=404, detail="Program ID not registered")
        ticker, source_key = identity.ticker, identity.source_key
    from .program_market_enrichment import enrich_program_market
    return enrich_program_market(program_id, source_key, ticker, range)


@app.get("/api/review/program-decision-readiness/{program_id}", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def review_program_decision_readiness(program_id: str, stage: str = "GEM_JR"):
    """Isolated, read-only evidence readiness. No trading or preset changes."""
    if os.getenv("PDUFA_ALPACA_REVIEW_SMOKE", "").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=404, detail="Isolated review disabled")
    if not PROGRAM_ID_PATTERN.fullmatch(program_id):
        raise HTTPException(status_code=422, detail="Invalid Program ID")
    if stage not in {"GEM_JR", "GEM"}:
        raise HTTPException(status_code=422, detail="Invalid research stage")
    with Session(ENGINE) as session:
        identity = session.get(ProgramIdentity, int(program_id[6:]))
        if identity is None:
            raise HTTPException(status_code=404, detail="Program ID not registered")
        exact_key, ticker = identity.source_key, identity.ticker
    from .program_market_enrichment import enrich_program_market
    from .assessment_readiness_adapter import assessment_readiness_inputs
    from .decision_readiness import decision_readiness
    from .risk_evidence_review import risk_evidence_from_assessment
    from .source_catalyst_review import primary_catalyst_review, apply_primary_catalyst
    market = enrich_program_market(program_id, exact_key, ticker, "1M")
    assessment = {"assessment_score": None, "assessment_coverage": None,
                  "status": "ASSESSMENT_UNAVAILABLE"}
    detail = None
    try:
        from .assessment_service import exact_detail
        detail = exact_detail(exact_key)
        assessment = assessment_readiness_inputs(
            detail, program_id=program_id, exact_key=exact_key, stage=stage)
    except HTTPException as exc:
        if exc.status_code not in {404, 409, 503}:
            raise
    risk_evidence = risk_evidence_from_assessment(
        detail, program_id=program_id, exact_key=exact_key, stage=stage)
    candidate = ((detail or {}).get("data") or {}).get("candidate") or {}
    primary = primary_catalyst_review(program_id, exact_key, ticker, candidate.get("pdufaDate"),
                                     current=(risk_evidence["identityStatus"] == "EXACT_IDENTITY_MATCH"
                                              and candidate.get("ticker") == ticker))
    risk_evidence = apply_primary_catalyst(risk_evidence, primary)
    readiness = decision_readiness(
        program_id=program_id, exact_key=exact_key,
        assessment_score=assessment["assessment_score"],
        assessment_coverage=assessment["assessment_coverage"],
        market_review=market["marketEvidenceReview"],
        catalyst_verified=risk_evidence["catalystVerified"],
        financing_risk_reviewed=risk_evidence["financingRiskReviewed"],
    )
    from .research_source_evidence import source_evidence
    observations = source_evidence(program_id, exact_key, ticker,
                                  current=(risk_evidence["identityStatus"] == "EXACT_IDENTITY_MATCH"
                                           and candidate.get("ticker") == ticker))
    return {"programId": program_id, "exactKey": exact_key, "stage": stage,
            "assessmentEvidence": assessment, "marketEvidenceReview": market["marketEvidenceReview"],
            "marketDataStatus": market.get("status"),
            "marketBarsAvailable": market.get("barsAvailable"),
            "marketDataFeed": market.get("feed"),
            "marketSignalStatus": (market.get("marketSignals") or {}).get("status"),
            "riskEvidenceReview": risk_evidence,
            "primaryCatalystReview": primary, "sourceEvidence": observations,
            "decisionReadiness": readiness, "researchOnly": True,
            "ordersEnabled": False, "fsFaChanges": False}


@app.get("/api/review/catalyst-evidence", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def review_primary_catalyst_catalog():
    """Bounded source evidence batch; no scans, grades, or list/preset writes."""
    if os.getenv("PDUFA_ALPACA_REVIEW_SMOKE", "").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=404, detail="Isolated review disabled")
    from .source_catalyst_review import catalog, primary_catalyst_review
    from .source_workspace import workspace, unique
    source = catalog()
    current = unique(workspace()["pipeline"], "id")
    with Session(ENGINE) as session:
        registered = {r.source_key: (f"PDUFA-{r.id:06d}", r.ticker) for r in session.scalars(
            select(ProgramIdentity).where(ProgramIdentity.source_key.in_(source["programs"]))).all()}
    records = []
    for key, item in source["programs"].items():
        identity = registered.get(key)
        if identity is None:
            records.append({"programId": None, "exactKey": key, "status": "UNREGISTERED_PROGRAM", "catalystVerified": False})
            continue
        pid, ticker = identity
        row = current.get(key) or {}
        records.append(primary_catalyst_review(pid, key, ticker, row.get("pdufaDate"),
                       current=row.get("ticker") == ticker))
    return {"status": "CHECKED", "catalogReviewedOn": source["reviewedOn"], "total": len(records),
            "confirmedTargets": sum(r["status"] == "CONFIRMED" for r in records),
            "reportedReadouts": sum(r["status"] == "READOUT_ALREADY_REPORTED" for r in records),
            "records": records, "researchOnly": True, "ordersEnabled": False,
            "assessmentScoreChange": False, "fsFaChanges": False}


@app.get("/api/review/alpaca-program-smoke", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def review_alpaca_program_smoke():
    """Read-only, authenticated, isolated-review program-to-Alpaca smoke test."""
    if os.getenv("PDUFA_ALPACA_REVIEW_SMOKE", "").lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=404, detail="Review smoke check disabled")
    with Session(ENGINE) as session:
        identity = session.scalars(
            select(ProgramIdentity).where(ProgramIdentity.ticker != "").order_by(ProgramIdentity.id).limit(1)
        ).first()
        if identity is None:
            return {"status": "NO_REGISTERED_PROGRAM", "verified": False}
        program_id = f"PDUFA-{identity.id:06d}"
        ticker, source_key = identity.ticker, identity.source_key
    from .program_market_enrichment import enrich_program_market
    result = enrich_program_market(program_id, source_key, ticker, "1M")
    return {"status": "CHECKED", "programId": program_id, "exactKey": source_key,
            "ticker": ticker, "enrichment": result}


@app.get("/api/wt-research/{program_id}", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def read_wt_research(program_id: str):
    """Return same GEM scoring per immutable trial/program, without bulk copying data."""
    if not PROGRAM_ID_PATTERN.fullmatch(program_id):
        raise HTTPException(status_code=422, detail="Invalid Program ID")
    with Session(ENGINE) as session:
        identity = session.get(ProgramIdentity, int(program_id[6:]))
        if identity is None:
            raise HTTPException(status_code=404, detail="Permanent Program ID not registered")
        exact_key = identity.source_key
    from .wt_research import for_exact_program
    try:
        result = for_exact_program(exact_key)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(
            "WT_RESEARCH_LOOKUP_FAILED error_type=%s", type(exc).__name__
        )
        raise HTTPException(status_code=503, detail="Source research temporarily unavailable") from None
    return {"programId": program_id, "exactKey": exact_key, **result}


@app.get("/api/workspace/summary", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def read_workspace_summary():
    """Return verified counts without transferring the full trial inventory."""
    from .source_workspace import workspace
    try:
        published = workspace()
        health = published.get("sourceHealth") or {}
        parity = health.get("streamlitPipelineParity") or health.get("pipelineSourceParity") or {}
        total = len(published.get("pipeline") or [])
        if not parity or parity.get("exactPrograms") != total:
            raise ValueError("Pipeline source parity mismatch")
        members = published.get("members") or {}
        return {
            "pipeline": total,
            "gemJr": len((members.get("GEM_JR") or {}).get("rows") or []),
            "gem": len((members.get("GEM") or {}).get("rows") or []),
            "sourceState": health.get("state", "UNKNOWN"),
            "asOf": published.get("asOf"),
        }
    except Exception:
        import logging
        logging.getLogger(__name__).exception("PDUFA_SUMMARY_FAILED")
        raise HTTPException(status_code=503, detail="Verified workspace summary unavailable") from None


# Cache only the verified, numbered representation of the SAME published-source
# object. source_workspace.workspace() owns freshness and replaces the object on
# refresh; keeping its reference prevents accidental id reuse.
_PAGE_CACHE_LOCK = threading.Lock()
_PAGE_CACHE: dict = {"source": None, "snapshot": None, "version": None}


def _verified_page_snapshot(source: dict):
    from .workspace_response import prepared
    with _PAGE_CACHE_LOCK:
        if _PAGE_CACHE["source"] is source and _PAGE_CACHE["snapshot"] is not None:
            return _PAGE_CACHE["snapshot"], _PAGE_CACHE["version"]
        snapshot = prepared(source)
        rows = snapshot.get("pipeline") or []
        health = snapshot.get("sourceHealth") or {}
        parity = health.get("streamlitPipelineParity") or health.get("pipelineSourceParity") or {}
        if not parity or parity.get("exactPrograms") != len(rows):
            raise ValueError("Pipeline source parity mismatch")
        current_version = snapshot.get("workspaceVersion")
        if not current_version:
            raise ValueError("Stale source cannot be paginated")
        _PAGE_CACHE.update(source=source, snapshot=snapshot, version=current_version)
        return snapshot, current_version


@app.get("/api/workspace/page", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def read_workspace_page(response: Response, offset: int = 0, limit: int = 50, version: str = "", query: str = ""):
    """Bounded, version-checked pipeline page; counts always describe the full snapshot.

    A version mismatch returns 409 so clients cannot silently combine pages
    from different source snapshots. This endpoint does not replace the full
    workspace API or modify any existing frontend behavior.
    """
    if offset < 0 or limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="Invalid page bounds")
    if len(query) > 100:
        raise HTTPException(status_code=422, detail="Search query too long")
    from .source_workspace import workspace
    started = time.perf_counter()
    try:
        snapshot, current_version = _verified_page_snapshot(workspace())
        rows = snapshot.get("pipeline") or []
        total = len(rows)
    except Exception:
        raise HTTPException(status_code=503, detail="Verified workspace page unavailable") from None
    if version and version != current_version:
        raise HTTPException(status_code=409, detail="Workspace version changed; restart pagination")
    # Filter only after validating the COMPLETE source. The version continues
    # to identify the full snapshot, never an arbitrary subset.
    search = query.strip().casefold()
    if search:
        rows = [row for row in rows if any(
            search in str(row.get(field) or "").casefold()
            for field in ("ticker", "drug", "id")
        )]
        total = len(rows)
    response.headers["Server-Timing"] = f"workspace_page;dur={(time.perf_counter() - started) * 1000:.1f}"
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "version": current_version,
        "asOf": snapshot.get("asOf"),
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": rows[offset:offset + limit],
        "nextOffset": offset + limit if offset + limit < total else None,
    }


@app.get("/api/workspace", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def read_workspace(accept_encoding: str = Header(default="")):
    from .source_workspace import workspace
    from .workspace_response import encoded
    started = time.perf_counter()
    try:
        body, compressed = encoded(workspace(), accept_encoding)
        headers = {
            "Cache-Control": "private, no-store",
            "Vary": "Accept-Encoding",
            "Server-Timing": f"workspace;dur={(time.perf_counter() - started) * 1000:.1f}",
        }
        if compressed:
            headers["Content-Encoding"] = "gzip"
        return Response(content=body, media_type="application/json", headers=headers)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("PDUFA_PROGRAM_REGISTRY_FAILED error_type=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Persistent program identification unavailable") from None


@app.get("/api/workspace/delta", dependencies=[Depends(require_internal_key), Depends(require_storage)])
def read_workspace_delta(since: str = ""):
    from .source_workspace import workspace
    from .workspace_response import prepared
    from .workspace_delta import publish
    try:
        snapshot = prepared(workspace())
        version = snapshot.get("workspaceVersion")
        if version and since == version:
            return {"version": version, "unchanged": True, "reset": False,
                    "asOf": snapshot.get("asOf")}
        return publish(snapshot, since=since or None)
    except Exception:
        raise HTTPException(status_code=503, detail="Versioned workspace unavailable") from None


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


def validate_program_checklist(session: Session, program_id: str, stage: str) -> tuple[str, str]:
    stage = stage.upper()
    if not PROGRAM_ID_PATTERN.fullmatch(program_id) or stage not in ALLOWED_STAGES:
        raise HTTPException(status_code=422, detail="Invalid program or stage")
    serial = int(program_id[6:])
    if not session.get(ProgramIdentity, serial):
        raise HTTPException(status_code=404, detail="Permanent Program ID not registered")
    return program_id, stage


@app.get("/api/science/dossier", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def read_science_dossier(programId: str, list: str):
    """Read-only publication boundary. Never fabricate 40 scores from registry metadata."""
    if not PROGRAM_ID_PATTERN.fullmatch(programId) or list not in {"GEM_JR", "GEM", "WT"}:
        raise HTTPException(status_code=422, detail="Invalid scientific dossier identity")
    with Session(ENGINE) as session:
        serial = int(programId[6:])
        if session.get(ProgramIdentity, serial) is None:
            raise HTTPException(status_code=404, detail="Permanent program ID not registered")
    # There is no reviewed, versioned SCIENCE dossier source installed yet.
    # Explicit 404 prevents the frontend from treating incomplete metadata as evidence.
    raise HTTPException(status_code=404, detail="Verified SCIENCE dossier not published")


@app.get("/api/science/source-inventory", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def science_source_inventory(programId: str):
    """Inventory archived source records; never promote a source inventory to SCIENCE scoring."""
    if not PROGRAM_ID_PATTERN.fullmatch(programId):
        raise HTTPException(status_code=422, detail="Invalid permanent program ID")
    with Session(ENGINE) as session:
        identity = session.get(ProgramIdentity, int(programId[6:]))
        if identity is None:
            raise HTTPException(status_code=404, detail="Permanent program ID not registered")
        # The registry's source key is not guaranteed to be a validated NCT link.
        # Do not infer an NCT from ticker or drug; only report exact NCT identifiers.
        nct_matches = sorted(set(re.findall(r"NCT[0-9]{8}", identity.source_key)))
        records = []
        for nct_id in nct_matches:
            row = session.get(FullTrialRecord, nct_id)
            if row:
                records.append({
                    "nctId": nct_id,
                    "sha256": row.sha256,
                    "fetchedAt": row.fetched_at.isoformat(),
                    "hasArchivedPayload": True,
                    "scientificEvidenceVerified": False,
                })
    return {
        "programId": programId,
        "schemaVersion": "science-source-inventory-v1",
        "sourceRecords": records,
        "exactNctIdsFromProgramSourceKey": nct_matches,
        "linkageVerified": False,
        "scientificDossierPublished": False,
        "assessmentScoresAvailable": False,
        "approvalProbability": None,
        "note": "Archival source inventory only; no historical cutoff or clinical evidence verification performed.",
    }


@app.get("/api/science/source-extract", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def science_source_extract(programId: str, nctId: str):
    """Extract archived registry fields with provenance; never convert them into scored evidence."""
    if not PROGRAM_ID_PATTERN.fullmatch(programId) or not re.fullmatch(r"NCT[0-9]{8}", nctId):
        raise HTTPException(status_code=422, detail="Invalid exact program or NCT identifier")
    with Session(ENGINE) as session:
        identity = session.get(ProgramIdentity, int(programId[6:]))
        if identity is None:
            raise HTTPException(status_code=404, detail="Permanent program ID not registered")
        # Program source_key is a candidate link, not clinical identity verification.
        linked_ids = set(re.findall(r"NCT[0-9]{8}", identity.source_key))
        if nctId not in linked_ids:
            raise HTTPException(status_code=409, detail="Exact NCT is not present in program source key")
        row = session.get(FullTrialRecord, nctId)
        if row is None:
            raise HTTPException(status_code=404, detail="Archived exact NCT record not found")
        summary = row.summary if isinstance(row.summary, dict) else {}
        statistics = row.statistics if isinstance(row.statistics, list) else []
        # Whitelist output to avoid leaking arbitrary archived registry payloads.
        fields = {name: summary[name] for name in (
            "nctId", "briefTitle", "overallStatus", "phase", "phases",
            "studyType", "enrollment", "startDate", "primaryCompletionDate",
            "completionDate", "lastUpdatePostDate", "primaryOutcomeMeasures",
        ) if name in summary}
        return {
            "schemaVersion": "science-source-extract-v1",
            "programId": programId, "nctId": nctId,
            "source": "archived-clinicaltrials-gov",
            "archiveSha256": row.sha256,
            "archiveFetchedAt": row.fetched_at.isoformat(),
            "fields": fields,
            "reportedStatisticsCount": len(statistics),
            "linkageVerified": False,
            "publicationDatesVerified": False,
            "scientificEvidenceVerified": False,
            "assessmentScoresAvailable": False,
            "approvalProbability": None,
        }


@app.get("/api/program-checklists/{program_id}/{stage}", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def read_program_checklist(program_id: str, stage: str):
    with Session(ENGINE) as session:
        program_id, stage = validate_program_checklist(session, program_id, stage)
        item = session.get(ProgramChecklist, (program_id, stage))
        return {
            "programId": program_id, "stage": stage,
            "selections": item.selections if item else {}, "notes": item.notes if item else "",
            "version": item.version if item else 0,
            "updated_at": item.updated_at if item else None,
        }


@app.put("/api/program-checklists/{program_id}/{stage}", dependencies=[
    Depends(require_internal_key), Depends(require_storage), Depends(require_writes_enabled),
])
def save_program_checklist(program_id: str, stage: str, payload: ChecklistPayload):
    payload.validate_size()
    now = datetime.now(timezone.utc)
    with Session(ENGINE) as session:
        program_id, stage = validate_program_checklist(session, program_id, stage)
        if payload.version == 0:
            session.add(ProgramChecklist(
                program_id=program_id, stage=stage, selections=payload.selections,
                notes=payload.notes, version=1, updated_at=now,
            ))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(status_code=409, detail="Program checklist conflict; reload")
            return {"saved": True, "programId": program_id, "version": 1, "updated_at": now}
        result = session.execute(
            update(ProgramChecklist)
            .where(
                ProgramChecklist.program_id == program_id,
                ProgramChecklist.stage == stage,
                ProgramChecklist.version == payload.version,
            )
            .values(
                selections=payload.selections, notes=payload.notes,
                version=payload.version + 1, updated_at=now,
            )
        )
        if result.rowcount != 1:
            session.rollback()
            raise HTTPException(status_code=409, detail="Program checklist conflict; reload")
        session.commit()
        return {"saved": True, "programId": program_id,
                "version": payload.version + 1, "updated_at": now}
