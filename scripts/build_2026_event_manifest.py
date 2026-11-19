#!/usr/bin/env python3
"""Build a provisional 2026 PDUFA event manifest without inventing missing events.

Usage: python scripts/build_2026_event_manifest.py
       python scripts/build_2026_event_manifest.py --target 296

Input: 2026 clinical-evidence backlog and provisional source ledger.
Output: 2026-event-manifest-provisional.csv, one row per tracked event ID.
No output row is certified as a verified distinct FDA review cycle.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "data/backtest/2026-clinical-evidence-backlog.csv"
SOURCES = ROOT / "data/backtest/2026-provisional-source-research.csv"
OUTPUT = ROOT / "data/backtest/2026-event-manifest-provisional.csv"
FIELDS = ["event_id", "drug", "indication", "application_number", "review_cycle",
          "research_cutoff_date", "source_ledger_rows", "candidate_identity_status",
          "researcher_outcome_exposure", "canonical_event_key_status",
          "review_cycle_verification", "full_year_inclusion_status"]

def read(path):
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=296)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.target < 1:
        parser.error("--target must be positive")
    backlog = read(BACKLOG)
    sources = defaultdict(list)
    for row in read(SOURCES):
        sources[row["event_id"]].append(row)
    seen = set()
    output = []
    conflicts = 0
    for row in backlog:
        event_id = row["event_id"]
        if not event_id or event_id in seen:
            raise SystemExit(f"Duplicate/empty backlog event ID: {event_id!r}")
        seen.add(event_id)
        refs = sources.get(event_id, [])
        values = {}
        for field in ("drug", "indication", "application_number", "review_cycle", "cutoff_date"):
            unique = sorted({r[field].strip() for r in refs if r.get(field, "").strip()})
            values[field] = unique[0] if len(unique) == 1 else ""
            if len(unique) > 1:
                conflicts += 1
        output.append({
            "event_id": event_id,
            "drug": values["drug"],
            "indication": values["indication"],
            "application_number": values["application_number"],
            "review_cycle": values["review_cycle"],
            "research_cutoff_date": values["cutoff_date"],
            "source_ledger_rows": len(refs),
            "candidate_identity_status": row["identity_status"],
            "researcher_outcome_exposure": row["researcher_outcome_exposure"],
            "canonical_event_key_status": "NOT_VERIFIED",
            "review_cycle_verification": "CONFLICTING_PROVISIONAL_FIELDS" if any(
                len({r[f].strip() for r in refs if r.get(f, "").strip()}) > 1
                for f in ("drug", "indication", "application_number", "review_cycle", "cutoff_date")
            ) else "NOT_VERIFIED",
            "full_year_inclusion_status": "PROVISIONAL",
        })
    unknown = set(sources) - seen
    if unknown:
        raise SystemExit(f"Source ledger IDs missing from backlog: {sorted(unknown)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)
    print(f"Provisional tracked events: {len(output)}")
    print(f"With source ledger rows: {sum(bool(r['source_ledger_rows']) for r in output)}")
    print(f"Without source ledger rows: {sum(not r['source_ledger_rows'] for r in output)}")
    print(f"Conflicting provisional field groups: {conflicts}")
    print(f"Claimed target: {args.target} (unverified); arithmetic gap: {args.target - len(output)}")
    print("No fabricated events, certified review cycles, blind predictions, or outcomes.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
