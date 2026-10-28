"""Leakage-aware evaluation of independently adjudicated FDA review-cycle predictions.

Input is JSONL with one row per review cycle. This evaluator does NOT train a
model, certify FDA sources, or establish trading readiness. Rows require
independent adjudication upstream and a prediction timestamp strictly before
the decision. Predictions must be frozen before outcome revelation.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import date
import json
import math
from pathlib import Path


def evaluate(rows):
    accepted, excluded = [], defaultdict(int)
    seen = set()
    for row in rows:
        try:
            key = (row["application_id"], row["submission_id"], int(row["review_cycle"]))
            if key in seen:
                excluded["duplicate_review_cycle"] += 1
                continue
            seen.add(key)
            if row.get("independently_adjudicated") is not True:
                excluded["unverified_outcome"] += 1
                continue
            if row.get("prediction_frozen") is not True:
                excluded["unfrozen_prediction"] += 1
                continue
            prediction_date = date.fromisoformat(row["prediction_as_of"])
            decision_date = date.fromisoformat(row["decision_date"])
            if prediction_date >= decision_date:
                excluded["temporal_leakage"] += 1
                continue
            label = row["outcome"]
            probability = row["approval_probability"]
            if label not in {"PASS", "FAIL"} or type(probability) not in {int, float}:
                excluded["invalid_binary_prediction"] += 1
                continue
            p = float(probability)
            if not math.isfinite(p) or not 0 <= p <= 1:
                excluded["invalid_probability"] += 1
                continue
            accepted.append((p, int(label == "PASS")))
        except (KeyError, ValueError, TypeError, OverflowError):
            excluded["malformed_record"] += 1
    n = len(accepted)
    if not n:
        return {"status": "INSUFFICIENT_VERIFIED_HOLDOUT", "evaluated_cycles": 0,
                "excluded": dict(excluded), "metrics": None,
                "independently_validated": False, "trading_authorized": False}
    brier = sum((p-y)**2 for p,y in accepted)/n
    eps = 1e-15
    log_loss = -sum(y*math.log(max(eps, min(1-eps, p))) +
                    (1-y)*math.log(max(eps, min(1-eps, 1-p)))
                    for p,y in accepted)/n
    accuracy = sum((p >= .5) == bool(y) for p,y in accepted)/n
    return {"status": "DESCRIPTIVE_METRICS_ONLY", "evaluated_cycles": n,
            "excluded": dict(excluded), "metrics": {
                "brier_score": brier, "log_loss": log_loss, "threshold_0_5_accuracy": accuracy,
                "observed_approval_rate": sum(y for _,y in accepted)/n},
            "independently_validated": False, "trading_authorized": False,
            "warning": "Caller-supplied adjudication flags are not independently authenticated. "
                       "No baseline, cohort completeness, independence, or prospective validation is established."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions_jsonl", type=Path)
    args = parser.parse_args()
    with args.predictions_jsonl.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    print(json.dumps(evaluate(rows), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
