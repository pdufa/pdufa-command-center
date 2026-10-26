#!/usr/bin/env python3
"""Compare independently evidenced daily SCIENCE, OUTCOME, MAIN completion ratios.

Input: JSON objects with as_of (YYYY-MM-DD) and systems containing each system's
completed, total, and evidence_uri. A null measurement means NOT VERIFIED.
Never substitute a subjective maturity estimate or an accuracy claim.
"""
import argparse
import json
from datetime import date
from pathlib import Path

SYSTEMS = ("SCIENCE", "OUTCOME", "MAIN")


def validate(snapshot):
    if date.fromisoformat(snapshot["as_of"]).isoformat() != snapshot["as_of"]:
        raise ValueError("Snapshot dates must use YYYY-MM-DD")
    systems = snapshot["systems"]
    if set(systems) != set(SYSTEMS):
        raise ValueError("Snapshots require SCIENCE, OUTCOME, and MAIN")
    for name in SYSTEMS:
        row = systems[name]
        if row is None:
            continue
        if set(row) != {"completed", "total", "evidence_uri", "scope"}:
            raise ValueError(f"{name}: exact audited fields required")
        done, total = row["completed"], row["total"]
        if (type(done) is not int or type(total) is not int
                or total <= 0 or done < 0 or done > total):
            raise ValueError(f"{name}: invalid audited denominator")
        if not isinstance(row["evidence_uri"], str) or not row["evidence_uri"].startswith("https://"):
            raise ValueError(f"{name}: evidence URL required")
        if not isinstance(row["scope"], str) or not row["scope"].strip():
            raise ValueError(f"{name}: denominator scope required")
    return snapshot


def compare(previous, current):
    validate(previous)
    validate(current)
    if current["as_of"] <= previous["as_of"]:
        raise ValueError("Current snapshot must be later than previous snapshot")
    result = {"from": previous["as_of"], "to": current["as_of"], "systems": {}}
    for name in SYSTEMS:
        a, b = previous["systems"][name], current["systems"][name]
        if b is None:
            result["systems"][name] = {"status": "NOT_VERIFIED", "percent": None, "change_pp": None}
            continue
        percent = round(100 * b["completed"] / b["total"], 2)
        adjacent_days = (date.fromisoformat(current["as_of"]) - date.fromisoformat(previous["as_of"])).days == 1
        same_scope = adjacent_days and a is not None and a["scope"] == b["scope"] and a["total"] == b["total"]
        result["systems"][name] = {
            "status": "MEASURED" if same_scope else "BASELINE_ONLY",
            "percent": percent,
            "change_pp": round(percent - 100 * a["completed"] / a["total"], 2) if same_scope else None,
            "completed": b["completed"], "total": b["total"], "scope": b["scope"],
            "evidence_uri": b["evidence_uri"],
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(json.loads(args.previous.read_text()), json.loads(args.current.read_text())), indent=2))


if __name__ == "__main__":
    main()
