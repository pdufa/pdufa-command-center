"""Offline operator queue from six-case FDA locator triage.

This is a deterministic work queue, not a source acquisition or adjudication.
"""
import argparse
import csv
from pathlib import Path

from research.official_locator_triage import build_locator_triage

COLUMNS = (
    "priority", "case_id", "application_id", "claimed_review_cycle_id",
    "document_id", "family", "locator_status", "reason", "official_source_route",
    "source_lead", "operator_next_action", "original_bytes_acquired",
    "publication_clock_verified", "independently_verified",
)


def build_operator_queue(triage=None):
    triage = build_locator_triage() if triage is None else triage
    rows = []
    for row in triage["rows"]:
        priority = 1 if row["locator_status"] == "KNOWN_LEAD_NOT_AUTHENTICATED" else (
            2 if row["locator_status"] == "DERIVED_LEAD_NOT_AUTHENTICATED" else 3)
        rows.append({"priority": priority, **{key: row[key] for key in COLUMNS if key != "priority"}})
    rows.sort(key=lambda row: (row["priority"], row["case_id"], row["document_id"]))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    rows = build_operator_queue()
    with args.output.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
