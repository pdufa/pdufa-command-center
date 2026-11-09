#!/usr/bin/env python3
"""MAIN Rev42: exact-NCT ClinicalTrials.gov posted-result evidence extraction.

PUBLIC FACTS ONLY. Registry as observed now, not an independently dated
predecision snapshot. This script never grades clinical efficacy/safety,
compares drugs, predicts FDA decisions, or changes the prediction ledger.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "app/data/focus_snapshot.json"
APPS = ROOT / "app/data/focus_application_snapshot.json"
MAX_BYTES = 5_000_000
MAX_PRIMARY_DETAILS = 30
MAX_ANALYSES = 30
NCT = re.compile(r"^NCT[0-9]{8}$")
SHA = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_FOCUS_AS_OF = "2026-11-08"

class RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        raise ValueError("EXACT_NCT_REGISTRY_REDIRECT_REJECTED")

def _text(raw, limit=450):
    """Do not copy large prose. Preserve values verbatim as short strings."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        return str(raw)
    return raw.strip()[:limit] if isinstance(raw, str) else None

def _list(obj):
    return obj if isinstance(obj, list) else []

def _dict(obj):
    return obj if isinstance(obj, dict) else {}

def strict_roster(snapshot, applications):
    if (not isinstance(snapshot, dict) or not isinstance(applications, dict)
        or snapshot.get("asOf") != EXPECTED_FOCUS_AS_OF
        or applications.get("asOf") != "2026-11-07"
        or applications.get("sourceVerifiedByFda") is not False
        or applications.get("clinicalSignoff") is not False
        or len(_list(snapshot.get("records"))) != 29
        or len(_list(applications.get("records"))) != 29):
        raise ValueError("R42_CANONICAL_FOCUS_ROSTER_NOT_VERIFIED")
    entries = snapshot["records"]
    ncts = [x.get("nct") for x in entries]
    if len(set(ncts)) != 29 or any(not isinstance(n, str) or not NCT.fullmatch(n) for n in ncts):
        raise ValueError("R42_FOCUS_NCT_MEMBERSHIP_INVALID")
    app_map = {r.get("nct"): r for r in applications["records"]}
    if set(app_map) != set(ncts) or len(app_map) != 29:
        raise ValueError("R42_APPLICATION_CROSSWALK_INCOMPLETE")
    cycles = set()
    for row in entries:
        if not isinstance(row.get("ticker"), str):
            raise ValueError("R42_FOCUS_TICKER_MISSING")
        a = _list(app_map[row["nct"]].get("candidateApplications"))
        if not a or any(c.get("ticker") != row["ticker"] or not isinstance(c.get("cycleId"), str) for c in a):
            raise ValueError("R42_TRIAL_APPLICATION_IDENTITY_MISMATCH")
        cycles.update(c["cycleId"] for c in a)
    if len(cycles) != 23:
        raise ValueError("R42_23_APPLICATION_GROUPS_NOT_MATCHED")
    return entries

def fetch_exact_registry(nct, timeout=18):
    if not NCT.fullmatch(nct):
        raise ValueError("INVALID_NCT")
    url = "https://clinicaltrials.gov/api/v2/studies/" + nct + "?format=json"
    try:
        req = Request(url, headers={"Accept": "application/json",
            "User-Agent": "PDUFA-FOCUS-29-public-registry-evidence-audit/1.0"})
        with build_opener(RejectRedirect()).open(req, timeout=timeout) as response:
            if response.status != 200:
                raise ValueError("REGISTRY_HTTP_STATUS_NOT_200")
            ctype = response.headers.get("content-type", "").split(";")[0].lower()
            if ctype != "application/json":
                raise ValueError("REGISTRY_NOT_JSON")
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise ValueError("REGISTRY_RESPONSE_EXCEEDS_5MB")
        return json.loads(data), {"status": "FETCHED", "sourceUrl": url,
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
            "contentType": "application/json"}
    except (OSError, HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        return None, {"status": "FETCH_BLOCKED", "sourceUrl": url,
            "errorClass": type(error).__name__}

def extract_registry_study(nct, ticker, study, receipt):
    """Extract *reported* primary measures and posted AEs, not effects."""
    if receipt.get("status") != "FETCHED" or not isinstance(study, dict):
        return {"nct": nct, "ticker": ticker, "registry": receipt,
            "resultsPresent": None, "primaryOutcomeCount": None,
            "primaryOutcomes": [], "seriousEventsPresent": None,
            "noScoresWritten": True, "independentReviewerSignoff": False}
    protocol = _dict(study.get("protocolSection"))
    identity = _dict(protocol.get("identificationModule")).get("nctId")
    if identity != nct:
        raise ValueError("REGISTRY_NCT_ID_MISMATCH")
    result_section = study.get("resultsSection")
    has_results = isinstance(result_section, dict)
    # Do not interpret hasResults=True without a resultsSection or vice versa.
    advertised = study.get("hasResults")
    if advertised is not None and advertised is not has_results:
        raise ValueError("REGISTRY_RESULTS_MEMBERSHIP_INCONSISTENT")
    results = _dict(result_section)
    measure_module = _dict(results.get("outcomeMeasuresModule"))
    all_outcomes = _list(measure_module.get("outcomeMeasures"))
    primary = [x for x in all_outcomes if isinstance(x, dict) and x.get("type") == "PRIMARY"]
    records = []
    for measure in primary[:MAX_PRIMARY_DETAILS]:
        analysis = []
        for row in _list(measure.get("analyses"))[:MAX_ANALYSES]:
            if not isinstance(row, dict):
                continue
            analysis.append({k: _text(row.get(k), 175) for k in (
                "pValue","pValueComment","method","methodDesc","estimate",
                "ciPctValue","ciLowerLimit","ciUpperLimit","paramType"
            ) if row.get(k) is not None})
        records.append({
            "type": "PRIMARY",
            "title": _text(measure.get("title"), 240),
            "timeFrame": _text(measure.get("timeFrame"), 180),
            "unitOfMeasure": _text(measure.get("unitOfMeasure"), 120),
            "paramType": _text(measure.get("paramType"), 120),
            "populationDescription": _text(measure.get("populationDescription"), 240),
            "analysisCount": len(_list(measure.get("analyses"))),
            "analysesShown": analysis,
            "groupLabels": [_text(x.get("title"), 130) for x in _list(measure.get("groups"))
                            if isinstance(x, dict)][:30],
            "measurementClassCount": len(_list(measure.get("classes"))),
            "dataNotClinicallyAdjudicated": True
        })
    ae = _dict(results.get("adverseEventsModule"))
    serious = _list(ae.get("seriousEvents"))
    other = _list(ae.get("otherEvents"))
    status = _dict(protocol.get("statusModule"))
    design = _dict(protocol.get("designModule"))
    return {
        "nct": nct, "ticker": ticker,
        "registry": receipt,
        "registryPhase": _list(design.get("phases")),
        "registryStatus": status.get("overallStatus"),
        "registryLastUpdatePosted": _dict(status.get("lastUpdatePostDateStruct")).get("date"),
        "resultsPresent": has_results,
        "primaryOutcomeCount": len(primary),
        "primaryOutcomeDetailsTruncated": len(primary) > MAX_PRIMARY_DETAILS,
        "primaryOutcomes": records,
        "postedSeriousEventRows": len(serious),
        "postedOtherEventRows": len(other),
        "seriousEventsPresent": bool(serious) if has_results else None,
        "adverseEventModulePresent": isinstance(results.get("adverseEventsModule"), dict),
        "participantFlowModulePresent": isinstance(results.get("participantFlowModule"), dict),
        "postedResultsEqualCompletePhase3Package": False,
        "originalFirstPublicDateAuthenticated": False,
        "pivotalEfficacySigned": False,
        "clinicalSafetyReviewed": False,
        "independentReviewerSignoff": False,
        "noScoresWritten": True
    }

def collect(roster, applications, fetcher=fetch_exact_registry):
    entries = strict_roster(roster, applications)
    tasks = {x["nct"]: x["ticker"] for x in entries}
    results = {}
    def one(nct):
        study, receipt = fetcher(nct)
        return nct, extract_registry_study(nct, tasks[nct], study, receipt)
    with ThreadPoolExecutor(max_workers=6) as pool:
        for future in as_completed([pool.submit(one, nct) for nct in tasks]):
            nct, item = future.result()
            results[nct] = item
    rows = [results[x["nct"]] for x in entries]
    fetched = sum(r["registry"]["status"] == "FETCHED" for r in rows)
    present = sum(r["resultsPresent"] is True for r in rows)
    missing = sum(r["resultsPresent"] is False for r in rows)
    primary = sum(r["primaryOutcomeCount"] or 0 for r in rows)
    trials_with_primary = sum(bool(r["primaryOutcomeCount"]) for r in rows)
    return {
        "schema": "MAIN_FOCUS_R42_POSTED_REGISTRY_RESULTS_RESEARCH",
        "snapshotObservedAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceRosters": {"focus": "2026-11-08", "applications": "2026-11-07"},
        "status": "POSTED_REGISTRY_FACTS_RESEARCH_ONLY_NO_CLINICAL_GRADES",
        "trialCount": 29,
        "applicationCycleCount": 23,
        "registryRecordsFetched": fetched,
        "registryFetchUnavailable": 29 - fetched,
        "registryResultsSectionsPresent": present,
        "registryResultsSectionsAbsent": missing,
        "registryResultsMembershipUnknown": 29 - fetched,
        "trialsWithPostedPrimaryOutcomeRecords": trials_with_primary,
        "postedPrimaryOutcomeRecords": primary,
        "postedPrimaryOutcomeRecordsScientificallyReviewed": 0,
        "originalPublicSourcePostingClocksVerified": 0,
        "independentClinicalReviews": 0,
        "officialFdaForecastsIndependentlyValidated": 0,
        "historicalFdaBacktestsCompleted": 0,
        "fdaApprovalProbability": None,
        "calibratedAccuracy": None,
        "trials": rows,
        "caveats": [
            "Current ClinicalTrials.gov API posted results are not a full Phase 3 scientific source corpus.",
            "A present primary outcome record is not proof of clinical benefit, statistical validity or FDA approval.",
            "Registry-reported p-values are transcribed strings, not recomputed or multiplicity-adjusted.",
            "A missing posted results section does not mean results are unavailable in peer-reviewed or sponsor sources.",
            "Current registry record is NOT a verified as-published predecision historical source.",
            "Raw protocol/SAP, efficacy population, full safety definitions, CMC and independent assessment remain separate gates."
        ],
        "clinicalGradingAuthorized": False,
        "predictionsAuthorized": False,
        "noClinicalOrProductionWrites": True
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("IMMUTABLE_RECEIPT_OUTPUT_MUST_BE_NEW")
    with ROSTER.open(encoding="utf-8") as f: roster=json.load(f)
    with APPS.open(encoding="utf-8") as f: apps=json.load(f)
    report=collect(roster,apps)
    raw=(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode()
    with a.output.open("xb") as f:f.write(raw)
    print(json.dumps({
        "status":report["status"],"ncts":29,"applications":23,
        "retrieved":report["registryRecordsFetched"],
        "registryResultsPresent":report["registryResultsSectionsPresent"],
        "trialsWithPrimaryOutcomes":report["trialsWithPostedPrimaryOutcomeRecords"],
        "primaryOutcomeRecords":report["postedPrimaryOutcomeRecords"],
        "sha256":hashlib.sha256(raw).hexdigest(),
        "scientificGrades":0,"historicalBacktests":0,"validatedFdaForecasts":0
    }),flush=True)

if __name__=="__main__":main()
