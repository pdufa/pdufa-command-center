#!/usr/bin/env python3
"""Report provisional 2026 PDUFA evidence without altering verified denominators.

The reconciliation ledger is the authority for cohort classification. Sidecar
research is never silently promoted to VERIFIED or counted as a new cycle.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "reports/2026-unrestricted-level1/2026-11-18/reconciled/30-lead-resolution.csv"
SIDECAR = ROOT / "data/2026-neladalkib-lead-076-reconciliation.csv"

def reconcile(ledger_rows, sidecar_rows):
    by_id = {row["record_id"]: row for row in ledger_rows}
    if len(by_id) != len(ledger_rows):
        raise ValueError("Duplicate record_id in authoritative ledger")
    result = []
    for row in sidecar_rows:
        lead = row["lead_id"]
        if lead not in by_id:
            raise ValueError(f"Unknown lead ID: {lead}")
        if row["cohort_status"] != "PROVISIONAL_MATCH_AWAITING_PRIMARY_APPLICATION_ID":
            raise ValueError(f"Unexpected sidecar classification for {lead}")
        if not row["application_id_source"].startswith("https://"):
            raise ValueError(f"Missing application-ID source for {lead}")
        base = by_id[lead]
        result.append({
            "lead_id": lead,
            "ledger_classification": base["classification"],
            "candidate_application_id": row["application_id"],
            "sidecar_status": row["cohort_status"],
            "promoted": False,
            "blocker": "Direct FDA application-ID source and authoritative ledger reconciliation required",
        })
    return result

def main():
    with LEDGER.open(newline="", encoding="utf-8") as f:
        ledger = list(csv.DictReader(f))
    with SIDECAR.open(newline="", encoding="utf-8") as f:
        sidecar = list(csv.DictReader(f))
    result = reconcile(ledger, sidecar)
    print(json.dumps({"ledger_leads": len(ledger), "provisional_sidecars": result,
                      "newly_verified_by_this_check": 0}, indent=2))

if __name__ == "__main__":
    main()
