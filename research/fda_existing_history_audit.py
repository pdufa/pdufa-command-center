"""Audit existing prediction-engine history without promoting legacy labels.

The legacy CSV contains model outcomes, not verified FDA review-cycle labels.
All imported rows remain research candidates until independently documented.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from research.fda_candidate_audit import audit_candidates


def audit_legacy_history(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    candidates = []
    periods = Counter()
    statuses = Counter()
    for row in rows:
        periods[row.get("validation_period") or "UNKNOWN"] += 1
        statuses[row.get("independence_status") or "UNKNOWN"] += 1
        # Do not infer action identity, FDA source, review cycle or chronology
        # from ticker, PDUFA date, outcome, or retrospective prediction.
        candidates.append({
            "source_cohort": "legacy_prediction_history_unverified",
            "action_type": "unverified",
            "original_filing_denominator_verified": False,
            "program_family_disjoint_verified": False,
        })
    report = audit_candidates(candidates)
    report["legacy_validation_period_counts"] = dict(sorted(periods.items()))
    report["legacy_independence_status_counts"] = dict(sorted(statuses.items()))
    report["source_type"] = "legacy_prediction_engine_history"
    report["legacy_predictions_validated_by_this_audit"] = False
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m research.fda_existing_history_audit data/prediction_engine_history.csv")
    print(json.dumps(audit_legacy_history(sys.argv[1]), indent=2, sort_keys=True))
