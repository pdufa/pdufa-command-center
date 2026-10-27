"""Read-only census-wide NCT identity audit. Does not score or modify trials.

Usage: python scripts/trial_census_identity_audit.py path/to/trials.csv
Outputs a JSON summary to stdout. No network access or writes.
"""
from __future__ import annotations
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

NCT = re.compile(r"^NCT[0-9]{8}$")
COLUMNS = ("nct_id", "nctId", "nct", "trial_id", "trialId", "NCT ID", "NCT Number")

def audit_csv(path: str) -> dict:
    counts = Counter()
    seen = set()
    examples = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        column = next((name for name in COLUMNS if name in (reader.fieldnames or [])), None)
        if column is None:
            raise ValueError("No supported NCT identity column found")
        for row_number, row in enumerate(reader, start=2):
            counts["rows"] += 1
            value = (row.get(column) or "").strip()
            if not value:
                issue = "missing_nct"
            elif not NCT.fullmatch(value):
                issue = "invalid_nct"
            elif value in seen:
                issue = "duplicate_nct"
            else:
                seen.add(value)
                counts["unique_valid_nct"] += 1
                continue
            counts[issue] += 1
            if len(examples) < 20:
                examples.append({"row": row_number, "issue": issue})
    return {"input": str(path), "column": column, "counts": dict(counts), "issue_examples": examples,
            "scope": "identity_only", "scientific_analysis_complete": False, "trade_authorized": False}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/trial_census_identity_audit.py trials.csv")
    print(json.dumps(audit_csv(sys.argv[1]), indent=2, sort_keys=True))
