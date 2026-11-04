#!/usr/bin/env python3
"""Build a bounded, exact-NCT registry evidence index for RAAS trial cards.

This transforms the separately collected primary registry receipts, not a
secondary model interpretation. It never computes efficacy, FDA probabilities,
PDUFA eligibility or RAAS 0–100 scores. Only the exact public-source packet
and publication dates are shown, without backdating research forecasts.
"""
from __future__ import annotations
import csv
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raas_registry_live_evidence.json"
ROSTER = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
DEST = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
ID = re.compile(r"NCT\d{8}\Z")
HEX = re.compile(r"[a-f0-9]{64}\Z")
ALLOWED_STATES = {"POSTED_RESULTS_UNGRADED", "PROTOCOL_ONLY"}

def string(value, limit=240):
    return value.strip()[:limit] if isinstance(value, str) else ""

def array(value):
    return value if isinstance(value, list) else []

def compact_trial(row: dict, ticker: str) -> dict:
    nct = row.get("nctId")
    if not isinstance(nct, str) or not ID.fullmatch(nct) or row.get("ticker") != ticker:
        raise ValueError("REGISTRY_INDEX_NCT_IDENTITY")
    if row.get("sourceUrl") != "https://clinicaltrials.gov/study/" + nct:
        raise ValueError("REGISTRY_INDEX_SOURCE_IDENTITY")
    if row.get("evidenceState") not in ALLOWED_STATES or not isinstance(row.get("hasPostedResults"), bool):
        raise ValueError("REGISTRY_INDEX_INVALID_SOURCE_STATE")
    posted = row["hasPostedResults"]
    if posted != (row["evidenceState"] == "POSTED_RESULTS_UNGRADED"):
        raise ValueError("REGISTRY_INDEX_RESULT_FLAG_CONFLICT")
    if not HEX.fullmatch(str(row.get("sourceSha256") or "")):
        raise ValueError("REGISTRY_INDEX_SOURCE_HASH")
    if row.get("overallRaasScore") is not None:
        raise ValueError("REGISTRY_INDEX_SCORE_NOT_ALLOWED")
    primary = []
    for obj in array(row.get("primaryPostedEvidence"))[:5]:
        if not isinstance(obj, dict):
            raise ValueError("REGISTRY_INDEX_MEASURE_SHAPE")
        analyses = array(obj.get("analyses"))
        primary.append({
            "title": string(obj.get("title"), 260),
            "timeFrame": string(obj.get("timeFrame"), 100),
            "unit": string(obj.get("unit"), 100),
            "analysisCount": int(obj.get("analysesCount") or 0),
            "pValues": [string(a.get("pValue"), 40) for a in analyses
                        if isinstance(a, dict) and string(a.get("pValue"), 40)][:5],
        })
    if not posted and (primary or row.get("postedPrimaryOutcomeCount", 0)):
        raise ValueError("REGISTRY_INDEX_UNPUBLISHED_OUTCOMES")
    definitions = []
    for obj in array(row.get("registeredPrimaryOutcomes"))[:4]:
        if isinstance(obj, dict):
            definitions.append({
                "measure": string(obj.get("measure"), 260),
                "timeFrame": string(obj.get("timeFrame"), 110),
            })
    return {
        "nctId": nct,
        "ticker": ticker,
        "sourceUrl": row["sourceUrl"],
        "sourceHash": row["sourceSha256"],
        "retrievedAt": string(row.get("fetchedAt"), 40),
        "registryLastUpdated": string(row.get("registryLastUpdated"), 30) or None,
        "resultsFirstPosted": string(row.get("resultsFirstPosted"), 30) or None,
        "registryStatus": string(row.get("registryStatus"), 70),
        "registeredPhases": [string(x, 30) for x in array(row.get("registeredPhases"))[:4]],
        "registeredConditions": [string(x, 150) for x in array(row.get("registeredConditions"))[:8]],
        "registeredInterventions": [string(x, 150) for x in array(row.get("registeredInterventions"))[:14]],
        "primaryDefinitions": definitions,
        "postedResults": posted,
        "postedPrimaryOutcomeCount": int(row.get("postedPrimaryOutcomeCount") or 0),
        "postedOtherOutcomeCount": int(row.get("postedOtherOutcomeCount") or 0),
        "primaryResults": primary,
        "seriousAdverseEventTermCount": int(row.get("seriousAdverseEventTermCount") or 0),
        "evidenceState": row["evidenceState"],
    }

def build_index(payload: dict, roster: dict[str, str]) -> dict:
    if payload.get("schemaVersion") != 1 or payload.get("scope") != "RAAS_CT_GOV_LIVE_EVIDENCE":
        raise ValueError("REGISTRY_INDEX_SOURCE_SCOPE")
    rows = payload.get("records")
    if not isinstance(rows, list) or not roster:
        raise ValueError("REGISTRY_INDEX_INVALID_POPULATION")
    records = {}
    for row in rows:
        if not isinstance(row, dict) or row.get("nctId") not in roster:
            raise ValueError("REGISTRY_INDEX_OUT_OF_COHORT")
        nct = row["nctId"]
        if nct in records:
            raise ValueError("REGISTRY_INDEX_DUPLICATE")
        records[nct] = compact_trial(row, roster[nct])
    if set(records) != set(roster):
        raise ValueError("REGISTRY_INDEX_INCOMPLETE_COHORT")
    results = [records[k] for k in sorted(records)]
    count = sum(r["postedResults"] for r in results)
    if int(payload.get("summary", {}).get("registrySourceRecordsStored", -1)) != len(results):
        raise ValueError("REGISTRY_INDEX_SUMMARY_MISMATCH")
    if int(payload.get("summary", {}).get("hasPostedRegistryResults", -1)) != count:
        raise ValueError("REGISTRY_INDEX_POSTED_COUNT_MISMATCH")
    return {"schemaVersion":1, "scope":"RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
        "source":"ClinicalTrials.gov API v2 exact-NCT evidence",
        "sourceAsOf":payload.get("latestAttemptAt"),
        "caution":"ClinicalTrials.gov protocol/results presence only: not an independently verified PDUFA date, source-timed TOP/BOTTOM assignment, predictive accuracy, or a numeric RAAS score.",
        "summary":{"researchNcts":len(results),"registryRecords":len(results),
                   "postedRegistryResults":count,"protocolOnly":len(results)-count,
                   "approvedOverallRaasScores":0},
        "records":results}

def main():
    with ROSTER.open(newline="",encoding="utf-8-sig") as f:
        roster={r["nct_id"]:r["ticker"] for r in csv.DictReader(f)}
    if len(roster) < 1:
        raise ValueError("REGISTRY_INDEX_EMPTY_ROSTER")
    result=build_index(json.loads(SOURCE.read_text(encoding="utf-8")),roster)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    content=json.dumps(result, ensure_ascii=False, separators=(",", ":"))+"\n"
    if not DEST.exists() or DEST.read_text(encoding="utf-8")!=content:
        DEST.write_text(content, encoding="utf-8")
    print("RAAS source index:",json.dumps(result["summary"],sort_keys=True))

if __name__=="__main__":
    main()
