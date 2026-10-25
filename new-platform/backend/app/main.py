"""Isolated prototype API. No jobs, trading orders, or source Streamlit mutations."""
from __future__ import annotations

import os
import re
import secrets
import threading
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import JSON, DateTime, Integer, LargeBinary, String, UniqueConstraint, create_engine, select, update
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


class ScientificBatchJob(Base):
    """Durable, isolated scientific import history; one unfinished batch at a time."""
    __tablename__ = "scientific_batch_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(28), nullable=False)
    nct_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    events: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    already_exists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Unique nullable slot prevents overlapping unfinished batches, across workers.
    active_slot: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScientificEvidenceLedgerEntry(Base):
    """Append-only independent-source candidate, never an auto-verified conclusion."""
    __tablename__ = "scientific_evidence_ledger"
    __table_args__ = (
        # Concurrent attempts to correct the same version cannot both succeed.
        UniqueConstraint("nct_id", "thread_id", "revision",
                         name="uq_scientific_evidence_revision"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nct_id: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    thread_id: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(String(32))
    gate_id: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str] = mapped_column(String(800), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_published_at: Mapped[str | None] = mapped_column(String(10))
    claim_text: Mapped[str] = mapped_column(String(1000), nullable=False)
    relationship: Mapped[str] = mapped_column(String(24), nullable=False)
    caution: Mapped[str] = mapped_column(String(1000), nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class ScientificReviewerFinding(Base):
    """Immutable, source-linked reviewer claim. NEVER independent verification."""
    __tablename__ = "scientific_reviewer_findings"
    __table_args__ = (
        UniqueConstraint("nct_id", "thread_id", "revision",
                         name="uq_scientific_reviewer_finding_revision"),
        UniqueConstraint("supersedes_id", name="uq_scientific_reviewer_finding_parent"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nct_id: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(70), nullable=False)
    gate_id: Mapped[str] = mapped_column(String(32), nullable=False)
    thread_id: Mapped[str] = mapped_column(String(32), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_url: Mapped[str] = mapped_column(String(800), nullable=False)
    source_locator: Mapped[str] = mapped_column(String(200), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(30), nullable=False)
    assertion: Mapped[str] = mapped_column(String(1500), nullable=False)
    uncertainty: Mapped[str] = mapped_column(String(1000), nullable=False)
    reviewer_label: Mapped[str] = mapped_column(String(80), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class ScientificSourceDocument(Base):
    """Captured original PDF bytes; archival integrity is NOT scientific review."""
    __tablename__ = "scientific_source_documents"
    __table_args__ = (
        UniqueConstraint("nct_id", "sha256",
                         name="uq_scientific_source_document_content"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nct_id: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    gate_id: Mapped[str] = mapped_column(String(32), nullable=False)
    source_url: Mapped[str] = mapped_column(String(800), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    filename: Mapped[str] = mapped_column(String(140), nullable=False)
    captured_by: Mapped[str] = mapped_column(String(80), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_length: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    capture_status: Mapped[str] = mapped_column(String(40), nullable=False)
    manifest_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class ScientificReviewerAccount(Base):
    """Isolated Google subject allowlist; a login alone grants no review role."""
    __tablename__ = "scientific_reviewer_accounts"

    google_subject: Mapped[str] = mapped_column(String(255), primary_key=True)
    verified_email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    credentials_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScientificReviewAuditEvent(Base):
    """Append-only audit envelope. Never constitutes clinical adjudication."""
    __tablename__ = "scientific_review_audit_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nct_id: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(70), nullable=False)
    google_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    event_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    event_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScientificReviewSubmission(Base):
    """Immutable reviewer submission; no scientific adjudication or score."""
    __tablename__ = "scientific_review_submissions"
    __table_args__ = (
        UniqueConstraint("nct_id", "question_id", "source_sha256", "google_subject",
                         name="uq_scientific_review_subject_source"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nct_id: Mapped[str] = mapped_column(String(11), nullable=False, index=True)
    question_id: Mapped[str] = mapped_column(String(70), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    google_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    attestation: Mapped[dict] = mapped_column(JSON, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScientificSmokeClaim(Base):
    """One durable execution claim per trial for temporary isolated live smoke."""
    __tablename__ = "scientific_smoke_claims"

    nct_id: Mapped[str] = mapped_column(String(11), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
            # Safe, read-only startup diagnostic; logs counts only, never trial data or secrets.
            try:
                from sqlalchemy import func, inspect
                with Session(ENGINE) as session:
                    present = inspect(session.get_bind()).has_table("full_trial_records")
                    total = session.scalar(select(func.count()).select_from(FullTrialRecord)) if present else None
                logging.getLogger(__name__).warning(
                    "SCIENTIFIC_ARCHIVE_STATUS table_present=%s stored_trial_count=%s",
                    present, total,
                )
            except Exception as diagnostic_error:
                logging.getLogger(__name__).warning(
                    "SCIENTIFIC_ARCHIVE_STATUS unavailable error_type=%s",
                    type(diagnostic_error).__name__,
                )
            # Read-only verification of the persistent batch-history table.
            try:
                from sqlalchemy import func
                with Session(ENGINE) as session:
                    batch_count = session.scalar(
                        select(func.count()).select_from(ScientificBatchJob)
                    )
                    active_count = session.scalar(
                        select(func.count()).select_from(ScientificBatchJob)
                        .where(ScientificBatchJob.active_slot.is_not(None))
                    )
                    claim_count = session.scalar(
                        select(func.count()).select_from(ScientificSmokeClaim)
                    )
                logging.getLogger(__name__).warning(
                    "SCIENTIFIC_BATCH_STORAGE_STATUS status=PASS stored_job_count=%s "
                    "active_job_count=%s smoke_claim_count=%s",
                    batch_count, active_count, claim_count,
                )
            except Exception as batch_diagnostic_error:
                logging.getLogger(__name__).warning(
                    "SCIENTIFIC_BATCH_STORAGE_STATUS status=FAIL error_type=%s",
                    type(batch_diagnostic_error).__name__,
                )
            # Read-only evidence ledger verification. Candidate entries must
            # never be counted as adjudicated clinical or FDA evidence.
            try:
                from sqlalchemy import func
                with Session(ENGINE) as ledger_session:
                    evidence_count = ledger_session.scalar(
                        select(func.count()).select_from(ScientificEvidenceLedgerEntry)
                    )
                logging.getLogger(__name__).warning(
                    "SCIENTIFIC_EVIDENCE_LEDGER_STORAGE status=PASS "
                    "candidate_revision_count=%d verified_gate_count=0",
                    evidence_count,
                )
                try:
                    from .scientific_source_documents import read_document_manifest
                    pdf_manifest = read_document_manifest("NCT02142738")
                    source_archive_ok = (
                        pdf_manifest["allCapturedBytesRehashed"] is True
                        and pdf_manifest["independentSourceVerificationCompleted"] is False
                    )
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_PDF_ARCHIVE_READBACK status=%s "
                        "captured_pdfs=%d byte_integrity_checked=True "
                        "independent_content_verification=False",
                        "PASS" if source_archive_ok else "FAIL",
                        pdf_manifest["sourceDocumentCount"],
                    )
                except Exception as pdf_archive_error:
                    logging.getLogger(__name__).error(
                        "SCIENTIFIC_PDF_ARCHIVE_READBACK status=FAIL error_type=%s",
                        type(pdf_archive_error).__name__,
                    )
                from .scientific_reviewer_findings import read_reviewer_statements
                reviewer = read_reviewer_statements("NCT02142738")
                reviewer_ok = (
                    reviewer["questionsIndependentlyResolved"] == 0
                    and reviewer["independentConfirmationImplemented"] is False
                    and reviewer["fdaApprovalProbability"] is None
                )
                logging.getLogger(__name__).warning(
                    "SCIENTIFIC_REVIEWER_NOTES_READBACK status=%s "
                    "statements=%d conflicted_questions=%d "
                    "independent_verification=False read_only=True",
                    "PASS" if reviewer_ok else "FAIL",
                    reviewer["totalStatements"],
                    reviewer["questionsWithConflictingStatements"],
                )
                from .scientific_evidence_ledger import pilot_candidates
                from .scientific_reconciliation_worklist import reconciliation_worklist
                worklist = reconciliation_worklist("NCT02142738")
                candidates = pilot_candidates("NCT02142738")
                safe = (
                    worklist["totalChecks"] == 8
                    and worklist["unresolvedChecks"] == 8
                    and worklist["verifiedChecks"] == 0
                    and all(item["independentlyVerified"] is False
                            for item in candidates)
                    and len(candidates) == 7
                )
                logging.getLogger(__name__).warning(
                    "SCIENTIFIC_SOURCE_RECONCILIATION status=%s "
                    "questions=%d unresolved=%d candidate_sources=%d "
                    "verified=0 read_only=True",
                    "PASS" if safe else "FAIL",
                    worklist["totalChecks"],
                    worklist["unresolvedChecks"], len(candidates),
                )
            except Exception as ledger_check_error:
                logging.getLogger(__name__).warning(
                    "SCIENTIFIC_EVIDENCE_LEDGER_STORAGE status=FAIL error_type=%s",
                    type(ledger_check_error).__name__,
                )
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
    # Read back and checksum-verify one archived record after every startup.
    # Diagnostic is read-only and does not log the trial payload.
    if _DB_STATE["available"] and REQUIRE_POSTGRES:
        try:
            from .scientific_stored_record import evidence_from_archive
            with Session(ENGINE) as verify_session:
                sample = verify_session.scalars(
                    select(FullTrialRecord).order_by(FullTrialRecord.nct_id).limit(1)
                ).first()
                if sample is None:
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_ARCHIVE_READBACK status=EMPTY"
                    )
                else:
                    verified = evidence_from_archive(
                        sample.nct_id, sample.payload_gzip, sample.sha256
                    )
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_ARCHIVE_READBACK status=PASS nct_id=%s evidence_status=%s",
                        sample.nct_id, verified.get("verificationStatus"),
                    )
        except Exception as verify_exc:
            logging.getLogger(__name__).error(
                "SCIENTIFIC_ARCHIVE_READBACK status=FAIL error_type=%s",
                type(verify_exc).__name__,
            )
    # Read-only depth-20 coverage smoke: checksum-verified archive, never a score.
    if _DB_STATE["available"] and REQUIRE_POSTGRES:
        try:
            from .scientific_stored_record import verified_record_from_archive
            from .scientific_investigation_20 import investigation_20
            from .scientific_quantitative_results import reported_quantitative_results
            with Session(ENGINE) as depth_session:
                depth_record = depth_session.scalars(
                    select(FullTrialRecord).order_by(FullTrialRecord.nct_id).limit(1)
                ).first()
                if depth_record is None:
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_INVESTIGATION20_READBACK status=EMPTY"
                    )
                else:
                    snapshot = verified_record_from_archive(
                        depth_record.nct_id,
                        depth_record.payload_gzip,
                        depth_record.sha256,
                    )
                    dossier = investigation_20(
                        depth_record.nct_id,
                        snapshot,
                        retrieved_at=depth_record.fetched_at.isoformat(),
                    )
                    ok = (
                        dossier["levelCount"] == 20
                        and dossier["scientificallyVerifiedLevels"] == 0
                        and dossier["overallScore"] is None
                        and dossier["fdaApprovalProbability"] is None
                    )
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_INVESTIGATION20_READBACK status=%s "
                        "level_count=%s source_covered_levels=%s scored=False",
                        "PASS" if ok else "FAIL",
                        dossier["levelCount"], dossier["levelsWithSourceFields"],
                    )
                    reported = reported_quantitative_results(depth_record.nct_id, snapshot)
                    quantitative_ok = (
                        reported["independentlyVerified"] is False
                        and reported["effectivenessConclusion"] is None
                        and reported["approvalProbability"] is None
                    )
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_QUANTITATIVE_READBACK status=%s "
                        "outcomes=%d analyses=%d pvalues_shown=%d source_only=True",
                        "PASS" if quantitative_ok else "FAIL",
                        reported["outcomeCountTotal"],
                        reported["analysisCountTotal"],
                        reported["reportedPValuesShown"],
                    )
                    from .scientific_readiness_grades import review_readiness
                    readiness = review_readiness(
                        depth_record.nct_id, snapshot,
                        archive_retrieved_at=depth_record.fetched_at.isoformat()
                        if depth_record.fetched_at else None,
                    )
                    analysis = readiness["analysisReadiness"]
                    reluctance = readiness["scientificReluctance"]
                    grade_ok = (
                        len(readiness["requirements"]) == 16
                        and analysis["readyForFullScientificConclusion"] is False
                        and analysis["verdict"] == "NOT_READY"
                        and reluctance["grade"] == "F"
                        and readiness["scientificScore"] is None
                        and readiness["fdaApprovalProbability"] is None
                    )
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_EVIDENCE_GRADES_READBACK status=%s "
                        "input_grade=%s input_coverage=%s reluctance_grade=%s "
                        "full_science_ready=False scores_assigned=False",
                        "PASS" if grade_ok else "FAIL",
                        analysis["grade"], analysis["coveragePercent"],
                        reluctance["grade"],
                    )
                    from .scientific_review_packet import (
                        build_review_packet, check_packet_integrity,
                    )
                    packet = build_review_packet(depth_record.nct_id)
                    packet_ok = (
                        check_packet_integrity(packet)
                        and packet["investigation20"]["levelCount"] == 20
                        and len(packet["evidenceInputGrades"]["requirements"]) == 16
                        and packet["reconciliation"]["independentlyResolvedCount"] == 0
                        and packet["adjudicationPreflight"]["questionsReadyForAdjudication"] == 0
                        and packet["adjudicationPreflight"]["questionsIndependentlyResolved"] == 0
                        and packet["adjudicationPreflight"]["independentDualReviewImplemented"] is False
                        and packet["scientificConclusion"] is None
                        and packet["fdaApprovalProbability"] is None
                    )
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_REVIEW_PACKET_READBACK status=%s "
                        "nct_id=%s questions=%d sha256_verified=%s "
                        "scored=False read_only=True",
                        "PASS" if packet_ok else "FAIL",
                        depth_record.nct_id,
                        packet["reconciliation"]["unresolvedCount"], packet_ok,
                    )
                    preflight = packet["adjudicationPreflight"]
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_ADJUDICATION_PREFLIGHT status=%s "
                        "nct_id=%s total_questions=%d reviewer_observed=%d "
                        "current_disputes=%d eligible=0 resolved=0 "
                        "identity_verified=False source_content_verified=False",
                        "PASS" if packet_ok else "FAIL",
                        depth_record.nct_id,
                        preflight["questionCount"],
                        preflight["questionsWithRecordedObservations"],
                        preflight["questionsWithCurrentDisputes"],
                    )
        except Exception as depth_error:
            logging.getLogger(__name__).error(
                "SCIENTIFIC_INVESTIGATION20_READBACK status=FAIL error_type=%s",
                type(depth_error).__name__,
            )
    # Verify the actual scientific API handler against the persisted archived
    # pilot (not synthetic pytest stubs). No credentials, payloads, or patient
    # details are logged, and this cannot promote evidence or trigger jobs.
    if (_DB_STATE["available"] and REQUIRE_POSTGRES
            and os.getenv("RENDER_SERVICE_ID") == "srv-dbehn9fb9u1s739ok5vg"):
        try:
            live_trial = get_scientific_assessment("TRIAL|NCT02142738")
            forty = live_trial.get("investigation40") or {}
            plan = forty.get("depthReview") or {}
            tasks = plan.get("tasks") or []
            stage_links = forty.get("stageCrosswalk") or {}
            ids = {
                (item.get("assessmentId"), item.get("depthLevel"))
                for item in tasks
            }
            forty_ok = (
                live_trial.get("registryEvidenceStatus") == "source_record_loaded"
                and forty.get("nctId") == "NCT02142738"
                and len(forty.get("layers") or []) == 8
                and forty.get("verification", {}).get("verified_assessments") == 0
                and plan.get("requiredTasks") == 320
                and plan.get("completedTasks") == 0
                and len(tasks) == len(ids) == 320
                and all(item.get("status") == "pending_independent_review"
                        and item.get("independentlyVerified") is False
                        and item.get("scientificScore") is None
                        for item in tasks)
                and plan.get("readyForScientificConclusion") is False
                and plan.get("approvalProbability") is None
                and live_trial.get("assessment", {}).get("overall_score") is None
                and stage_links.get("stageCount") == 20
                and stage_links.get("assessmentCount") == 40
                and stage_links.get("stagesWithLinkedAssessments") == 20
                and stage_links.get("independentlyVerifiedAssessments") == 0
                and stage_links.get("approvalProbability") is None
            )
            logging.getLogger(__name__).warning(
                "SCIENTIFIC_INVESTIGATION40_API_READBACK status=%s "
                "nct_id=NCT02142738 layers=%d assessments=%d tasks=%d "
                "stages=20 stage_coverage=20 independently_verified=0 "
                "scored=False read_only=True",
                "PASS" if forty_ok else "FAIL",
                len(forty.get("layers") or []),
                sum(len(layer.get("assessments") or [])
                    for layer in forty.get("layers") or []),
                len(tasks),
            )
        except Exception as check_exc:
            logging.getLogger(__name__).error(
                "SCIENTIFIC_INVESTIGATION40_API_READBACK status=FAIL error_type=%s",
                type(check_exc).__name__,
            )
    # Isolated review startup: read one known archived Phase 3 pilot, validate
    # evidence/source identity and eight unscored domains, log only booleans
    # and counts. Never changes any stored trial or candidate rankings.
    if (_DB_STATE["available"] and REQUIRE_POSTGRES
            and os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() in ("1", "true", "yes")):
        try:
            from .scientific_pilot_live_verify import verify_archived_keynote024
            with Session(ENGINE) as pilot_session:
                pilot_record = pilot_session.get(FullTrialRecord, "NCT02142738")
                if pilot_record is None:
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_KEYNOTE024_LIVE_PILOT status=NOT_ARCHIVED"
                    )
                else:
                    pilot_diagnostic = verify_archived_keynote024(
                        pilot_record.nct_id,
                        pilot_record.payload_gzip,
                        pilot_record.sha256,
                        pilot_record.fetched_at,
                    )
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_KEYNOTE024_LIVE_PILOT status=%s nct_id=%s "
                        "archive_verified=%s domains=%d publications=%d "
                        "completed=%s scored=%s read_only=%s",
                        pilot_diagnostic["status"],
                        pilot_diagnostic["nct_id"],
                        pilot_diagnostic["archived_source_verified"],
                        pilot_diagnostic["scientific_domains"],
                        pilot_diagnostic["published_analyses"],
                        pilot_diagnostic["scientific_assessment_completed"],
                        pilot_diagnostic["score_assigned"],
                        pilot_diagnostic["read_only"],
                    )
        except Exception as pilot_error:
            logging.getLogger(__name__).error(
                "SCIENTIFIC_KEYNOTE024_LIVE_PILOT status=FAIL error_type=%s",
                type(pilot_error).__name__,
            )
    # One exact archived-trial evidence audit in the ISOLATED review environment.
    # Never runs live source requests or scanner jobs and never mutates storage.
    if (_DB_STATE["available"] and REQUIRE_POSTGRES
            and os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() in ("1", "true", "yes")):
        try:
            from .scientific_dossier_archive import (
                dossier_from_archive, verified_archived_registry_record,
            )
            from .scientific_pilot_evidence_audit import keynote024_preinterim_evidence_audit
            from .scientific_protocol_readiness import keynote024_protocol_readiness
            from .scientific_pilot_keynote024_results import keynote024_published_results
            with Session(ENGINE) as audit_session:
                audit_record = audit_session.get(FullTrialRecord, "NCT02142738")
                if audit_record is None:
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_KEYNOTE024_SOURCE_AUDIT status=NOT_ARCHIVED"
                    )
                else:
                    archived_dossier = dossier_from_archive(
                        "TRIAL|NCT02142738", audit_record.nct_id,
                        audit_record.payload_gzip, audit_record.sha256, audit_record.fetched_at,
                    )
                    registry = verified_archived_registry_record(
                        audit_record.nct_id, audit_record.payload_gzip, audit_record.sha256,
                    )
                    publication = keynote024_published_results()
                    source_audit = keynote024_preinterim_evidence_audit(registry, publication)
                    grade = keynote024_protocol_readiness(archived_dossier, publication)
                    if (source_audit["earlyDesignEvidence"]["signedSapVerified"] is not False
                            or source_audit["inputReadinessGradeChanged"] is not False
                            or grade["inputReadiness"]["grade"] != "FAIL"
                            or grade["reluctance"]["grade"] != "HIGH"):
                        raise ValueError("Unsafe historical grade promotion")
                    logging.getLogger(__name__).warning(
                        "SCIENTIFIC_KEYNOTE024_SOURCE_AUDIT status=PASS nct_id=%s "
                        "timeline=%d safety_groups=%d preinterim_sap_verified=%s "
                        "input_grade=%s reluctance_grade=%s read_only=%s",
                        source_audit["nctId"],
                        len(source_audit["timeline"]),
                        source_audit["registrySafety"]["groupCount"],
                        source_audit["earlyDesignEvidence"]["signedSapVerified"],
                        grade["inputReadiness"]["grade"],
                        grade["reluctance"]["grade"],
                        source_audit["readOnly"],
                    )
        except Exception as audit_exc:
            logging.getLogger(__name__).error(
                "SCIENTIFIC_KEYNOTE024_SOURCE_AUDIT status=FAIL error_type=%s",
                type(audit_exc).__name__,
            )
    # Explicit one-record bootstrap for isolated review; disabled by default.
    # Never runs for production unless separately and deliberately configured.
    bootstrap_nct = os.getenv("PDUFA_SCIENTIFIC_BOOTSTRAP_NCT", "").strip()
    if bootstrap_nct and _DB_STATE["available"] and REQUIRE_POSTGRES:
        try:
            from .scientific_import import import_one
            bootstrap_result = import_one(bootstrap_nct)
            logging.getLogger(__name__).warning(
                "SCIENTIFIC_BOOTSTRAP nct_id=%s status=%s", bootstrap_nct, bootstrap_result
            )
        except Exception as bootstrap_exc:
            # Log only HTTP status code and exception class; never URLs or secrets.
            logging.getLogger(__name__).error(
                "SCIENTIFIC_BOOTSTRAP status=ERROR error_type=%s http_status=%s",
                type(bootstrap_exc).__name__,
                getattr(bootstrap_exc, "code", None),
            )
    logging.getLogger(__name__).warning(
        "PDUFA checklist write freeze active: %s",
        os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() in ("1", "true", "yes"),
    )

    # Lightweight asynchronous read-only smoke check; never delays service
    # readiness and never starts a survey, crawler, scan or trading order.
    import threading
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
    # Offline pytest runs use disposable SQLite engines; a detached background
    # thread can outlive a test fixture and race engine.dispose().
    # Keep the read-only smoke probe for deployed services, but skip it in tests.
    if _DB_STATE["available"] and "PYTEST_CURRENT_TEST" not in os.environ:
        threading.Thread(target=verify_published_sources, daemon=True).start()
    if (_DB_STATE["available"] and os.getenv("PDUFA_FULL_TRIAL_DOWNLOAD_BOOTSTRAP") == "1"
            and os.getenv("PDUFA_MIGRATION_READ_ONLY", "").lower() not in ("1", "true", "yes")):
        from .full_trial_archive import bootstrap
        threading.Thread(target=bootstrap, daemon=True).start()
    from .full_trial_archive import cleanup_retired_zip_exports
    cleanup_retired_zip_exports()
    # Explicit, temporary isolated-service opt-in only; never starts ordinary scans.
    if _DB_STATE["available"]:
        from .scientific_live_smoke import launch_once_if_requested
        launch_once_if_requested()
    from .scientific_api_read_probe import launch_if_isolated_review
    launch_if_isolated_review()
    yield


from .reconciliation_review import ReviewPackage

app = FastAPI(title="PDUFA New Platform Setup API", lifespan=lifespan)


@app.get("/api/scientific-assessment/reviewer/auth-status", dependencies=[Depends(require_internal_key)])
def scientific_reviewer_auth_status():
    """Configuration diagnostics without disclosing tokens, IDs or credentials."""
    configured = bool(os.getenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", "").strip())
    single_operator = os.getenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "").strip() == "single_operator"
    operator_email = os.getenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "").strip()
    return {
        "googleClientConfigured": configured,
        "googleIdentityVerificationEnabled": configured,
        "accessMode": "single_operator" if single_operator else "reviewer_allowlist",
        "singleOperatorConfigured": bool(configured and single_operator and operator_email),
        "independentVerificationRequiresDistinctReviewers": True,
        "reviewerSelfRegistrationAllowed": False,
        "credentialAutoVerificationAllowed": False,
        "scientificScoreAutoPromotionAllowed": False,
        "nextAction": (
            "single_operator_google_signin_then_admin_reviewer_provisioning"
            if configured and single_operator and operator_email
            else "admin_provision_and_real_google_signin" if configured
            else "configure_google_oauth_client_id_in_isolated_service"
        ),
    }


@app.get("/scientific/operator", response_class=HTMLResponse)
def scientific_single_operator_page():
    """Single-operator Google sign-in UI on the isolated review server."""
    from .scientific_operator_ui import operator_html

    if os.getenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "").strip() != "single_operator":
        raise HTTPException(status_code=503, detail="Single-operator login not configured")
    client_id = os.getenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", "").strip()
    if not client_id or not os.getenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "").strip():
        raise HTTPException(status_code=503, detail="Google operator login not configured")

    nonce = secrets.token_urlsafe(24)
    response = HTMLResponse(content=operator_html(client_id, nonce))
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; base-uri 'none'; form-action 'none'; "
        "frame-ancestors 'none'; object-src 'none'; "
        f"script-src 'nonce-{nonce}' https://accounts.google.com https://ssl.gstatic.com; "
        f"style-src 'nonce-{nonce}' https://accounts.google.com; "
        "connect-src 'self' https://accounts.google.com; "
        "frame-src https://accounts.google.com; "
        "img-src https://accounts.google.com https://ssl.gstatic.com data:"
    )
    return response


@app.get("/api/scientific-assessment/operator/me")
def scientific_single_operator_me(
    authorization: Annotated[str | None, Header()] = None,
):
    """Identify the one configured operator. This is NOT a reviewer or signoff role.

    No self-provisioning, review submission authorization, source verification,
    score promotion, or independence assertion can be derived from this endpoint.
    """
    from .scientific_google_identity import verified_google_identity

    single_operator = os.getenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "").strip() == "single_operator"
    allowed_email = os.getenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "").strip()
    if not single_operator or not allowed_email:
        raise HTTPException(status_code=503, detail="Single-operator login not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Google identity token required")
    try:
        identity = verified_google_identity(authorization[7:])
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google identity token")
    if identity["verifiedEmail"].casefold() != allowed_email.casefold():
        raise HTTPException(status_code=403, detail="Not the configured scientific operator")
    return {
        "provider": "google",
        "role": "operator",
        "identityVerified": True,
        "maySubmitScientificReview": False,
        "maySignOff": False,
        "independentlyVerified": False,
        "mayPromoteScientificScore": False,
        "reviewerProvisioningRequired": True,
    }


def require_scientific_google_reviewer(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Google token + isolated allowlist; fail closed, no signoff authorization."""
    from .scientific_google_identity import verified_google_identity
    from .scientific_reviewer_accounts import reviewer_access_preflight

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Google identity token required")
    try:
        identity = verified_google_identity(authorization[7:])
    except ValueError as exc:
        if "not configured" in str(exc):
            raise HTTPException(status_code=503, detail="Google reviewer sign-in not configured")
        raise HTTPException(status_code=401, detail="Invalid Google identity token")
    access = reviewer_access_preflight(identity["providerSubject"], identity["verifiedEmail"])
    if not access["roleAuthorized"]:
        raise HTTPException(status_code=403, detail="Scientific reviewer access not authorized")
    return {
        "provider": "google",
        "providerSubject": identity["providerSubject"],
        "verifiedEmail": identity["verifiedEmail"],
        "roleAuthorized": True,
        "credentialsVerified": access["credentialsVerified"],
        "maySignOff": False,
    }


class ScientificReviewSubmissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nctId: str = Field(min_length=11, max_length=11)
    questionId: str = Field(min_length=3, max_length=70)
    sourceSha256: str = Field(min_length=64, max_length=64)
    decision: Literal["requires_review", "supports_reconciliation", "disputes_reconciliation"]
    sourceLocator: str = Field(min_length=1, max_length=200)
    reviewNote: str = Field(min_length=1, max_length=1500)
    uncertaintyDisclosed: Literal[True]


@app.post("/api/scientific-assessment/reviewer/submissions", status_code=201)
def scientific_reviewer_submit(
    body: ScientificReviewSubmissionInput,
    reviewer: dict = Depends(require_scientific_google_reviewer),
):
    """Append an authenticated reviewer statement and audit event atomically."""
    from .scientific_review_submission import record_reviewer_submission
    try:
        return record_reviewer_submission(
            google_subject=reviewer["providerSubject"], nct_id=body.nctId,
            question_id=body.questionId, source_sha256=body.sourceSha256,
            decision=body.decision,
            attestation={
                "sourceLocator": body.sourceLocator,
                "reviewNote": body.reviewNote,
                "uncertaintyDisclosed": body.uncertaintyDisclosed,
            },
        )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Reviewer not authorized")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/scientific-assessment/reviewer/pairing")
def scientific_reviewer_pairing(
    nct_id: str,
    question_id: str,
    source_sha256: str,
    reviewer: dict = Depends(require_scientific_google_reviewer),
):
    """Read-only two-identity comparison; no adjudication or score promotion."""
    from .scientific_review_pairing import review_pairing_status
    try:
        return review_pairing_status(nct_id, question_id, source_sha256)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/scientific-assessment/reviewer/audit")
def scientific_reviewer_audit(
    nct_id: str,
    question_id: str,
    reviewer: dict = Depends(require_scientific_google_reviewer),
):
    """Authorized read-only integrity check of reviewer submission history."""
    from .scientific_review_audit import audit_readback
    try:
        return audit_readback(nct_id, question_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.get("/api/scientific-assessment/reviewer/me")
def scientific_reviewer_me(
    reviewer: dict = Depends(require_scientific_google_reviewer),
):
    """Authenticated identity preflight; never grants evidence signoff."""
    return reviewer


@app.get("/api/scientific-assessment/operator/research")
def scientific_operator_research(
    exact_id: str,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
):
    """Read-only archived science data for the one verified Google operator.

    Intentionally delegates to the existing scientific inventory code. No
    review assertion, audit mutation, independent verification, or score write.
    """
    scientific_single_operator_me(authorization)
    if not re.fullmatch(r"TRIAL\|NCT[0-9]{8}", exact_id or ""):
        raise HTTPException(status_code=422, detail="Exact archived NCT identity required")
    response.headers["Cache-Control"] = "private, no-store"
    result = get_scientific_assessment(exact_id)
    status = result.get("registryEvidenceStatus")
    if status == "record_not_found":
        raise HTTPException(status_code=404, detail="Trial not present in scientific archive")
    if status != "source_record_loaded":
        raise HTTPException(status_code=503, detail="Archived scientific evidence unavailable")
    # Keep returned grades and evidence flags as-is, especially unverified status.
    return result


@app.get("/api/scientific-assessment/operator/worksheet/{nct_id}")
def scientific_operator_review_worksheet(
    nct_id: str,
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
):
    """Authenticated read-only source worksheet with reproducible SHA-256.

    A worksheet contains unresolved questions, candidate citations and
    acceptance criteria; it never marks evidence verified or assigns scores.
    """
    scientific_single_operator_me(authorization)
    if not re.fullmatch(r"NCT[0-9]{8}", nct_id or ""):
        raise HTTPException(status_code=422, detail="Exact archived NCT identity required")
    from .scientific_review_packet import build_review_packet

    try:
        packet = build_review_packet(nct_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Trial not present in scientific archive") from None
    except ValueError:
        raise HTTPException(status_code=409, detail="Archived review worksheet integrity failed") from None
    response.headers["Cache-Control"] = "private, no-store"
    return packet


@app.get("/api/scientific-assessment/storage-status", dependencies=[Depends(require_internal_key)])
def scientific_assessment_storage_status():
    """Authenticated, read-only schema and record-count diagnostic."""
    if not storage_ready() or not _DB_STATE["available"]:
        return {"storageReady": False, "trialTablePresent": False, "storedTrialCount": None}
    try:
        from sqlalchemy import func, inspect
        with Session(ENGINE) as session:
            table_present = inspect(session.get_bind()).has_table("full_trial_records")
            count = session.scalar(select(func.count()).select_from(FullTrialRecord)) if table_present else None
        return {"storageReady": True, "trialTablePresent": table_present, "storedTrialCount": count}
    except Exception:
        return {"storageReady": False, "trialTablePresent": None, "storedTrialCount": None}


@app.get("/api/scientific-assessment/pilot/keynote024", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def get_keynote024_scientific_pilot(response: Response):
    """Source-attributed historical Phase 3 pilot; never a scoring decision.

    Requires a checksum-verified archived registry record for exact NCT ID.
    No network, imports, candidate score changes, FS/FA changes or DB writes.
    """
    from .scientific_pilot_keynote024_results import keynote024_published_results
    from .scientific_pilot_keynote024 import keynote024_pilot_manifest
    from .scientific_dossier_archive import dossier_from_archive, verified_archived_registry_record

    nct_id = "NCT02142738"
    exact_id = "TRIAL|" + nct_id
    response.headers["Cache-Control"] = "private, no-store"
    with Session(ENGINE) as session:
        archived = session.get(FullTrialRecord, nct_id)
        if archived is None:
            raise HTTPException(status_code=404, detail="Phase 3 pilot record not archived")
        try:
            dossier = dossier_from_archive(
                exact_id, nct_id,
                archived.payload_gzip, archived.sha256, archived.fetched_at,
            )
            registry_record = verified_archived_registry_record(
                nct_id, archived.payload_gzip, archived.sha256,
            )
        except ValueError:
            raise HTTPException(
                status_code=503, detail="Archived Phase 3 pilot failed verification",
            ) from None
    pilot = keynote024_pilot_manifest()
    published = keynote024_published_results()
    if (pilot["nct_id"] != nct_id or published["nct_id"] != nct_id
            or dossier["nct_id"] != nct_id
            or published["overall_score"] is not None
            or published["fda_approval_probability"] is not None):
        raise HTTPException(status_code=503, detail="Pilot evidence identity validation failed")
    from .scientific_protocol_readiness import keynote024_protocol_readiness
    try:
        scientific_readiness = keynote024_protocol_readiness(dossier, published)
    except ValueError:
        raise HTTPException(
            status_code=503, detail="Scientific pilot readiness inputs failed validation",
        ) from None
    from .scientific_pilot_evidence_audit import keynote024_preinterim_evidence_audit
    try:
        evidence_audit = keynote024_preinterim_evidence_audit(
            registry_record, published,
        )
    except ValueError:
        raise HTTPException(
            status_code=503, detail="Archived pilot safety and chronology audit failed verification",
        ) from None
    from .scientific_pilot_safety_chronology import keynote024_safety_chronology
    try:
        published_safety = keynote024_safety_chronology(published, evidence_audit)
        if (scientific_readiness["inputReadiness"]["grade"] != "FAIL"
                or scientific_readiness["reluctance"]["grade"] != "HIGH"
                or published_safety["inputReadinessGradeChanged"] is not False
                or published_safety["reluctanceGradeChanged"] is not False):
            raise ValueError("Unsupported scientific safety grade promotion")
    except ValueError:
        raise HTTPException(
            status_code=503, detail="Historical pilot safety reconciliation failed validation",
        ) from None
    from .scientific_pilot_interim_design import published_keynote024_interim_design
    try:
        interim_design = published_keynote024_interim_design(published, scientific_readiness)
    except ValueError:
        raise HTTPException(
            status_code=503, detail="Pilot statistical source comparison failed validation",
        ) from None
    from .scientific_pilot_eu_plan_crosscheck import keynote024_eu_protocol_crosscheck
    try:
        eu_registry_crosscheck = keynote024_eu_protocol_crosscheck(
            interim_design, published, scientific_readiness,
        )
    except ValueError:
        raise HTTPException(
            status_code=503, detail="Historical EU endpoint cross-source check failed validation",
        ) from None
    from .scientific_pilot_regulatory_timeline import keynote024_historical_pdufa_timeline
    try:
        regulatory_history = keynote024_historical_pdufa_timeline(
            published, scientific_readiness, interim_design, eu_registry_crosscheck,
        )
    except ValueError:
        raise HTTPException(
            status_code=503,
            detail="Historical interim-to-FDA timeline input verification failed",
        ) from None
    return {
        "historicalRegulatoryTimeline": regulatory_history,
        "europeanRegistryCrosscheck": eu_registry_crosscheck,
        "publishedInterimDesign": interim_design,
        "publishedSafetyReconciliation": published_safety,
        "sourceEvidenceAudit": evidence_audit,
        "scientificReadiness": scientific_readiness,
        "pilot": pilot,
        "dossier": dossier,
        "publishedResults": published,
        "assessmentStatus": "source_reported_requires_independent_appraisal",
        "scoringModified": False,
        "qualificationPresetsModified": False,
        "researchOnly": True,
    }


@app.get("/api/scientific-assessment/dossier/references", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def get_scientific_dossier_references(
    exact_id: str, response: Response, application_number: str = "",
):
    """Explicit, bounded, source-only PubMed and FDA lookup for one stored NCT.

    Off by default. This endpoint is never called by a scan or bulk job, does
    not write to a database, and does not score or adjudicate source findings.
    """
    if os.getenv("PDUFA_SCIENTIFIC_EXTERNAL_LOOKUP_ENABLED", "").lower() not in (
        "1", "true", "yes",
    ):
        raise HTTPException(status_code=404, detail="External source research disabled")
    match = re.fullmatch(r"TRIAL\|(NCT[0-9]{8})", exact_id or "")
    if match is None:
        raise HTTPException(status_code=422, detail="Exact TRIAL|NCT######## identity required")
    from .scientific_external_sources import (
        APPLICATION_PATTERN, SourceLookupError, attach_research_references,
        lookup_fda_application, lookup_pubmed_nct,
    )
    if application_number and not APPLICATION_PATTERN.fullmatch(application_number):
        raise HTTPException(status_code=422, detail="Exact NDA/BLA application number required")
    nct_id = match.group(1)
    response.headers["Cache-Control"] = "private, no-store"
    with Session(ENGINE) as session:
        record = session.get(FullTrialRecord, nct_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Scientific archive record not found")
        from .scientific_dossier_archive import dossier_from_archive
        try:
            dossier = dossier_from_archive(
                exact_id, nct_id, record.payload_gzip, record.sha256, record.fetched_at,
            )
        except ValueError:
            raise HTTPException(
                status_code=503, detail="Archived scientific source failed verification",
            ) from None
    # Only after validating the archive and caller-provided identifiers may
    # live lookups run. A lookup failure is not negative scientific evidence.
    try:
        pubmed = lookup_pubmed_nct(nct_id)
        fda = lookup_fda_application(application_number) if application_number else None
        result = attach_research_references(dossier, pubmed, fda)
    except SourceLookupError:
        raise HTTPException(status_code=503, detail="Scientific reference lookup unavailable") from None
    result["reference_lookups"] = {
        "pubmed": pubmed["status"],
        "fda": fda["status"] if fda is not None else "not_requested",
        "fda_application_linked_to_trial": False,
    }
    return result


@app.get("/api/scientific-assessment/dossier", dependencies=[
    Depends(require_internal_key), Depends(require_storage),
])
def get_scientific_dossier(exact_id: str, response: Response):
    """Authenticated, read-only dossier from a verified, stored NCT source.

    This endpoint cannot import sources or change existing rankings, presets,
    scores, scanning, trade lists, or database records.
    """
    match = re.fullmatch(r"TRIAL\|(NCT[0-9]{8})", exact_id or "")
    if match is None:
        raise HTTPException(status_code=422, detail="Exact TRIAL|NCT######## identity required")
    nct_id = match.group(1)
    response.headers["Cache-Control"] = "private, no-store"
    with Session(ENGINE) as session:
        stored = session.get(FullTrialRecord, nct_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="Scientific archive record not found")
        from .scientific_dossier_archive import dossier_from_archive
        try:
            return dossier_from_archive(
                exact_id, nct_id, stored.payload_gzip, stored.sha256, stored.fetched_at,
            )
        except ValueError:
            # Never return a partially verified trial, even with metadata present.
            raise HTTPException(
                status_code=503, detail="Archived scientific source failed verification",
            ) from None


@app.get("/api/scientific-assessment", dependencies=[Depends(require_internal_key)])
def get_scientific_assessment(exact_id: str):
    """Read-only scientific assessment; never invent missing trial evidence."""
    if not exact_id or len(exact_id) > 512 or not exact_id.startswith(("TRIAL|", "REG|", "PDUFA|")):
        raise HTTPException(status_code=422, detail="Exact trial identity required")
    from .scientific_assessment_adapter import scientific_trial_payload
    result = scientific_trial_payload(exact_id)
    result["registryEvidence"] = None
    result["registryEvidenceStatus"] = "not_available"
    result["investigation20"] = None
    result["investigation40"] = None
    result["quantitativeResults"] = None
    result["readinessGrades"] = None
    result["evidenceLedger"] = None
    result["evidenceLedgerStatus"] = "not_available"
    # Never use an ephemeral SQLite fallback on hosted review services.
    match = re.fullmatch(r"TRIAL\|(NCT[0-9]{8})", exact_id)
    if match and storage_ready() and _DB_STATE["available"]:
        try:
            from .scientific_stored_record import verified_record_from_archive
            from .scientific_registry_evidence import extract_trial_evidence
            from .scientific_investigation_20 import investigation_20
            from .scientific_quantitative_results import reported_quantitative_results
            from .scientific_readiness_grades import review_readiness
            with Session(ENGINE) as session:
                record = session.get(FullTrialRecord, match.group(1))
                if record is not None:
                    snapshot = verified_record_from_archive(
                        match.group(1), record.payload_gzip, record.sha256
                    )
                    result["registryEvidence"] = extract_trial_evidence(match.group(1), snapshot)
                    result["investigation20"] = investigation_20(
                        match.group(1), snapshot,
                        retrieved_at=record.fetched_at.isoformat() if record.fetched_at else None,
                    )
                    result["quantitativeResults"] = reported_quantitative_results(
                        match.group(1), snapshot,
                    )
                    result["readinessGrades"] = review_readiness(
                        match.group(1), snapshot,
                        archive_retrieved_at=record.fetched_at.isoformat() if record.fetched_at else None,
                    )
                    # Read-only 40-assessment inventory. Candidate citations and
                    # reviewer statements cannot self-certify independent evidence.
                    # This view is never a scientific outcome or approval forecast.
                    from .scientific_investigation_contract import (
                        LAYERS, investigation_plan, readiness,
                    )
                    from .scientific_stage_crosswalk import stage_crosswalk
                    result["investigation40"] = {
                        "schemaVersion": "scientific-investigation40-v1",
                        "nctId": match.group(1),
                        "layers": [
                            {"id": layer, "assessments": list(fields)}
                            for layer, fields in LAYERS.items()
                        ],
                        "verification": readiness({}),
                        "depthReview": investigation_plan(),
                        "stageCrosswalk": stage_crosswalk(result["investigation20"]),
                        "verificationSource": "independent_adjudication_not_available",
                        "note": (
                            "This is the required-question inventory only. No"
                            " independent review gates are satisfied by imported"
                            " registry records or candidate citations."
                        ),
                    }
                    # Optional read-only source queue: ledger failure cannot
                    # contaminate verified archive metadata or readiness grades.
                    try:
                        from .scientific_evidence_ledger import read_ledger
                        result["evidenceLedger"] = read_ledger(match.group(1))
                        result["evidenceLedgerStatus"] = "candidate_inventory_loaded"
                    except Exception:
                        result["evidenceLedgerStatus"] = "ledger_unavailable_or_invalid"
                    result["registryEvidenceStatus"] = "source_record_loaded"
                else:
                    result["registryEvidenceStatus"] = "record_not_found"
        except Exception:
            # A corrupt archive or unavailable database must never produce a score.
            result["registryEvidenceStatus"] = "record_unavailable_or_invalid"
    return result


@app.get(
    "/api/scientific-assessment/review-packet/{nct_id}",
    dependencies=[Depends(require_internal_key), Depends(require_storage)],
)
def get_scientific_review_packet(nct_id: str):
    """Download a bounded, audited review worksheet; no scientific auto-grading."""
    import json as _json
    from .scientific_review_packet import build_review_packet
    try:
        packet = build_review_packet(nct_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Exact archived trial not found") from None
    except ValueError:
        raise HTTPException(
            status_code=409,
            detail="Trial archive or source ledger failed integrity verification",
        ) from None
    serialized = _json.dumps(
        packet, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2,
    ).encode("utf-8")
    if len(serialized) > 2_000_000:
        raise HTTPException(status_code=413, detail="Review packet exceeds safe export limit")
    # Credentials remain request headers only, never serialized or placed in URLs.
    return Response(
        content=serialized,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                'attachment; filename="' + nct_id + '_scientific_review_packet.json"'
            ),
            "Cache-Control": "no-store, private",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "X-Packet-SHA256": packet["packetIntegrity"]["digest"],
        },
    )


def require_scientific_evidence_write_key(
    x_pdufa_scientific_review_key: Annotated[str | None, Header()] = None,
) -> None:
    """Separate from the batch API key; disabled on all services by default."""
    if (os.getenv("RENDER_SERVICE_ID") != "srv-dbehn9fb9u1s739ok5vg"
            or os.getenv("PDUFA_SCIENTIFIC_LEDGER_WRITE_ENABLED") != "1"
            or not DATABASE_URL.startswith("postgresql+psycopg://")):
        raise HTTPException(status_code=403, detail="Scientific evidence writing disabled")
    expected = os.getenv("PDUFA_SCIENTIFIC_REVIEW_WRITE_KEY")
    if not expected or expected == os.getenv("PDUFA_INTERNAL_API_KEY"):
        raise HTTPException(status_code=503, detail="Separate evidence review key not configured")
    if (not x_pdufa_scientific_review_key or
            not secrets.compare_digest(expected, x_pdufa_scientific_review_key)):
        raise HTTPException(status_code=401, detail="Unauthorized scientific evidence curator")



class ScientificReviewerStatementSubmission(BaseModel):
    """A source-anchored reviewer statement; not a verified medical finding."""
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(
        min_length=4, max_length=70, pattern=r"^[a-z0-9_]+$", alias="questionId"
    )
    source_url: str = Field(min_length=12, max_length=800, alias="sourceUrl")
    source_locator: str = Field(min_length=5, max_length=200, alias="sourceLocator")
    finding_type: Literal[
        "supports", "contradicts", "uncertain", "not_assessable"
    ] = Field(alias="findingType")
    assertion: str = Field(min_length=30, max_length=1500)
    uncertainty: str = Field(min_length=20, max_length=1000)
    reviewer_label: str = Field(min_length=2, max_length=80, alias="reviewerLabel")
    reviewer_attests_read_source: Literal[True] = Field(alias="reviewerAttestsReadSource")
    supersedes_id: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{32}$", alias="supersedesId"
    )


@app.post(
    "/api/scientific-assessment/reviewer-statements/{nct_id}",
    status_code=201,
    dependencies=[Depends(require_internal_key), Depends(require_storage),
                  Depends(require_scientific_evidence_write_key)],
)
def submit_scientific_reviewer_statement(
    nct_id: str,
    payload: ScientificReviewerStatementSubmission,
):
    """Append unverified evidence commentary; no gate or approval score changes."""
    from .scientific_reviewer_findings import append_reviewer_statement
    try:
        return append_reviewer_statement(nct_id, payload.model_dump(by_alias=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except IntegrityError:
        raise HTTPException(
            status_code=409, detail="Reviewer statement revision already recorded"
        ) from None


class ScientificSourceDocumentSubmission(BaseModel):
    """Curator-supplied PDF bytes, not independently authenticated science."""
    model_config = ConfigDict(extra="forbid")

    gate_id: Literal[
        "protocol_sap", "published_results",
        "independent_replication", "official_regulatory"
    ] = Field(alias="gateId")
    source_url: str = Field(min_length=12, max_length=800, alias="sourceUrl")
    source_type: Literal[
        "peer_reviewed_publication", "official_agency_document",
        "protocol_sap", "clinical_study_report",
        "institutional_summary", "other"
    ] = Field(alias="sourceType")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content_base64: str = Field(
        min_length=32, max_length=5592408, alias="contentBase64"
    )
    captured_by: str = Field(
        min_length=2, max_length=80, alias="capturedBy"
    )


def require_isolated_scientific_review_service() -> None:
    if (os.getenv("RENDER_SERVICE_ID") != "srv-dbehn9fb9u1s739ok5vg"
            or not DATABASE_URL.startswith("postgresql+psycopg://")):
        raise HTTPException(status_code=403, detail="Isolated scientific review service required")


def require_source_document_capture_enabled() -> None:
    # An additional opt-in beyond the independent scientific-review write key.
    if os.getenv("PDUFA_SCIENTIFIC_DOCUMENT_CAPTURE_ENABLED") != "1":
        raise HTTPException(status_code=403, detail="Scientific document capture disabled")


@app.post(
    "/api/scientific-assessment/source-documents/{nct_id}",
    status_code=201,
    dependencies=[
        Depends(require_internal_key), Depends(require_storage),
        Depends(require_scientific_evidence_write_key),
        Depends(require_source_document_capture_enabled),
    ],
)
def submit_scientific_source_document(
    nct_id: str,
    payload: ScientificSourceDocumentSubmission,
):
    """Store submitted PDF bytes only; never fetch sources or verify their claims."""
    from .scientific_source_documents import capture_document
    try:
        return capture_document(nct_id, payload.model_dump(by_alias=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Duplicate document content") from None


@app.get(
    "/api/scientific-assessment/source-documents/{nct_id}/{document_id}",
    dependencies=[
        Depends(require_internal_key), Depends(require_storage),
        Depends(require_isolated_scientific_review_service),
    ],
)
def download_scientific_source_document(nct_id: str, document_id: str):
    """Authenticated byte-for-byte PDF download from isolated review storage."""
    from .scientific_source_documents import get_captured_document
    try:
        meta, payload = get_captured_document(nct_id, document_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Captured PDF not found") from None
    except ValueError:
        raise HTTPException(status_code=409, detail="Captured PDF integrity failure") from None
    return Response(
        content=payload,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="' + meta["filename"] + '"',
            "Cache-Control": "private, no-store",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
            "X-Source-Document-SHA256": meta["sha256"],
            "X-Source-Scientific-Status": "not-independently-verified",
        },
    )


class ScientificEvidenceCandidateSubmission(BaseModel):
    """A submitted citation is always unverified; never an FDA/science score."""
    model_config = ConfigDict(extra="forbid")

    gate_id: Literal[
        "protocol_sap", "published_results",
        "independent_replication", "official_regulatory"
    ] = Field(alias="gateId")
    source_url: str = Field(min_length=12, max_length=800, alias="sourceUrl")
    source_type: Literal[
        "peer_reviewed_publication", "official_agency_document",
        "protocol_sap", "clinical_study_report",
        "institutional_summary", "other"
    ] = Field(alias="sourceType")
    source_published_at: date | None = Field(default=None, alias="sourcePublishedAt")
    claim_text: str = Field(min_length=20, max_length=1000, alias="claimText")
    relationship: Literal["supports", "contradicts", "context", "unresolved"]
    caution: str = Field(min_length=15, max_length=1000)
    recorded_by: str = Field(min_length=2, max_length=80, alias="recordedBy")
    supersedes_id: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{32}$", alias="supersedesId"
    )


@app.post("/api/scientific-assessment/evidence-ledger/{nct_id}",
          status_code=201,
          dependencies=[Depends(require_internal_key), Depends(require_storage),
                        Depends(require_scientific_evidence_write_key)])
def submit_scientific_evidence_candidate(
    nct_id: str,
    payload: ScientificEvidenceCandidateSubmission,
):
    """Append-only, review-only cited *candidate*; never verifies it by submission."""
    from .scientific_evidence_ledger import append_candidate
    try:
        return append_candidate(nct_id, payload.model_dump(by_alias=True, mode="json"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Evidence revision already recorded") from None


class ScientificBatchSubmission(BaseModel):
    nct_ids: list[str] = Field(min_length=1, max_length=25)


def require_scientific_batch_review_write() -> None:
    """Separate opt-in and exact Render service fence; never enable in production."""
    if (os.getenv("PDUFA_SCIENTIFIC_BATCH_WRITE_ENABLED") != "1"
            or os.getenv("RENDER_SERVICE_ID") != "srv-dbehn9fb9u1s739ok5vg"
            or not DATABASE_URL.startswith("postgresql+psycopg://")):
        raise HTTPException(status_code=403, detail="Scientific batch imports disabled outside isolated review")


@app.get("/scientific-assessment/batches")
def scientific_batch_control_panel():
    """Static same-origin UI; all job data/actions require the internal API key."""
    from .scientific_batch_ui import render_batch_panel
    return render_batch_panel()


@app.get("/api/scientific-assessment/batches",
         dependencies=[Depends(require_internal_key), Depends(require_storage)])
def list_scientific_batches():
    from .scientific_batch_jobs import list_jobs
    return {"jobs": list_jobs()}


@app.get("/api/scientific-assessment/batches/{job_id}",
         dependencies=[Depends(require_internal_key), Depends(require_storage)])
def get_scientific_batch(job_id: str):
    from .scientific_batch_jobs import get_job
    result = get_job(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scientific batch not found")
    return result


@app.get("/api/scientific-assessment/batches-recovery-status",
         dependencies=[Depends(require_internal_key), Depends(require_storage)])
def scientific_batch_recovery_status():
    """Authenticated read-only indication of potentially stranded batches."""
    from .scientific_batch_jobs import recovery_diagnostics
    return recovery_diagnostics()


@app.post("/api/scientific-assessment/batches", status_code=202,
          dependencies=[Depends(require_internal_key), Depends(require_storage),
                        Depends(require_scientific_batch_review_write)])
def submit_scientific_batch(payload: ScientificBatchSubmission):
    from .scientific_batch_jobs import submit_job
    try:
        return submit_job(payload.nct_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An unfinished scientific batch already exists") from exc


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
        "full_trial_download": archive_status(),
    }


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
