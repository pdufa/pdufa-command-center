#!/usr/bin/env python3
"""Auditable small RAAS source-evidence receipt for large registry evidence files.

The receipt separates a missing Neon mirror record from a missing public registry
record. Neither registry results nor statistical analyses are RAAS metric grades.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
GAPS = ROOT / "data/raas_registry_missing_backfill.json"
SOURCE = ROOT / "data/raas_registry_live_evidence.json"
DEST = ROOT / "data/raas_registry_evidence_summary.json"

def build_summary(data: dict, gap_report: dict, cohort_ids: set[str]) -> dict:
    if data.get("scope") != "RAAS_CT_GOV_LIVE_EVIDENCE" or data.get("schemaVersion") != 1:
        raise ValueError("Registry evidence scope incorrect")
    if gap_report.get("scope") != "RAAS_MISSING_REGISTRY_BACKFILL":
        raise ValueError("Registry mirror gap scope incorrect")
    records = data.get("records")
    if not isinstance(records, list):
        raise ValueError("Registry evidence entries absent")
    record_ids = [r.get("nctId") for r in records]
    if len(set(record_ids)) != len(record_ids) or not set(record_ids).issubset(cohort_ids):
        raise ValueError("Registry evidence duplicate or outside cohort")
    baseline_missing = {item.get("nctId") for item in gap_report.get("missing", [])}
    if not baseline_missing.issubset(cohort_ids):
        raise ValueError("Baseline mirror gap outside research cohort")
    stored = {r["nctId"] for r in records if r.get("sourceSha256")}
    errors = data.get("errors", [])
    if not isinstance(errors, list):
        raise ValueError("Invalid source error list")
    posted = sum(r.get("hasPostedResults") is True for r in records)
    outcome_analyses = sum(any(
        isinstance(x, dict) and any(
            isinstance(a, dict) and bool(a.get("pValue"))
            for a in (x.get("analyses") or []))
        for x in r.get("primaryPostedEvidence", []))
        for r in records)
    result = {
        "schemaVersion": 1,
        "scope": "RAAS_PUBLIC_REGISTRY_EVIDENCE_RECONCILIATION",
        "cohort": data.get("cohort"),
        "source": "ClinicalTrials.gov API v2 / verified exact NCT",
        "lastSourceAttempt": data.get("latestAttemptAt"),
        "researchTrials": len(cohort_ids),
        "recordsStored": len(stored),
        "postedRegistryResults": posted,
        "registeredPrimaryEndpointRecords": sum(
            bool(r.get("registeredPrimaryOutcomes")) for r in records),
        "primaryResultsWithReportedPValues": outcome_analyses,
        "noStoredRegistryEvidence": len(cohort_ids - stored),
        "baselineNeonMirrorMissing": len(baseline_missing),
        "baselineMirrorGapsWithPublicEvidence": len(baseline_missing & stored),
        "baselineMirrorGapsStillWithoutPublicEvidence": sorted(baseline_missing - stored),
        "sourceErrorsThisRun": len(errors),
        "sourceErrorNctsThisRun": sorted({x.get("nctId") for x in errors if x.get("nctId")}),
        "approvedOverallRaasScores": 0,
        "interpretation": "Evidence collection only: a registry entry is not a published Phase 3 readout, a posted result is not a verified PDUFA event, and a clinical p-value is not a validated 0–100 RAAS rating."
    }
    if data.get("summary", {}).get("researchTrials") != result["researchTrials"]:
        raise ValueError("Source report research population mismatch")
    if data.get("summary", {}).get("registrySourceRecordsStored") != result["recordsStored"]:
        raise ValueError("Source report stored-record count mismatch")
    if data.get("summary", {}).get("completeRaasScores") != 0:
        raise ValueError("Unexpected completed RAAS scores")
    if any(r.get("overallRaasScore") is not None for r in records):
        raise ValueError("Unexpected RAAS score on source evidence")
    return result

def main():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    gaps = json.loads(GAPS.read_text(encoding="utf-8"))
    with COHORT.open(newline="", encoding="utf-8-sig") as stream:
        cohort = {row["nct_id"] for row in csv.DictReader(stream)}
    summary = build_summary(data, gaps, cohort)
    DEST.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in summary.items() if not isinstance(v, list)}, sort_keys=True))

if __name__ == "__main__":
    main()
