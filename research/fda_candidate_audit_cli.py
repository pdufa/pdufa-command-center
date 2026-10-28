"""Offline research-only audit CLI for independently sourced FDA candidate JSONL.

Usage: python -m research.fda_candidate_audit_cli candidates.jsonl
Input is not downloaded or trusted; each line must be a JSON object.
"""
import argparse
import json
from pathlib import Path
from research.fda_candidate_audit import audit_candidates


def load_jsonl(path):
    records = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"line {line_number} must be a JSON object")
            records.append(record)
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit FDA candidates; no training or trading")
    parser.add_argument("input_jsonl", help="Local JSONL of independently inspected candidate records")
    args = parser.parse_args(argv)
    report = audit_candidates(load_jsonl(args.input_jsonl))
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
