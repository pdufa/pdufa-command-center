#!/usr/bin/env python3
"""Validate historical L1 blind packets without exposing outcomes to scorers.

This validator is deliberately conservative: a retrospective assessment is
not a genuine prospective prediction, and source timestamps alone do not
prove that an assessor was outcome-blind.
"""
import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "reports/2026-unrestricted-level1/2026-11-18/reconciled"
INPUT = BASE / "BLIND-INPUT-PACKETS.csv"
FORBIDDEN = {"actual_outcome", "outcome_action_date", "assessment", "rationale",
             "source_url", "outcome_published_at", "action_alignment_status"}
REQUIRED = {"record_id", "application_id", "predecision_evidence_cutoff",
            "historical_source_urls", "source_publication_dates",
            "source_content_hashes", "independent_reviewer_prediction",
            "prediction_frozen_at", "blind_packet_status"}

def inspect_packet(row):
    missing = [x for x in ("predecision_evidence_cutoff", "historical_source_urls",
                           "source_publication_dates", "source_content_hashes")
               if not row.get(x, "").strip()]
    if missing:
        return "BLOCKED_MISSING_" + "_".join(missing).upper()
    try:
        cutoff = date.fromisoformat(row["predecision_evidence_cutoff"])
        published = [date.fromisoformat(s.strip()) for s in
                     row["source_publication_dates"].split(";") if s.strip()]
    except ValueError:
        return "BLOCKED_INVALID_SOURCE_DATE"
    urls = [s.strip() for s in row["historical_source_urls"].split(";") if s.strip()]
    hashes = [s.strip() for s in row["source_content_hashes"].split(";") if s.strip()]
    if not published or len(urls) != len(published) or len(urls) != len(hashes):
        return "BLOCKED_SOURCE_PROVENANCE_MISMATCH"
    if any(not u.startswith(("https://", "http://")) or any(c.isspace() for c in u)
           for u in urls):
        return "BLOCKED_INVALID_SOURCE_URL"
    if any(d > cutoff for d in published):
        return "BLOCKED_POSTCUTOFF_SOURCE"
    if any(len(h) != 64 or any(c not in "0123456789abcdefABCDEF" for c in h)
           for h in hashes):
        return "BLOCKED_INVALID_SOURCE_HASH"
    # Hashes are syntax-checked here, not verified against downloaded source bytes.
    return "SOURCE_PACKET_DATE_CHECK_PASSED_REQUIRES_INDEPENDENT_BLIND_REVIEW"

def main():
    with INPUT.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns = set(reader.fieldnames or [])
        if FORBIDDEN & columns:
            raise ValueError("Outcome leakage: " + ",".join(sorted(FORBIDDEN & columns)))
        if not REQUIRED <= columns:
            raise ValueError("Missing required fields: " + ",".join(sorted(REQUIRED - columns)))
        rows = list(reader)
    if len(rows) != 71 or len({r["record_id"] for r in rows}) != 71:
        raise ValueError("Expected 71 unique cycle packets")
    for row in rows:
        print(row["record_id"] + "," + inspect_packet(row))
    print("NOTE: no prediction accuracy is computed by this source-packet validator.")

if __name__ == "__main__":
    main()
