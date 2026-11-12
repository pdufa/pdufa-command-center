#!/usr/bin/env python3
"""Build a read-only, source-grounded Level 2 research worklist for saved FOCUS.

Uses the saved 2026-11-08 ClinicalTrials.gov field scan, NOT a live API
retrieval. Preserves original NCT/source links and separates registry-reported
facts from mechanistic hypotheses, adjudication, and FDA predictions.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
SCAN = ROOT / "new-platform/frontend/data/focus-29-registry-source-scan-20261108.json"
REPORTS = Path.home() / "PDUFA-Agent-Reports"
NCT_RE = re.compile(r"NCT[0-9]{8}\Z")
SCAN_KIND = "FOCUS_29_TRIAL_SOURCE_INSPECTION_NOT_VALIDATED_FDA_ASSESSMENT"
REQUIRED_TESTS = {
    "test-1": "registry_identity",
    "test-2": "registry_phase_status",
    "test-3": "registered_conditions_interventions_sponsor",
    "test-4": "registered_study_design",
    "test-5": "registered_primary_outcomes",
}
STUDY_QUESTIONS = (
    "What molecular target and pharmacologic mechanism are supported by original sources?",
    "Does human target-engagement evidence support the proposed mechanism in this indication?",
    "What is the link between the proposed mechanism and the registered primary endpoint?",
    "What competing biological explanations or study-design effects could account for an observed result?",
    "What result would contradict or falsify this mechanistic hypothesis?",
)


def _day(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Expected canonical YYYY-MM-DD")
    try:
        d = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid calendar day") from exc
    if d.isoformat() != value:
        raise ValueError("Invalid calendar date representation")
    return d


def build_source_research(roster: object, scan: object) -> dict:
    if not isinstance(roster, dict) or not isinstance(scan, dict):
        raise ValueError("Invalid source documents")
    if roster.get("schemaVersion") != 1 or scan.get("schemaVersion") != 1:
        raise ValueError("Unexpected source schema")
    if scan.get("kind") != SCAN_KIND or scan.get("status") != "ALL_REGISTRY_SOURCES_SCANNED":
        raise ValueError("Scan is not the expected registry-only inspection")
    roster_date = _day(roster.get("asOf"))
    scan_roster_date = _day(scan.get("rosterAsOf"))
    completed = scan.get("completedAt")
    if not isinstance(completed, str) or not completed.endswith("Z"):
        raise ValueError("Registry scan completion time missing")
    scan_day = _day(completed[:10])
    if scan_roster_date > roster_date or scan_day > roster_date:
        raise ValueError("Saved registry inspection is newer than frozen FOCUS cohort")
    rows = roster.get("records")
    observations = scan.get("rows")
    if not isinstance(rows, list) or not isinstance(observations, list):
        raise ValueError("Expected saved FOCUS roster and registry rows")
    if not 29 <= len(rows) <= 100 or len(observations) != 29:
        raise ValueError("Saved source scan must have 29 entries within bounded FOCUS roster")
    roster_index = {}
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("Malformed FOCUS entry")
        nct = item.get("nct")
        if not isinstance(nct, str) or not NCT_RE.fullmatch(nct) or nct in roster_index:
            raise ValueError("Invalid or duplicate FOCUS NCT")
        roster_index[nct] = item

    scan_summary = scan.get("summary")
    if (not isinstance(scan_summary, dict)
            or scan_summary.get("targetTrials") != 29
            or scan_summary.get("sourceScanned") != 29
            or scan_summary.get("independentlyCompletedScientificReviews") != 0
            or scan_summary.get("calibratedFDAForecasts") != 0):
        raise ValueError("Registry scan contains unexpected scientific-readiness claims")

    mapped = {}
    for row in observations:
        if not isinstance(row, dict):
            raise ValueError("Malformed registry observation")
        nct = row.get("nct")
        if not isinstance(nct, str) or nct not in roster_index or nct in mapped:
            raise ValueError("Unmatched or duplicate registry scan NCT")
        original = roster_index[nct]
        if row.get("ticker") != original.get("ticker") or row.get("company") != original.get("company"):
            raise ValueError("Saved registry scan does not match FOCUS company identity")
        url = "https://clinicaltrials.gov/study/" + nct
        if row.get("registrySourceUrl") != url or row.get("sourceStatus") != "SOURCE_SCANNED":
            raise ValueError("Registry scan lacks exact NCT source provenance")
        last_update = _day(row.get("registryLastUpdate"))
        if last_update > scan_day:
            raise ValueError("Registry source date after inspection")
        if (row.get("scientificAssessment") != "INSUFFICIENT_VERIFIED_EVIDENCE"
                or row.get("prediction") != "ABSTAIN"
                or row.get("certainty") != "NOT_VALIDATED"):
            raise ValueError("Unreviewed source must not be promoted to scientific conclusion")
        tests = row.get("tests")
        if not isinstance(tests, list) or len(tests) != 12:
            raise ValueError("Expected complete 12-item source inspection")
        by_key = {}
        for entry in tests:
            if not isinstance(entry, dict) or not isinstance(entry.get("key"), str):
                raise ValueError("Malformed registry source check")
            key = entry["key"]
            if key in by_key:
                raise ValueError("Duplicate registry check key")
            by_key[key] = entry
        if set(by_key) != {f"test-{i}" for i in range(1, 13)}:
            raise ValueError("Registry check inventory differs")
        fact_rows = []
        for key, tag in REQUIRED_TESTS.items():
            item = by_key[key]
            text = item.get("summary")
            if (item.get("state") != "SOURCE_FIELD_PRESENT"
                    or item.get("sourceUrl") != url
                    or not isinstance(text, str) or not 1 <= len(text) <= 2000):
                raise ValueError("Unusable registry field summary")
            fact_rows.append({
                "field": tag,
                "source_reported_text": text,
                "source_url": url,
                "registry_last_update": last_update.isoformat(),
                "captured_at_utc": completed,
                "status": "CAPTURED_REGISTRY_FIELD_REQUIRES_PRIMARY_SOURCE_RECHECK",
                "independently_verified": False,
            })
        mapped[nct] = {
            "nct": nct,
            "ticker": original["ticker"],
            "company": original["company"],
            "saved_registry_facts": fact_rows,
            "level2_research_questions": list(STUDY_QUESTIONS),
            "mechanism_of_action": None,
            "biological_target_validated": False,
            "independent_scientific_review": "NOT_COMPLETED",
            "phase_independently_verified": False,
            "source_documents_retrieved_in_this_run": 0,
            "hypothesis_adjudication": None,
            "fda_prediction": None,
            "approval_probability": None,
            "status": "SOURCE_REPORTED_CONTEXT_ONLY_HYPOTHESIS_RESEARCH_REQUIRED",
        }
    if not set(mapped).issubset(set(roster_index)):
        raise ValueError("Registry snapshot contains an unrelated FOCUS identity")
    return {
        "schema_version": 1,
        "kind": "LEVEL2_SOURCE_GROUNDED_HYPOTHESIS_RESEARCH_WORKLIST",
        "roster_as_of": roster_date.isoformat(),
        "registry_scan_as_of": scan_roster_date.isoformat(),
        "registry_scan_completed_at": completed,
        "trial_count": len(mapped),
        "current_saved_roster_count": len(roster_index),
        "unscanned_focus_trial_count": len(roster_index) - len(mapped),
        "saved_registry_facts": len(mapped) * len(REQUIRED_TESTS),
        "level2_scientific_assessments_completed": 0,
        "fda_predictions": 0,
        "data_source": "SAVED_CLINICALTRIALS_GOV_FIELD_INSPECTION",
        "live_registry_fetched": False,
        "study_records_retrieved_in_run": 0,
        "production_modified": False,
        "records": [mapped[r["nct"]] for r in rows if r["nct"] in mapped],
    }


def main() -> int:
    try:
        audit = subprocess.run(
            [sys.executable, "-B", "scripts/audit_raas_retirement.py", "--check"],
            cwd=ROOT, capture_output=True, text=True, errors="replace", timeout=240,
        )
        if audit.returncode != 0:
            print("STOP: Retired-system policy check failed")
            return 2
        for source in (ROSTER, SCAN):
            if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(ROOT.resolve()):
                raise ValueError("Saved source file is missing or unsafe")
        roster_bytes = ROSTER.read_bytes()
        scan_bytes = SCAN.read_bytes()
        report = build_source_research(
            json.loads(roster_bytes.decode("utf-8")),
            json.loads(scan_bytes.decode("utf-8")),
        )
        report["roster_sha256"] = hashlib.sha256(roster_bytes).hexdigest()
        report["saved_scan_sha256"] = hashlib.sha256(scan_bytes).hexdigest()
        report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        REPORTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = REPORTS / f"level2-registry-hypothesis-research-{stamp}.json"
        with output.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("PASS: Retirement safety audit")
        print("PASS: Exact FOCUS trials matched:", report["trial_count"])
        print("Registry-source field observations:", report["saved_registry_facts"])
        print("Independent Level 2 scientific assessments completed:", report["level2_scientific_assessments_completed"])
        print("FDA predictions generated:", report["fda_predictions"])
        print("Saved-source research report:", output)
        print("No live records fetched, scientific verdicts, repository edits or production changes")
        return 0
    except (OSError, ValueError, UnicodeError, TypeError, subprocess.TimeoutExpired) as exc:
        print("STOP: Level 2 source-grounded research failed:", type(exc).__name__, str(exc)[:180])
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
