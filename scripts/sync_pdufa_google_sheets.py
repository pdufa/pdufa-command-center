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
    # Historical FDA model outcomes: append only separately identifiable research
    # records, explicitly marked retrospective. Never label model outcomes as
    # independently FDA-verified decisions or assign live ratings.
    historical_path = Path("data/fda_100_on_100_historical.csv")
    if historical_path.is_file():
        records = list(csv.DictReader(historical_path.open(newline="", encoding="utf-8-sig")))
        expected = {"event_key", "ticker", "pdufa_date", "qualified_direction", "actual_outcome", "source_layer", "status"}
        if records and all(expected.issubset(record) for record in records):
            history_url = BASE + "/values/" + requests.utils.quote("'FDA Outcome History'!A1:L500", safe="!:'")
            existing_response = session.get(history_url, timeout=45)
            existing_response.raise_for_status()
            existing = existing_response.json().get("values", [])
            header = ["Company", "Ticker", "Drug", "Indication", "NDA/BLA", "PDUFA Date",
                      "FDA Decision", "Rating", "Rating Date", "Decision Source URL",
                      "Verified On", "Notes"]
            if existing and existing[0] == header:
                # Preserve previously sourced rows; the event key is carried in Notes.
                seen = {cell for row in existing[1:] for cell in row[11:12] if cell}
                new_rows = []
                for record in records:
                    key = record["event_key"].strip()
                    if not key or any(key in note for note in seen):
                        continue
                    # Event key often embeds drug identity; no reliable NDA/BLA,
                    # indication, primary FDA decision URL or numeric rating here.
                    parts = key.split("|")
                    drug = parts[2] if len(parts) > 2 else ""
                    note = ("MODEL_HISTORY " + key + " | " + record.get("source_layer", "") +
                            " | " + record.get("status", "") +
                            " | historical outcome from research dataset; primary FDA decision not independently verified")
                    new_rows.append(["", record.get("ticker", ""), drug, "", "",
                                     record.get("pdufa_date", ""),
                                     record.get("actual_outcome", ""), "", "", "", "", note])
                if new_rows:
                    append_url = BASE + "/values/" + requests.utils.quote("'FDA Outcome History'!A:L", safe="!:'") + ":append"
                    response = session.post(append_url,
                        params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                        json={"values": new_rows}, timeout=45)
                    response.raise_for_status()
                print(f"Historical FDA research records appended: {len(new_rows)} (not independent FDA verification)")
            else:
                print("FDA Outcome History headers changed; skipping research import")
    # Phase 3 discovery milestones, keyed by NCT + date + event.
    # These are reported readouts, not independently confirmed regulatory events.
    milestone_path = Path("data/post_phase3_discoveries.csv")
    if milestone_path.is_file():
        discoveries = list(csv.DictReader(milestone_path.open(newline="", encoding="utf-8-sig")))
        expected = {"ticker", "drug", "indication", "nct_id", "readout_date", "source_url"}
        if discoveries and all(expected.issubset(d) for d in discoveries):
            range_name = "'Trial Milestone History'!A1:M500"
            response = session.get(BASE + "/values/" + requests.utils.quote(range_name, safe="!:'"), timeout=45)
            response.raise_for_status()
            existing = response.json().get("values", [])
            header = ["Company", "Ticker", "Drug", "Indication", "NCT ID", "Program ID",
                      "Event Date", "Previous Stage", "New Stage", "Direction",
                      "Evidence URL", "Verified On", "Notes"]
            if existing and existing[0] == header:
                seen = {(row[4], row[6], row[8]) for row in existing[1:] if len(row) > 8}
                new_rows = []
                for d in discoveries:
                    key = (d["nct_id"], d["readout_date"], "Phase 3 readout")
                    if key in seen or not all(key[:2]):
                        continue
                    new_rows.append(["", d["ticker"], d["drug"], d["indication"],
                                     d["nct_id"], "", d["readout_date"], "",
                                     "Phase 3 readout", "REPORTED", d["source_url"], "",
                                     "Published post-Phase 3 discovery; not independent trial outcome verification"])
                    seen.add(key)
                if new_rows:
                    append_url = BASE + "/values/" + requests.utils.quote("'Trial Milestone History'!A:M", safe="!:'") + ":append"
                    response = session.post(append_url,
                        params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                        json={"values": new_rows}, timeout=45)
                    response.raise_for_status()
                print(f"Reported Phase 3 milestones appended: {len(new_rows)}")
            else:
                print("Trial Milestone History headers changed; skipping milestones")
    print(f"Published Candidates synced: {len(candidates)} rows. Full Pipeline/GEM data is not included in this snapshot.")


if __name__ == "__main__":
    main()
