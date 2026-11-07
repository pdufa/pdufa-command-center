"""Sync only the canonical master POOL to PDUFA Master Scan Data.

The user retired all separate TOP, GEM/GEM JR, 730/741/762 and Before/Past
trial lists. Never recreate or require those tabs. P3 POST-DATA is separately
curated and must not be overwritten by the POOL source importer.
"""
from __future__ import annotations

import csv
import json
import os
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import google.auth.transport.requests
from google.oauth2 import service_account
import requests

SHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
HEADERS = [
    "ticker", "company", "nct_id", "phase", "status", "drug",
    "intervention_type", "route", "indication", "start_date",
    "primary_completion", "study_completion", "results_posted",
    "source_updated", "source_url", "checked_at",
]
TARGET = "Master Trials (Published)"


def main():
    path = Path("data/all_phase_trials.csv")
    if not path.is_file():
        raise SystemExit("Master POOL registry source absent; existing POOL preserved")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADERS:
            raise SystemExit("Master POOL source columns changed; existing POOL preserved")
        records = list(reader)
    ncts = [row["nct_id"] for row in records]
    if len(records) < 10_000 or len(ncts) != len(set(ncts)) or not all(
        len(nct) == 11 and nct.startswith("NCT") and nct[3:].isdigit() for nct in ncts
    ):
        raise SystemExit("Master POOL identity/count validation failed; no write")

    secret = os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "")
    if not secret:
        raise SystemExit("Google Sheets service account missing; no write")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(secret), scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {credentials.token}"

    def request(method, suffix, **kwargs):
        for attempt in range(8):
            try:
                response = session.request(method, BASE + suffix, timeout=60, **kwargs)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt == 7:
                    raise
            else:
                if response.status_code not in (429, 500, 502, 503, 504):
                    response.raise_for_status()
                    return response.json() if response.content else {}
                if attempt == 7:
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = max(0, float(retry_after))
                except (ValueError, TypeError):
                    try:
                        delay = max(
                            0, (parsedate_to_datetime(retry_after) -
                                datetime.now(timezone.utc)).total_seconds()
                        )
                    except (TypeError, ValueError, OverflowError):
                        delay = 0
                if delay:
                    time.sleep(min(delay, 120))
                    continue
            time.sleep(min(2 ** attempt + random.uniform(0, 1), 90))
        raise RuntimeError("Sheets retry attempts exhausted")

    def a1(cells):
        return quote(f"'{TARGET}'!{cells}", safe="!':")

    metadata = request(
        "GET", "",
        params={"fields": "sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))"},
    )
    sheets = {
        item["properties"]["title"]: item["properties"]
        for item in metadata.get("sheets", [])
    }
    master = sheets.get(TARGET)
    if not master or master.get("gridProperties", {}).get("columnCount", 0) < len(HEADERS):
        raise SystemExit("Expected canonical POOL tab missing/too narrow; no write")

    rows = [HEADERS] + [[record.get(key, "") for key in HEADERS] for record in records]
    capacity = master["gridProperties"]["rowCount"]
    if capacity < len(rows):
        request("POST", ":batchUpdate", json={
            "requests": [{"updateSheetProperties": {
                "properties": {
                    "sheetId": master["sheetId"],
                    "gridProperties": {"rowCount": len(rows) + 100},
                },
                "fields": "gridProperties.rowCount",
            }}]
        })
    for start in range(0, len(rows), 400):
        request("PUT", "/values/" + a1(f"A{start + 1}"),
                params={"valueInputOption": "RAW"},
                json={"majorDimension": "ROWS", "values": rows[start:start + 400]})
    final_capacity = max(capacity, len(rows) + 100 if capacity < len(rows) else capacity)
    if final_capacity > len(rows):
        request("POST", "/values/" + a1(f"A{len(rows) + 1}:P{final_capacity}") + ":clear",
                json={})

    first = request("GET", "/values/" + a1("A1:C2")).get("values", [])
    last = request("GET", "/values/" + a1(f"A{len(rows)}:C{len(rows)}")).get("values", [])
    if not first or first[0] != HEADERS[:3] or len(first) < 2 or first[1] != rows[1][:3]:
        raise RuntimeError("POOL first-row readback failed")
    if last != [rows[-1][:3]]:
        raise RuntimeError("POOL final-row readback failed")

    if "Import Status" in sheets:
        status_range = quote("'Import Status'!A1:D100", safe="!':")
        status = request("GET", "/values/" + status_range).get("values", [])
        if status and status[0] == ["Dataset", "Records", "Status", "Source / important qualification"]:
            replacements = []
            for index, row in enumerate(status, start=1):
                if not row:
                    continue
                label = row[0]
                if label == TARGET:
                    val = [len(records), "IMPORTED · SOURCE VALIDATED",
                           "Canonical master POOL refreshed from data/all_phase_trials.csv; P3 POST-DATA is independent."]
                elif label in ("GEM", "GEM JR"):
                    val = [0, "RETIRED", "Legacy GEM separate trial list retired; source history remains in Git."]
                elif label == "Automated Google Sheets Sync":
                    val = ["—", "ACTIVE · POOL ONLY",
                           "Only canonical POOL imported. No retired subsets created; P3 POST-DATA unchanged."]
                else:
                    continue
                replacements.append({"range": f"'Import Status'!B{index}:D{index}", "values": [val]})
            if replacements:
                request("POST", "/values:batchUpdate",
                        json={"valueInputOption": "RAW", "data": replacements})
    print(f"Master POOL synced: {len(records)} unique NCTs; P3 POST-DATA untouched; no old trial subsets.")


if __name__ == "__main__":
    main()
