#!/usr/bin/env python3
"""Read-only complete original Phase 3 registry census verification.

Never qualifies candidates, changes production data, or predicts FDA decisions.
"""
from __future__ import annotations
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import time
import sys
from check_phase3_original_registry_pilot import SOURCE_CSV, dated_census_sample, fetch_public_original

EXPECTED = 741

def fetch_with_diagnostics(row):
    for attempt in range(3):
        try:
            return fetch_public_original(row)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep((attempt + 1) * 2)
                continue
            return {"nct_id": row["nct_id"], "error": "HTTPError", "http_status": exc.code}
        except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
            return {"nct_id": row["nct_id"], "error": type(exc).__name__}
    raise AssertionError("Unreachable retry state")

def run(output: Path) -> int:
    source = SOURCE_CSV.read_text(encoding="utf-8-sig")
    dated_census_sample(source)  # validates complete inventory, identities and ticker count
    rows = list(csv.DictReader(source.splitlines()))
    if len(rows) != EXPECTED or len({r["nct_id"] for r in rows}) != EXPECTED:
        raise ValueError("Original census changed or contains duplicate NCT IDs")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch_with_diagnostics, rows))
    verified = []
    errors = []
    mismatches = []
    non_phase3 = []
    for row, result in zip(rows, results):
        nct = row["nct_id"]
        if result.get("nct_id") != nct:
            raise ValueError("Source association mismatch")
        if "error" in result:
            errors.append({"nct_id": nct, "error_type": result["error"], "http_status": result.get("http_status")})
            continue
        if (result.get("qualified_pipeline") is not None
            or result.get("fda_approval_probability") is not None
            or result.get("verified_us_fda_pdufa") is not False
            or result.get("verified_current_commercial_development_rights") is not False
            or result.get("census_ticker") != row["ticker"]):
            raise ValueError("Unverified source attempted candidate promotion")
        verified.append(result)
        if not result["status_matches_dated_census"]:
            mismatches.append(nct)
        if not result["phase3_in_current_registry"]:
            non_phase3.append(nct)
    report = {
        "report_type": "MAIN_ORIGINAL_PHASE3_FULL_CENSUS_RESEARCH_ONLY",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "census_total": EXPECTED,
        "source_identity_verified": len(verified),
        "source_errors": errors,
        "status_mismatch_nct_ids": mismatches,
        "not_currently_phase3_nct_ids": non_phase3,
        "original_source_records": verified,
        "qualified_pipeline_total": None,
        "fda_approval_probabilities": None,
        "limitations": "Registry source and identity checks only. No FDA PDUFA, rights, active development or market-cap qualification."
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(f"Original registry source identity: {len(verified)}/{EXPECTED}; errors: {len(errors)}; status changes: {len(mismatches)}; non-Phase-3: {len(non_phase3)}")
    return 0 if not errors else 1

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: check_phase3_full_original_sources.py <report-json-path>")
    sys.exit(run(Path(sys.argv[1])))
