#!/usr/bin/env python3
"""Bounded, resumable public registry extraction for the FOCUS roster.

Runs unattended; never changes FOCUS, scientific scores, or production.
"""
import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from level4_registry_extraction import extract

def run(roster, output, previous=None, limit=29, fetch=None):
    if fetch is None:
        def fetch(nct):
            req = Request("https://clinicaltrials.gov/api/v2/studies/" + nct,
                          headers={"Accept": "application/json", "User-Agent": "PDUFA-Research-Checkpoint/1.0"})
            with urlopen(req, timeout=20) as response:
                return response.read(2_000_001)
    ids = list(dict.fromkeys(x["nct"] for x in roster["records"]))
    if len(ids) != 29:
        raise ValueError("FOCUS roster count changed: stop for review, do not silently skip trials")
    prior = (previous or {}).get("results", {})
    results = dict(prior)
    for nct in ids[:limit]:
        if not re.fullmatch(r"NCT[0-9]{8}", nct):
            raise ValueError("Invalid NCT identifier")
        try:
            raw = fetch(nct)
            if len(raw) > 2_000_000:
                raise ValueError("Registry response exceeds size limit")
            packet = json.loads(raw)
            results[nct] = {"status": "CAPTURED_UNREVIEWED", "evidence": extract(packet, nct, raw)}
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
            results[nct] = {"status": "RETRY_REQUIRED", "errorType": type(exc).__name__}
        time.sleep(0.1)
    results = {n: results[n] for n in ids if n in results}
    summary = {"schemaVersion": 1, "generatedAt": datetime.now(timezone.utc).isoformat(),
               "rosterAsOf": roster.get("asOf"), "expectedTrials": 29,
               "captured": sum(v["status"] == "CAPTURED_UNREVIEWED" for v in results.values()),
               "retryRequired": sum(v["status"] == "RETRY_REQUIRED" for v in results.values()),
               "scientificallyReviewed": 0, "results": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2) + "\n")
    return summary

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--roster", type=Path, default=Path("new-platform/frontend/data/p3PostDataActive.json"))
    parser.add_argument("--output", type=Path, default=Path("phase4-artifacts/checkpoint.json"))
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--limit", type=int, default=29)
    args = parser.parse_args()
    if not 1 <= args.limit <= 29:
        parser.error("--limit must be 1..29")
    prior = json.loads(args.previous.read_text()) if args.previous and args.previous.exists() else None
    result = run(json.loads(args.roster.read_text()), args.output, prior, args.limit)
    print(json.dumps({k: result[k] for k in ("expectedTrials", "captured", "retryRequired", "scientificallyReviewed")}))

if __name__ == "__main__":
    main()
