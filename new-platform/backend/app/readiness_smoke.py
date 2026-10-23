"""Authenticated, read-only verification of the isolated deployed review API."""
from __future__ import annotations

import json
import logging
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

LOG = logging.getLogger(__name__)
REVIEW_URL = "https://pdufa-alpaca-enrichment-review.onrender.com"
STAGES = ("GEM_JR", "GEM")


class _NoRedirect(HTTPRedirectHandler):
    # The internal key must never be forwarded to a redirect target.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _AssessmentPending(ValueError):
    pass


def verify_payload(payload: dict, program_id: str, stage: str, exact_key: str | None = None) -> None:
    """Check identity, market observations, and all non-trading boundaries."""
    key = payload.get("exactKey")
    if (payload.get("programId") != program_id or payload.get("stage") != stage
            or not isinstance(key, str) or not key.strip()
            or (exact_key is not None and key != exact_key)):
        raise ValueError("Review identity mismatch")
    decision = payload.get("decisionReadiness") or {}
    market = payload.get("marketEvidenceReview") or {}
    risk = payload.get("riskEvidenceReview") or {}
    if any(value.get("programId") != program_id or value.get("exactKey") != key
           for value in (decision, market, risk)):
        raise ValueError("Evidence identity mismatch")
    if (payload.get("researchOnly") is not True or payload.get("ordersEnabled") is not False
            or payload.get("fsFaChanges") is not False
            or decision.get("ordersEnabled") is not False
            or decision.get("assessmentScoreChange") is not False
            or decision.get("fsFaChange") is not False
            or market.get("assessmentScoreChange") is not False
            or market.get("qualificationChange") is not False
            or market.get("fsFaChange") is not False
            or risk.get("researchOnly") is not True or risk.get("ordersEnabled") is not False
            or risk.get("assessmentScoreChange") is not False
            or risk.get("qualificationChange") is not False or risk.get("fsFaChange") is not False):
        raise ValueError("Research boundary mismatch")
    if (decision.get("tradeCall") is not None
            or any(decision.get(field) is not None for field in ("entryPrice", "targetPrice", "stopLoss"))
            or market.get("recommendation") is not None):
        raise ValueError("Research must not produce trading instructions")
    if (market.get("status") != "RESEARCH_ONLY"
            or market.get("coverage") != "IEX_ONLY_NOT_CONSOLIDATED"
            or len(market.get("observations") or []) != 2):
        raise ValueError("Live Alpaca market observations unavailable")
    assessment = payload.get("assessmentEvidence") or {}
    if assessment.get("status") == "ASSESSMENT_UNAVAILABLE":
        raise _AssessmentPending("Assessment index rebuilding")
    if assessment.get("status") not in {"COMPLETE", "ASSESSMENT_INCOMPLETE", "ASSESSMENT_MISSING"}:
        raise ValueError("Exact-program assessment unavailable")
    checks = risk.get("checks") or []
    if (risk.get("stage") != stage or risk.get("identityStatus") != "EXACT_IDENTITY_MATCH"
            or len(checks) != 3
            or {item.get("id") for item in checks} != {"catalystTiming", "cashRunway", "dilutionRisk"}):
        raise ValueError("Exact-program risk evidence checks unavailable")
    reviewed = {item["id"] for item in checks if item.get("status") == "REVIEWED"}
    catalyst = "catalystTiming" in reviewed
    financing = {"cashRunway", "dilutionRisk"}.issubset(reviewed)
    if (risk.get("catalystVerified") is not catalyst
            or risk.get("financingRiskReviewed") is not financing):
        raise ValueError("Risk readiness must match its source checks")
    missing = set()
    if assessment["status"] != "COMPLETE":
        missing.add("complete verified assessment")
    if not catalyst:
        missing.add("verified catalyst")
    if not financing:
        missing.add("financing and dilution risk review")
    expected_status = "NOT_READY" if missing else "READY_FOR_HUMAN_RESEARCH_REVIEW"
    if set(decision.get("missingRequirements") or []) != missing or decision.get("status") != expected_status:
        raise ValueError("Decision readiness must reflect missing source evidence")


def check_program(base: str, key: str, program_id: str, exact_key: str | None = None) -> None:
    """Only use the known isolated public host or this container's API socket."""
    if base not in {REVIEW_URL, "http://127.0.0.1:8000"}:
        raise ValueError("Refusing non-isolated review address")
    opener = build_opener(_NoRedirect())
    for stage in STAGES:
        path = f"/api/review/program-decision-readiness/{program_id}?" + urlencode({"stage": stage})
        request = Request(base + path, headers={"x-pdufa-internal-key": key})
        with opener.open(request, timeout=60) as response:
            payload = json.load(response)
        verify_payload(payload, program_id, stage, exact_key)
        LOG.warning(
            "PDUFA_READINESS_SMOKE program_id=%s stage=%s status=PASS market=%s assessment=%s "
            "decision=%s risk=%s missing_risk_evidence=%d orders_enabled=False fs_fa_changes=False",
            program_id, stage, payload["marketEvidenceReview"]["status"],
            payload["assessmentEvidence"]["status"],
            payload["decisionReadiness"]["status"], payload["riskEvidenceReview"]["status"],
            len(payload["riskEvidenceReview"]["missingEvidence"]),
        )


def check_deployed_program(program_id: str, exact_key: str) -> None:
    """Runs once on the isolated service; never exports its existing secret."""
    if os.getenv("PDUFA_ALPACA_REVIEW_SMOKE", "").lower() not in {"1", "true", "yes"}:
        return
    key = os.getenv("PDUFA_INTERNAL_API_KEY", "")
    if not key:
        LOG.error("PDUFA_READINESS_SMOKE status=FAIL reason=MISSING_INTERNAL_KEY")
        return
    # Source/assessment indexes build asynchronously. Retry only temporary
    # unavailability, never an identity mismatch or changed research boundary.
    deadline = time.monotonic() + 180
    while True:
        try:
            check_program("http://127.0.0.1:8000", key, program_id, exact_key)
            return
        except HTTPError as exc:
            if exc.code not in {409, 503}:
                break
        except (URLError, TimeoutError, _AssessmentPending):
            pass
        except Exception as exc:
            LOG.error("PDUFA_READINESS_SMOKE status=FAIL error_type=%s", type(exc).__name__)
            return
        if time.monotonic() >= deadline:
            break
        time.sleep(5)
    LOG.error("PDUFA_READINESS_SMOKE program_id=%s status=FAIL", program_id)
