#!/usr/bin/env python3
"""Rate-aware batched ClinicalTrials.gov research refresh for 741 original NCT IDs.

Uses the official API v2 studies endpoint with explicit NCT filters and a
minimal field projection. Never infers ownership, legal rights, PDUFA, or
Pipeline status from registry metadata. Every fetch or field failure remains
an explicit unresolved study; no historical value substitutes for live data.
"""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from audit_phase3_live_registry_metadata import extract

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
API = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = ("NCTId", "LeadSponsorName", "OverallStatus", "Phase",
          "InterventionName", "Condition", "LastUpdatePostDate", "StudyFirstPostDate")
DEFAULT_BATCH_SIZE = 40
MAX_BYTES = 2_000_000


def parse_batch(requested_ids, response):
    """Reject unexpected/duplicate identities rather than silently misjoin."""
    studies = response.get("studies")
    if not isinstance(studies, list):
        raise ValueError("Registry studies array missing")
    valid = set(requested_ids)
    found = {}
    for payload in studies:
        ident = payload.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
        if ident not in valid or ident in found:
            raise ValueError("Registry returned unexpected or duplicate NCT")
        found[ident] = extract(ident, payload)
    if response.get("nextPageToken"):
        raise ValueError("Registry batch was paginated unexpectedly")
    return found


def fetch_batch(nct_ids, sleep_fn=time.sleep):
    query = urllib.parse.urlencode({
        "filter.ids": ",".join(nct_ids),
        "pageSize": len(nct_ids),
        "fields": ",".join(FIELDS),
        "format": "json",
    })
    url = API + "?" + query
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "PDUFACommandCenterResearch/1.0 (read-only)",
            })
            with urllib.request.urlopen(request, timeout=18) as response:
                if response.status != 200:
                    raise ValueError("Registry returned non-200 HTTP status")
                body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ValueError("Projected registry batch exceeds size limit")
            return parse_batch(nct_ids, json.loads(body))
        except urllib.error.HTTPError as exc:
            if exc.code != 429 or attempt == 3:
                raise
            raw_retry = exc.headers.get("Retry-After", "")
            try:
                retry = max(1.0, min(float(raw_retry), 20.0))
            except ValueError:
                retry = min(3.0 * (2 ** attempt), 20.0)
            sleep_fn(retry)
    raise RuntimeError("Unreachable retry state")


def audit(batch_fetch=None, pause_fn=time.sleep, batch_size=DEFAULT_BATCH_SIZE):
    if batch_fetch is None:
        batch_fetch = fetch_batch
    if not (1 <= batch_size <= 100):
        raise ValueError("Invalid batch size")
    with TRIALS.open(encoding="utf-8-sig", newline="") as fp:
        originals = list(csv.DictReader(fp))
    if (len(originals) != 741 or len({r["nct_id"] for r in originals}) != 741
            or len({r["ticker"] for r in originals}) != 130):
        raise ValueError("Historical census changed: refusing to mix identities")
    originals.sort(key=lambda x: x["nct_id"])
    trials = []
    for i in range(0, len(originals), batch_size):
        batch = originals[i:i + batch_size]
        ids = [r["nct_id"] for r in batch]
        try:
            latest = batch_fetch(ids)
            if not isinstance(latest, dict) or any(n not in ids for n in latest):
                raise ValueError("Unexpected registry batch mapping")
            batch_error = None
        except (urllib.error.URLError, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            latest = {}
            batch_error = type(exc).__name__ + ": " + str(exc)[:200]
        retrieved_at = datetime.now(timezone.utc).isoformat()
        for row in batch:
            nct = row["nct_id"]
            record = latest.get(nct)
            trials.append({
                "nct_id": nct,
                "ticker": row["ticker"],
                "saved_original_lead_sponsor": row["company"],
                "saved_original_status": row["status"],
                "registry_url": row["source_url"],
                "live_retrieved_at_utc": retrieved_at if record is not None else None,
                "current_registry_metadata": record,
                "sponsor_name_equal": (
                    record["live_registry_lead_sponsor"] == row["company"] if record is not None else None
                ),
                "error": (batch_error or "Study not returned by official registry filter.ids")
                    if record is None else None,
                "current_legal_rights_verified": False,
                "fda_pdufa_verified": False,
                "qualified_pipeline": None,
            })
        if i + batch_size < len(originals):
            pause_fn(1.2)
    success = sum(x["current_registry_metadata"] is not None for x in trials)
    match = sum(x["sponsor_name_equal"] is True for x in trials)
    mismatch = sum(x["sponsor_name_equal"] is False for x in trials)
    return {
        "scope": "LIVE_REGISTRY_BATCHED_METADATA_RESEARCH_ONLY",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": API, "field_projection": list(FIELDS),
        "batch_size": batch_size, "historical_trial_count": 741,
        "historical_issuer_count": 130,
        "registry_metadata_retrieved": success,
        "registry_metadata_unresolved": 741 - success,
        "saved_vs_current_lead_sponsor_equal": match,
        "saved_vs_current_lead_sponsor_changed": mismatch,
        "current_legal_rights_verified": 0, "fda_pdufa_verified": 0,
        "qualified_pipeline_count": None,
        "limitations": "Current registry records are research metadata, not proof of legal rights, FDA NDA/BLA filings, or PDUFA dates. Failed or missing IDs remain unresolved.",
        "trials": trials,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: audit_phase3_batched_registry_metadata.py <output.json>")
    report = audit()
    path = Path(sys.argv[1])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Live batched registry metadata:", report["registry_metadata_retrieved"], "/741")
    print("Unresolved IDs:", report["registry_metadata_unresolved"], "/741")
    print("Exact current sponsor matches:", report["saved_vs_current_lead_sponsor_equal"], "/741")
    print("Changed current sponsor:", report["saved_vs_current_lead_sponsor_changed"], "/741")
    print("Current legal rights: 0/741; FDA/PDUFA: 0/741; qualified Pipeline: UNKNOWN.")
