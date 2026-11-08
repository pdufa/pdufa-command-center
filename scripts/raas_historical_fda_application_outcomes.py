#!/usr/bin/env python3
"""Application-level FDA outcome truth separated from RAAS trial metric evidence.

A retrospective CRL and an approval are NOT two training examples with valid
pre-action RAAS predictions. One NDA may rely on multiple NCTs; those cannot
be counted as independent action outcomes. Missing action dates remain N/A.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")


import csv
import io
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "new-platform/frontend/data/raas-historical-fda-application-outcomes.json"
REGISTRY = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
OUTPUT = ROOT / "new-platform/frontend/public/raas-historical-fda-application-outcomes.csv"
STATUS = ROOT / "new-platform/frontend/data/raas-historical-fda-application-outcomes-status.json"
FIELDS = (
    "applicationId","ticker","drug","indication","kind","linkedNcts",
    "applicationAcceptedDate","applicationAcceptanceSource","pdufaTargetDate",
    "preActionSourceDate","preActionSource","preActionFinding","actualOutcome",
    "actualDecisionDate","actualOutcomePublicDate","actualOutcomeSource",
    "outcomeReason","predictionIssuedBeforeDecision","calibratedPredictionEligible",
    "interpretation"
)


def _day(raw, *, nullable=False):
    if nullable and raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError("FDA_OUTCOME_INVALID_DATE")
    if date.fromisoformat(raw).isoformat()!=raw:
        raise ValueError("FDA_OUTCOME_INVALID_DATE")
    return raw


def _source(v, *, nullable=False):
    if nullable and v is None:
        return None
    if not isinstance(v,str) or not v.startswith("https://"):
        raise ValueError("FDA_OUTCOME_SOURCE_MISSING")
    return v


def export(cases, registry=None):
    if cases.get("schemaVersion")!=1 or cases.get("scope")!=(
        "RAAS_HISTORICAL_FDA_APPLICATION_OUTCOMES_NOT_MODEL_PREDICTIONS"):
        raise ValueError("FDA_OUTCOME_SCOPE_INVALID")
    latest=_day(cases.get("sourceAsOf"))
    seen_apps=set()
    nct_to_app={}
    rows=[]
    valid_ncts = None
    if registry is not None:
        if registry.get("scope")!="RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX":
            raise ValueError("FDA_OUTCOME_REGISTRY_SCOPE")
        valid_ncts={e["nctId"]:e["ticker"] for e in registry["records"]}
    for c in cases.get("records",[]):
        id=c.get("applicationId")
        refs=c.get("trialNcts")
        if (not isinstance(id,str) or not id or id in seen_apps or
            not isinstance(refs,list) or not refs or len(set(refs))!=len(refs) or
            c.get("kind") not in ("NDA","BLA") or
            c.get("actualOutcome") not in ("APPROVAL","COMPLETE_RESPONSE_LETTER","EXTENSION") or
            c.get("calibratedPredictionEligible") is not False or
            c.get("predictionIssuedBeforeDecision") is not False or
            not c.get("drug") or not c.get("ticker") or not c.get("indication")):
            raise ValueError("FDA_OUTCOME_IDENTITY_OR_PREDICTION_LEAK")
        seen_apps.add(id)
        for nct in refs:
            if (not isinstance(nct,str) or not __import__("re").fullmatch(r"NCT\d{8}",nct) or
                nct in nct_to_app or
                (valid_ncts is not None and valid_ncts.get(nct)!=c["ticker"])):
                raise ValueError("FDA_OUTCOME_CROSS_TRIAL_OR_DOUBLE_COUNT")
            nct_to_app[nct]=id
        d_pub=_day(c.get("actualOutcomePublicDate"))
        d_dec=_day(c.get("actualDecisionDate"),nullable=True)
        d_pre=_day(c.get("preActionSourceDate"),nullable=True)
        d_target=_day(c.get("pdufaTargetDate"),nullable=True)
        d_accept=_day(c.get("applicationAcceptedDate"),nullable=True)
        if (d_pub>latest or (d_dec is not None and d_dec>d_pub) or
            (d_pre is not None and d_pre>=d_pub) or
            (d_accept is not None and d_accept>=d_pub) or
            (d_accept is not None and d_target is not None and d_accept>d_target) or
            (d_pre is None)!=(c.get("preActionSource") is None) or
            (d_accept is None)!=(c.get("applicationAcceptanceSource") is None)):
            raise ValueError("FDA_OUTCOME_CHRONOLOGY_INVALID")
        _source(c.get("actualOutcomeSource"))
        _source(c.get("applicationAcceptanceSource"),nullable=True)
        _source(c.get("preActionSource"),nullable=True)
        rows.append({
            "applicationId":id,"ticker":c["ticker"],"drug":c["drug"],
            "indication":c["indication"],"kind":c["kind"],
            "linkedNcts":";".join(refs),"applicationAcceptedDate":d_accept or "",
            "applicationAcceptanceSource":c.get("applicationAcceptanceSource") or "",
            "pdufaTargetDate":d_target or "","preActionSourceDate":d_pre or "",
            "preActionSource":c.get("preActionSource") or "",
            "preActionFinding":c.get("preActionFinding") or "",
            "actualOutcome":c["actualOutcome"],"actualDecisionDate":d_dec or "",
            "actualOutcomePublicDate":d_pub,
            "actualOutcomeSource":c["actualOutcomeSource"],
            "outcomeReason":c.get("outcomeReason") or "",
            "predictionIssuedBeforeDecision":False,
            "calibratedPredictionEligible":False,
            "interpretation":"HISTORICAL_OUTCOME_ONLY_NOT_BACKTEST_OR_PREDICTIVE_ACCURACY"
        })
    if not rows:
        raise ValueError("FDA_OUTCOME_NO_PROGRAMS")
    status={
        "schemaVersion":1,
        "scope":"RAAS_APPLICATION_LEVEL_HISTORICAL_GROUND_TRUTH_NO_BLIND_PREDICTIONS",
        "sourceAsOf":latest,
        "uniqueApplicationDecisions":len(rows),
        "linkedTrialNcts":len(nct_to_app),
        "approvals":sum(r["actualOutcome"]=="APPROVAL" for r in rows),
        "completeResponseLetters":sum(r["actualOutcome"]=="COMPLETE_RESPONSE_LETTER" for r in rows),
        "extensions":sum(r["actualOutcome"]=="EXTENSION" for r in rows),
        "independentPreActionModelPredictions":0,
        "validatedPredictionAccuracy":None,
        "warning":"Two historical FDA application outcomes are source-verified, not prediction calibration. Cytisinicline ORCA-2 and ORCA-3 are ONE NDA event, not two independent CRLs. A postaction outcome cannot be used as a model feature at an earlier cutoff."
    }
    buffer=io.StringIO()
    writer=csv.DictWriter(buffer,fieldnames=FIELDS,lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key:("'"+str(value) if str(value)[:1] in ("=", "+", "-", "@") else value)
                         for key,value in row.items()})
    return buffer.getvalue(),json.dumps(status,indent=2)+"\n"


def main():
    source=json.loads(SOURCE.read_text(encoding="utf8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf8"))
    csv_out,status_out=export(source,registry)
    OUTPUT.write_text(csv_out,encoding="utf8")
    STATUS.write_text(status_out,encoding="utf8")
    print(status_out.strip())


if __name__=="__main__":
    main()
