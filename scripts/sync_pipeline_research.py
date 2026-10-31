"""Preserving, idempotent sync of the authenticated website's canonical dataset.

Never clears a tab. Existing formulas, reviewer notes and user-edited values win.
Only blank cells or unchanged cells explicitly owned by this synchronizer update.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import os
import time
from urllib.parse import quote

SHEET_ID = "1FSRXFXc4u2KTpdyP-vSbWil-Fgtrj3ucELSk2kpQAG0"
SITE = "https://pdufa-new-dashboard.vercel.app"
PREFIX = "PDUFA_RESEARCH_SYNC_V1:"
SHEETS = ("07 Competitive Master", "13 Exact Trial Evidence", "15 Ranked 20 Assessments",
          "16 Competitor Inventory", "17 Assessment Evidence", "18 Mapping and Sync", "14 Charts Dashboard")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def validate_pages(pages):
    records, ids, ncts = [], set(), set()
    version = None
    total = None
    offset = 0
    for page in pages:
        if (page.get("schemaVersion") != 1 or page.get("offset") != offset
                or not isinstance(page.get("records"), list) or page.get("originalFieldCount") != 38
                or page.get("assessmentCount") != 20):
            raise ValueError("Invalid canonical page")
        if version is None:
            version, total = page["datasetVersion"], page["total"]
        if page["datasetVersion"] != version or page["total"] != total:
            raise ValueError("Dataset changed during sync")
        for record in page["records"]:
            if record["recordId"] in ids or record["nctId"] in ncts:
                raise ValueError("Duplicate canonical record")
            if len(record["fields"]) != 38 or len(record["assessments"]) != 20:
                raise ValueError("Incomplete assessment mapping")
            ids.add(record["recordId"]); ncts.add(record["nctId"]); records.append(record)
        offset += len(page["records"])
        if page.get("nextOffset") not in (None, offset):
            raise ValueError("Invalid next offset")
    if total is None or len(records) != total or pages[-1].get("nextOffset") is not None:
        raise ValueError("Incomplete canonical dataset")
    return version, records


def owned_change(cell, value, record_id):
    """A human edit or human note prevents unattended overwrites."""
    before = cell.get("userEnteredValue", {})
    note = cell.get("note", "")
    after = {"numberValue": value} if isinstance(value, (int, float)) and not isinstance(value, bool) else {"stringValue": str(value)}
    if "formulaValue" in before:
        return None
    if before == after:
        return None
    if note and not note.startswith(PREFIX + record_id + ":"):
        return None
    if before and before != {"stringValue": ""}:
        if note != PREFIX + record_id + ":" + digest(before):
            return None
    rule = cell.get("dataValidation", {}).get("condition", {})
    if rule.get("type") == "ONE_OF_LIST" and str(value) not in [v.get("userEnteredValue") for v in rule.get("values", [])]:
        return None
    return {"userEnteredValue": after, "note": PREFIX + record_id + ":" + digest(after)}


def request(session, method, url, **kwargs):
    # GETs and absolute cell upserts are idempotent; no retryable append operation.
    for attempt in range(4):
        response = session.request(method, url, timeout=60, **kwargs)
        if response.status_code not in (429, 500, 502, 503, 504) or attempt == 3:
            if response.status_code in (401, 403):
                raise RuntimeError("GOOGLE_EDITOR_ACCESS_REQUIRED" if "googleapis.com" in url else "DASHBOARD_AUTHORIZATION_FAILED")
            response.raise_for_status()
            return response.json()
        time.sleep(min(2 ** attempt, 8))


def read_dataset(session):
    password = os.environ.get("DASHBOARD_PASSWORD")
    if not password:
        raise RuntimeError("MISSING_DASHBOARD_PASSWORD")
    response = session.post(SITE + "/api/auth", json={"password": password}, timeout=60)
    if response.status_code != 200:
        raise RuntimeError("DASHBOARD_AUTHORIZATION_FAILED")
    pages, offset = [], 0
    while True:
        page = request(session, "GET", SITE + "/api/pipeline-research/export", params={"offset": offset, "limit": 200})
        pages.append(page)
        if page.get("nextOffset") is None:
            break
        if page["nextOffset"] <= offset:
            raise ValueError("Nonadvancing pagination")
        offset = page["nextOffset"]
    return validate_pages(pages), pages[0]


def master_values(record):
    values = []
    for field in record["fields"]:
        # Preserve existing E/F date formulas and distinguish unknown from zero.
        values.append("Not assessed" if field["state"] == "MISSING" else field["value"])
    timeline = record.get("timeline") or {}
    release, action = timeline.get("phase3DataRelease"), timeline.get("pdufaTarget")
    values += [(date.fromisoformat(release["date"])-date(1899,12,30)).days if release else "", (date.fromisoformat(action["date"])-date(1899,12,30)).days if action else "",
               (release or {}).get("sourceUrl", ""), (action or {}).get("sourceUrl", ""),
               "Yes" if release else "No", "Yes" if action else "No", record["workflow"]]
    return values


def plan_cells(sheet_id, grid, records, values_for, key_column=0, start=4):
    """Match by stable NCT; never move/delete existing rows or overwrite notes."""
    existing = {}
    for index, row in enumerate(grid[start:], start):
        cells = row.get("values", [])
        value = cells[key_column].get("userEnteredValue", {}).get("stringValue", "") if len(cells) > key_column else ""
        if value:
            if value in existing:
                raise ValueError("Duplicate spreadsheet record identity")
            existing[value] = index
    used = set(existing.values())
    for index,row in enumerate(grid[start:], start):
        if any(c.get("note") or any(k != "formulaValue" and v not in ("", None) for k,v in c.get("userEnteredValue", {}).items()) for c in row.get("values", [])):
            used.add(index)
    requests, writes = [], []
    next_row = start
    for record in records:
        index = existing.get(record["nctId"])
        if index is None:
            while next_row in used:
                next_row += 1
            index = next_row; used.add(index)
        current = grid[index].get("values", []) if index < len(grid) else []
        for column, value in enumerate(values_for(record)):
            if value is None or value == "":
                continue
            cell = current[column] if column < len(current) else {}
            change = owned_change(cell, value, record["recordId"])
            if change is None:
                continue
            requests.append({"updateCells": {"start": {"sheetId": sheet_id, "rowIndex": index, "columnIndex": column},
                "rows": [{"values": [change]}], "fields": "userEnteredValue,note"}})
            writes.append((index, column, change["userEnteredValue"]))
    # Coalesce adjacent owned cells; a skipped manual cell always breaks a run.
    merged=[]
    for item in requests:
        change=item["updateCells"];start=change["start"]
        if merged:
            last=merged[-1]["updateCells"]
            if last["start"]["rowIndex"]==start["rowIndex"] and last["start"]["columnIndex"]+len(last["rows"][0]["values"])==start["columnIndex"]:
                last["rows"][0]["values"].extend(change["rows"][0]["values"]);continue
        merged.append(item)
    return merged, writes


def register_rows(records):
    """Only sourced observations; never generate an evidence row for a blank."""
    evidence, assessments, competitors = [], [], []
    for record in records:
        for field in record["fields"]:
            if field["state"] not in ("VERIFIED", "MODELED") or not field.get("sourceUrl"):
                continue
            evidence.append([record["nctId"], record["ticker"], record.get("drug") or "", record.get("indication") or "", field["id"], field["label"], field["value"], "", "", field["state"], field["why"], field.get("method") or "", field["sourceUrl"], field.get("sourceDate") or "", field.get("confidence") or "UNASSESSED", "SOURCE OBSERVATION; independent review required", ""])
        for assessment in record["assessments"]:
            for field in assessment["inputs"]:
                if field["state"] not in ("VERIFIED", "MODELED") or not field.get("sourceUrl"):
                    continue
                eid = digest([record["recordId"], field["id"], field["sourceUrl"]])
                assessments.append([eid, record["nctId"], record["ticker"], record.get("indication") or "", assessment["rank"], assessment["title"], field["value"], "Evidence recorded; not adjudicated", "", "", "", "", field["state"], field["sourceUrl"], field.get("sourceDate") or "", "PRIMARY SOURCE OBSERVATION", field.get("method") or "", field.get("confidence") or "UNASSESSED", field["why"]])
        for c in record["competitors"]:
            competitors.append([c["id"], record["nctId"], record["ticker"], record.get("indication") or "", c["kind"], c["therapy"], c["manufacturer"], c["regulatorOrTrialId"], c["approvalOrPhase"], c["lineOfTherapy"], c["patientPopulation"], c["comparisonBasis"], c["finding"], c["effectSize"], c["safety"], c["convenience"], c["firstYearPrice"], c["payerAccess"], "", "", c["sourceUrl"], c["sourceDate"], "VERIFIED", c["confidence"], c["reason"], "Review exact comparison and denominators"])
    return evidence, assessments, competitors


def plan_register(sheet_id, grid, values, key_columns):
    """Reuse the preserving cell planner with composite, one-to-many keys."""
    def key(row):
        return json.dumps([str(row[i]) if i < len(row) else "" for i in key_columns], separators=(",", ":"))
    adapted = []
    for row in grid:
        cells = row.get("values", [])
        plain = [c.get("userEnteredValue", {}).get("stringValue", c.get("userEnteredValue", {}).get("numberValue", "")) for c in cells]
        adapted.append({"values": [{"userEnteredValue": {"stringValue": key(plain)}}] + cells} if any(plain) and all(i < len(plain) and str(plain[i]).strip() for i in key_columns) else {"values": [{}] + cells})
    records = [{"nctId": key(row), "recordId": digest(key(row)), "values": row} for row in values]
    changes, writes = plan_cells(sheet_id, adapted, records, lambda r: [r["nctId"], *r["values"]])
    # The synthetic key column is local only and is never written to the Sheet.
    cleaned = []
    for item in changes:
        c = item["updateCells"]; col = c["start"]["columnIndex"]
        vals = c["rows"][0]["values"]
        if col == 0:
            vals = vals[1:]; col = 1
        if vals:
            cleaned.append({"updateCells": {**c, "start": {**c["start"], "columnIndex": col - 1}, "rows": [{"values": vals}]}})
    return cleaned, [(row, col - 1, val) for row, col, val in writes if col > 0]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--dry-run", action="store_true"); args = parser.parse_args()
    import requests
    dataset_session = requests.Session()
    (version, records), first = read_dataset(dataset_session)
    info = os.environ.get("GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON")
    if not info:
        raise RuntimeError("MISSING_GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON")
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    credentials = service_account.Credentials.from_service_account_info(json.loads(info), scopes=["https://www.googleapis.com/auth/spreadsheets"])
    session = AuthorizedSession(credentials)
    base = "https://sheets.googleapis.com/v4/spreadsheets/" + SHEET_ID
    metadata = request(session, "GET", base, params={"fields": "sheets(properties,charts(chartId,spec(title)))"})
    properties = {s["properties"]["title"]: s["properties"] for s in metadata["sheets"]}
    if not all(name in properties for name in SHEETS):
        raise ValueError("Required existing spreadsheet tabs unavailable")
    # First release syncs preserved master fields and retained ranked formulas.
    # Source/competitor registers receive only actual verified findings; empty
    # registers are never padded with fabricated evidence or fake competitors.
    tab = "07 Competitive Master"; prop = properties[tab]
    needed = max(prop["gridProperties"]["rowCount"], len(records) + 4)
    def read_grid(title, end, columns):
        data = request(session, "GET", base, params={"ranges": "'"+title+"'!A1:"+columns+str(end), "includeGridData": "true",
            "fields": "sheets(data(rowData(values(userEnteredValue,note,dataValidation))))"})
        return data["sheets"][0].get("data", [{}])[0].get("rowData", [])
    grid = read_grid(tab, prop["gridProperties"]["rowCount"], "AS")
    changes, writes = plan_cells(prop["sheetId"], grid, records, master_values)
    required_rows=max([needed,*[r+1 for r,_,_ in writes]])
    if not args.dry_run:
        if required_rows>prop["gridProperties"]["rowCount"]:
            request(session,"POST",base+":batchUpdate",json={"requests":[{"appendDimension":{"sheetId":prop["sheetId"],"dimension":"ROWS","length":required_rows-prop["gridProperties"]["rowCount"]}}]})
        for start in range(0, len(changes), 400):
            request(session, "POST", base + ":batchUpdate", json={"requests": changes[start:start+400]})
        after = read_grid(tab, required_rows, "AS")
        for row, col, value in writes:
            if after[row]["values"][col].get("userEnteredValue") != value:
                raise RuntimeError("SHEET_READBACK_RECONCILIATION_FAILED")
    source_rows, assessment_rows, competitor_rows=register_rows(records)
    register_stats={}
    for name, values, keycols, columns in (
      ("13 Exact Trial Evidence",source_rows,(0,4,12),"R"),
      ("17 Assessment Evidence",assessment_rows,(0,),"T"),
      ("16 Competitor Inventory",competitor_rows,(0,),"AA")):
        rp=properties[name]; rg=read_grid(name,rp["gridProperties"]["rowCount"],columns)
        updates,expected=plan_register(rp["sheetId"],rg,values,keycols)
        extent=max([rp["gridProperties"]["rowCount"],*[r+1 for r,_,_ in expected]])
        if not args.dry_run:
            if extent>rp["gridProperties"]["rowCount"]:
                request(session,"POST",base+":batchUpdate",json={"requests":[{"appendDimension":{"sheetId":rp["sheetId"],"dimension":"ROWS","length":extent-rp["gridProperties"]["rowCount"]}}]})
            for start in range(0,len(updates),400):request(session,"POST",base+":batchUpdate",json={"requests":updates[start:start+400]})
            if expected:
                verified=read_grid(name,extent,columns)
                for r,c,v in expected:
                    if verified[r]["values"][c].get("userEnteredValue")!=v:raise RuntimeError("SHEET_READBACK_RECONCILIATION_FAILED")
        register_stats[name]={"source_records":len(values),"managed_updates":len(expected)}
    # Preserve all existing ranked formulas while extending their exact master ranges.
    ranked=properties["15 Ranked 20 Assessments"]
    ranked_grid=read_grid("15 Ranked 20 Assessments",5,"AC")
    end=max(required_rows,304)
    formula_updates=[]
    for col,cell in enumerate(ranked_grid[4].get("values",[])):
        formula=cell.get("userEnteredValue",{}).get("formulaValue","")
        if formula.startswith(("=MAP(\'07 Competitive Master\'!", "=ARRAYFORMULA(IF(\'07 Competitive Master\'!")) and not cell.get("note"):
            expanded=formula.replace("$304","$"+str(end)).replace("A304","A"+str(end)).replace("B304","B"+str(end)).replace("C304","C"+str(end)).replace("D304","D"+str(end)).replace("E304","E"+str(end)).replace("F304","F"+str(end))
            if expanded!=formula:formula_updates.append({"updateCells":{"start":{"sheetId":ranked["sheetId"],"rowIndex":4,"columnIndex":col},"rows":[{"values":[{"userEnteredValue":{"formulaValue":expanded}}]}],"fields":"userEnteredValue"}})
    if not args.dry_run:
        if end>ranked["gridProperties"]["rowCount"]:
            request(session,"POST",base+":batchUpdate",json={"requests":[{"appendDimension":{"sheetId":ranked["sheetId"],"dimension":"ROWS","length":end-ranked["gridProperties"]["rowCount"]}}]})
        if formula_updates:request(session,"POST",base+":batchUpdate",json={"requests":formula_updates})
        ranked_after=read_grid("15 Ranked 20 Assessments",5,"AC")
        for change in formula_updates:
            col=change["updateCells"]["start"]["columnIndex"]
            if ranked_after[4]["values"][col].get("userEnteredValue")!=change["updateCells"]["rows"][0]["values"][0]["userEnteredValue"]:raise RuntimeError("SHEET_READBACK_RECONCILIATION_FAILED")
    # Charts and saved views keep their formulas, with the complete master extent.
    chart_updates=[]
    for name in ("14 Charts Dashboard","11 Compare Analytics","10 Research Board","08 Advanced Table","09 Trial Dossier"):
        prop_view=properties.get(name)
        if not prop_view:continue
        vgrid=read_grid(name,prop_view["gridProperties"]["rowCount"],"J" if name=="09 Trial Dossier" else "L")
        for r,row in enumerate(vgrid):
            for c,cell in enumerate(row.get("values",[])):
                formula=cell.get("userEnteredValue",{}).get("formulaValue","")
                if "'07 Competitive Master'!" not in formula or cell.get("note"):continue
                changed=formula.replace("$304","$"+str(end))
                if changed!=formula:chart_updates.append({"updateCells":{"start":{"sheetId":prop_view["sheetId"],"rowIndex":r,"columnIndex":c},"rows":[{"values":[{"userEnteredValue":{"formulaValue":changed}}]}],"fields":"userEnteredValue"}})
    if chart_updates and not args.dry_run:
        request(session,"POST",base+":batchUpdate",json={"requests":chart_updates})
        for name in ("14 Charts Dashboard","11 Compare Analytics","10 Research Board","08 Advanced Table","09 Trial Dossier"):
            prop_view=properties.get(name)
            if not prop_view:continue
            relevant=[u["updateCells"] for u in chart_updates if u["updateCells"]["start"]["sheetId"]==prop_view["sheetId"]]
            if not relevant:continue
            verified=read_grid(name,prop_view["gridProperties"]["rowCount"],"J" if name=="09 Trial Dossier" else "L")
            for item in relevant:
                r,c=item["start"]["rowIndex"],item["start"]["columnIndex"]
                if verified[r]["values"][c].get("userEnteredValue")!=item["rows"][0]["values"][0]["userEnteredValue"]:raise RuntimeError("SHEET_READBACK_RECONCILIATION_FAILED")
    mapping=properties["18 Mapping and Sync"]
    mapping_grid=read_grid("18 Mapping and Sync",24,"K")
    mapping_updates=[]
    state="SYNCED "+version+" | "+datetime.now(timezone.utc).isoformat()+" | independently qualified programs not established"
    for r in range(4,24):
        cells=mapping_grid[r].get("values",[]) if r<len(mapping_grid) else []
        cell=cells[10] if len(cells)>10 else {}
        bootstrap=cell.get("userEnteredValue",{}).get("stringValue")=="NOT INSTALLED · website / Google Sheet live sync" and not cell.get("note")
        change=owned_change({} if bootstrap else cell,state,"sync-status")
        if change:mapping_updates.append({"updateCells":{"start":{"sheetId":mapping["sheetId"],"rowIndex":r,"columnIndex":10},"rows":[{"values":[change]}],"fields":"userEnteredValue,note"}})
    if mapping_updates and not args.dry_run:
        request(session,"POST",base+":batchUpdate",json={"requests":mapping_updates})
        verified=read_grid("18 Mapping and Sync",24,"K")
        for item in mapping_updates:
            r=item["updateCells"]["start"]["rowIndex"]
            if verified[r]["values"][10].get("userEnteredValue")!={"stringValue":state}:raise RuntimeError("SHEET_READBACK_RECONCILIATION_FAILED")
    report = {"status": "DRY_RUN" if args.dry_run else "DATA_SYNC_VERIFIED", "dataset_version": version,
        "records": len(records), "cell_updates": len(writes), "original_fields": 38, "assessments_defined": 20,
        "verified_eligible_programs": first["verifiedEligiblePrograms"], "manual_cells_preserved": True,
        "register_sync": register_stats, "ranked_formula_expansion": "DRY_RUN" if args.dry_run else "VERIFIED", "chart_formula_ranges_updated":len(chart_updates), "charts_runtime": "VISUAL_VERIFICATION_PENDING",
        "verified_at": datetime.now(timezone.utc).isoformat()}
    print("PDUFA_PIPELINE_RESEARCH_SYNC " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Finite safe diagnostic categories only; requests may contain credentials.
        category = str(error) if str(error) in {"GOOGLE_EDITOR_ACCESS_REQUIRED", "DASHBOARD_AUTHORIZATION_FAILED", "MISSING_DASHBOARD_PASSWORD", "MISSING_GOOGLE_SHEETS_SERVICE_ACCOUNT_JSON", "SHEET_READBACK_RECONCILIATION_FAILED"} else type(error).__name__
        print("PDUFA_PIPELINE_RESEARCH_SYNC_FAILED " + category)
        raise SystemExit(1)
