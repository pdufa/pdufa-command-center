#!/usr/bin/env python3
"""Publish a minimal, read-only FOCUS FDA-date feed for Apple Calendar.

Reads the existing private FOCUS Google Sheet using the configured GitHub
Actions service account. Publishes only screened, dated issuer events, NOT
private research, ratings, scores, or sheet credentials. Does not alter FOCUS.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import json
import os
import re
import sys

from google.auth.transport.requests import Request
from google.oauth2 import service_account
import requests

SHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
A1_RANGE = "'FOCUS'!A3:AC"
OUTPUT = Path("data/ios_focus_pdufa_calendar.json")
APP_SNAPSHOT = Path("new-platform/backend/app/data/focus_application_snapshot.json")
MIN_CAP = 300_000_000
MAX_CAP = 10_000_000_000


def cell(row: list, index: int) -> str:
    return str(row[index]).strip() if index < len(row) and row[index] is not None else ""


def event_date(value: str) -> str | None:
    # Only a precise date, not "planned Q4" or an unassigned PDUFA goal.
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def drug_map() -> dict[str, str]:
    if not APP_SNAPSHOT.is_file():
        return {}
    source = json.loads(APP_SNAPSHOT.read_text(encoding="utf-8"))
    return {item["nct"]: item["drug"] for item in source.get("records", [])
            if re.fullmatch(r"NCT\d{8}", str(item.get("nct", "")))
            and isinstance(item.get("drug"), str)}


def read_focus() -> list[list]:
    raw = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON secret not configured")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(raw), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    creds.refresh(Request())
    url = "https://sheets.googleapis.com/v4/spreadsheets/" + SHEET_ID + "/values/" + requests.utils.quote(A1_RANGE, safe="!:'")
    response = requests.get(url, headers={"Authorization": "Bearer " + creds.token},
                            params={"valueRenderOption": "FORMATTED_VALUE"}, timeout=35)
    response.raise_for_status()
    rows = response.json().get("values", [])
    if not rows or cell(rows[0], 0) != "Ticker" or cell(rows[0], 26) != "Market Cap USD" or cell(rows[0], 28) != "PDUFA / FDA Filing":
        raise RuntimeError("FOCUS spreadsheet columns changed; refusing unsafe publication")
    return rows[1:]


def publish(rows: list[list]) -> bool:
    names = drug_map()
    groups: dict[tuple[str, str], dict] = {}
    for row in rows:
        ticker = cell(row, 0).upper()
        nct = cell(row, 1)
        company = cell(row, 2)
        target = event_date(cell(row, 28))
        if not re.fullmatch(r"[A-Z0-9.-]{1,10}", ticker) or not re.fullmatch(r"NCT\d{8}", nct):
            continue
        if not company or not target:
            continue
        try:
            cap = int(round(float(cell(row, 26).replace(",", "").replace("$", ""))))
        except ValueError:
            continue
        if not (MIN_CAP <= cap <= MAX_CAP):
            continue
        key = (ticker, target)
        if key not in groups:
            groups[key] = {
                "ticker": ticker,
                "company": company[:200],
                "date": target,
                "marketCapUsd": cap,
                "ncts": set(),
                "drugs": set(),
                "sourceUrls": set()
            }
        groups[key]["ncts"].add(nct)
        if nct in names:
            groups[key]["drugs"].add(names[nct])
        source_url = cell(row, 24)
        if re.fullmatch(r"https://[^\s]+", source_url):
            groups[key]["sourceUrls"].add(source_url)

    previous = {}
    if OUTPUT.is_file():
        previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
    old_events = previous.get("events", [])
    seen_old_ids: set[str] = set()
    results = []
    for key in sorted(groups, key=lambda pair: (pair[1], pair[0])):
        item = groups[key]
        ncts = sorted(item.pop("ncts"))
        drugs = sorted(item.pop("drugs"))
        urls = sorted(item.pop("sourceUrls"))
        choices = [
            prior for prior in old_events
            if prior.get("id") not in seen_old_ids
            and prior.get("ticker") == item["ticker"]
            and set(prior.get("ncts", [])).intersection(ncts)
        ]
        # Same application stays the same Apple Calendar event when a PDUFA
        # target changes; the UID never incorporates the mutable date.
        event_id = choices[0]["id"] if choices else "focus-" + item["ticker"].lower() + "-" + ncts[0].lower()
        seen_old_ids.add(event_id)
        item.update({
            "id": event_id,
            "ncts": ncts,
            "drug": drugs[0] if len(drugs) == 1 else "",
            "sourceUrl": urls[0] if urls else "",
        })
        results.append(item)

    if not rows:
        raise RuntimeError("FOCUS spreadsheet empty; retaining previously published calendar")
    if not results and previous.get("events"):
        raise RuntimeError("All dated events vanished; manual review required before clearing calendar")
    # No calendar/commit churn when the live roster has not changed.
    if previous.get("schemaVersion") == 1 and previous.get("events") == results:
        print("FOCUS calendar checked; no event changes")
        return False

    out = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": "FOCUS Google Sheet: cap-screened $300M-$10B trial population",
        "sourceSheetId": SHEET_ID,
        "events": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Published " + str(len(results)) + " FOCUS PDUFA dates; no other trial data changed")
    return True


if __name__ == "__main__":
    try:
        publish(read_focus())
    except Exception as exc:
        print("Unable to refresh FOCUS calendar safely: " + str(exc), file=sys.stderr)
        sys.exit(1)
