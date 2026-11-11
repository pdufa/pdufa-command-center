#!/usr/bin/env python3
"""Fetch ClinicalTrials.gov API v2 primary-source metadata for the 29 FOCUS NCTs.

Read-only. Registry data is not independently adjudicated and does not imply FDA approval.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
API = "https://clinicaltrials.gov/api/v2/studies/"
NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")


def fetch_study(nct, opener=urlopen, sleeper=time.sleep):
    if not isinstance(nct, str) or not NCT_PATTERN.fullmatch(nct):
        raise ValueError("Invalid NCT identifier")
    request = Request(API + nct, headers={"Accept": "application/json", "User-Agent": "pdufa-focus-evidence-inventory/1.0"})
    for attempt in range(3):
        try:
            with opener(request, timeout=20) as response:
                study = json.load(response)
            break
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        sleeper(2 ** attempt)
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    if identification.get("nctId") != nct:
        raise ValueError("ClinicalTrials.gov identifier mismatch")
    design = protocol.get("designModule", {})
    status = protocol.get("statusModule", {})
    outcomes = protocol.get("outcomesModule") or {}
    primary_outcomes = outcomes.get("primaryOutcomes") or []
    results = study.get("resultsSection") or {}
    outcome_results = (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
    if not isinstance(primary_outcomes, list) or not isinstance(outcome_results, list):
        raise ValueError("Unexpected registry outcome structure")
    return {
        "nct": nct,
        "source_url": API + nct,
        "phase": design.get("phases", []),
        "overall_status": status.get("overallStatus"),
        "primary_completion_date": status.get("primaryCompletionDateStruct", {}).get("date"),
        # A public resultsSection establishes posted results, not submission timing.
        "results_posted": bool(study.get("resultsSection")),
        "results_submitted": bool(study.get("resultsSection")),  # legacy compatibility only
        "registered_primary_outcomes": [
            {"measure": item.get("measure"), "time_frame": item.get("timeFrame")}
            for item in primary_outcomes if isinstance(item, dict)
        ],
        "posted_outcome_measures_count": len(outcome_results),
        "posted_primary_outcomes": [
            {"title": item.get("title"), "description": item.get("description"),
             "time_frame": item.get("timeFrame")}
            for item in outcome_results
            if isinstance(item, dict) and item.get("type") == "PRIMARY"
        ],
        "posted_primary_outcome_count": sum(
            1 for item in outcome_results
            if isinstance(item, dict) and item.get("type") == "PRIMARY"
        ),
        "endpoint_review_status": "requires_independent_review",
        "scientifically_verified": False,
        "fda_outcome_verified": False,
        "prediction": None,
    }


def collect(document, fetcher=fetch_study):
    records = document.get("records") if isinstance(document, dict) else None
    if not isinstance(records, list) or len(records) != 29:
        raise ValueError("Expected 29 FOCUS records")
    seen = set()
    output = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid FOCUS record")
        nct = record.get("nct")
        if not isinstance(nct, str) or not NCT_PATTERN.fullmatch(nct) or nct in seen:
            raise ValueError("Invalid or duplicate NCT")
        seen.add(nct)
        try:
            output.append({"status": "retrieved", **fetcher(nct)})
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
            output.append({"nct": nct, "status": "retrieval_failed", "error_type": type(exc).__name__,
                           "scientifically_verified": False, "prediction": None})
    return {"status": "primary_source_metadata_only", "trials": output, "scientific_adjudications": 0}


def main():
    document = json.loads(ROSTER.read_text(encoding="utf-8"))
    print(json.dumps(collect(document), indent=2))


if __name__ == "__main__":
    main()
