"""Read-only catalyst and financing evidence from existing exact-program reviews.

Review completeness is separate from investment suitability and trading. No
grades, weights, restrictions, list membership or FS/FA presets are changed.
"""
from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .assessment_readiness_adapter import assessment_readiness_inputs

CHECKS = (
    ("catalystTiming", "Source-reviewed upcoming catalyst", 7),
    ("cashRunway", "SEC cash runway evidence", 120),
    ("dilutionRisk", "Source-reviewed financing and dilution risk", 7),
)
CATALYST_TYPES = {"PDUFA", "PUBLIC_READOUT", "FDA_ADCOM"}


def _day(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _source(value):
    try:
        parsed = urlparse(value if isinstance(value, str) else "")
        return (parsed if parsed.scheme == "https" and parsed.hostname
                and not parsed.username and not parsed.password
                and not any(ch.isspace() for ch in value) else None)
    except ValueError:
        return None


def _review_metric(metric, key, label, age, today, candidate):
    result = {"id": key, "label": label, "status": "MISSING", "source": "",
              "checkedAt": "", "sourceDate": "", "value": None,
              "reason": "No source-reviewed evidence recorded for this exact program."}
    if not isinstance(metric, dict):
        return result
    result.update({field: metric.get(field, "") for field in ("source", "checkedAt", "sourceDate")})
    result["value"] = metric.get("value")
    if metric.get("status") != "OBSERVED":
        result.update(status=(metric.get("status") if metric.get("status") in {"STALE", "CONFLICTING", "MISSING"}
                              else "MISSING"), reason="An observed source review is required.")
        return result
    source = _source(metric.get("source"))
    checked, source_day = _day(metric.get("checkedAt")), _day(metric.get("sourceDate"))
    maximum, coverage, points = (metric.get(k) for k in ("maximum", "coverage", "points"))
    if (not source or not checked or not source_day or not source_day <= checked <= today
            or not all(_number(v) for v in (maximum, coverage, points)) or maximum <= 0
            or abs(coverage - maximum) > .000001 or not 0 <= points <= maximum):
        result.update(status="INVALID_EVIDENCE", reason="Dated source and complete observed evidence are required.")
        return result
    if (today - checked).days > age:
        result.update(status="STALE", reason=f"Review is older than the existing {age}-day evidence window.")
        return result
    if key == "cashRunway":
        if (source.hostname not in {"sec.gov", "www.sec.gov"}
                or not _number(metric.get("value")) or metric["value"] < 0):
            result.update(status="INVALID_EVIDENCE", reason="Reconciled SEC cash-only runway evidence is required.")
            return result
    else:
        value = metric.get("value") or {}
        # Catalyst scoring wraps the original review alongside reported dates.
        if key == "catalystTiming":
            value = value.get("reviewedMeasurements", {}) if isinstance(value, dict) else {}
        grade = value.get("reviewGrade") if isinstance(value, dict) else None
        measurements = value.get("measurements") if isinstance(value, dict) else None
        if (not _number(grade) or grade not in {0, 1, 2, 3, 4}
                or not measurements or not str(metric.get("note") or "").strip()):
            result.update(status="INVALID_EVIDENCE", reason="Reviewed measurements and rationale are required.")
            return result
        if key == "catalystTiming":
            event_date = measurements.get("eventDate") if isinstance(measurements, dict) else None
            event_day = _day(event_date)
            event_type = measurements.get("eventType") if isinstance(measurements, dict) else None
            if (not event_day or event_day.isoformat() != event_date
                    or not isinstance(event_type, str) or event_type not in CATALYST_TYPES
                    or measurements.get("dateConfirmed") is not True):
                result.update(status="UNCONFIRMED_EVENT_DATE",
                              reason="A confirmed public catalyst type and date are required; registry completion alone is insufficient.")
                return result
            if event_day < today:
                result.update(status="PAST_EVENT", reason="The reviewed catalyst date has passed.")
                return result
            reported = _day(candidate.get("pdufaDate"))
            if event_type == "PDUFA" and reported and reported != event_day:
                result.update(status="CONFLICTING", reason="Reviewed and currently reported PDUFA dates disagree.")
                return result
    result.update(status="REVIEWED", reason="Existing source-reviewed evidence retained; no score changed.")
    return result


def risk_evidence_from_assessment(record: dict | None, *, program_id: str, exact_key: str,
                                  stage: str = "GEM_JR", today: date | None = None) -> dict:
    """Only inspect the selected stage and exact immutable assessment identity."""
    if stage not in {"GEM_JR", "GEM"}:
        raise ValueError("Only GEM JR and GEM assessments are eligible")
    today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    identity = "ASSESSMENT_UNAVAILABLE"
    metrics, candidate = {}, {}
    if record is not None:
        assessment = assessment_readiness_inputs(record, program_id=program_id, exact_key=exact_key, stage=stage)
        identity = "IDENTITY_MISMATCH" if assessment["status"] == "IDENTITY_MISMATCH" else "EXACT_IDENTITY_MATCH"
        if identity == "EXACT_IDENTITY_MATCH":
            candidate = record["data"]["candidate"]
            model = (record.get("models") or {}).get(stage)
            model = model if isinstance(model, dict) else {}
            for category in model.get("categories") or []:
                if not isinstance(category, dict):
                    continue
                for metric in category.get("metrics") or []:
                    if not isinstance(metric, dict) or not isinstance(metric.get("id"), str):
                        continue
                    key = metric.get("id")
                    # Duplicate evidence IDs are ambiguous, never first-row-wins.
                    metrics[key] = None if key in metrics else metric
    checks = [_review_metric(metrics.get(key), key, label, age, today, candidate)
              for key, label, age in CHECKS]
    catalyst = checks[0]["status"] == "REVIEWED"
    financing = all(item["status"] == "REVIEWED" for item in checks[1:])
    return {"programId": program_id, "exactKey": exact_key, "stage": stage,
            "identityStatus": identity, "asOf": today.isoformat(),
            "status": "REVIEWED" if catalyst and financing else "REVIEW_REQUIRED",
            "catalystVerified": catalyst, "financingRiskReviewed": financing,
            "checks": checks, "missingEvidence": [c["label"] for c in checks if c["status"] != "REVIEWED"],
            "riskFlags": list(record.get("riskFlags") or []) if identity == "EXACT_IDENTITY_MATCH" else [],
            "researchOnly": True, "ordersEnabled": False, "assessmentScoreChange": False,
            "qualificationChange": False, "fsFaChange": False}
