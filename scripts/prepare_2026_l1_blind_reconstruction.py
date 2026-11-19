#!/usr/bin/env python3
"""Prepare a leakage-controlled Level 1 historical blind backtest.

The existing assessments.csv is outcome-aware. It must NEVER be passed to a
predictor as a blind feature table. This script creates a manifest only; it
does not claim that a retrospective prediction has been made.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENTS = ROOT / "reports/2026-unrestricted-level1/2026-11-18/reconciled/assessments.csv"
OUTPUT = ROOT / "reports/2026-unrestricted-level1/2026-11-18/reconciled/BLIND-RECONSTRUCTION-QUEUE.csv"
FIELDS = [
    "record_id", "application_id", "review_cycle", "supplement", "drug",
    "pdufa_date", "outcome_action_date", "evidence_cutoff_at",
    "prediction_frozen_at", "latest_evidence_published_at",
    "prediction_kind", "assessment_kind", "blind_reconstruction_status",
    "required_evidence",
]

def queue_rows(rows):
    output = []
    for r in rows:
        if r["verification_status"] != "VERIFIED":
            continue
        action = r["outcome_action_date"].strip()
        cutoff = r["evidence_cutoff_at"].strip()
        frozen = r["prediction_frozen_at"].strip()
        published = r["latest_evidence_published_at"].strip()
        predecision = bool(action and cutoff and frozen and published
                           and cutoff[:10] < action[:10]
                           and frozen[:10] < action[:10]
                           and published[:10] <= cutoff[:10])
        # This queue does not establish blind eligibility even if the row has
        # timestamps; the source packet and its creation history need auditing.
        status = ("AUDIT_FROZEN_SOURCE_PACKET" if predecision else
                  "RECONSTRUCT_FROM_ARCHIVED_PREDECISION_SOURCES")
        output.append({
            "record_id": r["record_id"],
            "application_id": r["application_id"],
            "review_cycle": r["review_cycle"],
            "supplement": r["supplement"],
            "drug": r["drug"],
            "pdufa_date": r["pdufa_date"],
            "outcome_action_date": action,
            "evidence_cutoff_at": cutoff,
            "prediction_frozen_at": frozen,
            "latest_evidence_published_at": published,
            "prediction_kind": r["prediction_kind"],
            "assessment_kind": r["assessment_kind"],
            "blind_reconstruction_status": status,
            "required_evidence": (
                "Archived source publication timestamp, pre-cutoff content hash, "
                "trial endpoint/effect/safety before action, immutable prediction artifact, "
                "and independently held FDA outcome"
            ),
        })
    return output

def main():
    with ASSESSMENTS.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    queue = queue_rows(rows)
    if len(queue) != 71:
        raise ValueError(f"Expected 71 verified cycles, got {len(queue)}; re-audit cohort before export")
    if len({r["record_id"] for r in queue}) != len(queue):
        raise ValueError("Duplicate record IDs")
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(queue)
    print(json.dumps({"verified_cycles": len(queue),
                      "needs_source_reconstruction": sum(r["blind_reconstruction_status"].startswith("RECONSTRUCT") for r in queue),
                      "frozen_source_audit_required": sum(r["blind_reconstruction_status"].startswith("AUDIT") for r in queue),
                      "new_blind_predictions": 0,
                      "blind_accuracy": None}))

if __name__ == "__main__":
    main()
