"""Opt-in, phase-first HUMAN reviewer submission for the isolated MAIN medical pilot.

No automated clinical scoring, no inferred reviewer authority, no FDA forecast.
Never expose these POST routes in production or without two independently
provisioned, role-separated reviewer credentials and durable ledger readiness.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import medical_assessment_ledger as ledger

CANARY = "NCT06081894"
ENABLED = ("1", "true", "yes")
ID_PATTERN = re.compile(r"[A-Za-z0-9_.@-]{3,120}\Z")
ROLES = ("phase", "method")
PHASE_ATTESTATION = "I_INDEPENDENTLY_VERIFIED_THE_ORIGINAL_PHASE_EVIDENCE"
METHOD_ATTESTATION = "I_PERSONALLY_EXAMINED_THE_REPORTED_EVIDENCE_AND_LIMITATIONS"


def _on() -> bool:
    return os.getenv("PDUFA_MEDICAL_REVIEW_WRITES_ENABLED", "").lower() in ENABLED


def _credentials() -> dict:
    """Credentials stay exclusively in environment secrets; never print them."""
    raw = os.getenv("PDUFA_MEDICAL_REVIEWER_CREDENTIALS_JSON", "")
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        data = None
    if not isinstance(data, dict) or set(data) != set(ROLES):
        raise HTTPException(503, "Two independent medical reviewer roles are not configured")
    all_ids, all_secrets = set(), set()
    for role in ROLES:
        principals = data.get(role)
        if not isinstance(principals, dict) or not principals:
            raise HTTPException(503, "Medical reviewer role is not configured")
        for identity, key in principals.items():
            if (not isinstance(identity, str) or not ID_PATTERN.fullmatch(identity)
                    or not isinstance(key, str) or len(key) < 32
                    or identity in all_ids or key in all_secrets):
                raise HTTPException(503, "Medical reviewer configuration is invalid")
            all_ids.add(identity)
            all_secrets.add(key)
    return data


def _authenticate(identity: str | None, secret: str | None, role: str) -> str:
    if not _on():
        raise HTTPException(503, "Medical reviewer writes are disabled")
    data = _credentials()
    if (not identity or not secret or role not in ROLES
            or identity not in data[role]
            or not secrets.compare_digest(data[role][identity], secret)):
        raise HTTPException(401, "Reviewer authorization required")
    return identity


def phase_reviewer(
    x_pdufa_reviewer_id: Annotated[str | None, Header(alias="X-PDUFA-Reviewer-Id")] = None,
    x_pdufa_reviewer_key: Annotated[str | None, Header(alias="X-PDUFA-Reviewer-Key")] = None,
) -> str:
    return _authenticate(x_pdufa_reviewer_id, x_pdufa_reviewer_key, "phase")


def method_reviewer(
    x_pdufa_reviewer_id: Annotated[str | None, Header(alias="X-PDUFA-Reviewer-Id")] = None,
    x_pdufa_reviewer_key: Annotated[str | None, Header(alias="X-PDUFA-Reviewer-Key")] = None,
) -> str:
    return _authenticate(x_pdufa_reviewer_id, x_pdufa_reviewer_key, "method")


def _timestamp(raw: str) -> None:
    try:
        when = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if when.tzinfo is None or when.utcoffset() is None:
            raise ValueError("No timezone")
        if when.astimezone(timezone.utc) > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Future review time")
    except (TypeError, ValueError):
        raise HTTPException(422, "A real timezone-aware review timestamp not in the future is required")


class PhaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sourceRunId: str = Field(min_length=36, max_length=36)
    verifiedPhase: Literal["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"]
    verifiedAt: str
    supersedesEventId: str | None = None
    attestation: Literal["I_INDEPENDENTLY_VERIFIED_THE_ORIGINAL_PHASE_EVIDENCE"]


class OriginalSource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    stageIndex: int = Field(ge=0, le=11)
    sourceUrl: str = Field(min_length=10, max_length=2048)


class MethodRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sourceRunId: str = Field(min_length=36, max_length=36)
    currentPhaseEventId: str = Field(min_length=36, max_length=36)
    assessmentIndex: int = Field(ge=1, le=40)
    methodIndex: int = Field(ge=1, le=20)
    disposition: Literal["SCORED", "NOT_APPLICABLE", "RETRACTED"]
    grade: int | None = Field(default=None, ge=0, le=5)
    sourceEvidence: list[OriginalSource] = Field(default_factory=list, max_length=12)
    findingsClassification: list[Literal["FAVORABLE", "UNFAVORABLE", "MISSING", "CONTRADICTORY"]] = Field(min_length=1, max_length=4)
    rationale: str = Field(min_length=80, max_length=6000)
    evidenceReviewedAt: str
    supersedesEventId: str | None = None
    attestation: Literal["I_PERSONALLY_EXAMINED_THE_REPORTED_EVIDENCE_AND_LIMITATIONS"]


def _canary(nct: str) -> None:
    if nct != CANARY:
        raise HTTPException(404, "Only the named isolated pilot has a reviewer intake")


def _response(nct: str, event_id: str, kind: str) -> dict:
    return {
        "nct": nct, "eventId": event_id, "eventKind": kind,
        "reviewStatus": "RECORDED_PENDING_INDEPENDENT_SIGNOFF",
        "clinicalSignoff": False, "certainty": "NOT_VALIDATED",
        "fdaPredictions": {"APPROVAL": "ABSTAIN", "CRL": "ABSTAIN", "REVIEW_DELAY": "ABSTAIN"},
        "accuracy": "NOT_CALIBRATED"
    }


def install_routes(app, engine_provider, require_storage, require_writes) -> None:
    router = APIRouter(
        prefix="/api/internal/medical-reviewer-intake",
        dependencies=[Depends(require_storage), Depends(require_writes)]
    )

    @router.post("/{nct}/phase", status_code=201)
    def verified_phase(nct: str, request: PhaseRequest, reviewer_id: str = Depends(phase_reviewer)):
        _canary(nct)
        _timestamp(request.verifiedAt)
        try:
            event = ledger.record_verified_phase(
                engine_provider(), nct=nct, run_id=request.sourceRunId,
                phase=request.verifiedPhase, reviewer_id=reviewer_id,
                verified_at=request.verifiedAt, supersedes_event_id=request.supersedesEventId)
        except (ValueError, LookupError) as exc:
            raise HTTPException(409, str(exc))
        return _response(nct, event, "PHASE_VERIFICATION")

    @router.post("/{nct}/method", status_code=201)
    def reviewed_method(nct: str, request: MethodRequest, reviewer_id: str = Depends(method_reviewer)):
        _canary(nct)
        _timestamp(request.evidenceReviewedAt)
        if request.disposition == "SCORED":
            if request.grade is None or not request.sourceEvidence:
                raise HTTPException(422, "Evidence-backed numerical grades require saved original sources")
            if not set(request.findingsClassification).intersection({"FAVORABLE", "UNFAVORABLE", "CONTRADICTORY"}):
                raise HTTPException(422, "Missing-only evidence cannot become a numerical grade")
        elif request.grade is not None:
            raise HTTPException(422, "Unreviewed or excluded methods do not receive numerical grades")
        # The method reviewer cannot attest the very phase they verified.
        history = ledger.trial_history(engine_provider(), nct)
        phase_events = history["phaseEvents"]
        if not phase_events or phase_events[-1]["phase_event_id"] != request.currentPhaseEventId:
            raise HTTPException(409, "A fresh, matching independently verified phase event is required")
        if phase_events[-1]["reviewer_id"] == reviewer_id:
            raise HTTPException(403, "Independent method reviewer must differ from phase verifier")
        try:
            event = ledger.append_review(
                engine_provider(), nct=nct, run_id=request.sourceRunId,
                phase_event_id=request.currentPhaseEventId,
                assessment_index=request.assessmentIndex, method_index=request.methodIndex,
                disposition=request.disposition, grade=request.grade,
                evidence=[item.model_dump() for item in request.sourceEvidence],
                rationale=request.rationale, reviewer_id=reviewer_id,
                evidence_reviewed_at=request.evidenceReviewedAt,
                supersedes_event_id=request.supersedesEventId)
        except (ValueError, LookupError) as exc:
            raise HTTPException(409, str(exc))
        return _response(nct, event, "METHOD_REVIEW")

    app.include_router(router)
