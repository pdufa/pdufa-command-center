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
SHEET_NAME = "BOTTOM — ACTIVE"
CANDIDATES = ROOT / "new-platform/backend/app/phase3_curated_announcements.json"
CAPS = ROOT / "data/phase_pipeline_market_caps.csv"
CENSUS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
POOL = ROOT / "data/all_phase_trials.csv"
DISCOVERIES = ROOT / "data/post_phase3_discoveries.csv"
AUDIT = ROOT / "reports/p3_auto_promotion_latest.json"
API = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/"
NCT = re.compile(r"NCT[0-9]{8}\Z")
TICKER = re.compile(r"[A-Z][A-Z0-9.]{0,9}\Z")


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
        if nct not in pool_ids:
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
        fda = item.get("pdufa_assignment") or {}
        reviewed = iso_day(item.get("reviewedOn"), cutoff)
        result_published = iso_day(result.get("published_at"), cutoff)
        fda_published = iso_day(fda.get("published_at"), cutoff)
        result_event = iso_day(result.get("event_date"), cutoff)
        fda_event = iso_day(fda.get("event_date"), cutoff)
        if (item.get("reviewerMethod") != "PRIMARY_PUBLIC_ISSUER_DISCLOSURE"
                or not reviewed or not result_published or not result_event
                or result.get("review_status") != "VERIFIED"
                or not link_ok(result.get("source_url"))
                or (reviewed and result_published and reviewed < result_published)):
            issues.append("PHASE3_PUBLIC_RESULTS_NOT_REVIEWED")
        try:
            target = date.fromisoformat(fda.get("pdufa_target_date", ""))
        except (ValueError, TypeError):
            target = None
        if (not fda_published or not fda_event
                or fda.get("review_status") != "VERIFIED"
                or not link_ok(fda.get("source_url"))
                or not reviewed or (reviewed and fda_published and reviewed < fda_published)
                or not target or target < cutoff):
            issues.append("NO_CURRENT_VERIFIED_FDA_PDUFA_PATH")
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
        description = ("Verified issuer Phase 3 public results and FDA accepted NDA/PDUFA "
                       "for exact-NCT program " + key)
        row = [""] * 28
        fields = {0:ticker, 1:nct, 2:next(r.get("company", "") for r in census if r.get("nct_id")==nct),
                  3:status, 4:"YES - company/SEC/journal", 5:result_event.isoformat(),
                  6:"https://clinicaltrials.gov/study/" + nct, 7:day, 8:now,
                  9:"PRIMARY_PUBLIC_ISSUER_DISCLOSURE", 10:"P3 automatic verified-source intake",
                  11:"0", 13:"30", 14:"0", 16:"NOT YET SCORED", 17:day,
                  18:"Open RAAS (search NCT)", 19:"FDA NDA review active",
                  20:description, 21:fda["source_url"], 22:day, 23:int(value),
                  24:check_day.isoformat(), 25:target.isoformat(),
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


def sheets_values(auth, range_name):
    url = API + quote(f"'{SHEET_NAME}'!{range_name}", safe="!':")
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
    current = sheets_values(auth, "A3:AB600")
    if not current or current[0][:3] != ["Ticker", "NCT ID", "Company"]:
        raise ValueError("Canonical P3 source headers changed; refusing to append")
    if any(not row or not row[1] for row in current[1:]):
        raise ValueError("Noncontiguous/empty NCT row: refuse to overwrite")
    existing_ids = [str(row[1]) for row in current[1:]]
    if len(existing_ids) != len(set(existing_ids)):
        raise ValueError("Source spreadsheet has duplicate NCTs; refusing to append")
    with CANDIDATES.open(encoding="utf-8") as f:
        catalog = json.load(f)
    with POOL.open(encoding="utf-8-sig", newline="") as f:
        pool_ids = {r.get("nct_id") for r in csv.DictReader(f) if NCT.fullmatch(r.get("nct_id") or "")}
    cutoff = datetime.now(timezone.utc).date()
    additions, review = evaluate(catalog, load_csv(CAPS), load_csv(CENSUS), pool_ids,
                                 set(existing_ids), cutoff)
    # Recheck the destination immediately before the write. Never overwrite existing rows.
    if sheets_values(auth, "A3:AB600") != current:
        raise RuntimeError("Source spreadsheet changed mid-run; fail closed")
    if additions:
        first = 3 + len(current)
        last = first + len(additions)-1
        if last > 600:
            raise ValueError("P3 row capacity safety bound reached")
        url = API + quote(f"'{SHEET_NAME}'!A{first}:AB{last}", safe="!':")
        result = requests.put(url, headers=auth, params={"valueInputOption":"RAW"},
                              json={"range":f"'{SHEET_NAME}'!A{first}:AB{last}",
                                    "majorDimension":"ROWS",
                                    "values":[a["values"] for a in additions]}, timeout=60)
        result.raise_for_status()
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
