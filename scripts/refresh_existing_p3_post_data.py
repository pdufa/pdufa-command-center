#!/usr/bin/env python3
"""Source-gated daily refresh of EXISTING P3 POST-DATA Google Sheets trial rows.

Updates only supported source columns. Never overwrites exact trial identity,
archived scoring, human research notes or historical trial evidence. Fail closed
on stale/missing sources and record each skipped field in an audit.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import google.auth.transport.requests
from google.oauth2 import service_account
import requests

from auto_promote_p3_post_data import (
    CAPS, CANDIDATES, NCT, SHEET_ID, SHEET_NAME, TICKER,
    iso_day, link_ok, load_csv, sheets_values, classify_regulatory_path,
)
from p3_market_cap_secondary import SOURCE as BACKUP_SOURCE, lookup_missing_primary

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "reports/p3_existing_row_refresh_latest.json"
CTGOV = "https://clinicaltrials.gov/api/v2/studies/"
SHEETS_API = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate"
MAX_TRIALS = None  # Candidate population has no arbitrary count cap
MAX_CAP_AGE = timedelta(days=3)
# A-C identity; live D-F evidence and retired N:X historical columns must remain unchanged.
# FDA source changes require specifically reviewed new regulatory evidence.
EDITABLE = frozenset((3, 4, 5, 6, 7, 8, 9, 21, 22, 23, 24, 25, 26, 27))
IMMUTABLE = frozenset((0, 1, 2, *range(10, 21)))
HEADERS = {0:"Ticker", 1:"NCT ID", 2:"Company", 3:"Registry Status",
           4:"Phase 3 Results Public?", 5:"Results Publication / Announcement Date",
           6:"Registry Source", 7:"Snapshot Date", 8:"Checked UTC",
           9:"Classification Basis", 21:"Issuer/FDA Evidence URL",
           22:"Review As-Of", 23:"Market Cap USD", 24:"Cap As-of",
           25:"PDUFA / FDA Filing", 26:"Public Phase 3 Results Source",
           27:"Market Cap Source"}


# Three source-only columns were inserted at D:F in the current FOCUS sheet.
# Reject unrecognized layouts instead of risking archived history.
INSERTED_HEADERS = ("FDA Special Designations", "D · P · p-value",
                    "Intelligence Prediction At (Pacific)")

def grid_shift(rows):
    if not rows:
        raise ValueError("P3 grid has no header")
    head=rows[0]
    if head[3:6]==list(INSERTED_HEADERS):
        if len(head)<31 or head[6]!="Registry Status":
            raise ValueError("FOCUS extended layout is incomplete")
        return 3
    if (len(head)>23 and head[3]=="Registry Status"
            and head[4]=="Phase 3 Results Public?" and head[23]=="Market Cap USD"):
        return 0
    raise ValueError("Unknown FOCUS headers; no source writes permitted")

def logical_rows(rows):
    return [list(row[:3])+list(row[6:]) for row in rows] if grid_shift(rows) else rows

def physical_index(idx,shift):
    return idx+shift if idx>=3 else idx

def val(row, idx):
    return row[idx] if idx < len(row) else ""


def validate_grid(rows):
    if not rows or len(rows) < 2:
        raise ValueError("Existing P3 grid empty or exceeds protected row limit")
    source=logical_rows(rows)
    for index, title in HEADERS.items():
        if val(source[0], index) != title:
            raise ValueError(f"Header changed in P3 column {index+1}: {title}")
    indexed = {}
    for row_no, row in enumerate(source[1:], start=4):
        ticker, nct = str(val(row, 0)).strip(), str(val(row, 1)).strip()
        if not TICKER.fullmatch(ticker) or not NCT.fullmatch(nct):
            raise ValueError("Blank or invalid exact trial identity on row " + str(row_no))
        if nct in indexed:
            raise ValueError("Duplicate NCT before refresh: " + nct)
        if not str(val(row, 2)).strip():
            raise ValueError("Company identity missing on row " + str(row_no))
        indexed[nct] = (row_no, ticker, row)
    return indexed


def cap_index(rows):
    index = {}
    for item in rows:
        ticker = str(item.get("ticker") or "").upper().strip()
        if not ticker or ticker in index:
            raise ValueError("Duplicate/blank Nasdaq market-cap ticker")
        index[ticker] = item
    return index


def cap_evidence(record, cutoff):
    if not record:
        return None, "MARKET_CAP_NOT_IN_CURRENT_LEDGER"
    try:
        cap = float(record["market_cap"])
        stamp = datetime.fromisoformat(record["market_cap_checked_at"].replace("Z","+00:00"))
        if not math.isfinite(cap) or stamp.tzinfo is None:
            raise ValueError("Invalid market-cap observation")
        cap_day = stamp.astimezone(timezone.utc).date()
    except (KeyError, TypeError, ValueError, OverflowError):
        return None, "MARKET_CAP_NOT_VERIFIED"
    if record.get("market_cap_status") != "VERIFIED" or not link_ok(record.get("market_cap_source")):
        return None, "MARKET_CAP_NOT_VERIFIED"
    if cap_day > cutoff or cutoff - cap_day > MAX_CAP_AGE:
        return None, "MARKET_CAP_STALE"
    if not 300_000_000 <= cap <= 10_000_000_000:
        return None, "MARKET_CAP_OUTSIDE_ACTIVE_RANGE"
    return (int(cap), cap_day.isoformat(), record["market_cap_source"]), None


def official_study(study, nct, cutoff):
    if not isinstance(study, dict):
        raise ValueError("Invalid official trial response")
    protocol = study.get("protocolSection") or {}
    id_module = protocol.get("identificationModule") or {}
    design = protocol.get("designModule") or {}
    status = protocol.get("statusModule") or {}
    if id_module.get("nctId") != nct or "PHASE3" not in design.get("phases", []):
        raise ValueError("Official registry NCT or Phase 3 identity mismatch")
    overall = status.get("overallStatus")
    if not isinstance(overall, str) or not re.fullmatch(r"[A-Z_]{3,45}", overall):
        raise ValueError("Missing current official trial status")
    posted = status.get("resultsFirstPostDateStruct")
    posted_date = None
    if posted:
        day = iso_day(posted.get("date"), cutoff)
        if not day:
            raise ValueError("Invalid/future official registry results-first-post date")
        if study.get("resultsSection") is None:
            raise ValueError("Registry results posted but results section missing")
        posted_date = day.isoformat()
    return overall, posted_date


def curated_fda(catalog, nct, ticker, cutoff, review_date):
    """Only apply an evidence-dated *newer* reviewed PDUFA date to this exact NCT."""
    for event_key, event in catalog.get("cases", {}).items():
        if not event_key.startswith("APPLICATION|" + ticker + "|") or event.get("nctId") != nct:
            continue
        reviewed = iso_day(event.get("reviewedOn"), cutoff)
        if event.get("reviewerMethod") != "PRIMARY_PUBLIC_ISSUER_DISCLOSURE":
            return None, "FDA_EVIDENCE_NOT_CURRENT_VERIFIED"
        classification, issue = classify_regulatory_path(event, cutoff, reviewed)
        if issue:
            return None, issue
        previous = iso_day(str(review_date), cutoff)
        if previous and reviewed <= previous:
            return None, "FDA_CURATED_EVIDENCE_NOT_NEWER_THAN_SHEET"
        return (classification["display"],classification["source"],classification["asOf"]), None
    return None, "NO_NEW_FDA_EVENT"


def build_plan(rows, market_rows, catalog, registry, cutoff, checked_at,
               backup_caps=None, backup_errors=None):
    """Pure plan: exact NCT -> registry; secondary caps only for unavailable primary."""
    backup_caps = backup_caps or {}
    backup_errors = backup_errors or {}
    indexed = validate_grid(rows)
    shift = grid_shift(rows)
    market = cap_index(market_rows)
    data = []
    report = []
    counts = {"trials":len(indexed),"registryChecked":0,"capUpdated":0,
              "backupCapRowsUpdated":0,"resultsUpdated":0,"fdaUpdated":0,
              "rowsChanged":0}
    today = cutoff.isoformat()
    if catalog.get("schemaVersion") != "pdufa-curated-phase3-announcements-v1":
        raise ValueError("Reviewed FDA catalog schema changed")
    for nct, (row_no,ticker,row) in indexed.items():
        updates = {}
        review = []
        cap, issue = cap_evidence(market.get(ticker),cutoff)
        backup_used = False
        # Never mask a VERIFIED Nasdaq out-of-range result with a secondary quote.
        can_fallback = issue in {"MARKET_CAP_NOT_IN_CURRENT_LEDGER",
                                 "MARKET_CAP_NOT_VERIFIED", "MARKET_CAP_STALE"}
        if can_fallback and ticker in backup_caps:
            candidate = backup_caps[ticker]
            expected_url = BACKUP_SOURCE.format(ticker=ticker.lower())
            try:
                dated = date.fromisoformat(str(candidate[1]))
                saved = date.fromisoformat(str(val(row,24)))
                if (candidate[2] == expected_url and
                        isinstance(candidate[0],int) and
                        300_000_000 <= candidate[0] <= 10_000_000_000 and
                        cutoff - timedelta(days=4) <= dated <= cutoff):
                    if dated < saved:
                        review.append("BACKUP_MARKET_CAP_OLDER_THAN_SAVED")
                    else:
                        cap, issue = candidate, None
                        backup_used = True
                else:
                    review.append("BACKUP_MARKET_CAP_SOURCE_INVALID")
            except (TypeError, ValueError, IndexError):
                review.append("BACKUP_MARKET_CAP_SOURCE_INVALID")
        if issue:
            review.append(issue)
            if ticker in backup_errors:
                review.append("BACKUP_" + backup_errors[ticker])
        else:
            changed_cap = False
            for index, new in ((23,cap[0]),(24,cap[1]),(27,cap[2])):
                if val(row,index) != new:
                    updates[index] = new
                    changed_cap = True
                    if index==23: counts["capUpdated"] += 1
            if changed_cap and backup_used:
                counts["backupCapRowsUpdated"] += 1
        study = registry.get(nct)
        if isinstance(study, Exception):
            review.append("CTGOV_UNAVAILABLE_" + type(study).__name__)
        else:
            try:
                overall, first_posted = official_study(study,nct,cutoff)
                counts["registryChecked"] += 1
                if val(row,3) != overall:
                    updates[3] = overall
                # A fetched official trial may have an independently verified
                # posting. NEVER downgrade a company/SEC/journal-public readout.
                current_flag = str(val(row,4)).upper()
                current_basis = str(val(row,9))
                source = "https://clinicaltrials.gov/study/" + nct
                if first_posted:
                    if not current_flag.startswith("YES"):
                        for idx, value in ((4,"YES"),(5,first_posted),
                                           (6,source),(9,"CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT"),
                                           (26,source)):
                            if val(row,idx)!=value:
                                updates[idx]=value
                        counts["resultsUpdated"] += 1
                    elif current_basis == "CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT":
                        for idx,value in ((5,first_posted),(6,source),(26,source)):
                            if val(row,idx)!=value:
                                updates[idx]=value
                                if idx==5: counts["resultsUpdated"] += 1
                elif current_basis == "CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT" and current_flag.startswith("YES"):
                    review.append("PREVIOUS_REGISTRY_RESULTS_NOT_RECONFIRMED")
                # H/I refer only to successfully refreshed source observation.
                for idx,value in ((7,today),(8,checked_at)):
                    if val(row,idx)!=value:
                        updates[idx]=value
            except (ValueError, AttributeError, TypeError) as exc:
                review.append("CTGOV_IDENTITY_OR_RESULTS_NEEDS_REVIEW_" + type(exc).__name__)
        fda, fda_issue = curated_fda(catalog,nct,ticker,cutoff,val(row,22))
        if fda:
            for idx,value in ((25,fda[0]),(21,fda[1]),(22,fda[2])):
                if val(row,idx)!=value:
                    updates[idx]=value
            if any(k in updates for k in (25,21,22)):
                counts["fdaUpdated"]+=1
        elif fda_issue and fda_issue not in {"FDA_CURATED_EVIDENCE_NOT_NEWER_THAN_SHEET", "NO_NEW_FDA_EVENT"}:
            review.append(fda_issue)
        # A date that has elapsed is not evidence of approval/CRL.
        try:
            previous_fda_date = date.fromisoformat(str(val(row,25)))
            if previous_fda_date < cutoff and not fda:
                review.append("PAST_FDA_TARGET_OUTCOME_REQUIRES_VERIFICATION")
        except ValueError:
            pass
        if any(index not in EDITABLE or index in IMMUTABLE for index in updates):
            raise AssertionError("Attempt to overwrite immutable trial/RAAS cells")
        if updates:
            counts["rowsChanged"] += 1
            for idx, value in sorted(updates.items()):
                column = a1_col(physical_index(idx,shift))
                data.append({"range":f"{SHEET_NAME}!{column}{row_no}",
                             "majorDimension":"ROWS","values":[[value]]})
        report.append({"nct":nct,"ticker":ticker,"row":row_no,
                       "updatedColumns":[a1_col(physical_index(k,shift)) for k in sorted(updates)],
                       "marketCapSourceKind":"SECONDARY_DATED_PUBLISHER_QUOTE" if backup_used
                         else ("NASDAQ_LEDGER" if not issue else "PRESERVED_NO_VERIFIED_UPDATE"),
                       "review":sorted(set(review))})
    return data, {"asOf":checked_at,"counts":counts,"records":report,
                  "protectedColumns":"A:F,N:X" if shift else "A:C,K:U",
                  "source":"Official ClinicalTrials.gov + Nasdaq cap ledger + dated Stock Analysis fallback + reviewed FDA evidence",
                  "secondaryLimitations":"Dated publisher quote, rounded to source precision; never a verified exchange-timestamped tick"}


def a1_col(zero_index):
    n=zero_index+1
    s=""
    while n:
        n,r=divmod(n-1,26)
        s=chr(65+r)+s
    return s


def ctgov_get(nct):
    try:
        response=requests.get(CTGOV+nct,timeout=40,headers={"Accept":"application/json",
                                                             "User-Agent":"PDUFAExistingTrialRefresh/1.0"})
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        return exc


def get_registry(ncts):
    output={}
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(ctgov_get,nct):nct for nct in ncts}
        for future in as_completed(futures):
            output[futures[future]]=future.result()
    return output


def api_auth():
    secret=os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON","")
    if not secret:
        raise RuntimeError("Google Sheets credential missing")
    creds=service_account.Credentials.from_service_account_info(
        json.loads(secret),scopes=["https://www.googleapis.com/auth/spreadsheets"])
    creds.refresh(google.auth.transport.requests.Request())
    return {"Authorization":"Bearer "+creds.token}


def main():
    auth=api_auth()
    before=sheets_values(auth,"A3:AE")
    indexed=validate_grid(before)
    checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds")
    cutoff=datetime.now(timezone.utc).date()
    with CANDIDATES.open(encoding="utf-8") as f:
        catalog=json.load(f)
    registries=get_registry(indexed)
    market_rows = load_csv(CAPS)
    market_by_ticker = cap_index(market_rows)
    missing = {ticker for _, ticker, _ in indexed.values()
               if cap_evidence(market_by_ticker.get(ticker),cutoff)[1] in {
                   "MARKET_CAP_NOT_IN_CURRENT_LEDGER", "MARKET_CAP_NOT_VERIFIED",
                   "MARKET_CAP_STALE"}}
    backup_caps, backup_errors = lookup_missing_primary(missing,cutoff)
    data, report=build_plan(before,market_rows,catalog,registries,cutoff,checked_at,
                            backup_caps=backup_caps,backup_errors=backup_errors)
    report["secondaryMarketCapCheck"]={
        "attemptedTickers":sorted(missing),
        "resolvedTickers":sorted(backup_caps),
        "failures":backup_errors,
        "sourcePrecision":"SOURCE_QUOTED_ROUNDED_NOT_EXCHANGE_TIMESTAMPED"
    }
    # Recheck before writing. A:F identity/evidence and N:X archive are protected.
    if sheets_values(auth,"A3:AE")!=before:
        raise RuntimeError("Google Sheet modified during refresh; no updates written")
    if data:
        response=requests.post(SHEETS_API,headers=auth,
            json={"valueInputOption":"RAW","data":data,"includeValuesInResponse":False},
            timeout=60)
        response.raise_for_status()
        updated=sheets_values(auth,"A3:AE")
        after=validate_grid(updated)
        if set(indexed)!=set(after):
            raise RuntimeError("Candidate identity changed during refresh")
        for nct,(row_no,ticker,row) in indexed.items():
            new_row=after[nct][2]
            if new_row[:3]!=row[:3] or any(val(new_row,k)!=val(row,k) for k in IMMUTABLE):
                raise RuntimeError("Protected trial identity/archived history changed: "+nct)
            if grid_shift(before):
                for col in (3,4,5):
                    if val(before[row_no-3],col)!=val(updated[row_no-3],col):
                        raise RuntimeError("Inserted D:F evidence changed during refresh: "+nct)
        for item in data:
            cell=item["range"].split("!")[-1]
            match=re.fullmatch(r"([A-Z]+)(\d+)",cell)
            idx=0
            for c in match.group(1):
                idx=idx*26+(ord(c)-64)
            idx-=1
            record=updated[int(match.group(2))-3]
            if val(record,idx)!=item["values"][0][0]:
                raise RuntimeError("Updated value not confirmed in "+cell)
    report["writes"]=len(data)
    report["poolModified"]=False
    report["historicalArchiveModified"]=False
    AUDIT.parent.mkdir(parents=True,exist_ok=True)
    AUDIT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"asOf":report["asOf"],"counts":report["counts"],
                      "writes":report["writes"],"secondaryMarketCapCheck":report["secondaryMarketCapCheck"],
                      "reviewTrialCount":sum(bool(r["review"]) for r in report["records"]),
                      "poolModified":False,"historicalArchiveModified":False},indent=2))


if __name__=="__main__":
    main()
