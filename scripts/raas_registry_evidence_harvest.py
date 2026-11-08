#!/usr/bin/env python3
"""Source-backed ClinicalTrials.gov evidence harvest for exact research-cohort NCTs.

Collects factual primary registry and posted-results evidence. DOES NOT assign
TOP/BOTTOM, regulatory PDUFA, RAAS component scores or clinical success odds.
A missing source remains missing; unknown never scores zero.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
COHORT = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
GAPS = ROOT / "data/raas_registry_missing_backfill.json"
DEST = ROOT / "data/raas_registry_live_evidence.json"
API = "https://clinicaltrials.gov/api/v2/studies"
NCT = re.compile(r"NCT\d{8}\Z")
BATCH = 12
HEADERS = {"User-Agent": "pdufa-raas-source-evidence-collector/1.0", "Accept": "application/json"}

def cohort():
    with COHORT.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if not 1 <= len(rows) <= 25000:
        raise ValueError("Unexpected research source population")
    by_id = {}
    for row in rows:
        ident = row.get("nct_id", "")
        if not NCT.fullmatch(ident) or ident in by_id or not row.get("ticker"):
            raise ValueError("Invalid or duplicate NCT in research pool")
        by_id[ident] = row["ticker"]
    return by_id

def chunks(items, n=BATCH):
    for i in range(0, len(items), n):
        yield items[i:i+n]

def request_batch(ids, delay=0.7):
    query = urlencode({"query.id": ",".join(ids), "pageSize": 100, "format": "json"})
    url = API + "?" + query
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=35) as resp:
                raw = resp.read(15_000_001)
            if len(raw) > 15_000_000:
                raise ValueError("CT_GOV_RESPONSE_TOO_LARGE")
            data = json.loads(raw)
            return verify_batch(data, ids)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            if attempt == 2:
                raise
            time.sleep(delay * (2**attempt))
    raise RuntimeError("Fetch retries exhausted")

def verify_batch(payload, requested):
    if not isinstance(payload, dict) or not isinstance(payload.get("studies"), list):
        raise ValueError("CT_GOV_BATCH_SHAPE_INVALID")
    if payload.get("nextPageToken"):
        raise ValueError("CT_GOV_UNEXPECTED_PAGINATION")
    permitted = set(requested)
    out = {}
    for study in payload["studies"]:
        if not isinstance(study, dict):
            raise ValueError("CT_GOV_STUDY_INVALID")
        identifier = (study.get("protocolSection") or {}).get("identificationModule") or {}
        nct = identifier.get("nctId")
        if nct not in permitted or nct in out:
            raise ValueError("CT_GOV_CROSS_TRIAL_OR_DUPLICATE")
        out[nct] = study
    return out

def trim(text, n=300):
    return str(text or "").strip()[:n]

def extract(nct, ticker, study, fetched_at):
    protocol = study.get("protocolSection") or {}
    status = protocol.get("statusModule") or {}
    ident = protocol.get("identificationModule") or {}
    sponsor = protocol.get("sponsorCollaboratorsModule") or {}
    design = protocol.get("designModule") or {}
    design_info = design.get("designInfo") or {}
    masking_info = design_info.get("maskingInfo") or {}
    enroll_info = design.get("enrollmentInfo") or {}
    if not isinstance(design_info, dict) or not isinstance(masking_info, dict) or not isinstance(enroll_info, dict):
        raise ValueError("CT_GOV_DESIGN_INFO_INVALID")
    conditions_module = protocol.get("conditionsModule") or {}
    if not isinstance(conditions_module, dict):
        raise ValueError("CT_GOV_CONDITIONS_MODULE_INVALID")
    conditions = conditions_module.get("conditions") or []
    if not isinstance(conditions, list):
        raise ValueError("CT_GOV_CONDITIONS_INVALID")
    arms = protocol.get("armsInterventionsModule") or {}
    outcomes = protocol.get("outcomesModule") or {}
    if not isinstance(arms, dict):
        raise ValueError("CT_GOV_INTERVENTIONS_MODULE_INVALID")
    interventions = arms.get("interventions") or []
    if not isinstance(interventions, list):
        raise ValueError("CT_GOV_INTERVENTIONS_INVALID")
    results = study.get("resultsSection") or {}
    reported = (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures") or []
    serious = (results.get("adverseEventsModule") or {}).get("seriousEvents") or []
    has = study.get("hasResults")
    if not isinstance(has, bool):
        raise ValueError("CT_GOV_RESULTS_FLAG_INVALID")
    if (has is False and (reported or serious)) or not isinstance(reported, list):
        raise ValueError("CT_GOV_POSTED_RESULTS_INCONSISTENT")
    primary = outcomes.get("primaryOutcomes") or []
    if not isinstance(primary, list):
        raise ValueError("CT_GOV_PRIMARY_OUTCOMES_INVALID")
    registry_date = (status.get("studyFirstPostDateStruct") or {}).get("date")
    last_update = (status.get("lastUpdatePostDateStruct") or {}).get("date")
    results_date = (status.get("resultsFirstPostDateStruct") or {}).get("date")
    def one_outcome(out):
        analyses = out.get("analyses") or []
        classes = out.get("classes") or []
        measures = []
        for cl in classes[:20]:
            for cat in (cl.get("categories") or [])[:20]:
                for m in (cat.get("measurements") or [])[:30]:
                    measures.append({k: m.get(k) for k in (
                        "groupId", "value", "spread", "lowerLimit", "upperLimit") if m.get(k) is not None})
        return {
            "type": out.get("type"), "title": trim(out.get("title"), 450),
            "timeFrame": trim(out.get("timeFrame"), 150),
            "unit": trim(out.get("unitOfMeasure"), 130),
            "groups": [{"id":trim(g.get("id"), 35),
                        "title":trim(g.get("title"), 180)}
                       for g in (out.get("groups") or [])[:30] if isinstance(g, dict)],
            "measurements": measures[:60],
            "analyses": [{k:a.get(k) for k in (
                "pValue", "pValueComment", "method", "paramType",
                "paramValue", "ciPctValue", "ciLowerLimit", "ciUpperLimit",
                "groupIds") if a.get(k) is not None} for a in analyses[:30]],
            "analysesCount": len(analyses), "measurementsTruncated": len(measures)>60,
        }
    posted_primary = [o for o in reported if o.get("type")=="PRIMARY"]
    posted_other = [o for o in reported if o.get("type")!="PRIMARY"]
    return {
        "nctId": nct, "ticker": ticker,
        "sourceUrl": f"https://clinicaltrials.gov/study/{nct}",
        "apiSourceUrl": f"https://clinicaltrials.gov/api/v2/studies/{nct}",
        "sourceSha256": hashlib.sha256(json.dumps(study, sort_keys=True,
            separators=(",",":")).encode()).hexdigest(),
        "fetchedAt": fetched_at, "registryFirstPosted": registry_date,
        "registryLastUpdated": last_update, "registryStatus": status.get("overallStatus"),
        "registryTitle": trim(ident.get("briefTitle"), 450),
        "leadSponsor": trim((sponsor.get("leadSponsor") or {}).get("name"), 200),
        "registeredPhases": design.get("phases") or [],
        "registeredDesign": {
            "allocation": trim(design_info.get("allocation"), 35),
            "masking": trim(masking_info.get("masking"), 35),
            "interventionModel": trim(design_info.get("interventionModel"), 55),
            "studyType": trim(design.get("studyType"), 45),
            "enrollment": enroll_info.get("count") if isinstance(enroll_info.get("count"), int) and not isinstance(enroll_info.get("count"), bool) and 0 < enroll_info["count"] <= 1000000 else None,
            "enrollmentType": trim(enroll_info.get("type"), 30)
        },
        "registeredConditions": [trim(x, 180)
            for x in conditions[:30] if isinstance(x, str) and trim(x, 180)],
        "registeredInterventions": [trim(x.get("name"), 180)
            for x in interventions[:30] if isinstance(x, dict) and trim(x.get("name"), 180)],
        "registeredPrimaryOutcomes": [{"measure":trim(x.get("measure"),350),
            "timeFrame":trim(x.get("timeFrame"),140)} for x in primary],
        "registeredSecondaryOutcomeCount": len(outcomes.get("secondaryOutcomes") or []),
        "hasPostedResults": has, "resultsFirstPosted": results_date,
        "postedPrimaryOutcomeCount": len(posted_primary),
        "postedOtherOutcomeCount": len(posted_other),
        "primaryPostedEvidence": [one_outcome(o) for o in posted_primary[:25]],
        "primaryResultsTruncated": len(posted_primary)>25,
        "seriousAdverseEventTermCount": len(serious),
        "seriousAdverseEventEvidence": [{
            "term":trim(x.get("term"),160),
            "assessmentType":x.get("assessmentType"),
            "stats":[{k:g.get(k) for k in (
                "groupId","numAffected","numAtRisk","numEvents")
                 if g.get(k) is not None} for g in (x.get("stats") or [])[:10]]
            } for x in serious[:20]],
        "seriousEventsTruncated":len(serious)>20,
        "evidenceState": "POSTED_RESULTS_UNGRADED" if has else "PROTOCOL_ONLY",
        "overallRaasScore": None,
    }

def harvest(by_id, subset, now=None, fetch=request_batch):
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    selected = sorted(set(subset))
    if any(n not in by_id for n in selected):
        raise ValueError("NCT outside exact cohort")
    observed = {}
    errors = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(fetch, batch):batch for batch in chunks(selected)}
        for future in as_completed(futures):
            batch = futures[future]
            try:
                found = future.result()
                for n in batch:
                    if n in found:
                        observed[n] = extract(n,by_id[n],found[n],now)
                    else:
                        errors[n] = "NOT_RETURNED_BY_REGISTRY_SEARCH"
            except Exception as error:
                # Failure is visible and never treated as a negative trial result.
                for n in batch:
                    errors[n] = "SOURCE_FETCH_FAILED:"+type(error).__name__
    return observed, errors

def verify_source_condition_coverage(observed: dict, requested_count: int) -> int:
    """Catch silently dropped indication fields on a full-cohort refresh."""
    covered = sum(bool(row.get("registeredConditions")) for row in observed.values())
    if requested_count >= 100 and (not observed or covered < 0.8 * len(observed)):
        raise ValueError("CT_GOV_CONDITION_COVERAGE_INCOMPLETE")
    return covered


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scope",choices=["missing","all"],default="all")
    args=parser.parse_args()
    by_id=cohort()
    if args.scope=="missing":
        gaps=json.loads(GAPS.read_text())
        if gaps.get("scope")!="RAAS_MISSING_REGISTRY_BACKFILL":
            raise ValueError("Invalid existing gap receipts")
        ids=[item["nctId"] for item in gaps["missing"]]
    else:
        ids=list(by_id)
    observed,errors=harvest(by_id,ids)
    conditions_covered=verify_source_condition_coverage(observed,len(ids))
    print("CT_GOV_SOURCE_CONDITIONS_DOCUMENTED",conditions_covered,"of",len(observed))
    old={}
    if DEST.exists():
        source=json.loads(DEST.read_text())
        if source.get("scope")=="RAAS_CT_GOV_LIVE_EVIDENCE" and source.get("schemaVersion")==1:
            old={x["nctId"]:x for x in source.get("records",[]) if x["nctId"] in by_id}
    old.update(observed)
    records=[old[n] for n in sorted(by_id) if n in old]
    result={"schemaVersion":1,"scope":"RAAS_CT_GOV_LIVE_EVIDENCE",
        "cohort":"data/phase3_all_years_300m_10b_trials.csv",
        "source":"ClinicalTrials.gov API v2",
        "latestAttemptAt":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "important":"Primary registry data, not validated TOP/BOTTOM, PDUFA, investment or RAAS scores.",
        "summary":{"researchTrials":len(by_id),"attemptedThisRun":len(ids),
            "retrievedThisRun":len(observed),"failedThisRun":len(errors),
            "registrySourceRecordsStored":len(records),
            "hasPostedRegistryResults":sum(r["hasPostedResults"] for r in records),
            "withRegisteredPrimaryEndpoints":sum(bool(r["registeredPrimaryOutcomes"]) for r in records),
            "completeRaasScores":0},
        "errors":[{"nctId":n,"reason":errors[n]} for n in sorted(errors)],
        "records":records}
    DEST.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(result["summary"],sort_keys=True))
    if not observed or len(errors)>len(ids)//4:
        raise SystemExit("BACKFILL_INCOMPLETE_UNAVAILABLE_OR_EXCESS_ERRORS")

if __name__=="__main__":
    main()
