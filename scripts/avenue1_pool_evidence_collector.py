#!/usr/bin/env python3
"""Read-only Avenue #1 clinical evidence collector for the entire POOL.

Requires PDUFA_API_BASE_URL and PDUFA_INTERNAL_API_KEY. Does not alter POOL,
FOCUS, prediction scores, or production databases. Output is local JSONL.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

def fetch_json(url, headers=None, attempts=3):
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {
                "User-Agent": "PDUFA-Avenue1-Evidence-Collector/1.0"
            }), timeout=35) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError):
            if attempt + 1 == attempts:
                raise
            time.sleep(2 ** attempt)

def pool_records():
    base = os.environ.get("PDUFA_API_BASE_URL", "").rstrip("/")
    key = os.environ.get("PDUFA_INTERNAL_API_KEY", "")
    if not base.startswith("https://") or not key:
        raise RuntimeError("Authenticated POOL backend variables missing")
    data = fetch_json(base + "/api/workspace?require_fresh=true", {
        "x-pdufa-internal-key": key, "User-Agent": "PDUFA-Avenue1-Evidence-Collector/1.0"
    })
    # Preserve the complete original source structure for schema inspection.
    return data

def study_evidence(nct):
    study = fetch_json("https://clinicaltrials.gov/api/v2/studies/" + nct)
    protocol = study.get("protocolSection") or {}
    results = study.get("resultsSection") or {}
    return {
        "nct": nct,
        "phase": (protocol.get("designModule") or {}).get("phases", []),
        "status": (protocol.get("statusModule") or {}).get("overallStatus"),
        "results_posted": bool(results),
        "primary_outcomes": (results.get("outcomeMeasuresModule") or {}).get("outcomeMeasures", []),
        "protocol_outcomes": (protocol.get("outcomesModule") or {}).get("primaryOutcomes", []),
        "adverse_events": results.get("adverseEventsModule"),
        "source": "https://clinicaltrials.gov/study/" + nct,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "superiority_to_active_soc": "NOT_ESTABLISHED_WITHOUT_COMPARATOR_REVIEW",
        "ten_category_scoring": "PENDING_EVIDENCE_REVIEW"
    }

def find_ncts(value):
    """Find all exact NCTs recursively; no FOCUS or market-cap filtering."""
    if isinstance(value, dict):
        for item in value.values():
            yield from find_ncts(item)
    elif isinstance(value, list):
        for item in value:
            yield from find_ncts(item)
    elif isinstance(value, str):
        import re
        yield from re.findall(r"\bNCT\d{8}\b", value.upper())

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="artifacts/avenue1")
    p.add_argument("--limit", type=int, default=0, help="Optional test limit; 0 means all")
    args = p.parse_args()
    raw = pool_records()
    ids = sorted(set(find_ncts(raw)))
    if not ids:
        raise RuntimeError("No exact NCT identifiers in authenticated POOL source; schema review required")
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "pool-source-inventory.json").write_text(json.dumps({
        "nct_count": len(ids), "ncts": ids, "source": "authenticated backend /api/workspace",
        "as_of": datetime.now(timezone.utc).isoformat()
    }, indent=2))
    errors = []
    done = 0
    with (out / "clinical-evidence.jsonl").open("w") as f:
        for nct in ids[:args.limit or None]:
            try:
                f.write(json.dumps(study_evidence(nct)) + "\n")
                done += 1
            except Exception as exc:
                errors.append({"nct": nct, "error_type": type(exc).__name__})
            time.sleep(0.15)
    (out / "collection-status.json").write_text(json.dumps({
        "pool_nct_count": len(ids), "attempted": min(len(ids), args.limit) if args.limit else len(ids),
        "collected": done, "errors": errors,
        "note": "Results posting is not proof of efficacy or superiority; no scores assigned."
    }, indent=2))
    print(f"POOL NCTs={len(ids)}; collected={done}; errors={len(errors)}")
    return 0 if not errors else 2

if __name__ == "__main__":
    sys.exit(main())
