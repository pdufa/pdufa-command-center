"""Read-only verification of completed Phase 3 trials lacking a results-posted date.

Usage:
  python scripts/verify_phase3_missing_results.py --input data/all_phase_trials.csv --output /tmp/phase3-results-audit.csv
No production database writes. Supports restart by retaining prior output.
"""
import argparse
import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API = "https://clinicaltrials.gov/api/v2/studies/"
NCT = re.compile(r"^NCT[0-9]{8}$")
FIELDS = ["nct_id", "ticker", "local_status", "local_study_completion",
          "local_source_updated", "registry_status", "registry_results_posted",
          "has_results", "outcome_measures", "statistical_analyses",
          "reported_p_values", "registry_last_updated", "classification",
          "checked_at_utc", "error"]


def verify(row):
    nct = row["nct_id"].strip()
    result = dict.fromkeys(FIELDS, "")
    result.update(nct_id=nct, ticker=row["ticker"], local_status=row["status"],
                  local_study_completion=row["study_completion"],
                  local_source_updated=row["source_updated"],
                  checked_at_utc=datetime.now(timezone.utc).isoformat())
    if not NCT.fullmatch(nct):
        result["classification"] = "INVALID_NCT_ID"
        return result
    try:
        req = Request(API + nct, headers={"User-Agent": "PDUFA-readonly-evidence-audit/1.0",
                                         "Accept": "application/json"})
        with urlopen(req, timeout=25) as response:
            study = json.load(response)
        protocol = study.get("protocolSection") or {}
        status = protocol.get("statusModule") or {}
        results = study.get("resultsSection") or {}
        outcomes = (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
        analyses = [a for outcome in outcomes for a in (outcome.get("analyses") or [])]
        result.update(
            registry_status=status.get("overallStatus", ""),
            registry_results_posted=(status.get("resultsFirstPostDateStruct") or {}).get("date", ""),
            has_results=str(study.get("hasResults", False)).lower(),
            outcome_measures=str(len(outcomes)),
            statistical_analyses=str(len(analyses)),
            reported_p_values=str(sum(a.get("pValue") not in (None, "") for a in analyses)),
            registry_last_updated=(status.get("lastUpdatePostDateStruct") or {}).get("date", ""),
        )
        result["classification"] = ("RESULTS_POSTED" if study.get("hasResults")
                                    else "NO_REGISTRY_RESULTS_POSTED")
    except HTTPError as exc:
        result["classification"] = "NOT_FOUND" if exc.code == 404 else "FETCH_ERROR"
        result["error"] = "HTTP " + str(exc.code)
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        result["classification"] = "FETCH_ERROR"
        result["error"] = type(exc).__name__
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/all_phase_trials.csv")
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=0, help="0 means all 805 candidates")
    parser.add_argument("--delay", type=float, default=0.3)
    args = parser.parse_args()
    if args.limit < 0 or args.delay < 0:
        parser.error("--limit and --delay must be nonnegative")
    with open(args.input, newline="", encoding="utf-8-sig") as f:
        source = list(csv.DictReader(f))
    targets = [r for r in source if r["status"] == "COMPLETED"
               and "PHASE3" in r["phase"].split("|") and not r["results_posted"].strip()]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if output.exists():
        with output.open(newline="", encoding="utf-8") as f:
            done = {r["nct_id"] for r in csv.DictReader(f)
                    if r.get("classification") not in ("FETCH_ERROR", "")}
    remaining = [r for r in targets if r["nct_id"] not in done]
    if args.limit:
        remaining = remaining[:args.limit]
    with output.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if f.tell() == 0:
            writer.writeheader()
        for row in remaining:
            writer.writerow(verify(row))
            f.flush()
            time.sleep(args.delay)
    print(json.dumps({"eligible": len(targets), "previously_verified": len(done),
                      "attempted_this_run": len(remaining), "output": str(output)}))


if __name__ == "__main__":
    main()
