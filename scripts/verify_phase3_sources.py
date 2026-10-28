"""Bounded ClinicalTrials.gov v2 source verification of Phase 3 field-complete candidates.

Run: python scripts/verify_phase3_sources.py data/all_phase_trials.csv --limit 10
Read-only. Never assigns efficacy, FDA approval, or trading scores.
"""
import argparse
import csv
import json
import time
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://clinicaltrials.gov/api/v2/studies/"
REQUIRED = ("drug", "indication", "primary_completion", "study_completion", "results_posted", "source_url")
EMPTY = {"", "NA", "N/A", "NULL", "NONE"}


def present(value):
    return (value or "").strip().upper() not in EMPTY


def candidates(path):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            if row.get("phase") not in {"PHASE3", "PHASE2|PHASE3"}:
                continue
            if all(present(row.get(field)) for field in REQUIRED) and row["source_url"].startswith(("http://", "https://")):
                yield row


def verify(row):
    nct = row["nct_id"]
    request = Request(BASE + nct, headers={"Accept": "application/json", "User-Agent": "PDUFA-research-audit/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            study = json.load(response)
    except HTTPError as exc:
        return {"nct_id": nct, "status": "NOT_FOUND" if exc.code == 404 else "HTTP_ERROR", "http_status": exc.code}
    except (URLError, TimeoutError, ValueError) as exc:
        return {"nct_id": nct, "status": "FETCH_ERROR", "error_type": type(exc).__name__}
    protocol = study.get("protocolSection", {})
    reported = protocol.get("identificationModule", {}).get("nctId")
    if reported != nct:
        return {"nct_id": nct, "status": "IDENTIFIER_MISMATCH"}
    status = protocol.get("statusModule", {})
    outcomes = protocol.get("outcomesModule", {})
    result = study.get("resultsSection") or {}
    return {
        "nct_id": nct,
        "status": "SOURCE_FOUND",
        "registry_overall_status": status.get("overallStatus"),
        "registry_primary_outcomes_listed": len(outcomes.get("primaryOutcomes") or []),
        "registry_results_section_present": bool(result),
        "registry_results_primary_outcomes": len((result.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []),
        "registry_last_update_posted": (status.get("studyFirstPostDateStruct") or {}).get("date"),
        "scientific_ready": False,
        "trade_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")
    results = []
    for row in candidates(args.csv_path):
        if len(results) >= args.limit:
            break
        results.append(verify(row))
        time.sleep(max(args.delay, 0.25))
    print(json.dumps({"source": "ClinicalTrials.gov API v2", "scope": "bounded registry source presence", "counts": dict(Counter(r["status"] for r in results)), "records": results, "scientific_ready": False, "trade_authorized": False}, indent=2))


if __name__ == "__main__":
    main()
