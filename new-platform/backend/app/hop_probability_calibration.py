"""Validation-only isotonic calibration for sealed historical research inputs.

This extends the existing blinded replay and exact-cycle target evaluator. It
fits no base forecaster and never authorizes model training, source truth or a
numerical FDA prediction. Caller-supplied adjudication/custody claims still need
independent audit. Synthetic protocol tests are not historical performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from math import isfinite
import re

from .hop_blinded_phase3_backtest import freeze_predecision_evidence
from .hop_forecast_metrics import summarize_binary_forecasts
from .medical_fda_validation import (
    TARGETS, FrozenTargetForecast, HistoricalReviewCycle, _identity, _label,
    evaluate_target,
)


@dataclass(frozen=True)
class TemporalCalibrationPlan:
    training_end: date
    validation_start: date
    validation_end: date
    calibration_frozen_on: date
    test_start: date
    test_end: date
    evaluation_as_of: date
    split_frozen_on: date
    training_programs: frozenset[str]
    validation_programs: frozenset[str]
    test_programs: frozenset[str]


@dataclass(frozen=True)
class IsotonicArtifact:
    """Immutable PAV blocks; test labels and test forecasts are absent."""
    target: str
    frozen_on: date
    base_model_sha256: str
    validation_input_sha256: str
    minimum_score: float
    maximum_score: float
    blocks: tuple[tuple[float, float, int, int], ...]

    def payload(self):
        return {"schema": "HOP_VALIDATION_ONLY_ISOTONIC_ARTIFACT_V1",
                "target": self.target, "frozenOn": self.frozen_on.isoformat(),
                "baseModelSha256": self.base_model_sha256,
                "validationInputSha256": self.validation_input_sha256,
                "minimumScore": self.minimum_score, "maximumScore": self.maximum_score,
                "blocks": [list(block) for block in self.blocks],
                "testLabelsUsedForFit": False, "modelValidated": False}

    @property
    def sha256(self):
        return _digest(self.payload())

    def transform(self, score):
        """Monotone step fit: a gap takes the next block's value; no extrapolation."""
        if score is None:
            return None
        if type(score) not in (int, float) or not isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Finite research score in [0,1] or abstention required")
        # No unsupported extrapolation beyond the validation score range.
        if not self.minimum_score <= score <= self.maximum_score:
            return None
        for _, upper, positives, count in self.blocks:
            if score <= upper:
                return positives / count
        raise ValueError("Calibration artifact has incomplete score support")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _plan(plan):
    if not isinstance(plan, TemporalCalibrationPlan):
        raise ValueError("Frozen three-way calibration plan required")
    clocks = (plan.training_end, plan.validation_start, plan.validation_end,
              plan.calibration_frozen_on, plan.test_start, plan.test_end, plan.evaluation_as_of)
    if (any(type(d) is not date for d in clocks + (plan.split_frozen_on,)) or
            not plan.training_end < plan.validation_start < plan.validation_end <=
                plan.calibration_frozen_on < plan.test_start < plan.test_end <= plan.evaluation_as_of or
            not plan.split_frozen_on < plan.validation_start):
        raise ValueError("Chronological train/validation/frozen-calibration/test separation required")
    groups = (plan.training_programs, plan.validation_programs, plan.test_programs)
    if (any(type(g) is not frozenset or not g or
            any(not isinstance(x, str) or not x for x in g) for g in groups) or
            any(groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3))):
        raise ValueError("Prespecified nonempty disjoint program-family partitions required")


def _frozen_packets(packets, rows):
    expected = {(r.identity.application_id, r.identity.review_cycle): r for r in rows}
    verified = {}
    for item in packets:
        if not isinstance(item, dict) or not isinstance(item.get("frozenEvidence"), dict):
            raise ValueError("Original blinded predecision packets required")
        packet = item["frozenEvidence"]
        raw = {name: packet.get(name) for name in (
            "applicationId", "reviewCycle", "programFamily", "nctIds",
            "phase3ReadoutPublicOn", "predictionCutoff")}
        raw["evidenceSources"] = packet.get("sourceVersions")
        if freeze_predecision_evidence(raw) != item:
            raise ValueError("Original blinded packet digest or safety fields changed")
        key = (packet["applicationId"], packet["reviewCycle"])
        row = expected.get(key)
        if (key in verified or row is None or packet["programFamily"] != row.identity.program_id or
                packet["predictionCutoff"] != row.public_features_as_of.isoformat()):
            raise ValueError("Blinded packet must match exact target cycle, family and feature cutoff")
        verified[key] = item["frozenSourceSha256"]
    if set(verified) != set(expected):
        raise ValueError("Every validation/test cycle requires its own blinded evidence packet")
    return verified


def _eligible_pairs(rows, forecasts, target, start, end, as_of):
    """Extract only rows accepted by the existing exact-target evaluator."""
    supplied = {f.identity: f for f in forecasts}
    pairs, material, applications, programs = [], [], set(), set()
    ordered = sorted(rows, key=lambda r: (_label(r, target, as_of=as_of)[1] or date.max,
                                         r.identity.application_id, r.identity.review_cycle))
    for row in ordered:
        label, event, _, reason = _label(row, target, as_of=as_of)
        if reason or not start <= event < end:
            continue
        if row.identity.application_id in applications or row.identity.program_id in programs:
            continue
        applications.add(row.identity.application_id)
        programs.add(row.identity.program_id)
        forecast = supplied.get(row.identity)
        if forecast is not None and forecast.probability is not None:
            pairs.append((float(forecast.probability), label))
            material.append([row.identity.application_id, row.identity.review_cycle,
                             row.identity.indication_id, row.identity.program_id,
                             float(forecast.probability), label])
    return pairs, material


def _fit(pairs, *, target, frozen_on, model_sha, material, min_validation):
    if len(pairs) < min_validation or {y for _, y in pairs} != {0, 1}:
        return None
    ties = {}
    for p, label in pairs:
        positive, count = ties.get(p, (0, 0))
        ties[p] = (positive + label, count + 1)
    blocks = []
    for score, (positives, count) in sorted(ties.items()):
        blocks.append((score, score, positives, count))
        while len(blocks) >= 2 and blocks[-2][2] / blocks[-2][3] > blocks[-1][2] / blocks[-1][3]:
            left, right = blocks[-2:]
            blocks[-2:] = [(left[0], right[1], left[2] + right[2], left[3] + right[3])]
    return IsotonicArtifact(target, frozen_on, model_sha, _digest(sorted(material)),
                            min(ties), max(ties), tuple(blocks))


def evaluate_calibration_protocol(rows, forecasts, frozen_packets, target, plan, *, min_validation=100):
    """Fit validation only, freeze a digest, then open the disjoint test labels.

    The supplied base-model artifact must already be frozen using the complete
    declared training roster. Independent source truth, genuine outcome-vault
    custody, prespecification and representative sampling remain external gates.
    This callable produces research mathematics only, even with asserted flags.
    """
    _plan(plan)
    if target not in TARGETS or type(min_validation) is not int or min_validation < 2:
        raise ValueError("Separate target and at least two validation observations required")
    if not isinstance(rows, list) or any(not isinstance(r, HistoricalReviewCycle) for r in rows):
        raise ValueError("Exact historical review-cycle records required")
    if not isinstance(forecasts, list) or any(not isinstance(f, FrozenTargetForecast) for f in forecasts):
        raise ValueError("Frozen base-model forecasts required")
    cycles, program_by_app = set(), {}
    for row in rows:
        _identity(row.identity)
        key = (row.identity.application_id, row.identity.review_cycle)
        if key in cycles or program_by_app.setdefault(row.identity.application_id, row.identity.program_id) != row.identity.program_id:
            raise ValueError("Duplicate cycle or changed canonical application family")
        cycles.add(key)
    all_groups = plan.training_programs | plan.validation_programs | plan.test_programs
    if {r.identity.program_id for r in rows} != all_groups:
        raise ValueError("Complete prespecified program roster required; no dropped or added families")
    training = [r for r in rows if r.identity.program_id in plan.training_programs]
    validation = [r for r in rows if r.identity.program_id in plan.validation_programs]
    test = [r for r in rows if r.identity.program_id in plan.test_programs]
    latest_training_label = date.min
    for row in training:
        _, event, public, reason = _label(row, target, as_of=plan.training_end)
        if reason or not event < plan.training_end:
            raise ValueError("Training roster requires reviewed original labels public before training end")
        latest_training_label = max(latest_training_label, public)
    training_apps = frozenset(r.identity.application_id for r in training)
    allowed = {r.identity for r in validation + test}
    if any(f.identity not in allowed for f in forecasts):
        raise ValueError("Forecast identity cannot borrow a different indication, cycle or split")
    model_digests = {f.model_artifact_sha256 for f in forecasts}
    if len(model_digests) != 1:
        raise ValueError("One unchanged frozen base model required across validation and test")
    for f in forecasts:
        if (f.training_program_ids != plan.training_programs or f.training_application_ids != training_apps or
                f.latest_training_label_public_on != latest_training_label or
                not f.fitted_through <= f.model_frozen_on <= plan.training_end):
            raise ValueError("Base-model training roster or publication clock changed after fitting")
    evidence_digests = _frozen_packets(frozen_packets, validation + test)
    validation_forecasts = [f for f in forecasts if f.identity.program_id in plan.validation_programs]
    validation_result = evaluate_target(validation, validation_forecasts, target,
        holdout_start=plan.validation_start, holdout_end=plan.validation_end,
        evaluation_as_of=plan.calibration_frozen_on, held_out_program_ids=plan.validation_programs,
        holdout_frozen_on=plan.split_frozen_on)
    pairs, material = _eligible_pairs(validation, validation_forecasts, target,
        plan.validation_start, plan.validation_end, plan.calibration_frozen_on)
    if len(pairs) != validation_result["researchMetrics"]["predictedCount"]:
        raise ValueError("Calibration rows differ from exact-target eligibility audit")
    material.append(["protocol", {
        "trainingEnd": plan.training_end.isoformat(),
        "trainingRoster": sorted([[r.identity.application_id, r.identity.review_cycle,
                                   r.identity.indication_id, r.identity.program_id] for r in training]),
        "validationWindow": [plan.validation_start.isoformat(), plan.validation_end.isoformat()],
        "testWindow": [plan.test_start.isoformat(), plan.test_end.isoformat()],
        "splitFrozenOn": plan.split_frozen_on.isoformat(),
        "trainingPrograms": sorted(plan.training_programs),
        "validationPrograms": sorted(plan.validation_programs),
        "prespecifiedTestPrograms": sorted(plan.test_programs),
    }])
    material.append(["frozenEvidence", sorted((key, digest) for key, digest in evidence_digests.items()
        if key in {(r.identity.application_id, r.identity.review_cycle) for r in validation})])
    artifact = _fit(pairs, target=target, frozen_on=plan.calibration_frozen_on,
                    model_sha=next(iter(model_digests)), material=material, min_validation=min_validation)
    result = {"schema": "HOP_TEMPORAL_CALIBRATION_RESEARCH_V1", "target": target,
        "status": "BLOCKED_INSUFFICIENT_VALIDATION_LABELS", "trainingCycles": len(training),
        "validationAudit": validation_result, "fittedArtifact": None, "fittedArtifactSha256": None,
        "untouchedTestEvaluated": False, "rawTestResearchMetrics": None,
        "calibratedTestResearchMetrics": None, "modelValidated": False,
        "sourceTruthVerifiedByThisCode": False, "outcomeVaultCustodyVerifiedByThisCode": False,
        "trainingAuthorized": False, "prediction": "ABSTAIN", "certainty": "NOT_VALIDATED",
        "accuracy": "NOT_CALIBRATED", "calibrationConfidenceInterval": None}
    if artifact is None:
        return result
    # This branch is reached only after the validation artifact is immutable.
    test_forecasts = [f for f in forecasts if f.identity.program_id in plan.test_programs]
    raw = evaluate_target(test, test_forecasts, target, holdout_start=plan.test_start,
        holdout_end=plan.test_end, evaluation_as_of=plan.evaluation_as_of,
        held_out_program_ids=plan.test_programs, holdout_frozen_on=plan.split_frozen_on)
    test_pairs, _ = _eligible_pairs(test, test_forecasts, target,
        plan.test_start, plan.test_end, plan.evaluation_as_of)
    calibrated = [(mapped, y) for p, y in test_pairs if (mapped := artifact.transform(p)) is not None]
    metrics = summarize_binary_forecasts(calibrated, eligible_count=raw["eligibleReviewCycles"])
    for bucket in metrics["calibrationBins"]:
        bucket["observedEventRate"] = bucket.pop("observedApprovalRate")
    result.update(status="RESEARCH_MATH_ONLY_NOT_VALIDATED_FDA_ACCURACY",
        fittedArtifact=artifact.payload(), fittedArtifactSha256=artifact.sha256,
        untouchedTestEvaluated=True, rawTestResearchMetrics=raw["researchMetrics"],
        calibratedTestResearchMetrics=metrics,
        testExclusions=raw["excluded"], testScoresOutsideValidationSupport=sum(
            artifact.transform(p) is None for p, _ in test_pairs))
    return result


def calibration_readiness_status(source_checkpoint=None):
    """Quarantine a validated Track-B checkpoint, or replay the pinned receipt.

    Track B must validate original candidate bytes before passing its checkpoint.
    This projection validates the checkpoint contract, not FDA source truth; it
    never fits on selected action-source rows or certifies fresh source access.
    """
    if source_checkpoint is None:
        from .hop_status import hop_readiness_status
        source = hop_readiness_status().get("fda_fresh_source_recapture")
        observed = {
            "sourceActionLeads": source["candidateRows"] if source else None,
            "sourceArchiveUrl": source["sourceArchiveUrl"] if source else None,
            "sourceArchiveExpiresAt": source["archiveExpiresAt"] if source else None,
            "sourceReceiptAsOf": source["asOf"] if source else None,
            "sourceCountBasis": "PINNED_R38_RECEIPT_METADATA_REPLAY",
        }
    else:
        c = source_checkpoint
        try:
            stamp = datetime.fromisoformat(c["generatedAtUtc"].replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp.utcoffset() is None:
                raise ValueError()
        except (TypeError, KeyError, AttributeError, ValueError):
            raise ValueError("Track-B checkpoint requires a timezone-aware receipt timestamp") from None
        if (not isinstance(c, dict) or c.get("schema") != "MAIN_R47_HISTORICAL_SOURCE_BUILD_CHECKPOINT"
                or c.get("status") != "LIVE_HISTORICAL_FDA_CANDIDATE_SOURCE_RESEARCH_NOT_REAL_BACKTEST"
                or type(c.get("researchSourceActionCandidates")) is not int
                or c["researchSourceActionCandidates"] < 0
                or any(not isinstance(c.get(k), str) or not re.fullmatch(r"[a-f0-9]{64}", c[k])
                       for k in ("candidateFileSha256", "originalFdaSourceReceiptSha256"))
                or any(c.get(k) is not False for k in (
                    "completeConsecutiveOriginalFilingCohort", "modelTrainingAuthorized",
                    "productionWriteAuthorized", "automaticAccuracyOrHundredPercentClaimAuthorized"))
                or any(type(c.get(k)) is not int or c[k] != 0 for k in (
                    "exactCycleOutcomesAdjudicated", "pairedIndependentHistory", "qualifiedResearchPredictions",
                    "qualifiedClinicalReviewerSignoffs", "outOfTimeValidationCases"))
                or any(c.get(k) is not None for k in ("prospectiveAccuracy", "calibration", "approvalProbability"))):
            raise ValueError("Track-B checkpoint cannot promote selected sources to calibration cases")
        observed = {
            "sourceActionLeads": c["researchSourceActionCandidates"],
            "candidateFileSha256": c["candidateFileSha256"],
            "originalFdaSourceReceiptSha256": c["originalFdaSourceReceiptSha256"],
            "sourceCheckpointGeneratedAt": c.get("generatedAtUtc"),
            "sourceCountBasis": "CURRENT_VALIDATED_TRACK_B_CANDIDATE_CHECKPOINT",
            "sourceCountIsFreshRetrieval": False,
            "sourceArchiveUrl": None, "sourceArchiveExpiresAt": None, "sourceReceiptAsOf": None,
        }
    return {"schema": "HOP_CALIBRATION_READINESS_V1", **observed,
        "sourceCountIsFreshRetrieval": False,
        "permanentSourceArchiveVerified": False,
        "calibrationProtocolHealth": "VALIDATION_ONLY_ISOTONIC_IMPLEMENTED",
        "fitStatus": "NOT_RUN_NO_MODEL_ELIGIBLE_CASES", "realCases": 0,
        "cohortSelection": "OUTCOME_SELECTED_NOT_COMPLETE_CONSECUTIVE_FILING_COHORT",
        "newHistoricalRecordsObtained": 0, "independentlyVerifiedCycles": 0,
        "modelEligibleCases": 0, "realTrainingCases": 0, "realValidationCases": 0,
        "realUntouchedTestCases": 0, "actualCalibrationFits": 0,
        "calibrationInfrastructure": "VALIDATION_ONLY_ISOTONIC_WITH_FROZEN_TEMPORAL_TEST",
        "modelValidationStatus": "BLOCKED", "accuracyAvailable": False,
        "measuredAccuracy": None, "brierScore": None, "logLoss": None,
        "perTargetModelEligibleCases": {target: 0 for target in TARGETS},
        "blockers": ["Complete consecutive filing denominator including negative/pending/withdrawn cases",
            "Exact application, indication and independently adjudicated review-cycle outcomes",
            "Original predecision source versions and first-publication clocks",
            "Independent outcome-vault custody and frozen program-disjoint partitions",
            "Sufficient independently assessed validation and untouched-test cases"],
        "trainingAuthorized": False, "prediction": "ABSTAIN", "certainty": "NOT_VALIDATED",
        "accuracy": "NOT_CALIBRATED"}
