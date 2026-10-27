"""Summarize announcement discoveries without treating them as adjudicated outcomes."""
import argparse
import json
from collections import Counter
from pathlib import Path


def summarize(document):
    rows = document.get("records", [])
    if not isinstance(rows, list):
        raise ValueError("records must be a list")
    categories = Counter()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid discovery record")
        category = ("EXTRAPOLATED_INDICATION_EXPANSION"
                    if row.get("review_status") == "INDICATION_EXPANSION_EXTRAPOLATED_EVIDENCE_ACTION_LETTER_REQUIRED"
                    else "ACTION_LETTER_AND_IDENTITY_REQUIRED")
        categories[category] += 1
    return {
        "discovered": len(rows),
        "categories": dict(sorted(categories.items())),
        "independently_verified": 0,
        "model_eligible": 0,
        "warning": "Discovery announcements cannot enter PASS/FAIL training or validation."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--discovery", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(json.loads(args.discovery.read_text(encoding="utf-8"))),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
