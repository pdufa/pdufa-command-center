"""Read-only Phase 3 evidence-field gate. No FDA outcome or trading prediction.

Usage: python scripts/phase3_evidence_gate.py data/all_phase_trials.csv
"""
import csv
import json
import sys
from collections import Counter

PHASES = {"PHASE3", "PHASE2|PHASE3"}
REQUIRED = ("drug", "indication", "primary_completion", "study_completion", "results_posted", "source_url")
EMPTY = {"", "NA", "N/A", "NULL", "NONE"}


def present(value):
    return (value or "").strip().upper() not in EMPTY


def audit(path):
    summary = Counter()
    missing = Counter()
    candidates = []
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not set(REQUIRED + ("nct_id", "phase")).issubset(reader.fieldnames or []):
            raise ValueError("Required trial columns absent")
        for row in reader:
            if row["phase"] not in PHASES:
                continue
            summary["phase3_or_2_3"] += 1
            absent = [field for field in REQUIRED if not present(row.get(field))]
            if present(row.get("source_url")) and not row["source_url"].startswith(("https://", "http://")):
                absent.append("source_url_invalid_scheme")
            for field in absent:
                missing[field] += 1
            if absent:
                summary["field_incomplete"] += 1
            else:
                summary["field_complete_candidates"] += 1
                candidates.append(row["nct_id"])
    return {
        "scope": "CSV_FIELD_PRESENCE_ONLY",
        "summary": dict(summary),
        "missing_by_field": dict(missing),
        "candidate_nct_ids": candidates,
        "source_verified": False,
        "scientific_ready": False,
        "model_validated": False,
        "trade_authorized": False,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/phase3_evidence_gate.py trials.csv")
    print(json.dumps(audit(sys.argv[1]), indent=2))
