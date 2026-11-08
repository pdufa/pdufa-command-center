#!/usr/bin/env python3
"""Source-dated accepted FDA application tracker with strict Phase 3 restriction.

Actions are NDA-level, not trial-level: distinct products/indications review
cycles are separate events. Minimum Phase 3 is a user screening restriction.
Phase 2-based accepted NDAs remain visible but DO NOT qualify for that screen.
No inferred FDA PASS/CRL/extension probabilities or presumed decisions.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")

import csv
from datetime import date
import io
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"new-platform/frontend/data/raas-current-accepted-fda-applications.json"
REVIEWS=ROOT/"new-platform/frontend/data/raas-reviewed-metric-assessments.json"
ROSTER=ROOT/"data/phase3_all_years_300m_10b_trials.csv"
OUTPUT=ROOT/"new-platform/frontend/public/raas-current-accepted-fda-applications.csv"
STATUS=ROOT/"new-platform/frontend/data/raas-current-accepted-fda-applications-status.json"
FIELDS=("applicationKey","ticker","issuer","marketCapUsd","marketCapAsOf",
        "marketCapSourceUrl","marketCapVerification","drug","indication",
        "pathway","trialName","trialNctId","trialSourceUrl","pivotalPhase",
        "pipelineRestrictionResult","applicationAcceptedDate",
        "applicationAcceptedSourceUrl","pdufaTargetDate","reviewDesignation",
        "additionalSponsorReportedDesignations","targetStatus",
        "sourceVerifiedAsOf","outcomeAsOf","reviewedProvisionalMetricCount",
        "independentReviewedMetricCount","full30MetricRaasScore",
        "fdaPassCrlExtensionProbability","outcomeData","outcomeEvidenceUrl",
        "interpretation")
NCT=re.compile(r"NCT\d{8}\Z")
ISO=re.compile(r"\d{4}-\d{2}-\d{2}\Z")

def day(value):
    if not isinstance(value,str) or not ISO.fullmatch(value):
        raise ValueError("CURRENT_PDUFA_INVALID_DATE")
    d=date.fromisoformat(value)
    if d.isoformat()!=value:
        raise ValueError("CURRENT_PDUFA_INVALID_DATE")
    return d

def https(u):
    return isinstance(u,str) and bool(re.fullmatch(r"https://[^\s<>\"']+",u))

def safe(v):
    s="" if v is None else str(v)
    return "'"+s if s[:1] in ("=","+","-","@") else s

def build(data,reviews,roster_csv,*,as_of):
    asof=day(as_of)
    if (data.get("schemaVersion")!=1 or data.get("scope")!=
        "RAAS_CURRENT_FDA_ACCEPTED_APPLICATIONS_RESTRICTED_BY_PIVOTAL_PHASE" or
        reviews.get("scope")!="RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY" or
        not isinstance(data.get("applications"),list) or
        not isinstance(reviews.get("records"),list)):
        raise ValueError("CURRENT_PDUFA_SOURCE_SCOPE")
    snapshot=day(data.get("sourceAsOf"))
    if asof<snapshot or day(reviews.get("sourceAsOf"))>asof:
        raise ValueError("CURRENT_PDUFA_FUTURE_SNAPSHOT")
    issuer=data.get("issuer")
    if (not isinstance(issuer,dict) or issuer.get("ticker")!="COGT" or
        issuer.get("exchange")!="NASDAQ" or
        not https(issuer.get("marketCapSourceUrl")) or
        not isinstance(issuer.get("marketCapUsd"),int) or
        isinstance(issuer.get("marketCapUsd"),bool)):
        raise ValueError("CURRENT_PDUFA_ISSUER_PROVENANCE")
    cap_day=day(issuer["marketCapAsOf"])
    if cap_day>snapshot:
        raise ValueError("CURRENT_PDUFA_FUTURE_MARKET_CAP")
    cap=issuer["marketCapUsd"]
    within_cap=300_000_000<=cap<=10_000_000_000
    age=(asof-cap_day).days
    cap_state=("CAP_OUTSIDE_300M_TO_10B" if not within_cap else
               "STALE_CAP_REVERIFY" if age>7 else "CAP_SOURCE_DATE_VERIFIED")
    raw_roster=list(csv.DictReader(io.StringIO(roster_csv)))
    if len(raw_roster)!=762:
        raise ValueError("CURRENT_PDUFA_ROSTER_SIZE")
    roster={}
    for r in raw_roster:
        n=r.get("nct_id")
        if not isinstance(n,str) or n in roster or not NCT.fullmatch(n):
            raise ValueError("CURRENT_PDUFA_DUPLICATE_NCT")
        roster[n]=r
    reviewed={}
    for r in reviews["records"]:
        if r.get("ticker")=="COGT" and r.get("stage")=="post":
            k=(r.get("nctId"),r.get("metricId"))
            if k in reviewed or r.get("independentReview")!="AI_SOURCE_CROSSCHECKED":
                raise ValueError("CURRENT_PDUFA_REVIEW_PROVENANCE")
            reviewed[k]=r
    seen_keys=set()
    seen_nct=set()
    seen_indication=set()
    rows=[]
    for item in data["applications"]:
        key=item.get("applicationKey")
        nct=item.get("trialNctId")
        indication=item.get("indication")
        phase=item.get("phaseOfPivotalEvidence")
        if (not isinstance(key,str) or not key.startswith("COGT-") or
            key in seen_keys or not isinstance(nct,str) or not NCT.fullmatch(nct) or
            nct in seen_nct or not isinstance(indication,str) or
            indication in seen_indication or phase not in (2,3) or
            item.get("pathway")!="NDA" or not item.get("drug") or
            item.get("outcomeAsOf")!="NO_VERIFIED_DECISION_AS_OF_SNAPSHOT" or
            not isinstance(item.get("additionalSponsorReportedDesignations"),list) or
            not all(https(item.get(k)) for k in
                ("trialSourceUrl","applicationAcceptedSourceUrl","outcomeEvidenceUrl")) or
            item["trialSourceUrl"]!="https://clinicaltrials.gov/study/"+nct):
            raise ValueError("CURRENT_PDUFA_APPLICATION_IDENTITY")
        seen_keys.add(key);seen_nct.add(nct);seen_indication.add(indication)
        accepted=day(item.get("applicationAcceptedDate"))
        target=day(item.get("pdufaTargetDate"))
        if (accepted>=target or accepted>snapshot or target<=snapshot or
            item.get("reviewDesignation") not in
            ("PRIORITY_REVIEW","SPONSOR_DID_NOT_STATE_PRIORITY")):
            raise ValueError("CURRENT_PDUFA_DATE_OR_REVIEW_STATUS")
        if phase>=3:
            r=roster.get(nct)
            if (not r or r.get("ticker")!="COGT" or
                item.get("scoreResearchStage")!="post"):
                raise ValueError("CURRENT_PDUFA_PHASE3_ROSTER_MISMATCH")
        else:
            if nct in roster or item.get("scoreResearchStage") is not None:
                raise ValueError("CURRENT_PDUFA_PHASE2_MUST_BE_EXCLUDED")
        grades=[x for (id,metric),x in reviewed.items() if id==nct]
        eligible=within_cap and phase>=3
        phase_result=("PHASE3_PIVOTAL_QUALIFIES_IF_CAP_FRESH" if eligible else
                      "PHASE2_PIVOTAL_EXCLUDED_BY_MIN_PHASE3" if phase<3 else
                      "OUTSIDE_CAP_RESTRICTION")
        if asof>target:
            target_status="TARGET_PASSED_OUTCOME_MUST_BE_REVERIFIED"
        elif asof==target:
            target_status="TARGET_TODAY_DECISION_UNVERIFIED"
        else:
            target_status="PUBLISHED_FUTURE_TARGET_NOT_DECISION"
        if cap_state!="CAP_SOURCE_DATE_VERIFIED" and phase>=3:
            phase_result="ELIGIBILITY_RECHECK_CAP_FRESHNESS" if within_cap else phase_result
        rows.append({
            "applicationKey":key,"ticker":issuer["ticker"],"issuer":issuer["name"],
            "marketCapUsd":cap,"marketCapAsOf":issuer["marketCapAsOf"],
            "marketCapSourceUrl":issuer["marketCapSourceUrl"],
            "marketCapVerification":cap_state,"drug":item["drug"],
            "indication":indication,"pathway":item["pathway"],
            "trialName":item["trialName"],"trialNctId":nct,
            "trialSourceUrl":item["trialSourceUrl"],"pivotalPhase":phase,
            "pipelineRestrictionResult":phase_result,
            "applicationAcceptedDate":item["applicationAcceptedDate"],
            "applicationAcceptedSourceUrl":item["applicationAcceptedSourceUrl"],
            "pdufaTargetDate":item["pdufaTargetDate"],
            "reviewDesignation":item["reviewDesignation"],
            "additionalSponsorReportedDesignations":";".join(item["additionalSponsorReportedDesignations"]),
            "targetStatus":target_status,"sourceVerifiedAsOf":data["sourceAsOf"],
            "outcomeAsOf":item["outcomeAsOf"],
            "reviewedProvisionalMetricCount":len(grades),
            "independentReviewedMetricCount":0,
            "full30MetricRaasScore":"",
            "fdaPassCrlExtensionProbability":"",
            "outcomeData":item["outcomeData"],
            "outcomeEvidenceUrl":item["outcomeEvidenceUrl"],
            "interpretation":"FDA_APPLICATION_TRACKER_NO_VERIFIED_DECISION_OR_VALIDATED_PREDICTION"
        })
    if len(rows)!=3 or {r["pdufaTargetDate"] for r in rows}!={"2026-11-30","2026-12-30","2027-06-29"}:
        raise ValueError("CURRENT_PDUFA_MISSING_OR_DUPLICATE_APPLICATION")
    status={
        "schemaVersion":1,
        "scope":"RAAS_THREE_SOURCE_VERIFIED_COGT_FDA_TARGETS_ONE_PHASE3_QUALIFIER",
        "sourceAsOf":data["sourceAsOf"],
        "generatedAsOf":as_of,
        "uniquePublicIssuers":1,
        "acceptedNdaApplications":len(rows),
        "minimumPhase3EligibleApplications":sum(r["pivotalPhase"]>=3 for r in rows),
        "phase2RegistrationApplicationsExcluded":sum(r["pivotalPhase"]==2 for r in rows),
        "currentCapVerifiedEligiblePhase3Applications":sum(
            r["pivotalPhase"]>=3 and r["marketCapVerification"]=="CAP_SOURCE_DATE_VERIFIED"
            for r in rows),
        "issuedBeforeTargetDates":sum(r["targetStatus"]=="PUBLISHED_FUTURE_TARGET_NOT_DECISION"
                                      for r in rows),
        "aiSourceReviewedPhase3MetricRecords":sum(r["reviewedProvisionalMetricCount"]
                                                 for r in rows if r["pivotalPhase"]>=3),
        "independentReviewed30MetricScores":0,
        "validatedFdaPassCrlExtensionPredictions":0,
        "verifiedFdaOutcomes":0,
        "fdaApplicationTargets":[{"applicationKey":r["applicationKey"],
            "pdufaTargetDate":r["pdufaTargetDate"],"minimumPhase3Eligible":r["pivotalPhase"]>=3}
            for r in rows],
        "warning":"Application-level sources are sponsor acceptance statements, not original FDA letters. One COGT ticker, three separate NDAs; only Phase3 GIST matches strict user Pipeline phase restriction. Two Phase2 pivotal cases are reference-only. A PDUFA TARGET is not a guaranteed decision date. No FDA outcome or model probability is inferred. After source-date, reverify FDA actions and issuer market cap."
    }
    return rows,status

def generate(data,reviews,roster_csv,*,as_of):
    rows,status=build(data,reviews,roster_csv,as_of=as_of)
    buffer=io.StringIO()
    writer=csv.DictWriter(buffer,fieldnames=FIELDS,lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k:safe(v) for k,v in row.items()})
    return buffer.getvalue(),json.dumps(status,indent=2)+"\n"

def main():
    csv_data,status_data=generate(
        json.loads(SOURCE.read_text(encoding="utf-8")),
        json.loads(REVIEWS.read_text(encoding="utf-8")),
        ROSTER.read_text(encoding="utf-8"),
        as_of=date.today().isoformat()
    )
    OUTPUT.write_text(csv_data,encoding="utf-8")
    STATUS.write_text(status_data,encoding="utf-8")
    print(status_data.strip())

if __name__=="__main__":
    main()
