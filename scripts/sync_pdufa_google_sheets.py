"""Sync verified published PDUFA candidate snapshot and audit to Google Sheets.

Requires GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON GitHub Actions secret.
Share the destination spreadsheet with the service account client_email (Editor).
No trial membership, FS/FA preset, or assessment calculation is changed here.
"""
import csv
import io
import json
import os
from pathlib import Path

import google.auth.transport.requests
from google.oauth2 import service_account
import requests

SHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
FIELDS = ["event_key","ticker","company","drug","indication","pdufa_date","nct_id","market_cap","science_score","regulatory_score","safety_score","cmc_score","approval_probability","pdufa_evidence_url","trial_evidence_url","last_checked"]


def main():
    credentials_json = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON")
    if not credentials_json:
        raise SystemExit("Google Sheets sync not configured: missing GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(credentials_json),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    creds.refresh(google.auth.transport.requests.Request())
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {creds.token}"
    def put(range_name, values):
        url = BASE + "/values/" + requests.utils.quote(range_name, safe="!:'") 
        result = session.put(url, params={"valueInputOption":"RAW"}, json={"range":range_name,"majorDimension":"ROWS","values":values}, timeout=45)
        result.raise_for_status()
    def clear(range_name):
        url = BASE + "/values/" + requests.utils.quote(range_name, safe="!:'") + ":clear"
        result = session.post(url, json={}, timeout=45)
        result.raise_for_status()

    path = Path("data/pdufa_candidates.csv")
    if not path.is_file():
        raise SystemExit("Published candidate file missing; refusing to erase existing spreadsheet")
    candidates = list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
    if not candidates:
        raise SystemExit("Published candidate file empty; refusing to erase existing spreadsheet")
    values = [FIELDS] + [[row.get(field, "") for field in FIELDS] for row in candidates]
    clear("'Published Candidates'!A2:P")
    put("'Published Candidates'!A1", values)

    audit_path = Path("data/nightly_scan_report.json")
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text())
        if audit.get("latest_run_id"):
            run_id = str(audit["latest_run_id"])
            range_name = "'Scan History'!A2:N"
            resp = session.get(BASE + "/values/" + requests.utils.quote(range_name, safe="!:'"), timeout=45)
            resp.raise_for_status()
            existing = resp.json().get("values", [])
            if not any(row and row[0] == run_id for row in existing):
                row = [run_id, audit.get("latest_run_started_at_utc", ""), audit.get("updated_at_utc", ""), audit.get("status", ""), "", "", "", "", "", "", "", "", "", "Published audit only; full-source verification not confirmed"]
                append_url = BASE + "/values/" + requests.utils.quote("'Scan History'!A:N", safe="!:'") + ":append"
                response = session.post(append_url, params={"valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"}, json={"values":[row]}, timeout=45)
                response.raise_for_status()
    print(f"Published Candidates synced: {len(candidates)} rows. Full Pipeline/GEM data is not included in this snapshot.")


if __name__ == "__main__":
    main()
