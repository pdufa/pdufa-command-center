#!/usr/bin/env python3
"""Level 7: leakage-resistant predictive-model validation *readiness* audit.

This is a pre-model engineering gate. It audits the provenance of each proposed
prediction input and the design of out-of-time calibration/backtesting. It never
trains a model, estimates probabilities, or declares a model clinically valid.

Future prospective and outcome-blind historical analyses use different source
requirements: a present-day ClinicalTrials.gov snapshot MUST NOT be treated as
evidence known before a past FDA decision.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

NCT = re.compile(r"NCT[0-9]{8}\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
LABELS = {"FUTURE_PROSPECTIVE", "HISTORICAL_OUTCOME_BLIND"}
SPLIT = "TEMPORAL_FORWARD_HOLDOUT"
CALIBRATION_FIT = "TRAINING_FOLDS_ONLY"
REQUIRED_METRICS = {
    "brier_score", "log_loss", "calibration_slope", "calibration_intercept",
    "expected_calibration_error", "reliability_diagram", "sample_size_by_outcome",
}
OUTCOME_KEYS = {
    "actual_outcome", "actual_fda_decision", "known_fda_decision",
    "fda_approval_outcome", "post_decision_label", "unblinded_outcome",
    "target_label", "decision_result", "final_fda_outcome",
}
MAX_BATCH = 32


def mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value or len(value) > 40:
        raise ValueError("Datetime must be a bounded RFC3339 string")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp") from exc
    if date.tzinfo is None or date.utcoffset() is None:
        raise ValueError("UTC offset is required")
    return date.astimezone(timezone.utc)


def outcome_key_paths(value: Any, prefix: str = "") -> list[str]:
    """Fail closed on explicit post-decision label fields nested anywhere."""
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                found.append(prefix + ".INVALID_KEY")
                continue
            path = (prefix + "." if prefix else "") + key
            if key.casefold() in OUTCOME_KEYS:
                found.append(path)
            if isinstance(child, (dict, list)):
                found.extend(outcome_key_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            if isinstance(child, (dict, list)):
                found.extend(outcome_key_paths(child, f"{prefix}[{index}]"))
    return found


def audit_input(row: dict) -> dict:
    """Report evidence gate issues without pretending a source was reviewed."""
    if not isinstance(row, dict):
        raise ValueError("Input must be an object")
    nct = row.get("nct")
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Exact NCT required")
    mode = row.get("mode")
    if mode not in LABELS:
        raise ValueError("Explicit future or historical mode required")
    issues = []
    tainted = outcome_key_paths(row)
    if tainted:
        issues.append("OUTCOME_LABEL_FIELDS_EXPOSED")
    evidence = row.get("evidence_sources")
    if not isinstance(evidence, list) or not evidence:
        issues.append("NO_PRIMARY_SOURCE_RECEIPTS")
        evidence = []
    cutoff = row.get("prediction_cutoff_utc")
    try:
        cut = timestamp(cutoff)
    except ValueError:
        issues.append("INVALID_PREDICTION_CUTOFF")
        cut = None
    for source in evidence:
        if not isinstance(source, dict):
            issues.append("INVALID_SOURCE_OBJECT")
            continue
        if not isinstance(source.get("sha256"), str) or not SHA256.fullmatch(source["sha256"]):
            issues.append("MISSING_EXACT_SOURCE_SHA256")
        if not isinstance(source.get("url"), str) or not source["url"].startswith("https://"):
            issues.append("UNVERIFIABLE_PRIMARY_SOURCE_URL")
        if not isinstance(source.get("phase_at_cutoff"), str) or not source["phase_at_cutoff"]:
            issues.append("PHASE_AT_CUTOFF_UNVERIFIED")
        if not isinstance(source.get("trial_nct"), str) or source["trial_nct"] != nct:
            issues.append("SOURCE_TRIAL_IDENTITY_NOT_PROVEN")
        try:
            access = timestamp(source.get("retrieved_at_utc"))
            available = timestamp(source.get("publicly_available_at_utc"))
        except ValueError:
            issues.append("SOURCE_ACCESS_OR_PUBLICATION_DATE_UNVERIFIED")
            continue
        if cut is not None and available > cut:
            issues.append("SOURCE_PUBLISHED_AFTER_PREDICTION_CUTOFF")
        if mode == "HISTORICAL_OUTCOME_BLIND":
            if source.get("source_revision") == "CURRENT_STATE_NOT_HISTORICAL_FREEZE":
                issues.append("CURRENT_REGISTRY_USED_AS_HISTORICAL_EVIDENCE")
            if cut is not None and access > cut and not source.get("immutable_pre_cutoff_capture_verified"):
                issues.append("LATE_RETRIEVAL_WITHOUT_VERIFIED_PRE_CUTOFF_FREEZE")
        elif cut is not None and access > cut:
            issues.append("FUTURE_PROSPECTIVE_SOURCE_RETRIEVED_AFTER_CUTOFF")
    return {
        "nct": nct, "mode": mode, "eligible_for_blinded_model_input": not issues,
        "review_leads": sorted(set(issues)), "independently_adjudicated": False,
        "source_count": len(evidence), "fda_probability": None, "prediction": None,
    }


def audit_plan(plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError("Model validation plan must be an object")
    issues = []
    if not isinstance(plan.get("model_version"), str) or not plan["model_version"].strip():
        issues.append("MODEL_VERSION_NOT_FROZEN")
    split = mapping(plan.get("split"))
    if split.get("method") != SPLIT:
        issues.append("NON_TEMPORAL_OR_UNSPECIFIED_VALIDATION_SPLIT")
    else:
        try:
            train_end = timestamp(split.get("train_end_utc"))
            holdout_start = timestamp(split.get("holdout_start_utc"))
            if not train_end < holdout_start:
                issues.append("TRAINING_OVERLAPS_FUTURE_HOLDOUT")
        except ValueError:
            issues.append("TRAIN_HOLDOUT_CUTOFF_NOT_DEFINED")
    if split.get("outcome_labels_sealed_until_final_evaluation") is not True:
        issues.append("HOLDOUT_OUTCOMES_NOT_SEALED")
    calibration = mapping(plan.get("calibration"))
    if calibration.get("fit_partition") != CALIBRATION_FIT:
        issues.append("CALIBRATION_FIT_MUST_EXCLUDE_FINAL_HOLDOUT")
    if calibration.get("method") not in {"PLATT", "ISOTONIC", "BETA"}:
        issues.append("CALIBRATION_METHOD_NOT_DEFINED")
    requested = plan.get("report_metrics")
    metric_set = set(requested) if isinstance(requested, list) and all(
        isinstance(x, str) for x in requested) else set()
    if REQUIRED_METRICS - metric_set:
        issues.append("PRESPECIFIED_CALIBRATION_METRICS_INCOMPLETE")
    if plan.get("outcome_label_definition_locked_before_validation") is not True:
        issues.append("OUTCOME_LABEL_DEFINITION_NOT_FROZEN")
    if plan.get("independent_validation_review") is not True:
        issues.append("INDEPENDENT_VALIDATION_REVIEW_PENDING")
    return {"model_version": plan.get("model_version"), "validation_plan_design_complete": not issues,
            "review_leads": sorted(set(issues)), "metrics_computed": False,
            "calibration_verified": False, "approval_probability": None}


def audit_bundle(bundle: dict) -> dict:
    if not isinstance(bundle, dict):
        raise ValueError("Expected input bundle")
    if set(bundle) - {"inputs", "plan", "bundle_label"}:
        raise ValueError("Unknown bundle fields; refuse potential leakage")
    inputs = bundle.get("inputs")
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= MAX_BATCH:
        raise ValueError("Expected 1-32 input records")
    reports = [audit_input(row) for row in inputs]
    ids = [row["nct"] for row in reports]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate NCT in batch")
    plan = audit_plan(bundle.get("plan"))
    return {
        "level": 7, "status": "MODEL_VALIDATION_READINESS_AUDIT_ONLY",
        "total": len(ids), "input_receipts_gate_passed": sum(
            r["eligible_for_blinded_model_input"] for r in reports),
        "plan": plan, "reports": reports,
        "ready_for_independent_review": plan["validation_plan_design_complete"] and
            all(r["eligible_for_blinded_model_input"] for r in reports),
        "independent_scientific_acceptance": False, "model_trained": False,
        "out_of_time_validation_performed": False, "uncertainty_calibrated": False,
        "scientific_level_complete": False, "fda_predictions_published": False,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    bundle = json.loads(args.input.read_text(encoding="utf-8"))
    report = audit_bundle(bundle)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"total": report["total"],
                      "ready_for_independent_review": report["ready_for_independent_review"],
                      "scientific_level_complete": False}))
    return 0 if report["ready_for_independent_review"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
