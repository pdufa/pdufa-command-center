#!/usr/bin/env python3
"""Back up the current, fully reconciled Phase 3 registry posting split to two
existing tabs in PDUFA Master Scan Data, without touching other Google tabs.

'Phase 3 Before' = no ClinicalTrials.gov results-first-posted date.
'Phase 3 Past' = ClinicalTrials.gov results have been posted.
These are NOT verified issuer public-readout announcement states.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "new-platform/frontend/public/phase3-registry-postings-current.json"
SHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
API = "https://sheets.googleapis.com/v4/spreadsheets/" + SHEET_ID
MEASURE = "CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT"
COLUMNS = [
    "Ticker", "NCT ID", "Company", "Registry Status", "Results Posted?",
    "First Posted Date", "Registry Source", "Snapshot Date", "Checked UTC",
    "Classification Basis",
]
SHEET_NAMES = ("Phase 3 Before", "Phase 3 Past")
TAB_LABELS = (
    "PHASE 3 BEFORE · REGISTRY RESULTS NOT POSTED",
    "PHASE 3 PAST · REGISTRY RESULTS POSTED",
)
CAUTION = ("Registry results-posting classification ONLY. A company's public "
           "Phase 3 announcement can happen before registry results are posted. "
           "Exact NCT census, not FDA qualification.")


def valid_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d") == value
    except ValueError:
        return False


def prepare(payload, min_trials=700):
    """Return all sheet values after source scope/count/identity preflight."""
    if not isinstance(payload, dict):
        raise ValueError("Missing source data")
    day = payload.get("snapshotDate")
    checked = payload.get("sourceAsOf")
    records = payload.get("records")
    if (payload.get("schemaVersion") != 2 or
            payload.get("measure") != MEASURE or
            payload.get("sourceKind") != "OFFICIAL_CLINICALTRIALS_GOV_API_EXACT_NCT" or
            payload.get("sourceFile") != "data/phase3_all_years_300m_10b_trials.csv" or
            not valid_day(day) or not isinstance(checked, str) or
            checked[:10] != day or not isinstance(records, list) or
            not isinstance(payload.get("total"), int) or
            not min_trials <= payload["total"] <= 20000 or
            len(records) != payload["total"] or
            not isinstance(payload.get("noResultsPosted"), int) or
            not isinstance(payload.get("resultsPosted"), int) or
            payload["noResultsPosted"] + payload["resultsPosted"] != payload["total"]):
        raise ValueError("Incomplete or inconsistent Phase 3 snapshot")
    # Refuse a future or malformed source timestamp.
    try:
        stamp = datetime.fromisoformat(checked.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Missing or malformed collection timestamp") from exc
    if stamp.tzinfo is None or stamp.astimezone(timezone.utc).date().isoformat() != day:
        raise ValueError("Snapshot collection time is inconsistent")
    if stamp > datetime.now(timezone.utc):
        raise ValueError("Future registry verification timestamp")

    rows = [[], []]
    ncts = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Invalid trial source record")
        nct = record.get("nctId")
        ticker = record.get("ticker")
        company = record.get("company")
        status = record.get("registryStatus")
        count = record.get("resultsCount")
        posted = record.get("resultsFirstPostedDate")
        if (not isinstance(nct, str) or not re.fullmatch(r"NCT\d{8}", nct) or
                nct in ncts or not isinstance(ticker, str) or
                not re.fullmatch(r"[A-Z0-9.-]{1,15}", ticker) or
                not isinstance(company, str) or not company or len(company) > 250 or
                not isinstance(status, str) or
                not re.fullmatch(r"[A-Z_]{3,50}", status) or
                type(count) is not int or count not in (0, 1) or
                not isinstance(posted, str) or
                bool(posted) != bool(count) or
                (posted and (not valid_day(posted) or posted > day))):
            raise ValueError("Duplicate or invalid trial classification")
        ncts.add(nct)
        rows[int(count)].append([
            ticker, nct, company, status, "YES" if count else "NO",
            posted, "https://clinicaltrials.gov/study/" + nct,
            day, checked, MEASURE,
        ])
    if (len(ncts) != payload["total"] or
            len(rows[0]) != payload["noResultsPosted"] or
            len(rows[1]) != payload["resultsPosted"]):
        raise ValueError("Posted/unposted counts do not reconcile")

    result = {}
    for index, title in enumerate(SHEET_NAMES):
        group = sorted(rows[index], key=lambda r: (r[0], r[1]))
        result[title] = [
            [TAB_LABELS[index], f"{len(group)} trials", "", "", "", "", "", day, checked, ""],
            [CAUTION, "", "", "", "", "", "", "", "", ""],
            COLUMNS,
            *group,
        ]
    return result


def google_session():
    secret = os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "")
    if not secret:
        raise RuntimeError("Google Sheets credential secret is absent; nothing was overwritten")
    import requests
    import google.auth.transport.requests
    from google.oauth2 import service_account

    auth = service_account.Credentials.from_service_account_info(
        json.loads(secret),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    auth.refresh(google.auth.transport.requests.Request())
    session = requests.Session()
    session.headers.update({"Authorization": "Bearer " + auth.token})
    return session


def request(session, method, suffix, **kw):
    response = session.request(method, API + suffix, timeout=60, **kw)
    response.raise_for_status()
    return response.json()


def sync(values, session):
    """Fail closed for missing tab/columns, resize new rows safely and verify."""
    details = request(session, "GET", "", params={
        "fields": "sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))",
    })
    sheets = {
        s["properties"]["title"]: s["properties"]
        for s in details.get("sheets", [])
    }
    for title in SHEET_NAMES:
        prop = sheets.get(title)
        if not prop or prop.get("gridProperties", {}).get("columnCount", 0) < len(COLUMNS):
            raise RuntimeError(f"Expected Google Drive backup tab missing or too narrow: {title}")

    resize = []
    for title in SHEET_NAMES:
        cap = sheets[title]["gridProperties"]["rowCount"]
        required = len(values[title])
        if cap < required:
            resize.append({"updateSheetProperties": {
                "properties": {
                    "sheetId": sheets[title]["sheetId"],
                    "gridProperties": {"rowCount": required + 100},
                },
                "fields": "gridProperties.rowCount",
            }})
    if resize:
        request(session, "POST", ":batchUpdate", json={"requests": resize})

    # The two data updates are submitted together so a failed source cannot
    # lead to one successfully sourced and one stale classification tab.
    data = [{
        "range": "'" + title + "'!A1:J" + str(len(values[title])),
        "majorDimension": "ROWS",
        "values": values[title],
    } for title in SHEET_NAMES]
    result = request(session, "POST", "/values:batchUpdate", json={
        "valueInputOption": "RAW", "data": data,
    })
    if len(result.get("responses", [])) != 2:
        raise RuntimeError("Both trial tabs were not acknowledged by Sheets")

    # Read back every NCT and ticker, not just a green API response or a count.
    for title in SHEET_NAMES:
        expected = [x[:2] for x in values[title][3:]]
        raw = request(session, "GET", "/values/" + quote(
            "'" + title + "'!A4:B" + str(len(values[title])), safe="!':"
        ))
        found = raw.get("values", [])
        if found != expected:
            raise RuntimeError(f"Google Drive readback does not match exact NCT IDs in {title}")
        count_range = "'" + title + "'!A1:B1"
        count_row = request(session, "GET", "/values/" + quote(count_range, safe="!':"))
        if count_row.get("values", []) != [values[title][0][:2]]:
            raise RuntimeError(f"Google Drive {title} count or header mismatch")

    # Delete stale trailing values after successful rows have been confirmed.
    clears = []
    for title in SHEET_NAMES:
        cap = max(sheets[title]["gridProperties"]["rowCount"], len(values[title]) + 100)
        start = len(values[title]) + 1
        if start <= cap:
            clears.append("'" + title + "'!A" + str(start) + ":J" + str(cap))
    if clears:
        request(session, "POST", "/values:batchClear", json={"ranges": clears})
    return {title: len(values[title]) - 3 for title in SHEET_NAMES}


def main():
    if not SOURCE.exists():
        raise RuntimeError("Current Phase 3 registry source missing; Google backup unchanged")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    values = prepare(data)
    result = sync(values, google_session())
    print(json.dumps({
        "snapshot": data["sourceAsOf"],
        "trials": data["total"],
        "drive": SHEET_ID,
        "tabs": result,
        "verification": "exact ticker/NCT readback passed",
    }, indent=2))


if __name__ == "__main__":
    main()
