"""Authenticated, read-only verification of the isolated deployed review API."""
from __future__ import annotations

import json
import logging
import os
import re
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


class _MarketEvidenceUnavailable(ValueError):
    """Only this exception contains bounded, non-secret provider diagnostics."""


def _verify_identity_boundaries(payload: dict, program_id: str, stage: str,
                                exact_key: str | None = None) -> None:
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


def _verify_assessment_risk(payload: dict, stage: str) -> None:
    decision = payload.get("decisionReadiness") or {}
    market = payload.get("marketEvidenceReview") or {}
    risk = payload.get("riskEvidenceReview") or {}
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
    if market.get("status") != "RESEARCH_ONLY":
        missing.add("exact-program market evidence")
    if not catalyst:
        missing.add("verified catalyst")
    if not financing:
        missing.add("financing and dilution risk review")
    expected_status = "NOT_READY" if missing else "READY_FOR_HUMAN_RESEARCH_REVIEW"
    if set(decision.get("missingRequirements") or []) != missing or decision.get("status") != expected_status:
        raise ValueError("Decision readiness must reflect missing source evidence")


def verify_payload(payload: dict, program_id: str, stage: str, exact_key: str | None = None) -> None:
    """Full verification still requires live market observations."""
    _verify_identity_boundaries(payload, program_id, stage, exact_key)
    market = payload.get("marketEvidenceReview") or {}
    if (market.get("status") != "RESEARCH_ONLY"
            or market.get("coverage") != "IEX_ONLY_NOT_CONSOLIDATED"
            or len(market.get("observations") or []) != 2):
        # Never log a provider response, URL, exception body, or arbitrary text.
        def status(value):
            return value if isinstance(value, str) and re.fullmatch(r"[A-Z_]{1,60}", value) else None
        bars = payload.get("marketBarsAvailable")
        bars = bars if type(bars) is int and 0 <= bars <= 10000 else None
        raise _MarketEvidenceUnavailable(
            "Live Alpaca market observations unavailable: "
            f"market_data_status={status(payload.get('marketDataStatus'))!r} "
            f"market_signal_status={status(payload.get('marketSignalStatus'))!r} "
            f"market_bars={bars!r} "
            f"market_feed={status(payload.get('marketDataFeed'))!r} "
            f"review_status={status(market.get('status'))!r}; "
            "research readiness remains NOT_READY until verified market evidence exists"
        )
    _verify_assessment_risk(payload, stage)


def verify_source_link(payload: dict, source: dict, stage: str) -> None:
    """Verify catalyst-to-readiness wiring independently of market availability.

    A source-link PASS is not a full readiness PASS. The actual missing-market
    requirement and NOT_READY decision must remain present when data is absent.
    """
    _verify_identity_boundaries(payload, source["programId"], stage, source["exactKey"])
    _verify_assessment_risk(payload, stage)
    primary = payload.get("primaryCatalystReview") or {}
    risk = payload["riskEvidenceReview"]
    catalyst = next(c for c in risk["checks"] if c["id"] == "catalystTiming")
    confirmed = source.get("status") == "CONFIRMED"
    if (primary.get("status") != source.get("status")
            or primary.get("catalystVerified") is not confirmed
            or risk.get("catalystVerified") is not confirmed
            or any(primary.get(field) != source.get(field)
                   for field in ("programId", "exactKey", "source", "sourceDate", "checkedAt", "eventDate", "eventType"))
            or primary.get("researchOnly") is not True
            or primary.get("ordersEnabled") is not False
            or primary.get("assessmentScoreChange") is not False
            or primary.get("fsFaChange") is not False
            or (confirmed and any(catalyst.get(field) != source.get(field)
                                  for field in ("source", "sourceDate", "checkedAt")))):
        raise ValueError("Primary-source catalyst did not reach exact-program readiness")


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
    """Verify every reviewed program in both GEM stages, even without market data."""
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
                or record.get("status") != ("CONFIRMED" if source["status"] == "CONFIRMED_TARGET" else "READOUT_ALREADY_REPORTED")
                or record.get("checkedAt") != source["reviewedOn"]
                or record.get("sourceDate") != source["sourcePublishedOn"]
                or record.get("researchOnly") is not True
                or record.get("ordersEnabled") is not False
                or record.get("assessmentScoreChange") is not False
                or record.get("fsFaChange") is not False
                or record.get("catalystVerified") is not (source["status"] == "CONFIRMED_TARGET")):
            raise ValueError("Source catalog evidence mismatch")
    LOG.warning("PDUFA_CATALYST_CATALOG_SMOKE status=PASS programs=%d confirmed_targets=%d reported_readouts=%d",
                len(records), targets, past)
    for record in records:
        for stage in STAGES:
            request = Request(base + f"/api/review/program-decision-readiness/{record['programId']}?stage={stage}",
                              headers={"x-pdufa-internal-key": key})
            with opener.open(request, timeout=60) as response:
                payload = json.load(response)
            verify_source_link(payload, record, stage)
            LOG.warning("PDUFA_CATALYST_LINK_SMOKE program_id=%s stage=%s status=PASS decision=%s market=%s",
                        record["programId"], stage, payload["decisionReadiness"]["status"], payload["marketEvidenceReview"]["status"])
    LOG.warning("PDUFA_CATALYST_SOURCE_SMOKE status=PASS programs=%d confirmed_targets=%d "
                "reported_readouts=%d program_stages=%d orders_enabled=False fs_fa_changes=False",
                len(records), targets, past, len(records) * len(STAGES))


def _retryable(exc: Exception) -> bool:
    if isinstance(exc, HTTPError):
        return exc.code in {409, 503}
    return isinstance(exc, (URLError, TimeoutError, _AssessmentPending))


def _run_check(check, retry_seconds: float) -> None:
    deadline = time.monotonic() + retry_seconds
    while True:
        try:
            check()
            return
        except Exception as exc:
            if not _retryable(exc) or time.monotonic() >= deadline:
                raise
        time.sleep(5)


def check_all(base: str, key: str, program_id: str, exact_key: str | None = None,
              *, retry_seconds: float = 0) -> None:
    """Run independent source and market checks; any failure still fails the run."""
    failures = []
    for name, check in (
        ("catalyst_sources", lambda: check_source_catalog(base, key)),
        ("market_readiness", lambda: check_program(base, key, program_id, exact_key)),
    ):
        try:
            _run_check(check, retry_seconds)
        except Exception as exc:
            failures.append(exc)
            LOG.error("PDUFA_REVIEW_CHECK check=%s status=FAIL error_type=%s", name, type(exc).__name__)
            if isinstance(exc, _MarketEvidenceUnavailable):
                LOG.error("PDUFA_MARKET_EVIDENCE_FAILURE %s", exc)
    if failures:
        # A non-retryable identity/boundary/provider failure must not be hidden
        # behind another check's temporary assessment-index startup failure.
        raise next((exc for exc in failures if not _retryable(exc)), failures[0])
    LOG.warning("PDUFA_REVIEW_CHECK status=PASS checks=2 orders_enabled=False fs_fa_changes=False")


def check_deployed_program(program_id: str, exact_key: str) -> None:
    """Runs once on the isolated service; never exports its existing secret."""
    if os.getenv("PDUFA_ALPACA_REVIEW_SMOKE", "").lower() not in {"1", "true", "yes"}:
        return
    key = os.getenv("PDUFA_INTERNAL_API_KEY", "")
    if not key:
        LOG.error("PDUFA_READINESS_SMOKE status=FAIL reason=MISSING_INTERNAL_KEY")
        return
    # Retry each check's temporary startup unavailability independently; an
    # Alpaca authentication failure must not prevent the source index warming.
    # Identity, boundary and provider authentication failures are never retried.
    try:
        check_all("http://127.0.0.1:8000", key, program_id, exact_key, retry_seconds=180)
    except Exception as exc:
        LOG.error("PDUFA_READINESS_SMOKE status=FAIL error_type=%s", type(exc).__name__)
