#!/usr/bin/env python3
"""Build an auditable, non-predictive ClinicalTrials.gov evidence retrieval manifest.

Reads the 2026 provisional source ledger; fetches *only explicitly linked NCT IDs*.
A current ClinicalTrials.gov record is NOT proof of what was public at a historical
cutoff. All retrieved data are quarantined as CURRENT_SNAPSHOT_UNVERIFIED_AT_CUTOFF.

Usage:
  python scripts/collect_2026_trial_registry_evidence.py
  python scripts/collect_2026_trial_registry_evidence.py --fetch
  python scripts/collect_2026_trial_registry_evidence.py --fetch --limit 10

Default mode makes a queue and does not use the network. --fetch downloads
registry JSON snapshots; it never issues or scores predictions.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/backtest/2026-provisional-source-research.csv"
OUTPUT = ROOT / "data/backtest/2026-trial-registry-evidence-manifest.csv"
CACHE = ROOT / "data/backtest/registry-current-snapshots"
NCT = re.compile(r"^NCT\d{8}$")
FIELDS = ["event_id", "nct_id", "cutoff_date", "source_url", "retrieval_utc",
          "snapshot_sha256", "registry_has_results_now", "registry_last_update_posted",
          "historical_cutoff_eligibility", "review_status", "error"]

def queue():
    result = {}
    with SOURCE.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            for raw in (row.get("trial_ids") or "").split("|"):
                nct = raw.strip()
                if not nct:
                    continue
                if not NCT.fullmatch(nct):
                    raise ValueError(f"Invalid NCT identifier: {nct!r} for {row['event_id']}")
                key = (row["event_id"], nct, row["cutoff_date"])
                result[key] = dict(zip(FIELDS, [
                    row["event_id"], nct, row["cutoff_date"],
                    f"https://clinicaltrials.gov/api/v2/studies/{nct}",
                    "", "", "", "", "NOT_VERIFIED", "AWAITING_REVIEW", ""
                ]))
    return [result[key] for key in sorted(result)]

def fetch_one(row):
    req = urllib.request.Request(row["source_url"],
                                 headers={"User-Agent": "PDUFA-public-research/1.0 (research archive)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            payload = response.read(10_000_000 + 1)
        if len(payload) > 10_000_000:
            raise ValueError("Registry response exceeds 10 MB safety cap")
        study = json.loads(payload)
        actual = study.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
        if actual != row["nct_id"]:
            raise ValueError(f"NCT mismatch: expected {row['nct_id']}, received {actual!r}")
        CACHE.mkdir(parents=True, exist_ok=True)
        name = row["nct_id"] + ".json"
        (CACHE / name).write_bytes(payload)
        row["retrieval_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        row["snapshot_sha256"] = hashlib.sha256(payload).hexdigest()
        row["registry_has_results_now"] = str(bool(study.get("hasResults", False))).lower()
        row["registry_last_update_posted"] = (
            study.get("protocolSection", {}).get("statusModule", {})
            .get("studyFirstPostDateStruct", {}).get("date", "")
        )
        row["historical_cutoff_eligibility"] = "NOT_VERIFIED"
        row["review_status"] = "CURRENT_SNAPSHOT_UNVERIFIED_AT_CUTOFF"
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        row["review_status"] = "FETCH_FAILED"
        row["error"] = str(exc)[:300]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fetch", action="store_true", help="Retrieve current public NCT snapshots")
    p.add_argument("--limit", type=int, default=0, help="Maximum distinct NCT IDs to fetch (0 = all)")
    p.add_argument("--output", type=Path, default=OUTPUT)
    args = p.parse_args()
    if args.limit < 0:
        p.error("--limit cannot be negative")
    rows = queue()
    if args.fetch:
        seen = set()
        for row in rows:
            nct = row["nct_id"]
            if nct in seen:
                continue
            if args.limit and len(seen) >= args.limit:
                break
            seen.add(nct)
            fetch_one(row)
            time.sleep(0.15)
        # Duplicate NCT IDs across events receive the same cached snapshot metadata.
        indexed = {r["nct_id"]: r for r in rows if r["retrieval_utc"] or r["error"]}
        for row in rows:
            source = indexed.get(row["nct_id"])
            if source and source is not row:
                for field in ("retrieval_utc", "snapshot_sha256", "registry_has_results_now",
                              "registry_last_update_posted", "review_status", "error"):
                    row[field] = source[field]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} event-to-trial links to {args.output}")
    print("Historical pre-cutoff eligibility: NOT VERIFIED for every row.")
    print("No scientific assessment or blind prediction has been issued.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
