#!/usr/bin/env python3
"""Create an actionable source-gap queue for every unresolved 2026 PDUFA lead.

No guessed application numbers or PDUFA goals; source actions are not goals.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/2026-unrestricted-level1/2026-11-18/reconciled/30-lead-resolution.csv"
OUTPUT = ROOT / "reports/2026-unrestricted-level1/2026-11-18/reconciled/RESEARCH-QUEUE.csv"

def build(rows):
    result = []
    for row in rows:
        if row["classification"] != "UNRESOLVED":
            continue
        missing_id = not row["application_id"].strip()
        missing_goal = not row["verified_application_cycle_goal"].strip()
        if missing_id and missing_goal:
            priority, request = 1, "Find application identifier AND application-specific PDUFA goal"
        elif missing_id:
            priority, request = 1, "Find original NDA/BLA or STN tied to disclosed goal"
        elif missing_goal:
            priority, request = 2, "Find filing acceptance, amendment, or FDA review goal letter for exact application/supplement"
        else:
            priority, request = 3, "Recheck classification against primary evidence"
        result.append({
            "priority": priority,
            "lead_id": row["record_id"],
            "drug": row["drug"],
            "application_id": row["application_id"],
            "supplement": row["supplement"],
            "disclosed_current_goal": row["disclosed_current_goal"],
            "fda_action_date": row["action_date"],
            "missing_application_id": missing_id,
            "missing_verified_goal": missing_goal,
            "next_evidence_request": request,
            "existing_followup": row["next_action"],
            "source": row["evidence_url"],
            "classification": row["classification"],
        })
    return sorted(result, key=lambda x: (x["priority"], x["lead_id"]))

def main():
    with SOURCE.open(newline="", encoding="utf-8") as f:
        source = list(csv.DictReader(f))
    queue = build(source)
    if len(queue) != 30 or len({x["lead_id"] for x in queue}) != 30:
        raise ValueError("Expected exactly 30 distinct unresolved leads from the pinned checkpoint")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(queue[0]))
        writer.writeheader()
        writer.writerows(queue)
    print(json.dumps({"unresolved": len(queue), "missing_application_id": sum(x["missing_application_id"] for x in queue), "missing_verified_goal": sum(x["missing_verified_goal"] for x in queue), "queue": str(OUTPUT)}))

if __name__ == "__main__":
    main()
