"""Research-only validation of frozen, separate FDA action and timing targets.

This adapter reuses HOP's canonical application identifiers, cohort gates and
metric implementation. It does not train a model, read clinical grades, create
forecasts, verify source content, or authorize release. Adjudication and cohort
flags are caller assertions which still require independent audit.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from math import isfinite
import re
from urllib.parse import urlsplit

from .hop_forecast_metrics import summarize_binary_forecasts
from .hop_outcome_cohort import OutcomeObservation, observation_exclusion
from .hop_outcomes_import import normalize_application_id

TARGETS = ("APPROVAL", "CRL", "REVIEW_DELAY")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_PROGRAM = re.compile(r"[A-Z0-9][A-Z0-9_.:-]{0,79}\Z")
_SOURCE_HOSTS = frozenset(("fda.gov", "www.fda.gov", "accessdata.fda.gov",
                           "open.fda.gov", "download.open.fda.gov", "www.sec.gov", "sec.gov"))


@dataclass(frozen=True)
class CycleIdentity:
    application_id: str
    review_cycle: int
    indication_id: str
    program_id: str


@dataclass(frozen=True)
class SourceReceipt:
    url: str
    title: str
    published_on: date
    content_sha256: str


@dataclass(frozen=True)
class ReviewDelayEvidence:
    """An extension and an action outcome are independent historical labels.

    NO_EXTENSION_CONFIRMED needs an affirmative, independently reviewed complete
    event history through the original goal date. Missing extension documents,
    an unexpired target, or a late action alone never establish either label.
    """
    original_goal_on: date
    original_goal_public_on: date
    disposition: str  # DOCUMENTED_EXTENSION / NO_EXTENSION_CONFIRMED / UNRESOLVED
    source: SourceReceipt | None
    extension_on: date | None = None
    revised_goal_on: date | None = None
    complete_event_history_through: date | None = None
    independently_adjudicated: bool = False
    original_goal_source: SourceReceipt | None = None


@dataclass(frozen=True)
class HistoricalReviewCycle:
    identity: CycleIdentity
    cohort_id: str
    cohort_complete_verified: bool
    independently_adjudicated: bool
    public_features_as_of: date
    action: str | None = None
    action_on: date | None = None
    action_source: SourceReceipt | None = None
    delay: ReviewDelayEvidence | None = None


@dataclass(frozen=True)
class FrozenTargetForecast:
    """An externally supplied frozen forecast, never derived from a grade here."""
    identity: CycleIdentity
    target: str
    probability: float | None  # None retains an explicit abstention.
    predicted_on: date
    features_as_of: date
    fitted_through: date
    latest_training_label_public_on: date
    model_frozen_on: date
    model_artifact_sha256: str
    training_program_ids: frozenset[str]
    training_application_ids: frozenset[str]


def _identity(value: CycleIdentity) -> None:
    if (not isinstance(value, CycleIdentity) or
            not isinstance(value.application_id, str) or
            normalize_application_id(value.application_id) != value.application_id or
            type(value.review_cycle) is not int or value.review_cycle < 1 or
            not isinstance(value.indication_id, str) or not 3 <= len(value.indication_id.strip()) <= 200 or
            not isinstance(value.program_id, str) or not _PROGRAM.fullmatch(value.program_id)):
        raise ValueError("Canonical application, review cycle, exact indication and program are required")


def _source(value: SourceReceipt | None, *, as_of: date) -> str | None:
    if not isinstance(value, SourceReceipt):
        return "missing_original_source"
    try:
        url = urlsplit(value.url)
        valid = (url.scheme == "https" and url.hostname in _SOURCE_HOSTS and
                 url.username is None and url.password is None and url.port is None and
                 url.path not in ("", "/") and not url.fragment)
    except (TypeError, ValueError):
        valid = False
    if (not valid or not isinstance(value.title, str) or not value.title.strip() or
            not isinstance(value.content_sha256, str) or not _DIGEST.fullmatch(value.content_sha256)):
        return "invalid_original_source_receipt"
    if type(value.published_on) is not date:
        return "unknown_source_publication"
    if value.published_on > as_of:
        return "source_not_yet_public"
    return None


def _label(row: HistoricalReviewCycle, target: str, *, as_of: date):
    """Return (binary label, target event date, publication date, exclusion)."""
    if (not isinstance(row.cohort_id, str) or not row.cohort_id.strip() or
            row.cohort_complete_verified is not True):
        return None, None, None, "selection_biased_or_unknown_denominator"
    if row.independently_adjudicated is not True:
        return None, None, None, "independent_label_review_missing"
    if type(row.public_features_as_of) is not date:
        return None, None, None, "unknown_feature_publication"
    if target in ("APPROVAL", "CRL"):
        reason = _source(row.action_source, as_of=as_of)
        if reason:
            return None, None, None, reason
        observation = OutcomeObservation(
            application_id=row.identity.application_id, review_cycle=row.identity.review_cycle,
            decision_date=row.action_on, outcome=row.action,
            ascertainment_source="COMPLETE_APPLICATION_COHORT", cohort_id=row.cohort_id,
            public_features_as_of=row.public_features_as_of,
            cohort_complete_verified=row.cohort_complete_verified,
            outcome_public_as_of=row.action_source.published_on)
        reason = observation_exclusion(observation, as_of=as_of)
        if reason:
            return None, None, None, reason
        approved = int(row.action == "APPROVED")
        return (approved if target == "APPROVAL" else 1 - approved), row.action_on, row.action_source.published_on, None
    delay = row.delay
    if not isinstance(delay, ReviewDelayEvidence):
        return None, None, None, "delay_evidence_missing"
    if delay.independently_adjudicated is not True:
        return None, None, None, "independent_delay_review_missing"
    if (type(delay.original_goal_on) is not date or type(delay.original_goal_public_on) is not date or
            delay.original_goal_public_on > delay.original_goal_on):
        return None, None, None, "original_goal_history_missing"
    reason = _source(delay.original_goal_source, as_of=as_of)
    if reason or delay.original_goal_source.published_on != delay.original_goal_public_on:
        return None, None, None, "original_goal_source_missing_or_inconsistent"
    reason = _source(delay.source, as_of=as_of)
    if reason:
        return None, None, None, reason
    if delay.disposition == "DOCUMENTED_EXTENSION":
        if (type(delay.extension_on) is not date or type(delay.revised_goal_on) is not date or
                delay.revised_goal_on <= delay.original_goal_on or delay.extension_on > as_of or
                delay.original_goal_public_on >= delay.extension_on or
                delay.source.published_on < delay.extension_on or
                row.public_features_as_of >= delay.extension_on):
            return None, None, None, "extension_history_invalid"
        return 1, delay.extension_on, delay.source.published_on, None
    if delay.disposition == "NO_EXTENSION_CONFIRMED":
        if (row.action not in ("APPROVED", "COMPLETE_RESPONSE") or type(row.action_on) is not date or
                row.action_on > delay.original_goal_on or
                delay.original_goal_public_on >= row.action_on or
                type(delay.complete_event_history_through) is not date or
                delay.complete_event_history_through < delay.original_goal_on or
                delay.complete_event_history_through > as_of or
                row.public_features_as_of >= row.action_on or
                delay.source.published_on < row.action_on):
            return None, None, None, "no_extension_followup_incomplete"
        # An explicit historical adjudication is essential. Merely observing an
        # approval or CRL before the goal does not prove no earlier extension.
        return 0, row.action_on, delay.source.published_on, None
    return None, None, None, "delay_unresolved"


def evaluate_target(
    rows: list[HistoricalReviewCycle], forecasts: list[FrozenTargetForecast], target: str,
    *, holdout_start: date, holdout_end: date, evaluation_as_of: date,
    held_out_program_ids: frozenset[str], holdout_frozen_on: date,
) -> dict:
    """Evaluate supplied frozen forecasts; never certify a real model or source.

    Every label remains isolated by exact application/cycle/indication/program.
    Complete cohorts, adjudication and frozen-model metadata are assertions to
    independently audit, not claims established by a boolean in this function.
    """
    if target not in TARGETS:
        raise ValueError("Keep approval, CRL and review delay as separate targets")
    if (any(type(d) is not date for d in (holdout_start, holdout_end, evaluation_as_of, holdout_frozen_on)) or
            not holdout_frozen_on < holdout_start < holdout_end <= evaluation_as_of or
            type(held_out_program_ids) is not frozenset or
            (rows and not held_out_program_ids) or
            any(not isinstance(p, str) or not _PROGRAM.fullmatch(p) for p in held_out_program_ids)):
        raise ValueError("Freeze program holdouts before an ordered temporal test window")
    by_identity, cycles, program_by_application = {}, set(), {}
    for row in rows:
        if not isinstance(row, HistoricalReviewCycle):
            raise ValueError("Historical review-cycle records required")
        _identity(row.identity)
        cycle = (row.identity.application_id, row.identity.review_cycle)
        if cycle in cycles:
            raise ValueError("Duplicate or conflicting application/review cycle")
        previous_program = program_by_application.setdefault(row.identity.application_id, row.identity.program_id)
        if previous_program != row.identity.program_id:
            raise ValueError("One canonical program family is required per application")
        cycles.add(cycle)
        by_identity[row.identity] = row
    supplied = {}
    for forecast in forecasts:
        if not isinstance(forecast, FrozenTargetForecast):
            raise ValueError("Frozen target forecasts required")
        _identity(forecast.identity)
        if forecast.target != target or forecast.identity not in by_identity or forecast.identity in supplied:
            raise ValueError("Forecast target, exact indication/cycle identity or uniqueness mismatch")
        if (forecast.probability is not None and
                (type(forecast.probability) not in (int, float) or not isfinite(forecast.probability) or
                 not 0 <= forecast.probability <= 1)):
            raise ValueError("A frozen research forecast must be finite in [0,1] or abstain")
        clocks = (forecast.predicted_on, forecast.features_as_of, forecast.fitted_through,
                  forecast.latest_training_label_public_on, forecast.model_frozen_on)
        if (any(type(d) is not date for d in clocks) or
                not forecast.latest_training_label_public_on < forecast.fitted_through <= forecast.model_frozen_on < holdout_start or
                not holdout_start <= forecast.predicted_on < holdout_end or
                not forecast.model_frozen_on <= forecast.features_as_of <= forecast.predicted_on or
                forecast.features_as_of != by_identity[forecast.identity].public_features_as_of or
                not isinstance(forecast.model_artifact_sha256, str) or not _DIGEST.fullmatch(forecast.model_artifact_sha256)):
            raise ValueError("Frozen model, feature or training-publication chronology leaks across holdout")
        if (type(forecast.training_program_ids) is not frozenset or
                not forecast.training_program_ids or
                any(not isinstance(p, str) or not _PROGRAM.fullmatch(p) for p in forecast.training_program_ids) or
                forecast.training_program_ids & held_out_program_ids or
                forecast.identity.program_id in forecast.training_program_ids):
            raise ValueError("Training programs overlap prespecified held-out program families")
        if (type(forecast.training_application_ids) is not frozenset or
                not forecast.training_application_ids or
                any(not isinstance(app, str) or normalize_application_id(app) != app
                    for app in forecast.training_application_ids) or
                forecast.identity.application_id in forecast.training_application_ids or
                any(app in program_by_application and program_by_application[app] in held_out_program_ids
                    for app in forecast.training_application_ids)):
            raise ValueError("Training applications overlap exact held-out applications or declared program families")
        supplied[forecast.identity] = forecast
    excluded, pairs, eligible = Counter(), [], 0
    used_applications, used_programs = set(), set()
    ordered_rows = sorted(rows, key=lambda row: (
        _label(row, target, as_of=evaluation_as_of)[1] or date.max,
        row.identity.application_id, row.identity.review_cycle))
    for row in ordered_rows:
        if row.identity.program_id not in held_out_program_ids:
            excluded["outside_prespecified_program_holdout"] += 1
            continue
        label, event_on, public_on, reason = _label(row, target, as_of=evaluation_as_of)
        if reason:
            excluded[reason] += 1
            continue
        if not holdout_start <= event_on < holdout_end:
            excluded["outside_temporal_holdout"] += 1
            continue
        forecast = supplied.get(row.identity)
        if forecast:
            if not forecast.predicted_on < event_on or not forecast.predicted_on < public_on:
                raise ValueError("Forecast must precede the target event and its public availability")
            if target == "REVIEW_DELAY" and not (
                    row.delay.original_goal_public_on <= forecast.features_as_of and
                    forecast.predicted_on < row.delay.original_goal_on):
                raise ValueError("Delay forecast requires the original publicly known unexpired goal")
        # Apply a prespecified earliest target-event cycle rule even when that
        # forecast abstains. Later easier cycles cannot replace an abstention.
        if row.identity.application_id in used_applications or row.identity.program_id in used_programs:
            excluded["repeated_application_or_program"] += 1
            continue
        used_applications.add(row.identity.application_id)
        used_programs.add(row.identity.program_id)
        eligible += 1
        if forecast and forecast.probability is not None:
            pairs.append((float(forecast.probability), label))
    metrics = summarize_binary_forecasts(pairs, eligible_count=eligible)
    # HOP's reusable mathematical kernel names its binary positive class
    # approval. Here CRL and timing positives keep their own explicit meaning.
    for bucket in metrics["calibrationBins"]:
        bucket["observedEventRate"] = bucket.pop("observedApprovalRate")
    return {
        "schema": "MAIN_FROZEN_TARGET_RESEARCH_VALIDATION_V1", "target": target,
        "inputReviewCycles": len(rows), "eligibleReviewCycles": eligible,
        "excluded": dict(excluded), "researchMetrics": metrics,
        "sourceTruthVerifiedByThisCode": False, "cohortClaimsIndependentlyAuditedByThisCode": False,
        "calibrationConfidenceInterval": None,
        "releaseDependencies": ["Independently adjudicated complete historical cohorts",
                                "Audited frozen model and untouched temporal/program holdout",
                                "Independent calibration uncertainty and release approval"],
        "modelValidated": False, "prediction": "ABSTAIN", "certainty": "NOT_VALIDATED",
        "accuracy": "NOT_CALIBRATED",
    }
