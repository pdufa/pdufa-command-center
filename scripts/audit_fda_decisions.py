"""Import sourced FDA decision events from JSONL or CSV into an auditable review report.

This is a *staging* validator, not a scraper and not a historical data corpus.
Rows need exact application_id/submission_id/review_cycle, action, decision_date,
source_url, evidence_as_of (publication availability), and retrieved_on. Missing
identities or dates remain quarantined. None of these fields proves source truth.
Use: python scripts/audit_fda_decisions.py input.jsonl --as-of 2026-10-27
No files or database rows are modified.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

from fda_decision_taxonomy import classify_decision, deduplicate_applications


def load_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        if path.suffix.lower() == ".csv":
            yield from csv.DictReader(stream)
        elif path.suffix.lower() in {".jsonl", ".ndjson"}:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                item = json.loads(line)
                if not isinstance(item, dict):
                    raise ValueError(f"Line {line_number}: expected JSON object")
                yield item
        else:
            raise ValueError("Input must be .csv, .jsonl, or .ndjson")


def audit(rows, *, as_of):
    events = list(rows)
    counts = {}
    for row in events:
        status = classify_decision(row, as_of=as_of)["status"]
        counts[status] = counts.get(status, 0) + 1
    deduped = deduplicate_applications(events, as_of=as_of)
    return {
        "audit": "historical_fda_decision_ingestion",
        "as_of": as_of,
        "input_events": len(events),
        "classification_counts": dict(sorted(counts.items())),
        "application_counts": deduped["counts"],
        "conflicting_applications": deduped["conflicting_applications"],
        "conflicting_review_cycles": deduped["conflicting_review_cycles"],
        "candidate_review_cycles": deduped["candidates"],
        "excluded_observations": deduped["excluded"],
        "independently_verified_pass_count": 0,
        "independently_verified_fail_count": 0,
        "model_eligible_records": 0,
        "complete_application_denominator_verified": False,
        "source_content_verified": False,
        "independent_backtest_complete": False,
        "prediction_model_validated": False,
        "warning": "A URL field is not proof the FDA source supports the event. Source documents and application identity require separate verification.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--as-of", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(audit(load_rows(args.input), as_of=args.as_of), indent=2, sort_keys=True))
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"AUDIT_FAILED: {error}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
