"""Levels 19–20 prospective metadata and official FDA action chronology screens.

These methods do NOT create calibrated predictions, qualify historical
reconstructions as blind, publish accuracy figures or use postdecision evidence
to construct forecasts. The Level 20 outcome record is separated from Level 19.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import re
from urllib.parse import urlparse
from .scientific_event_chronology import event_covered_by_review

VERSION = "scientific-forecast-outcome-integrity-v1"
_SHA = re.compile(r"[a-f0-9]{64}")
_APP = re.compile(r"[0-9]{6}")
_ACTIONS = {"APPROVED", "COMPLETE_RESPONSE", "WITHDRAWN", "OTHER"}
_TYPES = {"NDA", "BLA", "ANDA"}


def _utc(value):
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _official_fda(value):
    try:
        p = urlparse(value)
        host = (p.hostname or "").lower()
        return (p.scheme == "https" and (host == "fda.gov" or host.endswith(".fda.gov"))
                and not p.username and not p.password)
    except (TypeError, ValueError):
        return False


def _accepted(level, evidence, key, *, original_agency=False):
    accepted = level.get("acceptedEvidence") if isinstance(level, dict) else None
    receipt = accepted.get(key) if isinstance(accepted, dict) else None
    source = evidence.get(f"{level['level']}.{key}") if isinstance(level, dict) and isinstance(evidence, dict) else None
    if (not isinstance(receipt, dict) or receipt.get("sourceVerified") is not True
            or receipt.get("retrievalProvenance") != "RECORDED"
            or (original_agency and not _official_fda(receipt.get("source")))
            or not isinstance(source, dict)
            or not isinstance(source.get("measurements"), dict)):
        return None
    return source["measurements"]


def _application(value):
    if not isinstance(value, dict):
        return None
    app_type, number, cycle = value.get("applicationType"), value.get("applicationNumber"), value.get("reviewCycle")
    if (app_type not in _TYPES or not isinstance(number, str)
            or not _APP.fullmatch(number) or type(cycle) is not int or not 1 <= cycle <= 20):
        return None
    return (app_type, number, cycle)


def assess_prospective_metadata(level, evidence, *, trial_id, cutoff):
    base = {
        "methodVersion": VERSION, "status": "NOT_ASSESSED",
        "score": None, "fdaPrediction": "ABSTAIN", "scientificValidation": "NOT_VERIFIED",
        "genuinelyBlindVerified": False, "prospectiveAccuracyEligible": False,
        "modelCalibrated": False, "approvalProbability": None,
        "limitations": [
            "Submitted digest/timestamps are metadata, not independently authenticated immutable storage.",
            "Outcome-unexposed source isolation and external outcomes must be verified separately; historical hindsight cannot become blind by hiding results.",
            "No model accuracy, calibration or FDA prediction is computed from unverified metadata.",
        ],
    }
    fields = ("outcomeUnexposedSourceFreeze", "predictionModelArtifact", "prospectivePredictionTimestamp")
    data = {key: _accepted(level, evidence, key) for key in fields}
    if any(value is None for value in data.values()):
        return {**base, "reason": "Three separately reviewed dated freeze, model and prediction metadata records required."}
    freeze, model, prediction = (data[key] for key in fields)
    source_hash, model_hash = freeze.get("sourceFreezeSha256"), model.get("modelArtifactSha256")
    hashes_valid = (isinstance(source_hash, str) and _SHA.fullmatch(source_hash)
                    and isinstance(model_hash, str) and _SHA.fullmatch(model_hash))
    freeze_time, model_time, prediction_time = (_utc(freeze.get("frozenAt")),
                                                 _utc(model.get("modelFrozenAt")),
                                                 _utc(prediction.get("predictionAt")))
    cutoff_day = _day(cutoff)
    if (not hashes_valid or freeze.get("nctId") != trial_id
            or model.get("nctId") != trial_id or prediction.get("nctId") != trial_id
            or not freeze_time or not model_time or not prediction_time or not cutoff_day
            or not freeze_time <= model_time <= prediction_time
            or prediction_time.date() > cutoff_day
            or prediction.get("sourceFreezeSha256") != source_hash
            or prediction.get("modelArtifactSha256") != model_hash
            or not isinstance(prediction.get("predictionId"), str)
            or not 0 < len(prediction["predictionId"].strip()) <= 128
            or not event_covered_by_review(level, fields[0], freeze_time.date(), cutoff)
            or not event_covered_by_review(level, fields[1], model_time.date(), cutoff)
            or not event_covered_by_review(level, fields[2], prediction_time.date(), cutoff)):
        return {**base, "status": "REJECTED_FREEZE_METADATA",
                "reason": "Exact-trial digests, ordered timezone-aware timestamps, cutoff and prediction artifact reference must reconcile."}
    return {
        **base, "status": "FROZEN_METADATA_RECONCILED_NOT_PROSPECTIVE_CERTIFICATION",
        "nctId": trial_id, "sourceFreezeSha256": source_hash,
        "modelArtifactSha256": model_hash,
        "predictionId": prediction["predictionId"].strip(),
        "frozenAtUtc": freeze_time.isoformat(),
        "modelFrozenAtUtc": model_time.isoformat(),
        "predictionAtUtc": prediction_time.isoformat(),
        "nextAction": "Confirm externally isolated immutable prediction history and source freeze before prospective eligibility.",
    }


def assess_outcome_chronology(level, evidence, *, trial_id, cutoff, filing_context=None):
    base = {
        "methodVersion": VERSION, "status": "NOT_ASSESSED",
        "score": None, "fdaPrediction": "ABSTAIN", "scientificValidation": "NOT_VERIFIED",
        "outcomeComparisonStatus": "NO_TRUSTED_PERSISTED_PREDICTION_REFERENCE",
        "predictionAccuracy": None, "binaryDecisionAccuracyEligible": False,
        "limitations": [
            "The FDA action record is postdecision comparison material, never a prediction feature.",
            "Original goal date, revised goal dates and actual action date are different fields.",
            "Without a previously persisted outcome-unexposed forecast, no prospective accuracy may be computed.",
            "Withdrawal and OTHER are not approved-versus-CRL binary FDA outcomes.",
        ],
    }
    app = (filing_context or {}).get("candidateApplicationCycle") if isinstance(filing_context, dict) else None
    app_key = _application(app)
    if app_key is None:
        return {**base, "reason": "Exact target application/cycle is not yet reconciled."}
    goal = _accepted(level, evidence, "originalGoalDate", original_agency=True)
    outcome = _accepted(level, evidence, "officialActionAndDate", original_agency=True)
    if goal is None or outcome is None:
        return {**base, "reason": "Reviewed official goal and action original-source records required."}
    goal_date, action_date, cutoff_day = (_day(goal.get("originalGoalDate")),
                                          _day(outcome.get("officialActionDate")),
                                          _day(cutoff))
    if (goal.get("linkedNct") != trial_id or outcome.get("linkedNct") != trial_id
            or _application(goal) != app_key or _application(outcome) != app_key
            or not goal_date or not action_date or not cutoff_day
            or action_date > cutoff_day or goal_date > cutoff_day
            or outcome.get("officialAction") not in _ACTIONS
            or not event_covered_by_review(level, "officialActionAndDate", action_date, cutoff)):
        return {**base, "status": "REJECTED_ACTION_RECORD",
                "reason": "Exact application/cycle, trial, official original dates, and supported FDA action classification required."}
    action = outcome["officialAction"]
    delta_days = (action_date - goal_date).days
    return {
        **base,
        "status": "POSTDECISION_ACTION_CHRONOLOGY_ONLY",
        "application": app,
        "linkedNct": trial_id,
        "originalGoalDate": goal_date.isoformat(),
        "officialActionDate": action_date.isoformat(),
        "officialAction": action,
        "actionDaysRelativeToOriginalGoal": delta_days,
        "binaryActionCategory": action if action in {"APPROVED", "COMPLETE_RESPONSE"} else None,
        "actionSource": level["acceptedEvidence"]["officialActionAndDate"]["source"],
        "goalSource": level["acceptedEvidence"]["originalGoalDate"]["source"],
    }
