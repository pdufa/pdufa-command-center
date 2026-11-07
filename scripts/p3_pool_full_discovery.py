#!/usr/bin/env python3
"""Full canonical POOL -> evidence REVIEW screening. Never autonomously invent an FDA event.

Every run screens all exact-NCT Google POOL rows against the current listed-company
market-cap ledger. It then queries ClinicalTrials.gov for every in-band trial
in batches, classifies Phase 3 + *posted registry results*, and joins explicitly
reviewed issuer/FDA evidence. Issuer topline releases are an independent source.
No Google Sheet / RAAS / clinical-history writes occur here.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import google.auth.transport.requests
from google.oauth2 import service_account
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from auto_promote_p3_post_data import (
    CANDIDATES, CAPS, DISCOVERIES, NCT, TICKER,
    SHEET_ID, SHEET_NAME, classify_regulatory_path, iso_day, link_ok,
    load_csv,
)

API = "https://clinicaltrials.gov/api/v2/studies"
OUT = ROOT / "reports/p3_pool_full_discovery_latest.json"
REVIEW = ROOT / "reports/p3_pool_full_discovery_review.json"
BATCH_SIZE = 60
MAX_CAP_AGE = timedelta(days=7)
FIELDS = "NCTId,Phase,OverallStatus,HasResults,ResultsFirstPostDate,LastUpdatePostDate"


def validate_pool(rows):
    if not rows or rows[0][:3] != ["ticker", "company", "nct_id"]:
        raise ValueError("Canonical Master Trials (Published) header missing or changed")
    by_nct = {}
    for line_no, row in enumerate(rows[1:], 2):
        if len(row) < 3:
            raise ValueError("Incomplete master POOL row " + str(line_no))
        ticker, company, nct = (str(row[i]).strip() for i in range(3))
        if not TICKER.fullmatch(ticker) or not company or not NCT.fullmatch(nct):
            raise ValueError("Invalid exact ticker/company/NCT POOL row " + str(line_no))
        if nct in by_nct:
            raise ValueError("Duplicate NCT in canonical POOL: " + nct)
        by_nct[nct] = {"nct": nct, "ticker": ticker, "company": company}
    if not by_nct:
        raise ValueError("Empty master POOL")
    return by_nct


def validate_existing(rows):
    if not rows or rows[0][:3] != ["Ticker", "NCT ID", "Company"]:
        raise ValueError("P3 POST-DATA canonical heading changed")
    indexed = {}
    for r in rows[1:]:
        if len(r) < 3 or not NCT.fullmatch(str(r[1])) or not TICKER.fullmatch(str(r[0])):
            raise ValueError("Invalid P3 roster row")
        if r[1] in indexed:
            raise ValueError("Duplicate NCT in P3 roster")
        indexed[r[1]] = r[0]
    return indexed


def cap_eligible(pool, caps, cutoff):
    market = {}
    for row in caps:
        ticker = row.get("ticker", "")
        if not TICKER.fullmatch(ticker) or ticker in market:
            raise ValueError("Invalid or duplicate market-cap ticker: " + ticker)
        market[ticker] = row
    counters = Counter()
    filtered = {}
    for nct, row in pool.items():
        record = market.get(row["ticker"])
        if record is None:
            counters["CAP_MISSING"] += 1
            continue
        try:
            cap = float(record["market_cap"])
            stamp = datetime.fromisoformat(record["market_cap_checked_at"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("Naive timestamp")
            age = cutoff - stamp.astimezone(timezone.utc).date()
            if record["market_cap_status"] != "VERIFIED" or not link_ok(record["market_cap_source"]) or age < timedelta(0) or age > MAX_CAP_AGE:
                counters["CAP_UNVERIFIED_OR_STALE"] += 1
                continue
        except (ValueError, TypeError, KeyError, OverflowError):
            counters["CAP_UNVERIFIED_OR_STALE"] += 1
            continue
        if not 300_000_000 <= cap <= 10_000_000_000:
            counters["CAP_OUT_OF_BAND"] += 1
            continue
        filtered[nct] = {**row, "marketCap": int(cap), "marketCapSource": record["market_cap_source"],
                         "capChecked": stamp.date().isoformat()}
        counters["CAP_ELIGIBLE"] += 1
    if sum(counters.values()) != len(pool):
        raise AssertionError("Cap counters must partition the entire POOL")
    return filtered, dict(counters)


def parse_study(study):
    p = study.get("protocolSection") or {}
    identity = (p.get("identificationModule") or {}).get("nctId")
    design = p.get("designModule") or {}
    status = p.get("statusModule") or {}
    phases = design.get("phases") or []
    result_date = (status.get("resultsFirstPostDateStruct") or {}).get("date")
    # ClinicalTrials.gov results section and issuer public release are independent.
    posted = bool(study.get("hasResults") is True and result_date
                  and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(result_date)))
    return {"nct": identity, "phase3": "PHASE3" in phases,
            "registryPostedResults": posted, "registryResultDate": result_date if posted else None,
            "hasResults": study.get("hasResults") is True,
            "status": status.get("overallStatus"),
            "lastUpdate": (status.get("studyFirstPostDateStruct") or {}).get("date")}


def fetch_registry_batches(ncts, get=requests.get, batch_size=BATCH_SIZE):
    """Every returned NCT must have been requested. Missing NCTs are reported, not assumed negative."""
    indexed = {}
    chunks = [ncts[i:i + batch_size] for i in range(0, len(ncts), batch_size)]
    for index, chunk in enumerate(chunks, start=1):
        params = {"filter.ids": ",".join(chunk), "pageSize": 1000,
                  "format": "json", "fields": FIELDS}
        by_id = {}
        token = None
        seen_tokens = set()
        for page_number in range(1, 11):
            page_params = dict(params)
            if token:
                page_params["pageToken"] = token
            for attempt in range(3):
                try:
                    response = get(API, params=page_params, timeout=65,
                                   headers={"User-Agent": "PDUFA-Candidate-Evidence-Audit/1.0"})
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload.get("studies"), list):
                        raise ValueError("Registry batch has no studies list")
                    break
                except (requests.RequestException, ValueError) as exc:
                    if attempt == 2:
                        raise RuntimeError("Registry batch " + str(index) + "/" +
                                           str(len(chunks)) + ", page " + str(page_number) +
                                           " could not be validated") from exc
                    time.sleep(2 ** attempt)
            for study in payload["studies"]:
                data = parse_study(study)
                nct = data["nct"]
                if nct not in chunk or nct in by_id:
                    raise ValueError("Registry returned an unexpected or duplicate NCT in batch " +
                                     str(index) + ": " + str(nct))
                by_id[nct] = data
            token = payload.get("nextPageToken")
            if not token:
                break
            if token in seen_tokens:
                raise ValueError("Registry repeated a page token in batch " + str(index))
            seen_tokens.add(token)
        else:
            raise RuntimeError("ClinicalTrials.gov pagination exceeded 10 pages for 60-NCT batch")
        indexed.update(by_id)
        if index % 10 == 0 or index == len(chunks):
            print("Registry batches", index, "/", len(chunks), "studies returned", len(indexed), flush=True)
    return indexed, len(chunks)


def issuer_discovery_index(csv_rows, pool):
    indexed = {}
    for r in csv_rows:
        nct = r.get("nct_id") or ""
        if nct not in pool or r.get("ticker") != pool[nct]["ticker"]:
            continue
        url = r.get("source_url") or ""
        day = r.get("readout_date") or ""
        if link_ok(url) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            indexed[nct] = {"source": url, "date": day, "type": "ISSUER_ANNOUNCEMENT_LEAD_NOT_AUTO_VERIFIED"}
    return indexed


def classify(pool, eligible, registry, existing, discovery, catalog, as_of):
    """No staged candidate is promoted from this review-only function."""
    stages = {}
    for key, event in catalog.get("cases", {}).items():
        if not key.startswith("APPLICATION|") or not event.get("nctId"):
            continue
        nct = event["nctId"]
        ticker = key.split("|")[1] if len(key.split("|")) >= 3 else ""
        if nct not in eligible or eligible[nct]["ticker"] != ticker:
            continue
        info, issue = classify_regulatory_path(event, as_of, iso_day(event.get("reviewedOn"), as_of))
        if info and not issue:
            stages[nct] = {"stage": info["stage"], "source": info["source"]}
    review = []
    counters = Counter()
    known_ids = set(existing)
    for nct, row in sorted(eligible.items()):
        r = registry.get(nct)
        if r is None:
            counters["REGISTRY_NOT_RETURNED"] += 1
            continue
        counters["REGISTRY_RECORDS_RETURNED"] += 1
        if not r["phase3"]:
            counters["NOT_PHASE3"] += 1
            continue
        counters["PHASE3"] += 1
        if r["registryPostedResults"]:
            counters["REGISTRY_RESULTS_POSTED"] += 1
        if nct in discovery:
            counters["ISSUER_RESULT_LEAD"] += 1
        if nct in known_ids:
            counters["ALREADY_P3_POST_DATA"] += 1
            continue
        if not r["registryPostedResults"] and nct not in discovery:
            counters["PHASE3_NO_VERIFIED_PUBLIC_RESULTS"] += 1
            continue
        if nct in stages:
            counters["SOURCE_VERIFIED_FDA_PATH_NOT_YET_P3"] += 1
            reason = "CHECK_FOR_PROMOTION_BY_EXISTING_EXACT_NCT_GATES"
        else:
            counters["POST_PHASE3_NEEDS_REVIEWED_FDA_APPLICATION_PATH"] += 1
            reason = "FDA_STAGE_AND_EXACT_DRUG_INDICATION_REVIEW"
        review.append({"nct": nct, "ticker": row["ticker"], "company": row["company"],
                       "marketCap": row["marketCap"], "marketCapSource": row["marketCapSource"],
                       "registryStatus": r["status"], "registryResultsPosted": r["registryPostedResults"],
                       "registryResultsDate": r["registryResultDate"],
                       "registryUrl": "https://clinicaltrials.gov/study/" + nct,
                       "issuerReadoutLead": discovery.get(nct),
                       "reviewedFDAStage": stages.get(nct),
                       "reason": reason})
    review.sort(key=lambda r: (r["reason"] != "CHECK_FOR_PROMOTION_BY_EXISTING_EXACT_NCT_GATES",
                               not r["registryResultsPosted"], r["ticker"], r["nct"]))
    counts = dict(counters)
    counts["POOL_RECORDS"] = len(pool)
    counts["CAP_ELIGIBLE"] = len(eligible)
    counts["EXISTING_P3"] = len(existing)
    counts["REVIEW_QUEUE"] = len(review)
    counts["REVIEWED_FDA_STAGE_CATALOG"] = len(stages)
    return review, counts


def google_values(auth, tab, cell_range):
    target = quote("'%s'!%s" % (tab, cell_range), safe="!':")
    url = "https://sheets.googleapis.com/v4/spreadsheets/%s/values/%s" % (SHEET_ID, target)
    response = requests.get(url, headers=auth, params={"valueRenderOption": "UNFORMATTED_VALUE"},
                            timeout=65)
    response.raise_for_status()
    return response.json().get("values", [])


def execute(pool_rows, existing_rows, cap_rows, discovery_rows, catalog, registry_get=requests.get,
            checked_at=None):
    checked_at = checked_at or datetime.now(timezone.utc)
    day = checked_at.date()
    pool = validate_pool(pool_rows)
    existing = validate_existing(existing_rows)
    eligible, cap_counts = cap_eligible(pool, cap_rows, day)
    current = sorted(eligible)
    registry, batches = fetch_registry_batches(current, get=registry_get)
    discovery = issuer_discovery_index(discovery_rows, pool)
    review, counts = classify(pool, eligible, registry, existing, discovery, catalog, day)
    counts.update({k: v for k, v in cap_counts.items() if k != "CAP_ELIGIBLE"})
    counts["REGISTRY_QUERIED"] = len(current)
    counts["REGISTRY_BATCHES"] = batches
    if counts.get("REGISTRY_RECORDS_RETURNED", 0) + counts.get("REGISTRY_NOT_RETURNED", 0) != len(current):
        raise AssertionError("Registry audit coverage total inconsistent")
    summary = {"schemaVersion": "p3-full-pool-discovery-v1",
               "asOf": checked_at.isoformat(), "status": "COMPLETE" if not counts.get("REGISTRY_NOT_RETURNED") else "PARTIAL_REGISTRY_MATCHES",
               "sources": {"pool": "Google Master Trials (Published)",
                           "marketCaps": "data/phase_pipeline_market_caps.csv",
                           "registry": API, "issuerResults": "data/post_phase3_discoveries.csv",
                           "regulatory": "new-platform/backend/app/phase3_curated_announcements.json"},
               "counts": counts,
               "notes": [
                   "All POOL identities receive a cap screen; only in-band caps receive ClinicalTrials.gov queries.",
                   "Registry-posted results are not the same as issuer-public topline data.",
                   "No FDA filing, PDUFA assignment, or trial efficacy conclusion is inferred from study completion.",
                   "Only manually reviewed exact drug/indication issuer/FDA sources can trigger automatic promotion.",
                   "This queue is not exhaustive for issuer press releases or SEC filings not yet in the discovery ledger.",
                   "Scanner is read-only: POOL, P3 roster, RAAS values and histories are preserved."
               ], "topReview": review[:100]}
    detail = {"asOf": checked_at.isoformat(), "count": len(review), "records": review,
              "missingRegistryNcts": sorted(set(eligible) - set(registry))}
    return summary, detail


def main():
    secret = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "")
    if not secret:
        raise RuntimeError("Missing Google Sheets credentials; no scan fabricated")
    creds = service_account.Credentials.from_service_account_info(json.loads(secret),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    creds.refresh(google.auth.transport.requests.Request())
    auth = {"Authorization": "Bearer " + creds.token}
    pool = google_values(auth, "Master Trials (Published)", "A1:C")
    p3 = google_values(auth, SHEET_NAME, "A3:C")
    with CANDIDATES.open(encoding="utf-8") as f:
        catalog = json.load(f)
    summary, detail = execute(pool, p3, load_csv(CAPS), load_csv(DISCOVERIES), catalog)
    for path, result in ((OUT, summary), (REVIEW, detail)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "asOf": summary["asOf"],
                      "counts": summary["counts"], "reviewSample": summary["topReview"][:3]},
                     indent=2, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
