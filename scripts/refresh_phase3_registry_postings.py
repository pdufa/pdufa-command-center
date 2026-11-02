#!/usr/bin/env python3
"""Refresh the two TOOLS Phase 3 registry-results spreadsheets from official NCT records.

Source population is the last published $300M-$10B all-years Phase 3 census;
the binary classification is ONLY ClinicalTrials.gov results FIRST POSTED.
Never conflate first-posted results with issuer topline announcements or FDA
success. Every census NCT must be returned exactly once before publishing.
"""
import argparse
import csv
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
OUTPUT = ROOT / "new-platform/frontend/public/phase3-registry-postings-current.json"
SOURCE = "data/phase3_all_years_300m_10b_trials.csv"
MEASURE = "CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT"
API = "https://clinicaltrials.gov/api/v2/studies"
NCT = re.compile(r"^NCT\d{8}$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def census_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or reader.fieldnames != [
            "nct_id", "ticker", "company", "status", "source_url"
        ]:
            raise ValueError("Unexpected Phase 3 census format")
        rows = list(reader)
    if not 700 <= len(rows) <= 20000:
        raise ValueError("Census incomplete or implausibly large")
    seen = set()
    for row in rows:
        nct = row["nct_id"]
        if (not NCT.fullmatch(nct) or nct in seen
            or not re.fullmatch(r"[A-Z0-9.-]{1,15}", row["ticker"])
            or not row["company"].strip()
            or row["source_url"] != "https://clinicaltrials.gov/study/" + nct
            or not row["status"] or len(row["status"]) > 50):
            raise ValueError("Invalid census NCT, sponsor or source identity")
        seen.add(nct)
    return rows


def request_batch(ncts, page_token=""):
    params = {"filter.ids": ",".join(ncts), "pageSize": len(ncts), "format": "json"}
    if page_token:
        params["pageToken"] = page_token
    url = API + "?" + urlencode(params)
    for attempt in range(4):
        try:
            req = Request(url, headers={
                "User-Agent": "PDUFA-Research/1.0 (source audit)",
                "Accept": "application/json",
            })
            with urlopen(req, timeout=45) as response:
                if response.status != 200:
                    raise RuntimeError("Registry HTTP " + str(response.status))
                data = json.load(response)
            return data
        except (OSError, ValueError, RuntimeError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("Registry request failed")


def posted_date(study, nct, cutoff):
    protocol = study.get("protocolSection")
    if not isinstance(protocol, dict):
        raise ValueError("Missing registry protocol for " + nct)
    status = protocol.get("statusModule")
    if not isinstance(status, dict):
        raise ValueError("Missing registry status for " + nct)
    posted_struct = status.get("resultsFirstPostDateStruct")
    if posted_struct is not None and not isinstance(posted_struct, dict):
        raise ValueError("Invalid registry results date for " + nct)
    posted = posted_struct.get("date", "") if posted_struct else ""
    if posted:
        if (not isinstance(posted, str) or not DAY.fullmatch(posted)
            or datetime.strptime(posted, "%Y-%m-%d").strftime("%Y-%m-%d") != posted
            or posted > cutoff):
            raise ValueError("Impossible results posted date for " + nct)
    if study.get("resultsSection") and not posted:
        raise ValueError("Results section lacks recorded first-posted date for " + nct)
    return posted


def build_snapshot(rows, requester=request_batch, now=None, batch_size=25):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("UTC time required")
    if not 1 <= batch_size <= 100:
        raise ValueError("Invalid registry batch size")
    cutoff = now.astimezone(timezone.utc).strftime("%Y-%m-%d")
    recorded = {}
    for first in range(0, len(rows), batch_size):
        wanted = [r["nct_id"] for r in rows[first:first + batch_size]]
        expected = set(wanted)
        seen_tokens = set()
        page_token = ""
        # The registry can paginate even an explicit NCT ID filter. Collect
        # every page and reject omissions, repeats, foreign IDs and loops.
        for page_index in range(max(2, len(wanted) + 1)):
            payload = (requester(wanted, page_token) if page_token
                       else requester(wanted))
            if not isinstance(payload, dict) or not isinstance(payload.get("studies"), list):
                raise ValueError("Malformed ClinicalTrials.gov results page")
            for study in payload["studies"]:
                if not isinstance(study, dict):
                    raise ValueError("Malformed registry record")
                protocol = study.get("protocolSection", {})
                ident = protocol.get("identificationModule", {}) if isinstance(protocol, dict) else {}
                nct = ident.get("nctId") if isinstance(ident, dict) else None
                if not isinstance(nct, str) or nct not in expected or nct in recorded:
                    raise ValueError("Registry returned wrong or duplicate NCT")
                recorded[nct] = posted_date(study, nct, cutoff)
            token = payload.get("nextPageToken")
            # The API occasionally includes nextPageToken *after* returning
            # every specifically requested NCT. A complete exact-ID result
            # is already authoritative: do not traverse unrelated extra pages.
            if len(expected.intersection(recorded)) == len(expected):
                break
            if token is None or token == "":
                raise ValueError("Incomplete registry batch: missing exact NCTs")
            if not isinstance(token, str) or len(token) > 4000 or token in seen_tokens:
                raise ValueError("Invalid or repeated registry pagination token")
            seen_tokens.add(token)
            page_token = token
        else:
            raise ValueError("Registry pagination budget exhausted")
    if len(recorded) != len(rows):
        raise ValueError("Registry census not completely reconciled")
    entries = [{
        "nctId": row["nct_id"], "ticker": row["ticker"], "company": row["company"],
        "registryStatus": row["status"],
        "resultsCount": int(bool(recorded[row["nct_id"]])),
        "resultsFirstPostedDate": recorded[row["nct_id"]],
    } for row in rows]
    post = sum(bool(r["resultsFirstPostedDate"]) for r in entries)
    return {
        "schemaVersion": 2,
        "snapshotDate": cutoff,
        "sourceAsOf": now.astimezone(timezone.utc).isoformat(),
        "sourceFile": SOURCE,
        "sourceKind": "OFFICIAL_CLINICALTRIALS_GOV_API_EXACT_NCT",
        "measure": MEASURE,
        "cohort": "DATED_300M_10B_PHASE3_CENSUS_EXACT_NCTS",
        "total": len(entries),
        "noResultsPosted": len(entries) - post,
        "resultsPosted": post,
        "scopeNote": "Official registry results-first-posted date for each exact saved NCT; not evidence of company press release, success, or current market cap eligibility. Issuer-cap membership comes from a separate, dated census.",
        "records": entries,
    }


def atomic_publish(destination, result):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(".new")
    try:
        with temp.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(temp, destination)
    finally:
        if temp.exists():
            temp.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--census", type=Path, default=CENSUS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--batch-size", type=int, default=25)
    args = parser.parse_args()
    rows = census_rows(args.census)
    result = build_snapshot(rows, batch_size=args.batch_size)
    atomic_publish(args.output, result)
    print(json.dumps({
        "sourceAsOf": result["sourceAsOf"], "total": result["total"],
        "noResultsPosted": result["noResultsPosted"],
        "resultsPosted": result["resultsPosted"],
        "sourceKind": result["sourceKind"],
    }, indent=2))


if __name__ == "__main__":
    main()
