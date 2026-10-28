"""Prioritize legacy historical events for independent FDA verification.

This is a triage queue, not a validation cohort or outcome predictor.
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

PRIORITY = {
    "2025_EXTERNAL_BLIND": 0,
    "2024_FROZEN_PREDECISION_TUNE": 1,
    "2026_AUDIT_REPAIR_FROZEN_MODEL": 2,
}


def build_verification_queue(path):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    queue = []
    for row in rows:
        queue.append({
            "event_key": row.get("event_key", ""),
            "ticker": row.get("ticker", ""),
            "pdufa_date": row.get("pdufa_date", ""),
            "validation_period": row.get("validation_period", ""),
            "independence_status": row.get("independence_status", ""),
            "verification_status": "REQUIRES_INDEPENDENT_FDA_ACTION_EVIDENCE",
            "legacy_notes_quarantined": True,
            "prediction_input_eligibility": "BLOCKED_PENDING_PREDECISION_EVIDENCE_AUDIT",
            "requirements": [
                "FDA original action document and application identifier",
                "FDA review cycle and actual action date",
                "evidence availability before prediction cutoff",
                "program-family independence and sampling denominator",
            ],
            "trading_authorized": False,
        })
    queue.sort(key=lambda r: (PRIORITY.get(r["validation_period"], 9), r["pdufa_date"], r["event_key"]))
    return {
        "total_records": len(queue),
        "priority_period_counts": dict(sorted(Counter(x["validation_period"] for x in queue).items())),
        "queue": queue,
        "research_only": True,
        "validated_training_cohort": False,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m research.fda_verification_queue data/prediction_engine_history.csv")
    print(json.dumps(build_verification_queue(sys.argv[1]), indent=2))
