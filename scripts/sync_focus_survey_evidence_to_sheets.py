#!/usr/bin/env python3
"""Sync collector-owned FOCUS research tables; never overwrite original FOCUS.

Guardrail: table ownership is asserted by its exact header, data are precomputed
and bounded, credentials must be present, and every write is read back.
This is a research evidence queue, NOT independently verified survey answers.
"""
from __future__ import annotations
import json
import os
import re
from urllib.parse import quote

SPREADSHEET_ID = "1erY_z62b4mHhx5s_3HgJxXoJEslbLngMuQNfhcuSviU"
API = "https://sheets.googleapis.com/v4/spreadsheets/" + SPREADSHEET_ID
EVIDENCE_HEADERS = ["NCT ID", "Ticker", "Company", "Survey Number", "Survey",
                    "Ingredient ID", "Ingredient", "Evidence Status",
                    "Reviewed Value", "Reviewed Source URL", "Reviewed Source Date",
                    "Publication Leads", "Missing / Review Reason",
                    "Registry Source URL", "Registry Evidence Pointer", "Registry Lead Count"]
COVERAGE_HEADERS = ["Survey Number", "Survey", "Slots", "Verified",
                    "Source Captured Pending Review", "Missing / Unavailable"]
GAP_HEADERS = EVIDENCE_HEADERS
SOURCE_HEADERS = ["NCT ID", "Ticker", "Clinical Registry Retrieved",
                  "Literature Leads", "Verified Ingredients",
                  "Source Leads Pending Review", "Missing / Unavailable"]

def table_data(flat, report):
    if report.get("focusTrials") * 38 != len(flat) or len(flat) < 38 * 10:
        raise ValueError("REFUSING_PARTIAL_FOCUS_SHEET_SYNC")
    if len({(r["nctId"], r["ingredientId"]) for r in flat}) != len(flat):
        raise ValueError("DUPLICATED_NCT_INGREDIENT")
    if report.get("ingredientSlots") != len(flat) or report.get("surveyIngredients") != 38:
        raise ValueError("FOCUS_SURVEY_COVERAGE_MISMATCH")
    evidence = [[r.get(k) if r.get(k) is not None else "" for k in
       ("nctId", "ticker", "company", "surveyNumber", "surveyName", "ingredientId",
        "ingredientName", "status", "reviewedValue", "reviewedSourceUrl",
        "reviewedSourceDate", "publicationLeads", "reason", "registryLeadUrl",
        "registryLeadPointer", "registryLeadCount")] for r in flat]
    coverage = [[r.get(k) if r.get(k) is not None else "" for k in
       ("surveyNumber", "name", "slots", "verified", "capturedNeedsReview", "missing")]
       for r in report["bySurvey"]]
    gaps = [row for row in evidence if row[7] not in ("VERIFIED", "NOT_APPLICABLE")]
    source = [[r.get(k) if r.get(k) is not None else "" for k in
       ("nctId", "ticker", "registryRetrieved", "literatureLeads", "verified",
        "capturedNeedsReview", "missing")] for r in report["byTrial"]]
    return [
      ("FOCUS Survey Auto Evidence", EVIDENCE_HEADERS, evidence),
      ("FOCUS Survey Auto Coverage", COVERAGE_HEADERS, coverage),
      ("FOCUS Survey Auto Gaps", GAP_HEADERS, gaps),
      ("FOCUS Survey Auto Sources", SOURCE_HEADERS, source),
    ]

def sync(flat, report):
    """Existing four collector-owned FOCUS survey tabs."""
    if report.get("ingredientSlots") != len(flat):
        raise ValueError("FOCUS_SURVEY_COVERAGE_MISMATCH")
    return sync_tables(table_data(flat, report))

def sync_tables(tables):
    """Write only table-specific automation-owned tabs after header checks."""
    import requests
    from google.oauth2 import service_account
    import google.auth.transport.requests
    secret = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON")
    if not secret:
        raise RuntimeError("Google Sheets credentials unavailable; preserved existing workbook")
    info = json.loads(secret)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    creds.refresh(google.auth.transport.requests.Request())
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + creds.token
    session.headers["Accept"] = "application/json"
    def request(method, url, **kwargs):
        response = session.request(method, url, timeout=45, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else {}
    if not tables or len({name for name,_,_ in tables}) != len(tables):
        raise ValueError("DUPLICATE_OR_EMPTY_AUTOMATION_TABLES")
    if any(not name.startswith("FOCUS Survey Auto ") for name,_,_ in tables):
        raise ValueError("REFUSING_NON_AUTOMATION_SHEET")
    meta = request("GET", API, params={"fields": "sheets(properties(sheetId,title,gridProperties)),spreadsheetId"})
    current = {s["properties"]["title"]: s["properties"] for s in meta.get("sheets", [])}
    # Check ALL existing headings BEFORE changing any tab.
    for title, header, _ in tables:
        if title not in current:
            continue
        end_col = chr(ord("A") + len(header) - 1)
        target = quote("'" + title.replace("'", "''") + "'!A1:" + end_col + "1", safe="!':")
        value = request("GET", API + "/values/" + target).get("values", [])
        if not value or value[0] != header:
            raise RuntimeError("Refusing to replace non-collector-owned tab: " + title)
    changes = []
    for title, header, body in tables:
        required_rows = len(body) + 1
        required_cols = len(header)
        if title not in current:
            changes.append({"addSheet": {"properties": {"title": title,
              "gridProperties": {"rowCount": max(required_rows + 30, 100),
                                 "columnCount": max(required_cols, 16),
                                 "frozenRowCount": 1}}}})
        else:
            props = current[title]
            grid = props.get("gridProperties", {})
            if grid.get("rowCount", 0) < required_rows:
                changes.append({"updateSheetProperties": {
                  "properties": {"sheetId": props["sheetId"],
                                 "gridProperties": {"rowCount": required_rows + 30}},
                  "fields": "gridProperties.rowCount"}})
            if grid.get("columnCount", 0) < required_cols:
                changes.append({"updateSheetProperties": {
                  "properties": {"sheetId": props["sheetId"],
                                 "gridProperties": {"columnCount": required_cols}},
                  "fields": "gridProperties.columnCount"}})
    if changes:
        request("POST", API + ":batchUpdate", json={"requests": changes})
    # No mutation of FOCUS, Phase 3 Survey Ingredients, POOL or any score tab.
    body = []
    for title, header, rows in tables:
        a1 = "'" + title.replace("'", "''") + "'!A1"
        # A shorter refresh must not leave previous evidence as stale-looking live rows.
        # Include blank tail rows in the same values:batchUpdate request.
        previous_capacity = current.get(title, {}).get("gridProperties", {}).get("rowCount", 0)
        blanks = max(0, previous_capacity - len(rows) - 1)
        fresh_values = [header] + rows + [[""] * len(header) for _ in range(blanks)]
        body.append({"range": a1, "majorDimension": "ROWS", "values": fresh_values})
    request("POST", API + "/values:batchUpdate", json={
        "valueInputOption": "RAW", "data": body})
    # Read back full populated column including prior tail to catch stale records.
    for title, header, rows in tables:
        previous_capacity = current.get(title, {}).get("gridProperties", {}).get("rowCount", 0)
        readback_rows = max(previous_capacity, len(rows) + 1)
        cell = quote("'" + title + "'!A1:A" + str(readback_rows), safe="!':")
        returned = request("GET", API + "/values/" + cell).get("values", [])
        expected = [header[0]] + [str(r[0]) for r in rows]
        values = [str(r[0]) if r else "" for r in returned]
        if values != expected:
            raise RuntimeError("FOCUS_SURVEY_SHEETS_READBACK_MISMATCH: " + title)
    return {"status": "SUCCESS", "tabs": [s[0] for s in tables],
            "rowsWritten": sum(len(x[2]) for x in tables)}
