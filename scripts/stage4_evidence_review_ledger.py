#!/usr/bin/env python3
"""Validate human-reviewed Stage 4 evidence decisions without inventing verification."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
LEDGER = ROOT / "research/focus/stage4-evidence-review.json"

def validate(roster, ledger):
    records = roster.get("records")
    if not isinstance(records, list) or len(records) != 29:
        raise ValueError("Expected canonical 29-trial FOCUS roster")
    ncts = {r.get("nct") for r in records}
    if len(ncts) != 29:
        raise ValueError("Duplicate or missing roster NCT")
    if not isinstance(ledger, list):
        raise ValueError("Review ledger must be a list")
    seen = set()
    verified = 0
    for item in ledger:
        if not isinstance(item, dict) or item.get("nct") not in ncts:
            raise ValueError("Ledger entry must reference a FOCUS trial")
        key = (item["nct"], item.get("category"))
        if not isinstance(key[1], str) or not key[1].strip() or key in seen:
            raise ValueError("Category must be nonempty and unique per trial")
        seen.add(key)
        status = item.get("status")
        if status not in ("pending", "verified", "rejected"):
            raise ValueError("Review status must be pending, verified, or rejected")
        if status == "verified":
            for field in ("source_url", "reviewer", "reviewed_at_utc", "evidence_excerpt", "source_accessed_at_utc"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError(f"Verified review requires {field}")
            if not item["source_url"].startswith("https://"):
                raise ValueError("Verified review requires HTTPS source")
            verified += 1
    return {"focus_trials": 29, "ledger_entries": len(ledger), "documented_verifications": verified,
            "note": "Metadata completeness does not independently establish scientific validity"}

def main():
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    print(json.dumps(validate(roster, ledger), indent=2))

if __name__ == "__main__":
    main()
