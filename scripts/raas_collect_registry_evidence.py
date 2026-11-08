#!/usr/bin/env python3
"""Collect public ClinicalTrials.gov v2 evidence for every NCT in the evolving
RAAS research cohort. This is a source inventory, NEVER a numerical RAAS grade.
No database credentials, stock prices, assumed readout classification or PDUFA claims.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")

import argparse
import csv
import datetime as dt
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
DEST = ROOT / "data/raas_clinical_evidence_inventory.json"
API = "https://clinicaltrials.gov/api/v2/studies/"
ID = re.compile(r"NCT\d{8}\Z")
HEADER = ["nct_id", "ticker", "company", "status", "source_url"]
MAX_BYTES = 1_500_000
MAX_OUTCOMES = 15

def current_day():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_cohort(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != HEADER:
            raise ValueError("Unexpected RAAS research cohort schema")
        rows = list(reader)
    if not rows or len(rows) > 25000:
        raise ValueError("Empty or oversized research cohort")
    seen = set()
    for row in rows:
        nct = row["nct_id"]
        if not ID.fullmatch(nct) or nct in seen or not row["ticker"] or not row["company"] or row["source_url"] != "https://clinicaltrials.gov/study/" + nct:
            raise ValueError("Invalid or duplicated NCT research identity")
        seen.add(nct)
    return sorted(rows, key=lambda x: x["nct_id"])

def text(value, max_len=240):
    return value.strip()[:max_len] if isinstance(value, str) else ""

def arr(value):
    return value if isinstance(value, list) else []

def canonical_result(payload: dict, row: dict, retrieved: str, sha: str) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("REGISTRY_NOT_OBJECT")
    protocol = payload.get("protocolSection")
    if not isinstance(protocol, dict):
        raise ValueError("REGISTRY_PROTOCOL_MISSING")
    identity = protocol.get("identificationModule") or {}
    if not isinstance(identity, dict) or identity.get("nctId") != row["nct_id"]:
        raise ValueError("REGISTRY_NCT_MISMATCH")
    status = protocol.get("statusModule") or {}
    design = protocol.get("designModule") or {}
    sponsor = protocol.get("sponsorCollaboratorsModule") or {}
    arms = protocol.get("armsInterventionsModule") or {}
    cond = protocol.get("conditionsModule") or {}
    outcomes = protocol.get("outcomesModule") or {}
    if not all(isinstance(x, dict) for x in (status, design, sponsor, arms, cond, outcomes)):
        raise ValueError("REGISTRY_SECTION_INVALID")
    result = payload.get("resultsSection") or {}
    if not isinstance(result, dict):
        raise ValueError("REGISTRY_RESULTS_INVALID")
    measure_module = result.get("outcomeMeasuresModule") or {}
    adverse = result.get("adverseEventsModule") or {}
    if not isinstance(measure_module, dict) or not isinstance(adverse, dict):
        raise ValueError("REGISTRY_RESULT_MODULE_INVALID")
    posted = payload.get("hasResults") is True
    raw_measures = arr(measure_module.get("outcomeMeasures"))
    if not posted and (raw_measures or result):
        raise ValueError("REGISTRY_RESULTS_FLAG_CONFLICT")
    endpoint_specs = []
    for item in arr(outcomes.get("primaryOutcomes"))[:MAX_OUTCOMES]:
        if isinstance(item, dict):
            endpoint_specs.append({"measure": text(item.get("measure"), 320), "timeFrame": text(item.get("timeFrame"), 140)})
    outcome_results = []
    analysis_count = 0
    pvalue_count = 0
    for measure in raw_measures[:MAX_OUTCOMES]:
        if not isinstance(measure, dict):
            raise ValueError("REGISTRY_MEASURE_INVALID")
        analyses = arr(measure.get("analyses"))
        analysis_count += len(analyses)
        checked = []
        for a in analyses[:12]:
            if isinstance(a, dict):
                pv = text(a.get("pValue"), 40)
                if pv:
                    pvalue_count += 1
                checked.append({"pValue": pv or None, "method": text(a.get("statisticalMethod"), 130)})
        outcome_results.append({"type": text(measure.get("type"), 20),
           "title": text(measure.get("title"), 360),
           "timeFrame": text(measure.get("timeFrame"), 130),
           "analysisCount": len(analyses), "analyses": checked,
           "measurementsPresent": sum(len(arr(g.get("measurements"))) for g in arr(measure.get("classes")) if isinstance(g, dict))})
    lead = sponsor.get("leadSponsor") or {}
    if not isinstance(lead, dict):
        raise ValueError("REGISTRY_SPONSOR_INVALID")
    return {"nctId": row["nct_id"], "ticker": row["ticker"], "censusCompany": row["company"],
       "censusStatus": row["status"], "sourceUrl": API + row["nct_id"],
       "sourceSha256": sha, "retrievedAt": retrieved, "registryLastUpdated": text(status.get("lastUpdatePostDate"), 12),
       "registryStatus": text(status.get("overallStatus"), 55),
       "registeredSponsor": text(lead.get("name"), 230),
       "registeredPhases": [text(x, 30) for x in arr(design.get("phases"))[:5]],
       "registeredConditions": [text(x, 120) for x in arr(cond.get("conditions"))[:12]],
       "registeredInterventions": [text(x.get("name"), 180) for x in arr(arms.get("interventions"))[:16] if isinstance(x, dict)],
       "registeredPrimaryEndpoints": endpoint_specs,
       "postedResults": posted, "reportedOutcomeMeasures": outcome_results,
       "reportedStatisticalAnalyses": analysis_count, "reportedPValuesInSample": pvalue_count,
       "reportedAdverseEventTerms": sum(len(arr(adverse.get(k))) for k in ("seriousEvents", "otherEvents")),
       "evidenceState": "POSTED_RESULTS" if posted else "REGISTRY_PROTOCOL_ONLY",
       "raasOverallScore": None, "verifiedPipeline": None, "sourceError": None}

def fetch_one(row: dict, retries=2) -> dict:
    nct = row["nct_id"]
    url = API + nct
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json", "User-Agent": "RAAS-PDUFA-EvidenceAudit/1.0 (public-source-research)"
            }, method="GET")
            with urllib.request.urlopen(req, timeout=18) as response:
                if response.status != 200 or response.geturl().split("?")[0] != url:
                    raise ValueError("REGISTRY_HTTP_IDENTITY_MISMATCH")
                if "json" not in response.headers.get("content-type", "").lower():
                    raise ValueError("REGISTRY_CONTENT_TYPE")
                raw = response.read(MAX_BYTES + 1)
            if not (0 < len(raw) <= MAX_BYTES):
                raise ValueError("REGISTRY_SIZE_INVALID")
            return canonical_result(json.loads(raw), row, current_day(), hashlib.sha256(raw).hexdigest())
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            error = "HTTP_" + str(exc.code) if isinstance(exc, urllib.error.HTTPError) else (
                str(exc) if isinstance(exc, ValueError) and str(exc).startswith("REGISTRY_") else type(exc).__name__)
            if attempt < retries and error in ("HTTP_429", "HTTP_500", "HTTP_502", "HTTP_503", "HTTP_504", "TimeoutError", "URLError"):
                time.sleep((attempt + 1) * 2)
                continue
            return {"nctId": nct, "ticker": row["ticker"],
                "sourceUrl": url, "evidenceState": "FETCH_FAILED",
                "sourceError": error, "retrievedAt": None, "postedResults": None,
                "raasOverallScore": None, "verifiedPipeline": None}

def collect(rows: list[dict], prior: dict | None = None, max_age_days: int = 7, workers: int = 8) -> dict:
    captured_at = current_day()
    previous = {x["nctId"]: x for x in arr((prior or {}).get("records")) if isinstance(x, dict) and isinstance(x.get("nctId"), str)}
    now = dt.datetime.now(dt.timezone.utc)
    results = {}
    todo = []
    for row in rows:
        old = previous.get(row["nct_id"])
        fresh = False
        if old and old.get("sourceSha256") and old.get("evidenceState") in ("POSTED_RESULTS", "REGISTRY_PROTOCOL_ONLY"):
            try:
                age = now - dt.datetime.fromisoformat(old["retrievedAt"].replace("Z", "+00:00"))
                fresh = dt.timedelta(0) <= age < dt.timedelta(days=max_age_days)
            except (ValueError, TypeError, KeyError):
                pass
        if fresh:
            results[row["nct_id"]] = old
        else:
            todo.append(row)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = {pool.submit(fetch_one, row): row for row in todo}
        for future in as_completed(jobs):
            row = jobs[future]
            try:
                entry = future.result()
            except Exception:
                entry = {"nctId": row["nct_id"], "ticker": row["ticker"], "sourceUrl": API + row["nct_id"],
                         "evidenceState": "FETCH_FAILED", "sourceError": "WORKER_ERROR", "postedResults": None,
                         "raasOverallScore": None, "verifiedPipeline": None}
            old = previous.get(row["nct_id"])
            if entry.get("evidenceState") == "FETCH_FAILED" and old and old.get("sourceSha256"):
                entry = {**old, "refreshError": entry["sourceError"], "lastRefreshAttempt": captured_at}
            results[row["nct_id"]] = entry
    output = [results[row["nct_id"]] for row in rows]
    counted = {"totalNctIds": len(rows), "usableRegistryRecords": sum(bool(x.get("sourceSha256")) for x in output),
       "postedRegistryResults": sum(x.get("postedResults") is True for x in output),
       "protocolOnly": sum(x.get("evidenceState") == "REGISTRY_PROTOCOL_ONLY" for x in output),
       "registryRecordsWithStatisticalAnalyses": sum(int(x.get("reportedStatisticalAnalyses") or 0) > 0 for x in output),
       "unavailableSourceRecords": sum(not x.get("sourceSha256") for x in output),
       "sourceRefreshFailures": sum(bool(x.get("sourceError") or x.get("refreshError")) for x in output),
       "overallRaasScores": 0}
    return {"schemaVersion": 1, "scope": "RAAS_PUBLIC_CLINICALTRIALS_EVIDENCE_INVENTORY",
        "cohort": "data/phase3_all_years_300m_10b_trials.csv", "capturedAt": captured_at,
        "source": "ClinicalTrials.gov API v2 exact-NCT public records",
        "caution": "Registry entry, sponsor and result posting are neither FDA PDUFA approval nor a verified RAAS TOP/BOTTOM stage. Do not equate a reported p value, result, or protocol with a validated numerical RAAS score.",
        "summary": counted, "records": output}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=DEST)
    ap.add_argument("--max-age-days", type=int, default=7)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    if args.max_age_days < 0 or not 1 <= args.workers <= 12:
        ap.error("Invalid refresh parameters")
    rows = load_cohort(COHORT)
    prior = None
    if args.output.exists():
        prior = json.loads(args.output.read_text(encoding="utf-8"))
        if prior.get("scope") != "RAAS_PUBLIC_CLINICALTRIALS_EVIDENCE_INVENTORY":
            raise ValueError("Existing source inventory has the wrong scope")
    result = collect(rows, prior, args.max_age_days, args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("RAAS ClinicalTrials.gov source evidence:", json.dumps(result["summary"], sort_keys=True))
    if result["summary"]["unavailableSourceRecords"]:
        print("Unverified source NCTs: " + ", ".join(x["nctId"] for x in result["records"] if not x.get("sourceSha256")))

if __name__ == "__main__":
    main()
