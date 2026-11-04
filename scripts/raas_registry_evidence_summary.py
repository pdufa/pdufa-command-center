#!/usr/bin/env python3
"""Audit source harvest and publish small, parseable RAAS evidence status for UI.

Never confuse source collection, registry result-posting, TOP/BOTTOM readout,
or FDA decision with scored/approved RAAS research metrics.
"""
from __future__ import annotations
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data/raas_registry_live_evidence.json"
COHORT=ROOT/"data/phase3_all_years_300m_10b_trials.csv"
GAPS=ROOT/"data/raas_registry_missing_backfill.json"
OUT=ROOT/"new-platform/frontend/data/raas-registry-evidence-status.json"
NCT=re.compile(r"NCT\d{8}\Z")

def summarize(payload, roster, gap_ids):
    if payload.get("schemaVersion")!=1 or payload.get("scope")!="RAAS_CT_GOV_LIVE_EVIDENCE":
        raise ValueError("RAAS_SOURCE_SNAPSHOT_INVALID")
    if len(roster)!=len(set(roster)) or any(not NCT.fullmatch(x) for x in roster):
        raise ValueError("RAAS_SOURCE_ROSTER_INVALID")
    rows=payload.get("records")
    if not isinstance(rows,list):
        raise ValueError("RAAS_SOURCE_ROWS_INVALID")
    observed={}
    for r in rows:
        n=r.get("nctId")
        if n not in roster or n in observed or r.get("ticker")!=roster[n] or (
            r.get("sourceUrl")!="https://clinicaltrials.gov/study/"+n):
            raise ValueError("RAAS_SOURCE_CROSS_TRIAL_OR_DUPLICATE")
        if r.get("overallRaasScore") is not None or not isinstance(r.get("hasPostedResults"),bool):
            raise ValueError("RAAS_SOURCE_SCORE_OR_RESULTS_INVALID")
        if r.get("evidenceState")!=("POSTED_RESULTS_UNGRADED" if r["hasPostedResults"] else "PROTOCOL_ONLY"):
            raise ValueError("RAAS_SOURCE_EVIDENCE_TYPE_INVALID")
        if not re.fullmatch("[0-9a-f]{64}",str(r.get("sourceSha256",""))):
            raise ValueError("RAAS_SOURCE_HASH_INVALID")
        observed[n]=r
    failures=payload.get("errors")
    if not isinstance(failures,list) or any(
        x.get("nctId") not in roster or not x.get("reason") for x in failures):
        raise ValueError("RAAS_SOURCE_ERRORS_INVALID")
    if len(set(x["nctId"] for x in failures))!=len(failures):
        raise ValueError("RAAS_SOURCE_DUPLICATE_ERROR")
    original_gaps=set(gap_ids)
    if not original_gaps.issubset(roster):
        raise ValueError("RAAS_SOURCE_GAP_LIST_INVALID")
    pending=sorted(set(roster)-set(observed))
    recovered=sorted(original_gaps.intersection(observed))
    posted=sum(r["hasPostedResults"] for r in observed.values())
    posted_analyses=sum(any(a.get("analysesCount",0)>0
        for a in r.get("primaryPostedEvidence",[])) for r in observed.values())
    severe=sum(r.get("seriousAdverseEventTermCount",0)>0 for r in observed.values())
    primary_arms=sum(any(o.get("measurements") for o in r.get("primaryPostedEvidence",[]))
                     for r in observed.values())
    group_comparisons=sum(any(any(len(a.get("groupIds") or [])>=2
                                   for a in o.get("analyses",[]))
                              for o in r.get("primaryPostedEvidence",[]))
                          for r in observed.values())
    primary_intervals=sum(any(any(a.get("ciLowerLimit") is not None and
                                   a.get("ciUpperLimit") is not None
                                   for a in o.get("analyses",[]))
                              for o in r.get("primaryPostedEvidence",[]))
                          for r in observed.values())
    serious_denominators=sum(any(any(isinstance(g.get("numAffected"),int) and
                                    isinstance(g.get("numAtRisk"),int) and
                                    g.get("numAtRisk")>0 for g in event.get("stats",[]))
                                for event in r.get("seriousAdverseEventEvidence",[]))
                             for r in observed.values())
    summary={
        "researchTrials":len(roster),
        "sourceRecordsStored":len(observed),
        "postedRegistryResults":posted,
        "protocolOnly":len(observed)-posted,
        "trialsWithPrimaryRegistryAnalyses":posted_analyses,
        "trialsWithSeriousAdverseEventEvidence":severe,
        "trialsWithPrimaryGroupMeasurements":primary_arms,
        "trialsWithPrimaryComparisons":group_comparisons,
        "trialsWithPrimaryConfidenceIntervals":primary_intervals,
        "trialsWithSafetyRiskDenominators":serious_denominators,
        "sourceRecordsStillMissing":len(pending),
        "missingRecordsRecoveredFromOriginal35":len(recovered),
        "original35StillMissing":len(original_gaps)-len(recovered),
        "sourceFetchErrorsInLatestRun":len(failures),
        "approvedOverallRaasScores":0
    }
    return {"schemaVersion":1,"scope":"RAAS_CT_GOV_EVIDENCE_COLLECTION_STATUS",
      "source":"ClinicalTrials.gov API v2","collectedAsOf":payload.get("latestAttemptAt"),
      "note":"Direct registry evidence, not PDUFA eligibility, independently verified TOP/BOTTOM classification or validated 0-100 RAAS prediction. Some metrics need additional SEC, FDA, market and independent clinical benchmarks.",
      "summary":summary,
      "pendingRegistryNctIds":pending,
      "failedRegistryNctIds":[x["nctId"] for x in failures],
      "recoveredFromOriginalGaps":recovered,
      "evidenceFile":"data/raas_registry_live_evidence.json"}

def main():
    import csv
    with COHORT.open(encoding="utf-8-sig",newline="") as f:
        roster={r["nct_id"]:r["ticker"] for r in csv.DictReader(f)}
    gaps=json.loads(GAPS.read_text())
    payload=json.loads(SRC.read_text())
    receipt=summarize(payload,roster,[x["nctId"] for x in gaps["missing"]])
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt["summary"],sort_keys=True))

if __name__=="__main__":
    main()
