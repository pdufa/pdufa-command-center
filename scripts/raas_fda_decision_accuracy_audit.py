#!/usr/bin/env python3
"""RAAS three-way FDA first-disclosed-goal audit. Never trains or alters trading.

PASS = approval on/before original goal; CRL = complete response on/before
original goal; EXTENSION = publicly documented formal FDA goal extension
on/before the original goal, regardless of ultimate later approval.
Clinical outcomes and retrospective price research are NOT prediction features.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from math import isfinite, log, sqrt
from pathlib import Path
import csv
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CLASSES = ("PASS", "CRL", "EXTENSION")
SCOPES = {
    "protocol": "RAAS_FDA_THREE_WAY_VALIDATION_PROTOCOL",
    "roster": "RAAS_FDA_THREE_WAY_PROSPECTIVE_ELIGIBLE_CASE_ROSTER",
    "forecasts": "RAAS_FDA_THREE_WAY_CHRONOLOGIC_FROZEN_FORECASTS",
    "outcomes": "RAAS_FDA_THREE_WAY_INDEPENDENT_FDA_ACTIONS",
}
FDA_LINK = re.compile(r"^https://(?:www\.fda\.gov|www\.accessdata\.fda\.gov|download\.open\.fda\.gov)/\S+$")
LINK = re.compile(r"^https://[a-z0-9.-]+\.[a-z]{2,}/\S+$", re.I)
IDENT = re.compile(r"^[A-Z0-9][A-Z0-9_|:.-]{2,160}$")


def gate(ok, code):
    if not ok:
        raise ValueError("RAAS_FDA_THREE_WAY_" + code)


def day(s):
    gate(isinstance(s, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s),
         "INVALID_DATE")
    try:
        return date.fromisoformat(s)
    except ValueError as exc:
        raise ValueError("RAAS_FDA_THREE_WAY_INVALID_DATE") from exc


def utc(s):
    gate(isinstance(s, str) and re.fullmatch(
        r"\d{4}-\d{2}T\d{2}:\d{2}:\d{2}Z", s), "INVALID_UTC")
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError("RAAS_FDA_THREE_WAY_INVALID_UTC") from exc


def identity(s):
    gate(isinstance(s, str) and IDENT.fullmatch(s), "INVALID_CASE_ID")
    return s


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        gate(bool(reader.fieldnames) and len(reader.fieldnames) ==
             len(set(reader.fieldnames)), "CSV_COLUMNS_INVALID")
        return list(reader)


def parse_prospective(protocol, roster, forecasts, outcomes):
    gate(type(protocol) is dict and protocol.get("schemaVersion") == 1
         and protocol.get("scope") == SCOPES["protocol"]
         and protocol.get("classes") == list(CLASSES)
         and protocol.get("protocolVersion") == "FDA_GOAL_DISPOSITION_V1"
         and protocol.get("approvalOfHistoricalAccuracy") is False
         and protocol.get("approvalOfCalibratedRAASMetrics") is False
         and protocol.get("predictionTarget") ==
         "FIRST_DISCLOSED_PDUFA_GOAL_DISPOSITION_AS_OF_OR_BEFORE_ORIGINAL_GOAL_DATE",
         "PROTOCOL_UNTRUSTED")
    start = utc(protocol["prospectiveEarliestFreezeUTC"])
    gate(type(protocol.get("minAdjudicatedProspectivePrograms")) is int and
         protocol["minAdjudicatedProspectivePrograms"] >= 30 and
         type(protocol.get("minProgramsPerClass")) is int and
         protocol["minProgramsPerClass"] >= 5, "LOWERED_VALIDATION_THRESHOLD")
    for n, feed in (("roster", roster), ("forecasts", forecasts), ("outcomes", outcomes)):
        gate(type(feed) is dict and feed.get("schemaVersion") == 1 and
             feed.get("scope") == SCOPES[n] and type(feed.get("records")) is list
             and len(feed["records"]) <= 20000, "INVALID_" + n.upper())
        day(feed["sourceAsOf"])
    gate(type(roster.get("cohortCompletenessIndependentlyVerified")) is bool and
         type(forecasts.get("immutableReceiptIndependentAuditComplete")) is bool and
         type(outcomes.get("independentFdaCensusAdjudicated")) is bool,
         "MISSING_INDEPENDENT_AUDIT_STATUS")
    cases, families, cycles = {}, set(), set()
    for c in roster["records"]:
        gate(type(c) is dict, "INVALID_ROSTER_CASE")
        k = identity(c.get("caseId"))
        fam = identity(c.get("issuerProgramFamilyId"))
        app = identity(c.get("applicationId"))
        cycle = c.get("reviewCycle")
        gate(type(cycle) is int and cycle > 0, "INVALID_REVIEW_CYCLE")
        goal = day(c["originalPdufaGoalDate"])
        public = day(c["goalFirstPublicAtDate"])
        registration = utc(c["registeredAtUTC"])
        gate(k not in cases and fam not in families and (app, cycle) not in cycles,
             "DUPLICATE_PROGRAM_OR_REVIEW_CYCLE")
        gate(registration >= start and registration.date() < goal and
             public <= registration.date() and public < goal and
             LINK.fullmatch(c.get("goalFirstPublicSourceUrl", "")),
             "ROSTER_PREGOAL_SOURCE_INVALID")
        cases[k] = c
        families.add(fam)
        cycles.add((app, cycle))
    preds = {}
    for p in forecasts["records"]:
        gate(type(p) is dict, "INVALID_FORECAST_ROW")
        k = identity(p.get("caseId"))
        gate(k in cases and k not in preds, "UNREGISTERED_OR_DUPLICATE_FORECAST")
        timestamp = utc(p.get("frozenAtUTC"))
        goal = day(cases[k]["originalPdufaGoalDate"])
        registration = utc(cases[k]["registeredAtUTC"])
        gate(start <= timestamp and registration <= timestamp and timestamp.date() < goal
             and day(p.get("asOfDate")) == timestamp.date() and
             LINK.fullmatch(p.get("immutableReceiptUrl", "")) and
             type(p.get("receiptIndependentlyVerified")) is bool and
             isinstance(p.get("modelVersion"), str) and len(p["modelVersion"]) > 2,
             "PREDICTION_NOT_FROZEN_PREGOAL")
        facts = p.get("publicEvidence")
        gate(type(facts) is list and 0 < len(facts) <= 100,
             "FORECAST_EVIDENCE_REQUIRED")
        for fact in facts:
            gate(type(fact) is dict and
                 LINK.fullmatch(fact.get("url", "")) and
                 day(fact["firstPublicDate"]) < timestamp.date(),
                 "FUTURE_PUBLIC_EVIDENCE_LEAKAGE")
        status = p.get("status")
        gate(status in ("PREDICTED", "ABSTAIN"), "FORECAST_STATUS_UNRECOGNIZED")
        if status == "PREDICTED":
            probs = p.get("probabilities")
            gate(type(probs) is dict and set(probs) == set(CLASSES),
                 "THREE_PROBABILITIES_REQUIRED")
            gate(all(type(probs[c]) in (int, float) and isfinite(probs[c])
                     and 0 <= probs[c] <= 1 for c in CLASSES) and
                 abs(sum(probs.values()) - 1) <= 1e-8,
                 "THREE_WAY_PROBABILITIES_INVALID")
            gate(p.get("predictedClass") == max(CLASSES, key=lambda c: probs[c])
                 and p.get("abstainReason") is None,
                 "PREDICTION_ARGMAX_INCONSISTENT")
        else:
            gate(p.get("probabilities") is None and p.get("predictedClass") is None
                 and isinstance(p.get("abstainReason"), str) and
                 p["abstainReason"].strip(),
                 "ABSTENTION_MUST_HAVE_NO_PROBABILITIES")
        preds[k] = p
    labels = {}
    for o in outcomes["records"]:
        gate(type(o) is dict, "OUTCOME_RECORD_INVALID")
        k = identity(o.get("caseId"))
        gate(k in cases and k not in labels, "DUPLICATE_OR_UNREGISTERED_OUTCOME")
        actual = o.get("actualClass")
        gate(actual in CLASSES, "OUTCOME_CATEGORY_INVALID")
        goal = day(cases[k]["originalPdufaGoalDate"])
        happened = day(o["dispositionDate"])
        disclosed = utc(o["firstPublicOutcomeAtUTC"])
        gate(day(cases[k]["goalFirstPublicAtDate"]) < happened <= goal
             and disclosed.date() >= happened,
             "OUTCOME_DISPOSITION_CHRONOLOGY_INVALID")
        gate(FDA_LINK.fullmatch(o.get("officialFdaSourceUrl", "")) and
             type(o.get("independentFDAReviewerVerified")) is bool and
             (actual == "EXTENSION") ==
             (o.get("formalFDAExtensionDocumented") is True),
             "EXTENSION_OR_FDA_PRIMARY_SOURCE_MISSING")
        if k in preds:
            gate(utc(preds[k]["frozenAtUTC"]).date() < happened,
                 "PREDICTION_AFTER_FDA_OUTCOME")
        labels[k] = o
    return cases, preds, labels


def score_three_way(scored, decided):
    gate(type(decided) is int and decided >= len(scored), "INVALID_COVERAGE_DENOMINATOR")
    n = len(scored)
    result = {
        "scope": "MATHEMATICAL_DIAGNOSTIC_NOT_FDA_VALIDATION",
        "countScored": n, "decidedEligibleCount": decided,
        "abstentionsAndUnverified": decided - n,
        "coverage": round(n/decided, 5) if decided else None,
        "accuracy": None, "balancedAccuracy": None,
        "multiclassBrier": None, "logLoss": None, "expectedCalibrationError": None,
        "alwaysPASSBaselineAccuracy": None, "accuracyWilson95": None,
        "perClassRecall": {k: None for k in CLASSES},
        "confusion": {k: {j: 0 for j in CLASSES} for k in CLASSES},
        "trueClassCounts": {k: 0 for k in CLASSES},
        "calibrationBins": [], "modelValidated": False,
    }
    if not n:
        return result
    briers, logloss, bins = [], [], defaultdict(list)
    correct = 0
    for probs, truth in scored:
        gate(truth in CLASSES and type(probs) is dict and
             set(probs) == set(CLASSES) and
             all(type(probs[k]) in (int, float) and isfinite(probs[k])
                 and 0 <= probs[k] <= 1 for k in CLASSES) and
             abs(sum(probs.values())-1) <= 1e-8,
             "MATH_VECTOR_OR_LABEL_INVALID")
        winner = max(CLASSES, key=lambda k: probs[k])
        hit = int(winner == truth)
        correct += hit
        result["confusion"][truth][winner] += 1
        result["trueClassCounts"][truth] += 1
        briers.append(sum((probs[k]-int(k == truth))**2 for k in CLASSES))
        logloss.append(-log(max(probs[truth],1e-15)))
        confidence = probs[winner]
        bins[min(4,int(confidence*5))].append((confidence,hit))
    result["accuracy"] = round(correct/n, 5)
    result["multiclassBrier"] = round(sum(briers)/n, 6)
    result["logLoss"] = round(sum(logloss)/n, 6)
    result["alwaysPASSBaselineAccuracy"] = round(result["trueClassCounts"]["PASS"]/n,5)
    for k in CLASSES:
        support = result["trueClassCounts"][k]
        if support:
            result["perClassRecall"][k] = round(result["confusion"][k][k]/support,5)
    # No EXTENSION ground-truth: three-way balanced accuracy is UNDEFINED.
    if all(result["perClassRecall"][k] is not None for k in CLASSES):
        result["balancedAccuracy"] = round(sum(result["perClassRecall"].values())/3,5)
    ece = 0
    for b in sorted(bins):
        group = bins[b]
        mean = sum(x for x,_ in group)/len(group)
        observed = sum(x for _,x in group)/len(group)
        ece += len(group)/n*abs(mean-observed)
        result["calibrationBins"].append({
            "bin":b,"count":len(group),
            "meanPredictedConfidence":round(mean,5),"observedAccuracy":round(observed,5)})
    result["expectedCalibrationError"] = round(ece,6)
    z=1.959963984540054
    proportion=correct/n
    center=(proportion+z*z/(2*n))/(1+z*z/n)
    spread=z*sqrt(proportion*(1-proportion)/n+z*z/(4*n*n))/(1+z*z/n)
    result["accuracyWilson95"]=[round(max(0,center-spread),5),round(min(1,center+spread),5)]
    return result


def legacy_audit(rows):
    required={"event_key","ticker","pdufa_date","actual_outcome","model_class",
              "correct","independence_status","public_model_class"}
    gate(bool(rows) and len(rows)<=100000 and required <= set(rows[0]),
         "HISTORICAL_SOURCE_COLUMNS_MISSING")
    seen=set()
    years=defaultdict(Counter)
    total=Counter()
    queue=[]
    for r in rows:
        k=r["event_key"]
        gate(bool(k) and k not in seen,"HISTORICAL_DUPLICATE_EVENT")
        seen.add(k)
        actual=r["actual_outcome"].upper().strip()
        proposed=r["model_class"].upper().strip()
        gate(actual in ("APPROVED","CRL") and proposed in ("APPROVED","CRL"),
             "HISTORICAL_LABEL_UNKNOWN")
        match=actual==proposed
        gate(r["correct"].lower().strip() == ("true" if match else "false"),
             "HISTORICAL_REPORTED_MATCH_INCONSISTENT")
        public=r["public_model_class"].upper().strip()
        gate(public in ("","REVIEW","APPROVED","CRL"),
             "HISTORICAL_PUBLIC_CALL_INVALID")
        y=day(r["pdufa_date"]).year
        for counters in (total,years[y]):
            counters["cases"]+=1
            counters["correct"]+=int(match)
            counters["approvals"]+=int(actual=="APPROVED")
            counters["crls"]+=int(actual=="CRL")
            counters["publicCalls"]+=int(public in ("APPROVED","CRL"))
            counters["publicCallsRight"]+=int(public==actual)
        queue.append({"event_key":k,"ticker":r["ticker"],"pdufa_date":r["pdufa_date"],
                      "actual_outcome":actual,
                      "validationStatus":"RETROSPECTIVE_ONLY_NOT_THREE_WAY_FROZEN",
                      "missingEvidence":"original goal versions, independent review-cycle census, independently archived preaction three-way probabilities, official action or formal extension"})
    n=total["cases"]
    return ({
        "cases":n,"approved":total["approvals"],"CRL":total["crls"],"extensionCases":0,
        "legacyRetrospectiveCorrect":total["correct"],
        "legacyRetrospectiveAccuracyPct":round(total["correct"]/n*100,2),
        "alwaysApproveCorrect":total["approvals"],
        "alwaysApproveAccuracyPct":round(total["approvals"]/n*100,2),
        "legacyVsAlwaysApprovePctPoints":round((total["correct"]-total["approvals"])/n*100,2),
        "publicDirectionalCallsWithoutCertifiedThreeWayFreeze":total["publicCalls"],
        "publicDirectionalCorrect":total["publicCallsRight"],
        "publicDirectionalCoveragePct":round(total["publicCalls"]/n*100,2),
        "byYear":{str(y):{"cases":c["cases"],"actualApprovals":c["approvals"],
                         "actualCRLs":c["crls"],"legacyCorrect":c["correct"],
                         "legacyAccuracyPct":round(c["correct"]/c["cases"]*100,2)}
                  for y,c in sorted(years.items())},
        "independentlyValidated":False,
        "warning":"146 outcome-selected retrospective binary rows are not a complete blind FDA review-cycle cohort or three-way predictive validation."
    },queue)


def legacy_freeze_inventory(rows):
    required={"event_key","fda_regulatory_case_id","pdufa_date","model_version",
              "frozen_at","prospective_eligible","forced_direction"}
    gate(bool(rows) and required <= set(rows[0]),"OLD_FREEZE_COLUMNS_MISSING")
    by_version=Counter()
    cases=defaultdict(set)
    post_goal=0
    for r in rows:
        version=r["model_version"]
        gate(version.startswith("FDA-DIRECTIONAL-100-V1"),"OLD_VERSION_UNRECOGNIZED")
        frozen=utc(r["frozen_at"])
        goal=day(r["pdufa_date"])
        by_version[version]+=1
        if frozen.date()>=goal:
            post_goal+=1
        if (r["prospective_eligible"]=="YES" and
            r.get("count_in_coverage")=="YES" and frozen.date()<goal):
            cases[version].add(r["fda_regulatory_case_id"])
    return {
        "rowsAcrossRepeatedVersions":len(rows),
        "modelVersions":dict(sorted(by_version.items())),
        "latestV1_9ProspectivelyEligibleUniqueCases":len(cases.get("FDA-DIRECTIONAL-100-V1.9",set())),
        "rowsFrozenOnOrAfterGoalDate":post_goal,
        "certifiedThreeClassProbabilities":0,
        "portedToThreeWayLedger":0,
        "warning":"Old directional predictions have repeated model versions and no certified three-way probability vector; cannot be silently promoted into PASS/CRL/EXTENSION validation."
    }


def prospective_audit(protocol, roster, forecasts, outcomes, asof):
    cases,preds,labels=parse_prospective(protocol,roster,forecasts,outcomes)
    cutoff=utc(asof)
    gate(cutoff.date()>=day(protocol["sourceAsOf"]), "REPORT_EARLIER_THAN_PROTOCOL")
    scored=[]
    pending=unverified=unverified_receipt=abstained=not_frozen=decided=0
    statuses=[]
    for k,c in sorted(cases.items()):
        p=preds.get(k)
        o=labels.get(k)
        if o is None or utc(o["firstPublicOutcomeAtUTC"])>cutoff:
            status="FDA_GOAL_OUTCOME_PENDING"
            pending+=1
        elif o["independentFDAReviewerVerified"] is not True:
            status="OUTCOME_INDEPENDENT_SOURCE_UNVERIFIED"
            unverified+=1
        else:
            decided+=1
            if p is None:
                status="MISSING_PUBLISHED_FORECAST"
                not_frozen+=1
            elif p["status"]=="ABSTAIN":
                status="ABSTAINED"
                abstained+=1
            elif p["receiptIndependentlyVerified"] is not True:
                status="FORECAST_RECEIPT_UNVERIFIED"
                unverified_receipt+=1
            else:
                status="MATH_RESEARCH_ONLY"
                scored.append((p["probabilities"],o["actualClass"]))
        statuses.append({"caseId":k,"status":status,
                         "originalPdufaGoalDate":c["originalPdufaGoalDate"]})
    m=score_three_way(scored,decided)
    criteria=[
        protocol["cohortCompleteVerified"],
        protocol["immutableForecastReceiptAuditComplete"],
        protocol["FDAOutcomeAdjudicationIndependentAuditComplete"],
        protocol["issuerDisjointHoldoutIndependentAuditComplete"],
        protocol["modelPreRegistrationIndependentAuditComplete"],
        roster["cohortCompletenessIndependentlyVerified"],
        forecasts["immutableReceiptIndependentAuditComplete"],
        outcomes["independentFdaCensusAdjudicated"],
        decided>=protocol["minAdjudicatedProspectivePrograms"],
        all(m["trueClassCounts"][c]>=protocol["minProgramsPerClass"] for c in CLASSES),
        len(scored)>0,
    ]
    return {
        "status":"RESEARCH_ONLY_PENDING_INDEPENDENT_PROSPECTIVE_VALIDATION",
        "registeredEligibleCycleCount":len(cases),
        "frozenThreeClassPredictions":len(preds),
        "independentlyReviewedFDAOutcomes":decided,
        "pendingOutcomes":pending,"unverifiedOutcomes":unverified,
        "noForecast":not_frozen,"abstained":abstained,
        "unverifiedFreezeReceipts":unverified_receipt,
        "coveredScoredCases":len(scored),
        "independentGatesPassed":sum(bool(x) for x in criteria),
        "independentGatesRequired":len(criteria),
        "mathMetrics":m,"verifiedFDAAccuracyPct":None,
        "approvedModel":False,"approvedRAASMetrics":0,
        "statuses":statuses,
        "warnings":[
            "Extension is a formal goal change before the original target, NOT final approval after a revised target.",
            "No threshold/model selection on outcomes from the holdout.",
            "Missing and abstained decisions remain part of coverage denominator.",
            "Green software tests never establish independent FDA predictive accuracy.",
        ]
    }


def execute(folder=DATA, asof="2026-11-03T23:59:59Z"):
    folder=Path(folder)
    historical,queue=legacy_audit(csv_rows(folder/"prediction_engine_history.csv"))
    frozen=legacy_freeze_inventory(csv_rows(folder/"fda_directional_100pct_freezes.csv"))
    prospective=prospective_audit(
        load_json(folder/"raas_fda_three_way_protocol.json"),
        load_json(folder/"raas_fda_three_way_eligible_cases.json"),
        load_json(folder/"raas_fda_three_way_frozen_forecasts.json"),
        load_json(folder/"raas_fda_three_way_outcomes.json"), asof)
    return {
        "schemaVersion":1,"scope":"RAAS_FDA_THREE_WAY_DECISION_ACCURACY_AUDIT",
        "asOfUTC":asof,"status":"BENCHMARK_INSTALLED_NO_VALIDATED_THREE_WAY_ACCURACY",
        "historicalBinaryRetrospective":historical,
        "olderFrozenBinaryDirections":frozen,
        "threeWayProspective":prospective,
        "historicalReviewQueue":queue,
        "approvedBestPredictiveModel":None,
        "approvedFDAOutcomeAccuracyPct":None,
        "approvedRAASMetricCalibrations":0,
        "mostImportantNextGate":"Independently certify complete FDA application/review-cycle denominator, freeze three-way predictions before action, then source-adjudicate original-goal PASS/CRL/EXTENSION outcomes."
    }


def export(report, report_path, queue_path):
    json_file=Path(report_path)
    json_file.parent.mkdir(parents=True,exist_ok=True)
    json_file.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    path=Path(queue_path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as f:
        cols=["event_key","ticker","pdufa_date","actual_outcome","validationStatus","missingEvidence"]
        w=csv.DictWriter(f,fieldnames=cols)
        w.writeheader()
        w.writerows(report["historicalReviewQueue"])


def main():
    asof=os.getenv("RAAS_FDA_EVALUATION_AS_OF_UTC","2026-11-03T23:59:59Z")
    report=execute(DATA,asof)
    export(report,os.getenv("RAAS_FDA_ACCURACY_JSON",str(ROOT/"raas-fda-decision-accuracy.json")),
           os.getenv("RAAS_FDA_ACCURACY_QUEUE_CSV",str(ROOT/"raas-fda-historical-source-queue.csv")))
    brief={
        "status":report["status"],
        "legacyCohortCases":report["historicalBinaryRetrospective"]["cases"],
        "legacyRetrospectiveAccuracyPct":report["historicalBinaryRetrospective"]["legacyRetrospectiveAccuracyPct"],
        "alwaysApproveBaselinePct":report["historicalBinaryRetrospective"]["alwaysApproveAccuracyPct"],
        "existingBinaryFreezeCasesV1_9":report["olderFrozenBinaryDirections"]["latestV1_9ProspectivelyEligibleUniqueCases"],
        "frozenThreeWayPredictions":report["threeWayProspective"]["frozenThreeClassPredictions"],
        "FDAThreeWayValidatedAccuracyPct":None,"modelApproved":False}
    print(json.dumps(brief,sort_keys=True))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as f:
            f.write("\n### RAAS PASS / CRL / EXTENSION outcome accuracy\n\n"
                    "Research framework complete, NO validated predictive accuracy.\n\n"
                    +json.dumps(brief,indent=2)+"\n")


if __name__=="__main__":
    main()
