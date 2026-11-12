#!/usr/bin/env python3
"""Report FOCUS specialist gate coverage; missing evidence is never a pass."""
import json
from pathlib import Path
from stage4_evidence_review_ledger import validate, ROSTER, LEDGER

GATES = ("phase_and_design", "efficacy", "safety", "statistics", "clinical_relevance", "regulatory", "manufacturing", "evidence_integrity")

def coverage(roster, ledger):
    validate(roster, ledger)
    trials = []
    total_verified = 0
    for record in roster["records"]:
        nct = record["nct"]
        statuses = {}
        for gate in GATES:
            matches = [entry for entry in ledger if entry["nct"] == nct and entry["category"] == gate]
            status = matches[0]["status"] if matches else "not_reviewed"
            statuses[gate] = status
            if status == "verified":
                total_verified += 1
        trials.append({"nct": nct, "ticker": record.get("ticker"), "gates": statuses,
                       "all_gates_verified": all(s == "verified" for s in statuses.values())})
    return {"trials": trials, "total_gates": 29 * len(GATES),
            "documented_verified_gates": total_verified,
            "trials_with_all_gates_verified": sum(t["all_gates_verified"] for t in trials),
            "note": "A documented review is not an independent scientific adjudication"}

if __name__ == "__main__":
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else []
    print(json.dumps(coverage(roster, ledger), indent=2))
