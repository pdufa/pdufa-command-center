#!/usr/bin/env python3
"""Dated, explicitly non-exhaustive 2-NCT CURRENT Phase 3 TOP RAAS audit.

Unlike the 10-trial retrospective post-readout pilot this reads genuinely
recruiting Phase 3 trials and separately source-dated issuer market caps.
No incomplete metric, PDUFA date or FDA prediction is imputed. Expired cap
quotes and phase-status source checks fail CLOSED to non-current eligibility.
"""
from __future__ import annotations

import csv
from datetime import date
import io
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "new-platform/frontend/data/raas-current-pipeline-pre-candidate-snapshots.json"
REVIEWS = ROOT / "new-platform/frontend/data/raas-reviewed-metric-assessments.json"
COHORT = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
LEDGER = ROOT / "new-platform/frontend/public/raas-trial-score-ledger.csv"
OUTPUT = ROOT / "new-platform/frontend/public/raas-current-pipeline-pre-metric-audit.csv"
STATUS = ROOT / "new-platform/frontend/data/raas-current-pipeline-pre-metric-audit-status.json"
NCT = re.compile(r"NCT\d{8}\Z")
METRIC_IDS = tuple(f"pre-{cat}-{item}" for cat in range(1, 7)
                   for item in range(1, 6))
SCORES = {"MATERIAL_ADVERSE": 0, "BELOW_BENCHMARK": 25,
          "MIXED_EVIDENCE": 50, "ABOVE_BENCHMARK": 75,
          "EXCEPTIONAL_EVIDENCE": 100}
FIELDS = (
    "nctId","ticker","company","trialName","drug","indication","researchStage",
    "registryStatus","registryStatusCheckedAt","registryUrl",
    "publicMarket","marketCapUsdAsOfSource","marketCapAsOf",
    "marketCapSourceUrl","readoutExpectedWindow","readoutGuidancePublished",
    "readoutGuidanceUrl","currentSourceQualification",
    "metricId","metricReviewStatus","provisionalMetricScore",
    "observedFinding","sourceDate","sourceUrl","benchmarkSourceUrl",
    "benchmarkContext","observedResult","uncertaintyReview","criticalRiskReview",
    "humanIndependentReview","missingDataRequired","full30MetricRaasScore",
    "fdaPassCrlExtensionProbability","pdufaTarget",
    "currentPdufaEligibility","interpretation"
)


def iso(d: object) -> date:
    if not isinstance(d, str):
        raise ValueError("CURRENT_TOP_INVALID_DATE")
    value = date.fromisoformat(d)
    if value.isoformat() != d:
        raise ValueError("CURRENT_TOP_INVALID_DATE")
    return value


def secure(v: object) -> bool:
    return isinstance(v, str) and re.fullmatch(r"https://[^\s<>\"']+", v) is not None


def cap_state(record: dict, as_of: date, registry_status: str) -> str:
    cap_age = (as_of - iso(record["marketCapAsOf"])).days
    trial_age = (as_of - iso(record["registryStatusCheckedAt"])).days
    if registry_status not in {"RECRUITING", "NOT_YET_RECRUITING",
                               "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}:
        return "NOT_ACTIVE_IN_CURRENT_REGISTRY"
    if record.get("phase3OutcomeAlreadyPublic") is not False:
        return "READOUT_STATUS_NOT_VERIFIED_PRE"
    if cap_age < 0 or trial_age < 0:
        raise ValueError("CURRENT_TOP_FUTURE_SNAPSHOT")
    if cap_age > 7:
        return "STALE_MARKET_CAP_REVERIFY"
    if trial_age > 30:
        return "STALE_REGISTRY_STATUS_REVERIFY"
    if not 300_000_000 <= record["marketCapUsd"] <= 10_000_000_000:
        return "OUTSIDE_MARKET_CAP_RESTRICTIONS"
    if as_of > iso(record["readoutWindowEnd"]):
        return "HISTORICAL_OR_EXPIRED_READOUT_WINDOW"
    return "CURRENT_CAP_AND_PHASE3_SOURCE_VERIFIED_NO_PDUFA"


def safe(cell: object) -> str:
    val = "" if cell is None else str(cell)
    return ("'" + val) if val[:1] in ("=", "+", "-", "@") else val


def build(snapshot: dict, reviews: dict, cohort_csv: str, ledger_csv: str,
          *, as_of: str) -> tuple[list[dict], dict]:
    day = iso(as_of)
    if (snapshot.get("schemaVersion") != 1 or
        snapshot.get("scope") != "RAAS_CURRENT_SOURCE_VERIFIED_PHASE3_CAP_SNAPSHOT_NOT_FDA_PDUFA" or
        reviews.get("schemaVersion") != 1 or
        reviews.get("scope") != "RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY" or
        not isinstance(reviews.get("records"), list) or
        not isinstance(snapshot.get("trialSnapshots"), list)):
        raise ValueError("CURRENT_TOP_SOURCE_SCOPE")
    if iso(snapshot.get("asOf")) > day or iso(reviews.get("sourceAsOf")) > day:
        raise ValueError("CURRENT_TOP_FUTURE_ASSESSMENT")
    cohort = list(csv.DictReader(io.StringIO(cohort_csv)))
    registry = list(csv.DictReader(io.StringIO(ledger_csv)))
    if len(cohort) != 762 or len(registry) != 762:
        raise ValueError("CURRENT_TOP_COHORT_SIZE")
    c_map = {}
    for row in cohort:
        nct = row.get("nct_id")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in c_map:
            raise ValueError("CURRENT_TOP_COHORT_NCT_DUPLICATE")
        c_map[nct] = row
    reg_map = {}
    for row in registry:
        nct = row.get("nctId")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in reg_map:
            raise ValueError("CURRENT_TOP_REGISTRY_NCT_DUPLICATE")
        reg_map[nct] = row
    if set(c_map) != set(reg_map):
        raise ValueError("CURRENT_TOP_ROSTER_REGISTRY_IDENTITY")
    case_map = {}
    for rec in snapshot["trialSnapshots"]:
        nct = rec.get("nctId")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in case_map:
            raise ValueError("CURRENT_TOP_DUPLICATE_CASE")
        c, r = c_map.get(nct), reg_map.get(nct)
        if (not c or not r or
            c["ticker"] != rec.get("ticker") or r["ticker"] != rec.get("ticker") or
            rec.get("researchStage") != "pre" or rec.get("phase") != "PHASE3" or
            rec.get("publicMarket") != "NASDAQ" or
            rec.get("fdaApplicationAccepted") is not False or
            rec.get("pdufaTarget") is not None or
            not isinstance(rec.get("marketCapUsd"), int) or
            isinstance(rec.get("marketCapUsd"), bool) or
            rec["marketCapUsd"] < 0 or
            not all(secure(rec.get(k)) for k in (
                "clinicalRegistryUrl","issuerTrialSourceUrl",
                "marketCapSourceUrl","readoutGuidanceUrl")) or
            rec["clinicalRegistryUrl"] != "https://clinicaltrials.gov/study/" + nct or
            r["sourceUrl"] != rec["clinicalRegistryUrl"] or
            r.get("registryResultsPosted") != "False" or
            rec.get("registryReportedStatus") != r.get("registryStatus") or
            iso(rec.get("readoutGuidancePublished")) > iso(snapshot["asOf"]) or
            iso(rec.get("marketCapAsOf")) > iso(snapshot["asOf"]) or
            iso(rec.get("registryStatusCheckedAt")) > iso(snapshot["asOf"]) or
            iso(rec.get("readoutWindowEnd")) <= iso(snapshot["asOf"])):
            raise ValueError("CURRENT_TOP_CASE_PROVENANCE")
        case_map[nct] = rec
    if set(case_map) != {"NCT07671911", "NCT07363577"}:
        raise ValueError("CURRENT_TOP_NONEXHAUSTIVE_PILOT_IDENTITIES")
    all_r = {}
    for r in reviews["records"]:
        if r.get("nctId") not in case_map or r.get("stage") != "pre":
            continue
        case = case_map[r["nctId"]]
        k = r["nctId"], r["metricId"]
        if (k in all_r or r["metricId"] not in METRIC_IDS or
            r.get("ticker") != case["ticker"] or
            r.get("drug") != case["drug"] or
            r.get("indication", "").casefold() != case["indication"].casefold() or
            r.get("finding") not in SCORES or
            r.get("independentReview") != "AI_SOURCE_CROSSCHECKED" or
            not secure(r.get("sourceUrl")) or
            not secure(r.get("benchmarkSourceUrl")) or
            r["sourceUrl"] == r["benchmarkSourceUrl"] or
            iso(r.get("sourceDate")) > iso(r.get("assessedAt")) or
            iso(r["assessedAt"]) > iso(reviews["sourceAsOf"]) or
            not all(len(str(r.get(x, ""))) >= 12 for x in (
                "observedResult","benchmarkContext","uncertaintyReview",
                "criticalRiskReview","reviewerMethod"))):
            raise ValueError("CURRENT_TOP_METRIC_REVIEW_INVALID")
        all_r[k] = r
    rows = []
    states = {}
    by_trial = {}
    for nct in sorted(case_map):
        case = case_map[nct]
        reg = reg_map[nct]
        state = cap_state(case, day, reg["registryStatus"])
        states[nct] = state
        by_trial[nct] = 0
        for metric in METRIC_IDS:
            r = all_r.get((nct, metric))
            by_trial[nct] += int(r is not None)
            rows.append({
                "nctId":nct,"ticker":case["ticker"],
                "company":case["company"],"trialName":case["trialName"],
                "drug":case["drug"],"indication":case["indication"],
                "researchStage":"TOP_PRE_READOUT_RESEARCH",
                "registryStatus":reg["registryStatus"],
                "registryStatusCheckedAt":case["registryStatusCheckedAt"],
                "registryUrl":case["clinicalRegistryUrl"],
                "publicMarket":case["publicMarket"],
                "marketCapUsdAsOfSource":case["marketCapUsd"],
                "marketCapAsOf":case["marketCapAsOf"],
                "marketCapSourceUrl":case["marketCapSourceUrl"],
                "readoutExpectedWindow":case["readoutExpectedWindow"],
                "readoutGuidancePublished":case["readoutGuidancePublished"],
                "readoutGuidanceUrl":case["readoutGuidanceUrl"],
                "currentSourceQualification":state,
                "metricId":metric,
                "metricReviewStatus":"AI_SOURCE_CROSSCHECKED_PROVISIONAL" if r else "NOT_SCORED",
                "provisionalMetricScore":SCORES[r["finding"]] if r else "",
                "observedFinding":r["finding"] if r else "",
                "sourceDate":r["sourceDate"] if r else "",
                "sourceUrl":r["sourceUrl"] if r else "",
                "benchmarkSourceUrl":r["benchmarkSourceUrl"] if r else "",
                "benchmarkContext":r["benchmarkContext"] if r else "",
                "observedResult":r["observedResult"] if r else "",
                "uncertaintyReview":r["uncertaintyReview"] if r else "",
                "criticalRiskReview":r["criticalRiskReview"] if r else "",
                "humanIndependentReview":False,
                "missingDataRequired":"" if r else "MISSING_METRIC_SPECIFIC_REVIEW",
                "full30MetricRaasScore":"",
                "fdaPassCrlExtensionProbability":"",
                "pdufaTarget":"",
                "currentPdufaEligibility":"NOT_YET_FDA_ACCEPTED_APPLICATION_OR_PDUFA",
                "interpretation":"CURRENT_PHASE3_PARTIAL_TOP_METRICS_NO_VALIDATED_OVERALL_OR_FDA_PREDICTION"
            })
    count = sum(1 for r in rows if r["provisionalMetricScore"] != "")
    status = {
        "schemaVersion":1,
        "scope":"RAAS_DATED_TWO_CURRENT_PHASE3_TOP_TRIAL_PARTIAL_METRICS_NO_PDUFA",
        "sourceAsOf":as_of,
        "snapshotSourceAsOf":snapshot["asOf"],
        "pilotPhase3TrialNcts":list(sorted(case_map)),
        "pilotTrialCount":len(case_map),
        "pilotMetricSlots":len(rows),
        "provisionalAiReviewedMetricSlots":count,
        "missingMetricSlots":len(rows)-count,
        "perTrialProvisionalReviewCount":by_trial,
        "currentCapAndPhase3SourceVerifiedAsOf":sum(
            s == "CURRENT_CAP_AND_PHASE3_SOURCE_VERIFIED_NO_PDUFA"
            for s in states.values()),
        "eligibilityByNct":states,
        "humanIndependentReviewedMetricSlots":0,
        "complete30MetricRaasScores":0,
        "confirmedPdufaTargets":0,
        "calibratedFdaPredictions":0,
        "warning":"Two sampled current source-checked trials, not a comprehensive screen of the active $300M-$10B public Phase 3 universe. A cap quote becomes stale after seven calendar days and trial-status source after 30 days; no new price/status is invented. Both are pre-readout, and neither has an accepted NDA/BLA or verified PDUFA date. 0–100 figures are research-only metric bands, never complete 30/30, FDA PASS/CRL/extension probabilities or trade signals."
    }
    return rows, status


def generate(snapshot, reviews, cohort_csv, ledger_csv, *, as_of):
    rows, status = build(snapshot, reviews, cohort_csv, ledger_csv, as_of=as_of)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k:safe(v) for k,v in row.items()})
    return out.getvalue(), json.dumps(status, indent=2) + "\n"


def main():
    as_of = date.today().isoformat()
    csv_data, json_data = generate(
        json.loads(SNAPSHOT.read_text(encoding="utf8")),
        json.loads(REVIEWS.read_text(encoding="utf8")),
        COHORT.read_text(encoding="utf8"),
        LEDGER.read_text(encoding="utf8"), as_of=as_of
    )
    OUTPUT.write_text(csv_data, encoding="utf8")
    STATUS.write_text(json_data, encoding="utf8")
    print(json_data.strip())


if __name__ == "__main__":
    main()
