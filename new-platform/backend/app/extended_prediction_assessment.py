"""Sponsor evidence and research-only prediction validation for Levels 17–20."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import math
import re
from urllib.parse import urlsplit

from .assessment_runtime import NCT, clinical_context, now, sha

NAMES = {
    17: "Sponsor and commercial intelligence",
    18: "Versioned prediction and uncertainty",
    19: "Blind backtesting and calibration",
    20: "Integrated validation and release readiness",
}
EXPLANATIONS = {
    17: "Registry attribution identifies the declared trial sponsor. Commercial rights and execution capability need original, program-specific evidence.",
    18: "The assessment records a versioned abstention while a validated prediction model and calibrated uncertainty are unavailable.",
    19: "Only outcome-unexposed, predecision forecasts with verified exact application-cycle outcomes are eligible for accuracy and calibration.",
    20: "Development release readiness depends on verified trial evidence, end-to-end behavior, and out-of-sample predictive validation.",
}
VERSION = "extended-prediction-v1.0.0"
SOURCE_FIELDS = ("snapshot_id", "nct_id", "captured_at", "published_at", "source_url", "raw_sha256", "input_sha256")


def _instant(value: str) -> datetime:
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() is None:
        raise ValueError("Evidence and prediction timestamps require explicit timezones")
    return stamp.astimezone(timezone.utc)


def assess_prediction_level(request, source: dict) -> dict:
    """Assess business/prediction readiness without taking historical outcomes."""
    level = request.level
    name = NAMES[level]
    nct = request.nct
    document = json.loads(source["document_json"])
    protocol = document["protocolSection"]
    if (source["nct_id"] != nct or protocol["identificationModule"]["nctId"] != nct
            or sha(document) != source["input_sha256"]):
        raise ValueError("Extended prediction source identity or digest mismatch")
    captured = _instant(source["captured_at"]).date()
    published = date.fromisoformat(source["published_at"])
    cutoff = request.cutoffDate
    if published > captured or (request.mode == "BLIND_HISTORICAL" and (
        cutoff is None or max(captured, published) > cutoff
    )):
        raise ValueError("Historical evidence leakage or invalid source chronology")

    checks = []
    observations = []

    def check(identifier, explanation, locator, *, state="MISSING"):
        checks.append({"id": identifier, "state": state, "explanation": explanation, "locator": locator})

    if level == 17:
        sponsors = protocol.get("sponsorCollaboratorsModule", {})
        lead = sponsors.get("leadSponsor", {}).get("name")
        registry_url = "https://clinicaltrials.gov/api/v2/studies/" + nct
        sponsor = lead.strip() if isinstance(lead, str) and source["source_url"] == registry_url else ""
        if sponsor:
            observations.append({"id": "registry_lead_sponsor", "value": sponsor, "sourceUrl": registry_url,
                                 "meaning": "Sponsor-reported attribution for this trial"})
        check("sponsor_attribution", "Record lead sponsor from the exact trial registry receipt.",
              "protocolSection.sponsorCollaboratorsModule.leadSponsor.name", state="AVAILABLE" if sponsor else "MISSING")
        check("commercial_rights", "Current jurisdiction-specific rights require original dated filings or agreements.",
              "Original issuer filings or licensing agreements")
        check("sponsor_execution", "Development and commercialization capability require dated program-specific sources.",
              "Original issuer filings and program communications")
    elif level == 18:
        check("prediction_model", "A versioned FDA application-cycle prediction model and verified input contract are required.",
              "Validated prediction model receipt")
        check("prediction_uncertainty", "Confidence bounds require an eligible calibration cohort and documented uncertainty method.",
              "Out-of-sample validation receipt")
    elif level == 19:
        check("blind_predictions", "Calibration requires predecision forecasts locked before any outcome was known.",
              "Immutable prospective forecast history and exact application-cycle outcomes")
        check("held_out_calibration", "An eligible locked cohort is needed before directional accuracy and calibration can be scored.",
              "Chronological holdout and outcome verification receipts")
    else:
        check("evidence_cohort", "Release requires reconciled real evidence across every eligible trial in the validation cohort.",
              "Exact-NCT cohort evidence audit")
        check("integrated_validation", "Release requires end-to-end persistence, ordering, reassessment and dashboard verification.",
              "Integrated development validation receipt")
        check("predictive_validation", "FDA prediction release requires demonstrated out-of-sample reliability with documented uncertainty.",
              "Locked model and calibration receipts")

    gaps = [check["explanation"] for check in checks if check["state"] == "MISSING"]
    return {
        "schemaVersion": 2, "kind": "TRIAL_LEVEL_EVIDENCE_ASSESSMENT",
        "nct": nct, "level": level, "name": name, "engineVersion": f"{VERSION}/level-{level}",
        "mode": request.mode, "cutoffDate": cutoff.isoformat() if cutoff else None, "executedAt": now(),
        "scientificStatus": "EVIDENCE_GAPS", "score": {"value": None, "kind": "NOT_SCORED"},
        "fdaPrediction": {"outcome": "ABSTAIN", "probability": None, "confidence": "UNCALIBRATED",
                          "calibration": "NO_VALIDATED_FDA_MODEL"},
        "context": clinical_context(document), "checks": checks, "observations": observations,
        "explanation": EXPLANATIONS[level],
        "risks": gaps, "recommendations": gaps,
        "limitations": ["Registry lead sponsor is trial attribution. Commercial rights require their own sources.",
                        "The retained snapshot does not establish that a human evaluator was outcome-unexposed."],
        "evidence": {key: source[key] for key in SOURCE_FIELDS},
        "ownerReviewStatus": "OWNER_NOT_REVIEWED", "activationStatus": "NOT_ACTIVE_SCIENTIFIC_GAPS",
        "historicalAccuracyEligible": False, "savedToDatabase": True,
    }


@dataclass(frozen=True)
class LockedForecast:
    """A receipt from trusted append-only forecast storage, read before outcome linkage."""

    application_cycle: str
    nct: str
    model_version: str
    feature_cutoff: str
    captured_at: str
    locked_at: str
    outcome_unexposed: bool
    approval_probability: float | None


@dataclass(frozen=True)
class VerifiedOutcome:
    """An exact application-cycle outcome receipt from the separate outcome ledger."""

    application_cycle: str
    nct: str
    outcome: str
    decision_date: str
    source_url: str
    verification: str


def evaluate_locked_calibration(
    forecasts: tuple[LockedForecast, ...],
    outcomes: tuple[VerifiedOutcome, ...],
    *,
    model_version: str,
    holdout_start: date,
) -> dict:
    """Compare locked binary forecasts only after freeze. Does not fit or release a model.

    Both ledgers must be trusted and append-only upstream. New reconstructions
    locked after the official decision are ineligible, even with old evidence.
    A cycle with multiple forecast or outcome versions requires protocol-level
    adjudication before this comparison, so all its records remain excluded.
    """
    if not model_version.strip():
        raise ValueError("An exact model version is required")
    by_cycle = {row.application_cycle: row for row in outcomes}
    outcome_counts = Counter(row.application_cycle for row in outcomes)
    model_forecasts = [row for row in forecasts if row.model_version == model_version]
    forecast_counts = Counter(row.application_cycle for row in model_forecasts)
    counts = Counter()
    scored = []
    for row in model_forecasts:
        outcome = by_cycle.get(row.application_cycle)
        if forecast_counts[row.application_cycle] != 1 or outcome_counts[row.application_cycle] > 1:
            counts["AMBIGUOUS_CYCLE"] += 1
            continue
        if not row.application_cycle.strip() or not NCT.fullmatch(row.nct) or row.outcome_unexposed is not True:
            counts["BLIND_PROVENANCE_UNAVAILABLE"] += 1
            continue
        if (outcome is None or outcome.nct != row.nct or outcome.verification != "VERIFIED"
                or outcome.outcome not in {"APPROVAL", "CRL"}):
            counts["NO_VERIFIED_BINARY_OUTCOME"] += 1
            continue
        try:
            url = urlsplit(outcome.source_url)
            cutoff = _instant(row.feature_cutoff)
            captured = _instant(row.captured_at)
            locked = _instant(row.locked_at)
            decision = date.fromisoformat(outcome.decision_date)
            if url.scheme != "https" or not url.hostname or url.username is not None or decision.isoformat() != outcome.decision_date:
                raise ValueError("Invalid outcome provenance")
        except (ValueError, TypeError):
            counts["INVALID_PROVENANCE"] += 1
            continue
        if not captured <= cutoff <= locked or locked.date() >= decision:
            counts["TEMPORAL_LEAKAGE"] += 1
            continue
        if locked.date() < holdout_start:
            counts["PRE_HOLDOUT"] += 1
            continue
        probability = row.approval_probability
        if probability is None:
            counts["ABSTAINED"] += 1
            continue
        if (type(probability) not in {int, float} or not 0 <= probability <= 1
                or not math.isfinite(probability)):
            counts["INVALID_PROBABILITY"] += 1
            continue
        scored.append((probability, int(outcome.outcome == "APPROVAL")))

    buckets = [[] for _ in range(5)]
    for probability, observed in scored:
        buckets[min(4, int(probability * 5))].append((probability, observed))
    bins = [
        {"count": len(bucket),
         "meanApprovalProbability": sum(p for p, _ in bucket) / len(bucket),
         "approvalFrequency": sum(y for _, y in bucket) / len(bucket)}
        for bucket in buckets if bucket
    ]
    count = len(scored)
    approvals = sum(y for _, y in scored)
    return {
        "status": "RESEARCH_ONLY" if count else "NO_ELIGIBLE_SCORED_FORECASTS",
        "modelVersion": model_version, "holdoutStart": holdout_start.isoformat(),
        "forecastCount": len(model_forecasts), "scoredCount": count, "approvals": approvals,
        "completeResponseLetters": count - approvals, "exclusions": dict(sorted(counts.items())),
        "directionalAccuracy": sum((p >= 0.5) == bool(y) for p, y in scored) / count if count else None,
        "alwaysApproveAccuracy": approvals / count if count else None,
        "brierScore": sum((p - y) ** 2 for p, y in scored) / count if count else None,
        "expectedCalibrationError": (
            sum(b["count"] * abs(b["meanApprovalProbability"] - b["approvalFrequency"]) for b in bins) / count
            if count else None
        ),
        "reliabilityBins": bins, "releasePermitted": False,
    }
