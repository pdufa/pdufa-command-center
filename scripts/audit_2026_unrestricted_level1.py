#!/usr/bin/env python3
"""Audit an unrestricted 2026 Level-1 FDA event cohort. No fabricated predictions."""
import argparse, csv, json
from collections import Counter
from datetime import date, datetime
from pathlib import Path

REQUIRED = ("application_id", "review_cycle", "indication", "pdufa_date",
            "prediction", "prediction_frozen_at", "evidence_cutoff_at",
            "actual_outcome", "outcome_published_at", "source_url")
YES = {"APPROVAL", "CRL"}
def timestamp(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date() if s else None

def audit(path, asof, expected):
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = sorted(set(REQUIRED) - set(reader.fieldnames or []))
        if missing:
            raise ValueError("Missing columns: " + ", ".join(missing))
        rows = list(reader)
    issues, seen = [], set()
    historical = prospective = correct = incorrect = 0
    for index, r in enumerate(rows, 2):
        key = tuple(r[k].strip().upper() for k in ("application_id", "review_cycle", "indication"))
        if not all(key) or key in seen:
            issues.append({"row": index, "issue": "missing or duplicate event identity"})
        seen.add(key)
        try:
            due = date.fromisoformat(r["pdufa_date"])
            frozen = timestamp(r["prediction_frozen_at"])
            cutoff = timestamp(r["evidence_cutoff_at"])
            published = timestamp(r["outcome_published_at"])
        except ValueError:
            issues.append({"row": index, "issue": "invalid date"})
            continue
        if due.year != 2026:
            issues.append({"row": index, "issue": "outside 2026"})
        if not r["source_url"].strip():
            issues.append({"row": index, "issue": "missing outcome/evidence source"})
        if due <= asof:
            historical += 1
            # Point-in-time frozen records only; retrospectively reconstructed
            # predictions are not certified blind.
            if not frozen or not cutoff or frozen > due or cutoff > frozen or (published and frozen >= published):
                issues.append({"row": index, "issue": "no verifiable pre-outcome freeze"})
                continue
            if r["prediction"] not in YES or r["actual_outcome"] not in YES or not published:
                issues.append({"row": index, "issue": "prediction/outcome missing or unsupported"})
                continue
            if r["prediction"] == r["actual_outcome"]:
                correct += 1
            else:
                incorrect += 1
        else:
            prospective += 1
    if len(rows) != expected:
        issues.append({"issue": "cohort count mismatch", "expected": expected, "actual": len(rows)})
    eligible = correct + incorrect
    return {"as_of": asof.isoformat(), "target": expected, "rows": len(rows),
            "historical": historical, "future": prospective, "correct": correct,
            "incorrect": incorrect, "verified_comparisons": eligible,
            "accuracy_pct": round(100 * correct / eligible, 2) if eligible else None,
            "issues": issues, "complete": not issues}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--as-of", default="2026-11-18")
    parser.add_argument("--expected", type=int, default=196)
    args = parser.parse_args()
    print(json.dumps(audit(args.csv, date.fromisoformat(args.as_of), args.expected), indent=2))
