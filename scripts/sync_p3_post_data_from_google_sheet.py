"""Publish only the vetted P3 POST-DATA roster from the owner's Google Sheet.

The master POOL and source research snapshots remain unchanged. No historical
TOP/BOTTOM/762 universe is rebuilt or inferred. Never publish malformed data.
"""
from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

import google.auth.transport.requests
from google.oauth2 import service_account
import requests

SPREADSHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
SOURCE_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit#gid=202611061"
RANGE = "'BOTTOM — ACTIVE'!A4:AB600"
TARGET = Path("new-platform/frontend/data/p3PostDataActive.json")


def https_url(v):
    if not isinstance(v, str):
        return False
    url = urlsplit(v)
    return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password


def extract(rows):
    trials = []
    seen = set()
    for row in rows:
        if len(row) < 2 or not str(row[1]).strip():
            continue
        fields = list(row) + [""] * max(0, 28 - len(row))
        ticker, nct, company = (str(fields[i]).strip() for i in (0, 1, 2))
        if not re.fullmatch(r"NCT[0-9]{8}", nct) or nct in seen:
            raise ValueError("Invalid or duplicate candidate NCT ID: " + nct)
        if not re.fullmatch(r"[A-Z][A-Z0-9.]{0,9}", ticker):
            raise ValueError("Invalid ticker " + ticker)
        cap = fields[23]
        if isinstance(cap, bool) or not isinstance(cap, (int, float)) or not 300_000_000 <= cap <= 10_000_000_000:
            raise ValueError("Unverified/out-of-range market cap for " + nct)
        if not str(fields[4]).strip().upper().startswith("YES"):
            raise ValueError("Phase 3 results not marked publicly posted: " + nct)
        if not company or not str(fields[19]).strip() or not str(fields[25]).strip():
            raise ValueError("Missing company or ongoing FDA application path: " + nct)
        if not https_url(fields[21]) or not https_url(fields[26]):
            raise ValueError("Missing valid results and FDA evidence URLs: " + nct)
        seen.add(nct)
        trials.append({
            "ticker": ticker, "nct": nct, "company": company, "marketCap": int(cap),
            "fdaStatus": str(fields[25]).strip(), "resultsUrl": fields[26],
            "regulatoryUrl": fields[21],
        })
    if not trials:
        raise ValueError("P3 POST-DATA candidate table is empty")
    return sorted(trials, key=lambda x: (x["ticker"], x["nct"]))


def main():
    secret = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "")
    if not secret:
        raise RuntimeError("Google Sheets service account absent; preserved current site snapshot")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(secret), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    target = quote(RANGE, safe="!':")
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{target}"
    response = requests.get(url, headers={"Authorization": "Bearer " + creds.token},
                            params={"valueRenderOption": "UNFORMATTED_VALUE"}, timeout=60)
    response.raise_for_status()
    rows = response.json().get("values")
    if not isinstance(rows, list):
        raise ValueError("Missing P3 POST-DATA source rows")
    trials = extract(rows)
    previous = json.loads(TARGET.read_text()) if TARGET.is_file() else None
    if previous and previous.get("records") == trials:
        print(f"P3 POST-DATA unchanged: {len(trials)} unique candidates")
        return
    snapshot = {
        "schemaVersion": 1,
        "asOf": datetime.now(timezone.utc).date().isoformat(),
        "origin": "BOTTOM — ACTIVE / Google Sheet",
        "source": SOURCE_URL,
        "records": trials,
    }
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"P3 POST-DATA refreshed: {len(trials)} unique candidates; POOL untouched")


if __name__ == "__main__":
    main()
