"""CLI bridge from existing list exports to the priority prediction queue.

Usage:
 python -m scripts.export_priority_prediction_queue --input list_rows.json --output priority_queue.json

Input: JSON array of records with list_name, program_id and optional
classification/phase3_evidence_status; or object with a 'rows' array.
Read-only: does not change GEM JR/GEM/WT membership or preset associations.
"""
import argparse
import json
from pathlib import Path
from scripts.build_priority_prediction_queue import build_initial_queue


def run(input_path: str, output_path: str) -> dict:
    source = Path(input_path)
    data = json.loads(source.read_text(encoding="utf-8"))
    rows = data.get("rows") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("Expected JSON array of trial records or object with rows array")
    result = build_initial_queue(rows)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Existing trial-list JSON export")
    parser.add_argument("--output", required=True, help="Destination queue JSON")
    args = parser.parse_args()
    result = run(args.input, args.output)
    print(json.dumps({
        "unique_program_count": result["unique_program_count"],
        "phase3_results_released_count": result["phase3_results_released_count"],
        "skipped_rows": result["skipped_rows"],
        "trading_ready": result["trading_ready"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
