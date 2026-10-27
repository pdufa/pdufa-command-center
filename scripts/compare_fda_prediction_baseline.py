"""Temporal baseline comparison for FDA binary forecasts.

A baseline rate must come from independently verified review cycles whose FDA
decision dates precede EVERY holdout prediction timestamp. No model training,
source authentication, prospective validation, or trading authorization.
"""
from __future__ import annotations
from datetime import date
import math


def compare_to_prior_rate(training_rows, holdout_rows):
    """Return Brier skill vs strictly prior approval-rate baseline, or abstain."""
    try:
        train = []
        for row in training_rows:
            if row.get("independently_adjudicated") is not True:
                continue
            if row["outcome"] not in ("PASS", "FAIL"):
                continue
            train.append((date.fromisoformat(row["decision_date"]),
                          int(row["outcome"] == "PASS")))
        holdout = []
        keys = set()
        for row in holdout_rows:
            if row.get("independently_adjudicated") is not True or row.get("prediction_frozen") is not True:
                return _abstain("Unverified or unfrozen holdout")
            key = (row["application_id"], row["submission_id"], int(row["review_cycle"]))
            if key in keys:
                return _abstain("Duplicate holdout review cycle")
            keys.add(key)
            forecast_date = date.fromisoformat(row["prediction_as_of"])
            decision_date = date.fromisoformat(row["decision_date"])
            if forecast_date >= decision_date:
                return _abstain("Prediction is not earlier than decision")
            p = row["approval_probability"]
            if type(p) not in (float, int) or not math.isfinite(p) or not 0 <= p <= 1:
                return _abstain("Invalid probability")
            if row["outcome"] not in ("PASS", "FAIL"):
                return _abstain("Invalid outcome")
            holdout.append((forecast_date, float(p), int(row["outcome"] == "PASS")))
        if not train or not holdout:
            return _abstain("No eligible training or holdout decisions")
        first_prediction = min(row[0] for row in holdout)
        if any(decision_date >= first_prediction for decision_date, _ in train):
            return _abstain("Baseline training decision overlaps holdout prediction period")
        rate = sum(y for _, y in train) / len(train)
        model_brier = sum((p-y)**2 for _,p,y in holdout) / len(holdout)
        baseline_brier = sum((rate-y)**2 for _,_,y in holdout) / len(holdout)
        return {"status": "DESCRIPTIVE_BASELINE_COMPARISON", "training_cycles": len(train),
                "holdout_cycles": len(holdout), "prior_approval_rate": rate,
                "model_brier": model_brier, "baseline_brier": baseline_brier,
                "brier_skill": (1-model_brier/baseline_brier if baseline_brier > 0 else None),
                "independently_validated": False, "trading_authorized": False,
                "warning": "Caller-supplied verification is not independently authenticated; "
                           "review-cycle overlap across sets, cohort selection, and source provenance "
                           "require separate independent audit."}
    except (KeyError, ValueError, TypeError, OverflowError):
        return _abstain("Malformed row")


def _abstain(reason):
    return {"status": "INSUFFICIENT_VERIFIED_HOLDOUT", "reason": reason,
            "independently_validated": False, "trading_authorized": False}
