#!/usr/bin/env python3
"""Fetch current ClinicalTrials.gov v2 record with explicit provenance.

Usage: python scripts/fetch_focus_registry_evidence.py NCT05507203 --out-dir /tmp/focus-registry
Does not modify roster, scores, adjudication status, or prediction history.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

NCT_RE = re.compile(r"^NCT[0-9]{8}$")
BASE = "https://clinicaltrials.gov/api/v2/studies/"


def retrieve(nct: str, timeout: int = 20) -> tuple[dict, dict]:
    if not NCT_RE.fullmatch(nct):
        raise ValueError("Expected NCT followed by exactly eight digits")
    url = BASE + nct
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "PDUFA-Research-SourceAudit/1.0"})
    with urlopen(req, timeout=timeout) as response:
        raw = response.read(12_000_001)
        if len(raw) > 12_000_000:
            raise ValueError("Registry response exceeds size limit")
    record = json.loads(raw)
    if record.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nct:
        raise ValueError("Registry record NCT does not match requested identifier")
    metadata = {
        "nct": nct,
        "source_url": url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "has_results_section": bool(record.get("resultsSection")),
        "status_verified_date": record.get("protocolSection", {}).get("statusModule", {}).get("statusVerifiedDate"),
        "source_type": "PRIMARY_REGISTRY",
        "scientific_adjudication": "NOT_ADJUDICATED",
        "independent_review": "NOT_COMPLETED",
        "fda_probability": None,
    }
    return record, metadata


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("nct")
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    try:
        record, meta = retrieve(args.nct)
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"nct": args.nct, "status": "DIRECT_REGISTRY_FETCH_UNAVAILABLE", "reason": str(exc)}), file=sys.stderr)
        return 2
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / (args.nct + ".json")).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / (args.nct + ".provenance.json")).write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
