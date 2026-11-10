#!/usr/bin/env python3
"""Retrieve a ClinicalTrials.gov v2 study record with source provenance.

Usage: python scripts/fetch_focus_registry_record.py NCT05507203
Writes a timestamped JSON provenance envelope to stdout. Does not modify roster,
scores, predictions, or mark scientific categories as verified.
"""
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request

def retrieve(nct):
    if not re.fullmatch(r"NCT[0-9]{8}", nct):
        raise ValueError("Expected exact NCT identifier")
    url = "https://clinicaltrials.gov/api/v2/studies/" + nct
    req = urllib.request.Request(url, headers={
        "User-Agent": "PDUFA-Command-Center-Research/1.0",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        raw = response.read(15_000_001)
        if len(raw) > 15_000_000:
            raise ValueError("Registry response exceeds 15 MB")
    data = json.loads(raw)
    actual = data.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
    if actual != nct:
        raise ValueError(f"Registry identity mismatch: {actual!r}")
    protocol = data.get("protocolSection", {})
    status = protocol.get("statusModule", {})
    return {
        "nct": nct,
        "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_url": url,
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "results_section_present": bool(data.get("resultsSection")),
        "study_first_post_date": status.get("studyFirstPostDateStruct"),
        "status_verified_date": status.get("statusVerifiedDate"),
        "protocol_outcomes_present": bool(protocol.get("outcomesModule")),
        "document_module_present": bool(data.get("documentSection")),
        "verification_status": "SOURCE_RETRIEVED_NOT_INDEPENDENTLY_ADJUDICATED",
        "raw_record": data,
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: fetch_focus_registry_record.py NCT########")
    try:
        print(json.dumps(retrieve(sys.argv[1]), indent=2))
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"nct": sys.argv[1], "verification_status": "DIRECT_REGISTRY_FETCH_UNAVAILABLE", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)
