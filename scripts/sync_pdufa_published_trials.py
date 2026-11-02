"""Synchronize validated public trial feed and saved GEM stages to native Google Sheets.

Requires GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON (Google Actions secret) and Editor
access for its service account on the destination sheet. This NEVER writes to
the qualified Pipeline tab, FDA designations, or scoring fields. GEM JR and
GEM manual score/FS/FA/scan fields are restored by exact ID independently.
"""
from __future__ import annotations

import csv
import json
import os
import random
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import google.auth.transport.requests
from google.oauth2 import service_account
import requests

SHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
TRIAL_HEADERS = [
    "ticker", "company", "nct_id", "phase", "status", "drug",
    "intervention_type", "route", "indication", "start_date",
    "primary_completion", "study_completion", "results_posted",
    "source_updated", "source_url", "checked_at",
]


def main() -> None:
    secret = os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "")
    if not secret:
        raise SystemExit("Missing GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON; existing Sheet unchanged")
    path = Path("data/all_phase_trials.csv")
    if not path.is_file():
        raise SystemExit("Published registry feed missing; existing Sheet unchanged")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != TRIAL_HEADERS:
            raise SystemExit("Unexpected clinical feed columns; existing Sheet unchanged")
        trials = list(reader)
    ncts = [row["nct_id"] for row in trials]
    if len(trials) < 10_000 or len(set(ncts)) != len(ncts) or not all(
        len(nct) == 11 and nct.startswith("NCT") and nct[3:].isdigit() for nct in ncts
    ):
        raise SystemExit("Clinical trial feed failed count/identity validation; existing Sheet unchanged")
    ledger_path = Path("data/gem_stage_membership.json")
    if not ledger_path.is_file():
        raise SystemExit("GEM ledger missing; existing Sheet unchanged")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if ledger.get("schema_version") != 1:
        raise SystemExit("Unknown GEM ledger schema; existing Sheet unchanged")
    by_nct = {row["nct_id"]: row for row in trials}
    by_ticker = {}
    for row in trials:
        by_ticker.setdefault(row["ticker"], row["company"])
    stage_rows = {}
    for stage in ("GEM_JR", "GEM"):
        records = ledger.get("stages", {}).get(stage, {}).get("entries", {})
        items = sorted(
            [(identity, rec) for identity, rec in records.items()
             if rec.get("status") == "ACTIVE" and rec.get("pipeline_id") == identity],
            key=lambda pair: (pair[1].get("ticker", ""), pair[0]),
        )
        if len(items) > 500 or len(items) == 0:
            raise SystemExit(f"{stage} membership count invalid; existing Sheet unchanged")
        stage_rows[stage] = items

    creds = service_account.Credentials.from_service_account_info(
        json.loads(secret), scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {creds.token}"

    def req(method, suffix, **kwargs):
        # Sheets quotas can return 429 during large published-feed imports.
        # Retry only transient failures; preserve existing data on exhaustion.
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
                delay = 0.0
                if retry_after:
                    try:
                        delay = max(0.0, float(retry_after))
                    except ValueError:
                        try:
                            delay = max(0.0, (parsedate_to_datetime(retry_after) -
                                             datetime.now(timezone.utc)).total_seconds())
                        except (TypeError, ValueError, OverflowError):
                            pass
                if delay:
                    time.sleep(min(delay, 120.0))
                    continue
            time.sleep(min(2 ** attempt + random.uniform(0, 1), 90.0))
        raise RuntimeError("Sheets retry attempts exhausted")

    def a1(sheet, cells):
        return quote(f"'{sheet}'!{cells}", safe="!':")

    def read(sheet, cells):
        return req("GET", "/values/" + a1(sheet, cells)).get("values", [])

    def put(sheet, start, values):
        if not values:
            return
        req("PUT", "/values/" + a1(sheet, start),
            params={"valueInputOption": "RAW"},
            json={"majorDimension": "ROWS", "values": values})

    def clear(sheet, cells):
        req("POST", "/values/" + a1(sheet, cells) + ":clear", json={})

    details = req("GET", "", params={"fields": "sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))"})
    sheets = {sheet["properties"]["title"]: sheet["properties"] for sheet in details["sheets"]}
    expected = {"Master Trials (Published)": 16, "GEM JR": 11, "GEM": 10}
    for title, count in expected.items():
        if title not in sheets or sheets[title]["gridProperties"]["columnCount"] < count:
            raise SystemExit(f"Target {title} missing or has insufficient columns")

    total_rows = len(trials) + 1
    master = sheets["Master Trials (Published)"]
    if master["gridProperties"]["rowCount"] < total_rows:
        req("POST", ":batchUpdate", json={"requests": [{
            "updateSheetProperties": {
                "properties": {"sheetId": master["sheetId"],
                               "gridProperties": {"rowCount": total_rows}},
                "fields": "gridProperties.rowCount",
            }
        }]})

    # Fetch every stage's old values before changing anything. Manual values
    # are retained by immutable identity, never borrowed across GEM/GEM JR.
    original_stage = {
        title: read(title, "A2:K1000" if title == "GEM JR" else "A2:J1000")
        for title in ("GEM JR", "GEM")
    }
    stage_updates = {}
    for stage, title in (("GEM_JR", "GEM JR"), ("GEM", "GEM")):
        old = {row[0]: row for row in original_stage[title] if row and row[0]}
        values = []
        for identity, record in stage_rows[stage]:
            ticker = record.get("ticker", "")
            nct = record.get("nct_id", "")
            clinical = by_nct.get(nct, {})
            company = clinical.get("company") or by_ticker.get(ticker, "")
            url = f"https://clinicaltrials.gov/study/{nct}" if nct else ""
            if stage == "GEM_JR":
                row = [identity, ticker, company, record.get("drug", ""),
                       clinical.get("indication", ""), "", "", "", "", url, ""]
                for index in (5, 6, 7, 8, 10):
                    previous = old.get(identity, [])
                    if len(previous) > index:
                        row[index] = previous[index]
            else:
                row = [identity, ticker, company, record.get("drug", ""),
                       clinical.get("indication", ""), "", "", "", url, ""]
                for index in (5, 6, 7, 9):
                    previous = old.get(identity, [])
                    if len(previous) > index:
                        row[index] = previous[index]
            values.append(row)
        stage_updates[title] = values

    # Write source data in bounded batches; never clear the entire master tab.
    values = [TRIAL_HEADERS] + [[record.get(key, "") for key in TRIAL_HEADERS] for record in trials]
    for start in range(0, len(values), 400):
        put("Master Trials (Published)", f"A{start+1}", values[start:start+400])
    old_capacity = master["gridProperties"]["rowCount"]
    if old_capacity > len(values):
        clear("Master Trials (Published)", f"A{len(values)+1}:P{old_capacity}")

    for title, records in stage_updates.items():
        for start in range(0, len(records), 200):
            put(title, f"A{start+2}", records[start:start+200])
        # Remove stale departed stage rows while retaining the published
        # membership history in GitHub. No cross-stage preset transfers.
        old_count = len(original_stage[title])
        if old_count > len(records):
            last_col = "K" if title == "GEM JR" else "J"
            clear(title, f"A{len(records)+2}:{last_col}{old_count+1}")
    # Idempotent dated publication snapshot. This is NOT evidence of a completed scan.
    # Keep the independently verified backend universe separate from the published feed.
    daily_header = [
        "Date", "Snapshot Type", "Pipeline", "GEM JR", "GEM",
        "Clinical Rows", "Regulatory Programs", "Phase 3 Programs",
        "Phase 3 Results", "Scanner Completion", "Source Health",
        "Evidence / Notes",
    ]
    from datetime import datetime
    from zoneinfo import ZoneInfo
    snapshot_date = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    published_count = len(trials)
    jr_count = len(stage_updates["GEM JR"])
    gem_count = len(stage_updates["GEM"])
    if "Daily Results" in sheets:
        history = read("Daily Results", "A1:L500")
        if not history or history[0][:len(daily_header)] != daily_header:
            raise SystemExit("Daily Results schema changed; refusing to write history")
        snapshot_type = "GitHub published feed"
        if not any(len(row) >= 2 and row[0] == snapshot_date and row[1] == snapshot_type for row in history[1:]):
            snapshot = [
                snapshot_date, snapshot_type, "", jr_count, gem_count,
                published_count, "", "", "", "NOT VERIFIED",
                "PUBLISHED FEED ONLY",
                "Validated unique NCTs from data/all_phase_trials.csv; saved GEM memberships. "
                "No qualified Pipeline count, regulatory count, or completed scanner status inferred.",
            ]
            req("POST", "/values/" + a1("Daily Results", "A:L") + ":append",
                params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                json={"values": [snapshot]})
            print(f"Daily Results publication snapshot appended for {snapshot_date}")
        else:
            print(f"Daily Results publication snapshot already present for {snapshot_date}")
    else:
        print("Daily Results tab missing; skipping history without changing source imports")

    # Publish import status only after all source and history writes succeed.
    # A successful import is separate from completion of the overnight scanner.
    if "Import Status" in sheets:
        status_rows = read("Import Status", "A1:D100")
        status_header = ["Dataset", "Records", "Status", "Source / important qualification"]
        if not status_rows or status_rows[0] != status_header:
            raise SystemExit("Import Status schema changed; refusing to overwrite status")
        import subprocess
        source_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
        imported_at = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %I:%M:%S %p %Z")
        event = os.getenv("GITHUB_EVENT_NAME", "local")
        automatic = event in ("push", "workflow_run", "schedule")
        repository = os.getenv("GITHUB_REPOSITORY", "pdufa/pdufa-command-center")
        run_id = os.getenv("GITHUB_RUN_ID", "")
        run_url = f"https://github.com/{repository}/actions/runs/{run_id}" if run_id else ""
        updates = {
            "Master Trials (Published)": [
                published_count, "IMPORTED · SOURCE VALIDATED",
                f"Unique NCT IDs in data/all_phase_trials.csv; imported {imported_at}. "
                "This validates the published feed, not a newly completed scanner run.",
            ],
            "GEM JR": [
                jr_count, "IMPORTED · SAVED MEMBERS",
                "Published GEM_JR membership ledger; FS/FA and sourced scores retained independently by trial ID.",
            ],
            "GEM": [
                gem_count, "IMPORTED · SAVED MEMBERS",
                "Published GEM membership ledger; FS/FA and sourced scores retained independently by trial ID.",
            ],
            "Automated Google Sheets Sync": [
                "—", "ACTIVE · AUTOMATIC IMPORT VERIFIED" if automatic else "ACTIVE · MANUAL IMPORT VERIFIED",
                f"Last completed import: {imported_at}; trigger: {event}. {run_url} "
                f"Imported {published_count:,} published NCTs, {jr_count} GEM JR and {gem_count} GEM. "
                "Qualified Pipeline and FDA designations are not populated by this import; "
                "overnight scanner completion is not verified here.",
            ],
            "Published feed commit SHA": [
                source_sha, "PROVENANCE",
                f"https://github.com/{repository}/blob/{source_sha}/data/all_phase_trials.csv",
            ],
        }
        data = [
            {"range": f"'Import Status'!B{number}:D{number}", "values": [updates[row[0]]]}
            for number, row in enumerate(status_rows, start=1)
            if row and row[0] in updates
        ]
        if data:
            req("POST", "/values:batchUpdate", json={"valueInputOption": "RAW", "data": data})
        print(f"Import Status refreshed: {imported_at}; trigger={event}; source={source_sha}")

    print(
        f"Synced {len(trials)} unique published trials, "
        f"{len(stage_updates['GEM JR'])} GEM JR, {len(stage_updates['GEM'])} GEM. "
        "Pipeline qualifications and FDA designations intentionally not inferred."
    )


if __name__ == "__main__":
    main()
