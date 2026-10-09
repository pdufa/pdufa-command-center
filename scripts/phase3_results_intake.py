#!/usr/bin/env python3
"""Append-only Phase 3 posted-results intake from ClinicalTrials.gov.

Registered trial results are distinct from corporate topline press releases.
This source cannot establish complete coverage of all company announcements.
"""
import argparse
import csv
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
API = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = ["ticker", "company", "drug", "indication", "phase3_results_posted_at",
          "phase3_result", "phase3_results_source", "phase3_status",
          "verification_status", "source_list_note", "nct_id", "source_type",
          "first_seen_at", "last_checked_at"]


def normalized(value):
    value = re.sub(r"[^a-z0-9 ]", " ", str(value or "").lower())
    return " ".join(x for x in value.split() if x not in
                    {"inc", "incorporated", "corporation", "corp", "plc", "ltd", "limited", "llc"})


def rows(path):
    if not path.exists() or not path.stat().st_size:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write(path, records):
    temp = path.with_suffix(".tmp")
    with temp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    os.replace(temp, path)


def fetch(params):
    url = API + "?" + urlencode(params)
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": "PDUFA-Research/1.0 (public research)"}),
                         timeout=55) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def scan(mode, max_pages, data_dir=DATA):
    data_dir = Path(data_dir)
    registry = rows(data_dir / "company_registry.csv")
    sponsors = {}
    for company in registry:
        key = normalized(company.get("company"))
        if key:
            sponsors.setdefault(key, []).append(company)
    path = data_dir / "phase3_announcements.csv"
    existing = rows(path)
    by_nct = {r.get("nct_id"): r for r in existing if r.get("nct_id")}
    old_without_nct = [r for r in existing if not r.get("nct_id")]
    now = datetime.now(timezone.utc).isoformat()
    params = {"query.term": "AREA[Phase]PHASE3 AND AREA[StudyType]INTERVENTIONAL",
              "pageSize": 1000, "format": "json", "sort": "LastUpdatePostDate:desc"}
    state = {"mode": mode, "started_at": now, "registry_companies": len(registry),
             "pages": 0, "studies_checked": 0, "matched_posted_results": 0,
             "new_records": 0, "complete": False, "errors": []}
    if mode == "daily":
        # Incremental scan: recently updated studies, plus retained historical ledger.
        params["query.term"] += " AND AREA[LastUpdatePostDate]RANGE[" + (
            (datetime.now(timezone.utc).date() - timedelta(days=90)).isoformat()) + ",MAX]"
    try:
        for page in range(max_pages):
            payload = fetch(params)
            studies = payload.get("studies")
            if not isinstance(studies, list):
                raise ValueError("ClinicalTrials.gov returned no studies list")
            for study in studies:
                state["studies_checked"] += 1
                p = study.get("protocolSection") or {}
                status = p.get("statusModule") or {}
                posted = (status.get("resultsFirstPostDateStruct") or {}).get("date", "")
                nct = (p.get("identificationModule") or {}).get("nctId", "")
                if not re.fullmatch(r"NCT\d{8}", nct) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", posted):
                    continue
                sponsor = (p.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
                matches = sponsors.get(normalized(sponsor.get("name")), [])
                if len(matches) != 1:
                    continue
                phases = (p.get("designModule") or {}).get("phases") or []
                if "PHASE3" not in phases:
                    continue
                interventions = [i.get("name", "") for i in
                    ((p.get("armsInterventionsModule") or {}).get("interventions") or [])
                    if i.get("type") in ("DRUG", "BIOLOGICAL") and i.get("name")]
                conditions = (p.get("conditionsModule") or {}).get("conditions") or []
                if not interventions or not conditions:
                    continue
                # Multiple interventions remain a REVIEW, not a falsely identified drug.
                drug = " | ".join(sorted(set(interventions)))
                indication = " | ".join(sorted(set(conditions)))
                old = by_nct.get(nct, {})
                row = {key: old.get(key, "") for key in FIELDS}
                row.update({"ticker": matches[0].get("ticker", ""), "company": matches[0].get("company", ""),
                    "drug": drug, "indication": indication, "phase3_results_posted_at": posted,
                    "phase3_result": "Results posted to ClinicalTrials.gov; efficacy outcome not adjudicated",
                    "phase3_results_source": "https://clinicaltrials.gov/study/" + nct,
                    "phase3_status": "RESULTS_VERIFIED" if len(set(interventions)) == 1 else "RESULTS_REVIEW",
                    "verification_status": "REGISTERED_RESULTS_POSTED" if len(set(interventions)) == 1 else "DRUG_IDENTITY_REVIEW",
                    "source_list_note": "Registry results-post date, NOT a company topline press-release date",
                    "nct_id": nct, "source_type": "CLINICALTRIALS_RESULTS",
                    "first_seen_at": old.get("first_seen_at") or now, "last_checked_at": now})
                if nct not in by_nct:
                    state["new_records"] += 1
                by_nct[nct] = row
                state["matched_posted_results"] += 1
            state["pages"] += 1
            token = payload.get("nextPageToken")
            if not token:
                state["complete"] = True
                break
            params["pageToken"] = token
            print("page", state["pages"], "studies", state["studies_checked"], flush=True)
    except Exception as exc:
        state["errors"].append(type(exc).__name__ + ": " + str(exc))
    merged = old_without_nct + list(by_nct.values())
    merged.sort(key=lambda r: (r.get("phase3_results_posted_at", ""), r.get("ticker", ""), r.get("nct_id", "")), reverse=True)
    # Existing evidence is never removed when an upstream request fails.
    write(path, merged)
    state.update({"finished_at": datetime.now(timezone.utc).isoformat(),
                  "stored_results": len(merged),
                  "status": ("COMPLETE WITH WARNINGS" if state["complete"] and state["errors"] else "COMPLETE" if state["complete"] else "PARTIAL" if state.get("studies_checked", 0) else "FAILED")})
    (data_dir / "phase3_intake_status.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2))
    if state["errors"]:
        raise RuntimeError("Phase 3 intake incomplete; retained successful records.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["backfill", "daily"], default="daily")
    parser.add_argument("--max-pages", type=int, default=120)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    a = parser.parse_args()
    scan(a.mode, a.max_pages, a.data_dir)
