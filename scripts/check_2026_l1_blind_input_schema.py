#!/usr/bin/env python3
"""Fail-closed schema check for the outcome-masked 2026 L1 input manifest."""
import csv
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "data/backtest/blind_inputs/2026-l1-outcome-masked-179.csv"
ALLOWED = ["case_id","ticker","drug_or_event","original_pdufa_goal_date","indication","application_id","evidence_cutoff","clinical_evidence_packet","regulatory_evidence_packet"]
with P.open(newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    assert reader.fieldnames == ALLOWED, f"Unsafe columns: {reader.fieldnames}"
    rows = list(reader)
assert len(rows) == 179, f"Expected 179 rows, got {len(rows)}"
assert len({r["case_id"] for r in rows}) == 179
for row in rows:
    assert not any(row[k].startswith("2026-") for k in ("original_pdufa_goal_date", "evidence_cutoff")), "Unverified dates populated without source review"
print("PASS: 179 masked rows, no outcome/action-date fields; historical blindness NOT certified.")
