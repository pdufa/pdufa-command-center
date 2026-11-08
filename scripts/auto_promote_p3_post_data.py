#!/usr/bin/env python3
"""Fail-closed POOL -> P3 POST-DATA Google Sheet promotion.

Only an exact-NCT, previously reviewed Phase 3 + FDA evidence pair can be
promoted. An issuer's trial completion or an unreviewed PDUFA guess is not enough.
The master POOL is read-only; existing P3 rows, scores and history are untouched.
"""
from __future__ import annotations

import csv
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

import google.auth.transport.requests
from google.oauth2 import service_account
import requests

ROOT = Path(__file__).resolve().parents[1]
SHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
SHEET_NAME = "FOCUS"
CANDIDATES = ROOT / "new-platform/backend/app/phase3_curated_announcements.json"
CAPS = ROOT / "data/phase_pipeline_market_caps.csv"
CENSUS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
POOL = ROOT / "data/all_phase_trials.csv"
DISCOVERIES = ROOT / "data/post_phase3_discoveries.csv"
AUDIT = ROOT / "reports/p3_auto_promotion_latest.json"
API = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/"
NCT = re.compile(r"NCT[0-9]{8}\Z")
TICKER = re.compile(r"[A-Z][A-Z0-9.]{0,9}\Z")


# Canonical FOCUS sheet inserted three source-only columns at D:F.
LIVE_FOCUS_INSERTS=("FDA Special Designations","D · P · p-value",
                    "Intelligence Prediction At (Pacific)")

def focus_layout(headers):
    if headers[3:6]==list(LIVE_FOCUS_INSERTS):
        if len(headers)<31 or headers[6]!="Registry Status" or headers[26]!="Market Cap USD":
            raise ValueError("Unrecognized 31-column FOCUS destination")
        return 3
    if len(headers)>23 and headers[3]=="Registry Status" and headers[23]=="Market Cap USD":
        return 0
    raise ValueError("Unrecognized FOCUS layout; refuse append")


def physical_append_row(logical, shift):
    if len(logical)!=28 or shift not in (0,3):
        raise ValueError("Candidate append schema is invalid")
    # The nine archived research/rubric cells are blank for new NCTs.
    if any(str(logical[i]).strip() for i in range(10,19)):
        raise ValueError("New record attempts to initialize retired research archive")
    return logical[:3]+["Not verified","","Not yet predicted"]+logical[3:] if shift else logical


def link_ok(link):
    if not isinstance(link, str):
        return False
    try:
        p = urlsplit(link)
        return (p.scheme == "https" and bool(p.hostname)
                and not p.username and not p.password and not any(c.isspace() for c in link))
    except ValueError:
        return False


def iso_day(value, cutoff):
    if not isinstance(value, str):
        return None
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return None
    return day if day <= cutoff else None


def load_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def cap_ledger(rows, cutoff):
    indexed = {}
    for row in rows:
        ticker = (row.get("ticker") or "").upper().strip()
        if not ticker or ticker in indexed:
            raise ValueError("Missing or duplicate ticker in market-cap ledger: " + ticker)
        indexed[ticker] = row
    return indexed


def registry_phase3(nct):
    """Check current exact-NCT registry identity; no status-based exclusion."""
    response = requests.get("https://clinicaltrials.gov/api/v2/studies/" + nct, timeout=35)
    response.raise_for_status()
    study = response.json()
    protocol = study.get("protocolSection", {})
    identity = protocol.get("identificationModule", {})
    design = protocol.get("designModule", {})
    status = protocol.get("statusModule", {})
    if identity.get("nctId") != nct or "PHASE3" not in design.get("phases", []):
        raise ValueError("Registry identity or Phase 3 stage does not match: " + nct)
    return status.get("overallStatus", "UNKNOWN")



def classify_regulatory_path(item, cutoff, reviewed):
    """Four evidence-backed stages; a planned filing is never an accepted NDA/BLA."""
    p = item.get("regulatory_path") or item.get("pdufa_assignment") or {}
    stage = p.get("stage") or ("PDUFA_ASSIGNED" if item.get("pdufa_assignment") else "")
    app = p.get("application_type") or ("NDA" if item.get("pdufa_assignment") else "")
    published, occurred = iso_day(p.get("published_at"), cutoff), iso_day(p.get("event_date"), cutoff)
    if (stage not in {"PLANNED", "SUBMITTED", "ACCEPTED", "PDUFA_ASSIGNED"}
            or app not in {"BLA","NDA","sBLA","sNDA"} or not reviewed
            or not published or not occurred or occurred > published or reviewed < published
            or p.get("review_status") != "VERIFIED" or not link_ok(p.get("source_url"))):
        return None,"NO_CURRENT_VERIFIED_FDA_PATH"
    if stage == "PLANNED":
        period = str(p.get("planned_filing_period",""))
        if (not re.fullmatch(r"(?:Q[1-4] )?20[0-9]{2}",period)
                or int(period[-4:]) < cutoff.year or p.get("pdufa_target_date")):
            return None,"PLANNED_FILING_NOT_CURRENT_OR_FALSE_PDUFA"
        status,display=f"POST-P3 / {app} filing planned",f"{app} filing planned {period}; PDUFA not assigned"
    elif stage == "SUBMITTED":
        submission=iso_day(p.get("submitted_on"),cutoff)
        if not submission or submission > published or p.get("pdufa_target_date"):
            return None,"SUBMISSION_NOT_VERIFIED_OR_FALSE_PDUFA"
        status,display=f"FDA {app} submitted / acceptance pending",f"{app} submitted {submission.isoformat()}; FDA acceptance pending"
    elif stage == "ACCEPTED":
        accepted=iso_day(p.get("accepted_on"),cutoff)
        if not accepted or accepted > published or p.get("pdufa_target_date"):
            return None,"ACCEPTANCE_NOT_VERIFIED_OR_FALSE_PDUFA"
        status,display=f"FDA {app} accepted for review",f"{app} accepted {accepted.isoformat()}; PDUFA date pending"
    else:
        try:
            target=date.fromisoformat(p.get("pdufa_target_date",""))
        except (ValueError,TypeError):
            target=None
        if not target or target < cutoff:
            return None,"NO_CURRENT_VERIFIED_FDA_PDUFA_PATH"
        status,display=f"FDA {app} review / PDUFA active",target.isoformat()
    return {"stage":stage,"status":status,"display":display,
            "source":p["source_url"],"asOf":reviewed.isoformat()},None


def master_pool_identity(rows):
    """Fetch exact ticker/NCT pairs from the canonical 11k+ Google POOL."""
    if not rows or rows[0][:3] != ["ticker","company","nct_id"]:
        raise ValueError("Master POOL header changed or unavailable")
    result={}
    for row in rows[1:]:
        if len(row)<3 or not TICKER.fullmatch(str(row[0])) or not NCT.fullmatch(str(row[2])):
            raise ValueError("Invalid canonical POOL source row")
        nct,ticker=str(row[2]),str(row[0])
        if nct in result:
            raise ValueError("Duplicate master POOL NCT: "+nct)
        result[nct]=ticker
    if not result:
        raise ValueError("Master POOL empty; promotion must fail, not silently reject all")
    return result


def evaluate(catalog, caps, census, pool_ids, existing, cutoff, phase3_check=registry_phase3):
    if (catalog.get("schemaVersion") != "pdufa-curated-phase3-announcements-v1"
            or not isinstance(catalog.get("cases"), dict)):
        raise ValueError("Verified issuer source catalog schema mismatch")
    identity = {}
    for row in census:
        nct, ticker = row.get("nct_id"), row.get("ticker")
        if nct in identity and identity[nct] != ticker:
            raise ValueError("Census has conflicting ticker for " + str(nct))
        identity[nct] = ticker
    market = cap_ledger(caps, cutoff)
    additions, review = [], []
    for key, item in sorted(catalog["cases"].items()):
        nct = item.get("nctId")
        ticker = key.split("|")[1] if key.startswith("APPLICATION|") and len(key.split("|")) >= 3 else ""
        issues = []
        if not NCT.fullmatch(nct or "") or not TICKER.fullmatch(ticker):
            issues.append("INVALID_EXACT_ID")
        if nct in existing:
            continue
        if identity.get(nct) != ticker:
            issues.append("NOT_IN_PHASE3_CENSUS_WITH_EXACT_TICKER")
        if nct not in pool_ids or (isinstance(pool_ids,dict) and pool_ids.get(nct)!=ticker):
            issues.append("NOT_IN_MASTER_POOL")
        cap = market.get(ticker, {})
        try:
            value = float(cap["market_cap"])
            check_day = datetime.fromisoformat(cap["market_cap_checked_at"].replace("Z", "+00:00")).date()
            if (cap.get("market_cap_status") != "VERIFIED"
                    or not 300_000_000 <= value <= 10_000_000_000
                    or check_day > cutoff or cutoff - check_day > timedelta(days=7)
                    or not link_ok(cap.get("market_cap_source"))):
                issues.append("CAP_NOT_CURRENT_VERIFIED_300M_10B")
        except (KeyError, ValueError, TypeError):
            issues.append("CAP_NOT_CURRENT_VERIFIED_300M_10B")
            value = None
        result = item.get("phase3_results") or {}
        reviewed=iso_day(item.get("reviewedOn"),cutoff)
        result_published=iso_day(result.get("published_at"),cutoff)
        result_event=iso_day(result.get("event_date"),cutoff)
        if (item.get("reviewerMethod")!="PRIMARY_PUBLIC_ISSUER_DISCLOSURE"
                or not reviewed or not result_published or not result_event
                or result_event>result_published or reviewed<result_published
                or result.get("review_status")!="VERIFIED"
                or not link_ok(result.get("source_url"))):
            issues.append("PHASE3_PUBLIC_RESULTS_NOT_REVIEWED")
        regulatory,path_issue=classify_regulatory_path(item,cutoff,reviewed)
        if path_issue:
            issues.append(path_issue)
        if item.get("regulatory_path") and not (
                str(item.get("drug","")).strip() and
                str(item.get("indication","")).strip()):
            issues.append("PROGRAM_DRUG_INDICATION_UNVERIFIED")
        if issues:
            review.append({"nct": nct, "ticker": ticker, "reasons": sorted(set(issues))})
            continue
        try:
            status = phase3_check(nct)
        except (ValueError, requests.RequestException) as exc:
            review.append({"nct": nct, "ticker": ticker,
                           "reasons": ["CTGOV_PHASE3_CURRENT_SOURCE_UNAVAILABLE"],
                           "detail": type(exc).__name__})
            continue
        now = datetime.now(timezone.utc).isoformat()
        day = cutoff.isoformat()
        description = (
            f"Public Phase 3 results for {item.get('drug','issuer candidate')} / "
            f"{item.get('indication','stated indication')}; "
            f"{regulatory['display']}. Trial {nct}. "
            f"{item.get('clinicalRiskNote','')}"
        ).strip()
        row = [""] * 28
        fields = {0:ticker, 1:nct,
                  2:next(r.get("company","") for r in census if r.get("nct_id")==nct),
                  3:status, 4:"YES - company/SEC/journal", 5:result_event.isoformat(),
                  6:"https://clinicaltrials.gov/study/" + nct, 7:day, 8:now,
                  9:"PRIMARY_PUBLIC_ISSUER_DISCLOSURE",
                  # Legacy rating columns 11..18 intentionally remain blank.
                  # New source rows must never initialize retired scores or controls.
                  19:regulatory["status"],
                  20:description, 21:regulatory["source"], 22:regulatory["asOf"],
                  23:int(value), 24:check_day.isoformat(), 25:regulatory["display"],
                  26:result["source_url"], 27:cap["market_cap_source"]}
        for index, cell in fields.items():
            row[index] = cell
        additions.append({"nct":nct, "ticker":ticker, "values":row})
    for item in load_csv(DISCOVERIES) if DISCOVERIES.exists() else []:
        nct = item.get("nct_id")
        if nct and nct not in existing and not any(x["nct"]==nct for x in additions+review):
            review.append({"nct":nct, "ticker":item.get("ticker"),
                           "reasons":["FDA_APPLICATION_PATH_NOT_VERIFIED_FOR_EXACT_PROGRAM"]})
    return additions, review


def sheets_values(auth, range_name, sheet_name=SHEET_NAME):
    url = API + quote(f"{sheet_name}!{range_name}" if sheet_name == 'FOCUS' else f"'{sheet_name}'!{range_name}", safe="!':")
    response = requests.get(url, headers=auth, params={"valueRenderOption":"UNFORMATTED_VALUE"}, timeout=60)
    response.raise_for_status()
    return response.json().get("values", [])


def main():
    secret = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON")
    if not secret:
        raise RuntimeError("Missing Google Sheets service account; existing rows preserved")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(secret), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    credentials.refresh(google.auth.transport.requests.Request())
    auth = {"Authorization":"Bearer " + credentials.token}
    current = sheets_values(auth, "A3:AE")
    if not current or current[0][:3] != ["Ticker", "NCT ID", "Company"]:
        raise ValueError("Canonical P3 source headers changed; refusing to append")
    shift = focus_layout(current[0])
    if any(not row or not row[1] for row in current[1:]):
        raise ValueError("Noncontiguous/empty NCT row: refuse to overwrite")
    existing_ids = [str(row[1]) for row in current[1:]]
    if len(existing_ids) != len(set(existing_ids)):
        raise ValueError("Source spreadsheet has duplicate NCTs; refusing to append")
    with CANDIDATES.open(encoding="utf-8") as f:
        catalog = json.load(f)
    pool_ids=master_pool_identity(sheets_values(auth,"A1:C","Master Trials (Published)"))
    cutoff = datetime.now(timezone.utc).date()
    additions, review = evaluate(catalog, load_csv(CAPS), load_csv(CENSUS), pool_ids,
                                 set(existing_ids), cutoff)
    # Recheck the destination immediately before the write. Never overwrite existing rows.
    if sheets_values(auth, "A3:AE") != current:
        raise RuntimeError("Source spreadsheet changed mid-run; fail closed")
    if additions:
        first = 3 + len(current)
        last = first + len(additions)-1
        end="AE" if shift else "AB"
        url = API + quote(f"{SHEET_NAME}!A3:{end}", safe="!:") + ":append"
        result=requests.post(url,headers=auth,
            params={"valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"},
            json={"majorDimension":"ROWS","values":[physical_append_row(x["values"],shift) for x in additions]},
            timeout=60)
        result.raise_for_status()
        reported=(result.json().get("updates") or {}).get("updatedRange","")
        if not reported.split("!")[-1].startswith(f"A{first}:"):
            raise RuntimeError("P3 append did not return expected range: "+reported)
        check = sheets_values(auth, f"A{first}:B{last}")
        expected = [[a["ticker"],a["nct"]] for a in additions]
        if check != expected:
            raise RuntimeError("Post-write P3 candidate identity verification failed")
    AUDIT.parent.mkdir(exist_ok=True, parents=True)
    audit = {"date":cutoff.isoformat(), "existing":len(existing_ids),
             "added":[{"nct":a["nct"],"ticker":a["ticker"]} for a in additions],
             "review":review, "total":len(existing_ids)+len(additions),
             "poolModified":False, "historicalScoresModified":False}
    AUDIT.write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
