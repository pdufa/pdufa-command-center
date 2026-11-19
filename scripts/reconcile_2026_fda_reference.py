#!/usr/bin/env python3
"""Reconcile the 2026 FDA novel-approval reference against independently sourced batches.

This is a *reference-only* quality gate. It never treats approval dates as PDUFA dates,
and never creates or scores historical predictions.
"""
import csv
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "data/2026-fda-novel-approvals-reference.csv"
BATCH = ROOT / "data/2026-fda-verified-indications-batch01.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def audit(reference, batch):
    issues = []
    index = {}
    for i, row in enumerate(reference, 2):
        name = row["drug_name"].strip().casefold()
        if not name:
            issues.append(f"reference line {i}: missing drug name")
        if name in index:
            issues.append(f"reference line {i}: duplicate drug {name}")
        index[name] = row
        if row["pdufa_date_verified"].lower() != "false":
            issues.append(f"reference line {i}: PDUFA date must remain unverified")
        if row["level1_prediction"].strip():
            issues.append(f"reference line {i}: reference cannot contain L1 predictions")
    for i, row in enumerate(batch, 2):
        name = row["drug_name"].strip().casefold()
        if name not in index:
            issues.append(f"batch line {i}: {name} absent from FDA reference")
            continue
        if row["approval_date"] != index[name]["approval_date"]:
            issues.append(f"batch line {i}: approval-date disagreement for {name}")
        if row["pdufa_date"].strip() or row["level1_prediction"].strip():
            issues.append(f"batch line {i}: unverified PDUFA/prediction field populated")
        if not row["active_ingredient"].strip() or not row["source_url"].startswith("https://www.fda.gov/"):
            issues.append(f"batch line {i}: missing ingredient or FDA source")
    return issues


def main():
    reference, batch = read_csv(REFERENCE), read_csv(BATCH)
    issues = audit(reference, batch)
    print(f"FDA novel approvals in reference: {len(reference)}")
    print(f"Indication evidence rows cross-checked: {len(batch)}")
    print("This is not the full-year PDUFA event count or L1 completion count.")
    for issue in issues:
        print(f"ERROR: {issue}", file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
