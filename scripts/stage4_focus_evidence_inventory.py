#!/usr/bin/env python3
"""Read-only FOCUS evidence inventory; URLs are leads, never verified evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"


def summarize(document):
    if not isinstance(document, dict) or not isinstance(document.get("records"), list):
        raise ValueError("FOCUS document must contain a records list")
    records = document["records"]
    if len(records) != 29:
        raise ValueError(f"Expected 29 FOCUS trials, got {len(records)}")
    seen = set()
    missing = []
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Record {i} must be an object")
        nct = record.get("nct")
        if not isinstance(nct, str) or not nct.startswith("NCT") or not nct[3:].isdigit():
            raise ValueError(f"Record {i} lacks valid NCT identifier")
        if nct in seen:
            raise ValueError(f"Duplicate NCT identifier: {nct}")
        seen.add(nct)
        absent = [field for field in ("resultsUrl", "regulatoryUrl") if not isinstance(record.get(field), str) or not record[field].startswith("https://")]
        if absent:
            missing.append({"nct": nct, "missing_source_links": absent})
    return {
        "focus_trials": len(records),
        "source_link_gaps": missing,
        "source_links_are_verified": False,
        "independent_trial_adjudications_verified": 0,
        "specialist_review_gates_verified": 0,
        "specialist_review_gates_total": 232,
        "status": "inventory_only_not_scientific_assessment"
    }


if __name__ == "__main__":
    print(json.dumps(summarize(json.loads(ROSTER.read_text(encoding="utf-8"))), indent=2))
