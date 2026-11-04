#!/usr/bin/env python3
"""Lossless read-only coverage audit of every NCT in the changing source pool.

IMPORTANT: a source-pool candidate is not a qualified Pipeline trial, nor does
its clinical registry status establish that an issuer has released Phase 3 data.
Never assume a missing RAAS metric is zero or import a pilot grade as an overall
RAAS score. The original 741-NCT dated reference is immutable; newer NCTs remain
in a separate evolving research cohort with explicit reconciliation differences.
"""
from __future__ import annotations
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PINNED = ROOT / "new-platform/frontend/public/phase3-census-2026-10-26.csv"
EVOLVING = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
READOUT = ROOT / "new-platform/frontend/public/phase3-public-readout-evidence-2026-11-01.json"
HISTORY = ROOT / "new-platform/frontend/data/raas-trial-score-history.json"
DEST = ROOT / "data/raas_population_coverage_audit.json"
HEADER = ["nct_id", "ticker", "company", "status", "source_url"]
NCT = re.compile(r"NCT\d{8}\Z")
TICKER = re.compile(r"[A-Z]{1,7}(?:[.-][A-Z]{1,3})?\Z")
STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION",
            "NOT_YET_RECRUITING", "COMPLETED", "TERMINATED", "WITHDRAWN", "UNKNOWN"}


def parse_census(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != HEADER:
            raise ValueError(f"Unexpected Phase 3 census schema: {path.name}")
        rows = list(reader)
    if not rows or len(rows) > 25000:
        raise ValueError("Missing/oversized source population")
    by_nct = {}
    for row in rows:
        nct = row.get("nct_id")
        if (not isinstance(nct, str) or not NCT.fullmatch(nct)
                or nct in by_nct or not TICKER.fullmatch(row.get("ticker") or "")
                or row.get("status") not in STATUSES
                or row.get("source_url") != "https://clinicaltrials.gov/study/" + nct
                or not (row.get("company") or "").strip()):
            raise ValueError("Invalid or duplicate source identity")
        by_nct[nct] = row
    return by_nct


def source_readouts(path: Path, original: dict) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data.get("schemaVersion") != 1 or data.get("censusDate") != "2026-10-26"
            or not isinstance(data.get("entries"), list)):
        raise ValueError("Unverified Phase 3 readout evidence feed")
    parsed = {}
    for entry in data["entries"]:
        nct = entry.get("nctId")
        if (nct not in original or nct in parsed
                or entry.get("ticker") != original[nct]["ticker"]
                or entry.get("kind") not in ("PRE_AS_OF_CHECK", "POST_PUBLIC_READOUT")
                or not str(entry.get("evidenceUrl", "")).startswith("https://")):
            raise ValueError("Unverified/cross-study public-readout classification")
        parsed[nct] = "TOP" if entry["kind"] == "PRE_AS_OF_CHECK" else "BOTTOM"
    return parsed


def source_grades(path: Path, readouts: dict) -> dict:
    ledger = json.loads(path.read_text(encoding="utf-8"))
    if (ledger.get("schemaVersion") != 1
            or ledger.get("scope") != "RAAS_TRIAL_SCORE_HISTORY"
            or not isinstance(ledger.get("records"), list)):
        raise ValueError("Invalid RAAS score history")
    grades = {}
    for event in ledger["records"]:
        if event.get("kind") != "METRIC_SCORE_UPDATED":
            continue
        nct = event.get("nctId")
        stage = "TOP" if event.get("stage") == "pre" else "BOTTOM"
        if (nct not in readouts
                or event.get("score") is not None
                or event.get("scoreKind") != "UNSCORED"
                or not isinstance(event.get("metricGrades"), list)):
            raise ValueError("Cross-trial or composite score in experimental ledger")
        if readouts[nct] != stage:
            # A TOP grade remains in the permanent ledger after a later BOTTOM
            # classification; only current-stage grades appear in this audit.
            continue
        for grade in event["metricGrades"]:
            metric_id = grade.get("metricId")
            score = grade.get("score")
            if metric_id != "pre-4-1" or score not in (0, 25, 50, 75, 100):
                raise ValueError("Unapproved numerical RAAS metric")
            key = (nct, metric_id)
            if key not in grades or event["recordedAt"] > grades[key]["recordedAt"]:
                grades[key] = {
                    "metricId": metric_id, "score": score, "scoreType": "EXPERIMENTAL_NOT_VALIDATED",
                    "ruleId": grade["ruleId"], "sourceUrl": grade["sourceUrl"],
                    "sourceDate": grade["sourceDate"], "recordedAt": event["recordedAt"]
                }
    return grades


def coverage_snapshot(original: dict, evolving: dict, readouts: dict, grades: dict) -> dict:
    if len(original) != 741:
        raise ValueError("Original dated historical census must remain 741 exact NCTs")
    original_ids, evolving_ids = set(original), set(evolving)
    added = sorted(evolving_ids-original_ids)
    removed = sorted(original_ids-evolving_ids)
    changed = sorted(nct for nct in original_ids & evolving_ids
                     if original[nct] != evolving[nct])
    def audit_population(rows: dict):
        output=[]
        for nct in sorted(rows):
            row=rows[nct]
            stage=readouts.get(nct, "UNVERIFIED")
            rating=grades.get((nct, "pre-4-1"))
            if stage != "TOP":
                rating = None
            output.append({
                "nctId": nct, "ticker": row["ticker"], "registryStatus": row["status"],
                "readoutStage": stage, "approvedOverallScore": None,
                "experimentalMetricGrades": [rating] if rating else [],
                "metricGradesAvailable": 1 if rating else 0,
                "metricGradesMissing": 29 if rating else (30 if stage != "UNVERIFIED" else None),
                "missingReason": "CLASSIFICATION_REQUIRED" if stage == "UNVERIFIED"
                    else (None if rating else "NO_ELIGIBLE_NUMERICAL_METRIC_INPUTS"),
                "pdufaQualified": None, "sourceUrl": row["source_url"]
            })
        return {
            "trials": len(output),
            "componentScored": sum(bool(r["experimentalMetricGrades"]) for r in output),
            "approvedOverallScored": 0,
            "top": sum(r["readoutStage"] == "TOP" for r in output),
            "bottom": sum(r["readoutStage"] == "BOTTOM" for r in output),
            "unverified": sum(r["readoutStage"] == "UNVERIFIED" for r in output),
            "records": output
        }
    a=audit_population(original);b=audit_population(evolving)
    digest=lambda d: hashlib.sha256(
        json.dumps(d, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schemaVersion": 1, "scope": "RAAS_SOURCE_POPULATION_COVERAGE_ONLY",
        "note": "Assessment coverage, NOT validated RAAS predictive ratings. Original 741-row study is immutable; evolving source is separate and not automatically Pipeline-qualified.",
        "sources": {
            "historical": str(PINNED.relative_to(ROOT)),
            "evolving": str(EVOLVING.relative_to(ROOT)),
            "readout": str(READOUT.relative_to(ROOT)),
            "history": str(HISTORY.relative_to(ROOT))
        },
        "historicalCensus": a, "evolvingResearch": b,
        "reconciliation": {
            "addedToEvolving": added, "missingFromEvolving": removed,
            "changedMetadata": changed,
            "preservedOriginalNctCount": len(original),
            "evolvingNctCount": len(evolving)
        },
        "fingerprint": digest([a, b])
    }


def main():
    original = parse_census(PINNED)
    evolving = parse_census(EVOLVING)
    readouts = source_readouts(READOUT, original)
    grades = source_grades(HISTORY, readouts)
    snapshot = coverage_snapshot(original, evolving, readouts, grades)
    text = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    if not DEST.exists() or DEST.read_text(encoding="utf-8") != text:
        DEST.write_text(text, encoding="utf-8")
    print("RAAS coverage: historical " + str(snapshot["historicalCensus"]["trials"])
          + ", evolving " + str(snapshot["evolvingResearch"]["trials"])
          + ", grade-bearing " + str(snapshot["historicalCensus"]["componentScored"])
          + ", approved overall 0; no cohort conflation.")


if __name__ == "__main__":
    main()
