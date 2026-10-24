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
        raise ValueError(
            "Live Alpaca market observations unavailable: "
            f"market_data_status={payload.get('marketDataStatus')!r} "
            f"market_signal_status={payload.get('marketSignalStatus')!r} "
            f"market_bars={payload.get('marketBarsAvailable')!r} "
            f"market_feed={payload.get('marketDataFeed')!r} "
            f"review_status={market.get('status')!r}; "
            "research readiness remains NOT_READY until verified market evidence exists"
        )
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


def check_source_catalog(base: str, key: str) -> None:
    """Verify all reviewed source keys and one real application readiness link."""
    from .source_catalyst_review import catalog
    if base not in {REVIEW_URL, "http://127.0.0.1:8000"}:
        raise ValueError("Refusing non-isolated review address")
    opener = build_opener(_NoRedirect())
    request = Request(base + "/api/review/catalyst-evidence", headers={"x-pdufa-internal-key": key})
    with opener.open(request, timeout=60) as response:
        batch = json.load(response)
    expected = catalog()["programs"]
    records = batch.get("records") or []
    if (batch.get("status") != "CHECKED" or len(records) != len(expected)
            or {r.get("exactKey") for r in records} != set(expected)
            or len({r.get("programId") for r in records}) != len(expected)
            or any(not r.get("programId") for r in records)
            or batch.get("ordersEnabled") is not False or batch.get("fsFaChanges") is not False
            or batch.get("assessmentScoreChange") is not False):
        raise ValueError("Source catalog identity or research boundary mismatch")
    targets = sum(v["status"] == "CONFIRMED_TARGET" for v in expected.values())
    past = sum(v["status"] == "READOUT_ALREADY_REPORTED" for v in expected.values())
    if batch.get("confirmedTargets") != targets or batch.get("reportedReadouts") != past:
        raise ValueError("Source date review needs reconciliation or refresh")
    for record in records:
        source = expected[record["exactKey"]]
        if (record.get("source") != source["sourceUrl"]
                or record.get("eventDate") != source["eventDate"]
                or record.get("catalystVerified") is not (source["status"] == "CONFIRMED_TARGET")):
            raise ValueError("Source catalog evidence mismatch")
    sample = next(r for r in records if r["status"] == "CONFIRMED")
    for stage in STAGES:
        request = Request(base + f"/api/review/program-decision-readiness/{sample['programId']}?stage={stage}",
                          headers={"x-pdufa-internal-key": key})
        with opener.open(request, timeout=60) as response:
            payload = json.load(response)
        verify_payload(payload, sample["programId"], stage, sample["exactKey"])
        if (payload.get("primaryCatalystReview", {}).get("status") != "CONFIRMED"
                or payload["riskEvidenceReview"].get("catalystVerified") is not True):
            raise ValueError("Primary-source catalyst did not reach exact-program readiness")
    LOG.warning("PDUFA_CATALYST_SOURCE_SMOKE status=PASS programs=%d confirmed_targets=%d "
                "reported_readouts=%d application_stages=2 orders_enabled=False fs_fa_changes=False",
                len(records), targets, past)


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
            check_source_catalog("http://127.0.0.1:8000", key)
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
