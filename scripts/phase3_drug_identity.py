#!/usr/bin/env python3
"""Conservative company/drug identity reconciliation for Phase 3 result records.

A trial intervention string is not proof of a unique investigational product.
Only single-agent candidates get provisional IDs; uncertain combinations/aliases
are retained as review candidates, not silently counted as verified drugs.
"""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
CONTROL = re.compile(r"^(placebo|saline|vehicle|sham|observation|no intervention|standard of care|best supportive care|usual care)(?:\b|$)", re.I)
DOSE = re.compile(r"\s+\d+(?:\.\d+)?\s*(?:mg|mcg|ug|µg|g|ml|iu)(?:\s*/\s*(?:kg|m2|m\^2|day|week))?\b.*$", re.I)
COLS = ["ticker", "company", "candidate_drug_name", "identity_status",
        "phase3_trial_count", "indications", "nct_ids", "source_urls",
        "first_result_date", "last_result_date", "notes"]

def normalize(value):
    return " ".join(str(value or "").strip().lower().split())

def candidate(value):
    value = normalize(value)
    value = re.sub(r"^(?:open[- ]label|blinded|part \d+ blinded|experimental)\s*[-:]\s*", "", value)
    value = DOSE.sub("", value)
    return value.strip()

def main():
    with (DATA / "phase3_announcements.csv").open(newline="", encoding="utf-8") as handle:
        source = list(csv.DictReader(handle))
    groups = {}
    for row in source:
        ticker = normalize(row.get("ticker")).upper()
        parts = re.split(r"\s+\|\s+", row.get("drug", ""))
        for raw in parts:
            name = candidate(raw)
            if not ticker or not name or CONTROL.match(name):
                continue
            key = (ticker, name)
            group = groups.setdefault(key, {"ticker": ticker, "company": row.get("company", ""),
                "candidate_drug_name": name, "ncts": set(), "indications": set(),
                "sources": set(), "dates": set(), "multi": False, "nonregistry": False})
            group["multi"] |= len(parts) > 1
            group["nonregistry"] |= not bool(row.get("nct_id"))
            if row.get("nct_id"): group["ncts"].add(row["nct_id"])
            if row.get("indication"): group["indications"].add(row["indication"])
            if row.get("phase3_results_source"): group["sources"].add(row["phase3_results_source"])
            if row.get("phase3_results_posted_at"): group["dates"].add(row["phase3_results_posted_at"])
    records = []
    for group in groups.values():
        multi = group["multi"]
        records.append({"ticker": group["ticker"], "company": group["company"],
            "candidate_drug_name": group["candidate_drug_name"],
            "identity_status": "REVIEW_MULTI_ARM_OR_ALIAS" if multi else "PROVISIONAL_SINGLE_INTERVENTION",
            "phase3_trial_count": len(group["ncts"]), "indications": " | ".join(sorted(group["indications"])),
            "nct_ids": " | ".join(sorted(group["ncts"])), "source_urls": " | ".join(sorted(group["sources"])),
            "first_result_date": min(group["dates"]) if group["dates"] else "",
            "last_result_date": max(group["dates"]) if group["dates"] else "",
            "notes": "Not an independently verified unique active drug; requires alias, arm and regimen review."})
    records.sort(key=lambda r: (r["ticker"], r["candidate_drug_name"]))
    output = DATA / "phase3_drug_identity_review.csv"
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLS)
        writer.writeheader()
        writer.writerows(records)
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(),
        "phase3_result_records": len(source), "candidate_company_intervention_names": len(records),
        "provisional_single_intervention_candidates": sum(r["identity_status"] == "PROVISIONAL_SINGLE_INTERVENTION" for r in records),
        "multi_arm_or_alias_review_candidates": sum(r["identity_status"] == "REVIEW_MULTI_ARM_OR_ALIAS" for r in records),
        "verified_unique_drug_count": None,
        "reason": "ClinicalTrials.gov intervention names do not establish unique active substances or resolve aliases, regimens, dose variants and controls."}
    (DATA / "phase3_drug_identity_status.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
