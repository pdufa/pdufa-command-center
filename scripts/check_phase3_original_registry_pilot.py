#!/usr/bin/env python3
"""Independent, read-only pilot against eight ORIGINAL ClinicalTrials.gov v2 study records.

Verifies public source reachability and exact NCT identity (one study for each
dated registry status), not drug ownership, active development, U.S. FDA PDUFA
eligibility, scientific review, or the qualified Pipeline denominator.

Never posts, authenticates with API keys, writes production data, or promotes
this 741-row historical research census to approved candidates.
"""
from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

SOURCE_CSV = Path(__file__).resolve().parents[1] / "data/phase3_all_years_300m_10b_trials.csv"
STATUSES = (
    "RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION",
    "NOT_YET_RECRUITING", "COMPLETED", "TERMINATED", "WITHDRAWN", "UNKNOWN",
)
ORIGIN = "https://clinicaltrials.gov"
MAX_BYTES = 800_000
MAX_TEXT = 1000


def dated_census_sample(csv_text: str) -> list[dict[str, str]]:
    """Fail closed on incomplete inventory; select exactly one per status."""
    reader = csv.DictReader(csv_text.splitlines())
    if reader.fieldnames != ["nct_id", "ticker", "company", "status", "source_url"]:
        raise ValueError("Original census header mismatch")
    rows = list(reader)
    if len(rows) != 741:
        raise ValueError("Original Phase 3 census is not 741 rows")
    ids: set[str] = set()
    tickers: set[str] = set()
    picked: dict[str, dict[str, str]] = {}
    for row in rows:
        nct = row["nct_id"]
        if (not re.fullmatch(r"NCT\d{8}", nct) or nct in ids
            or not re.fullmatch(r"[A-Z]{1,7}(?:[.-][A-Z]{1,3})?", row["ticker"])
            or row["status"] not in STATUSES
            or row["source_url"] != f"{ORIGIN}/study/{nct}"):
            raise ValueError("Invalid/duplicate registry source ID or status")
        ids.add(nct)
        tickers.add(row["ticker"])
        if row["status"] not in picked:
            picked[row["status"]] = row
    if len(ids) != 741 or len(tickers) != 130 or len(picked) != len(STATUSES):
        raise ValueError("Phase 3 census population cannot be reconciled")
    return [picked[status] for status in STATUSES]


PROGRAM_ITEMS_LIMIT = 100
PROGRAM_NAME_LIMIT = 400


def original_program_field(module, section, key, typed=False):
    """Bound original registered intervention/condition names without inference.

    A malformed or over-limit field is explicitly flagged for manual review
    rather than silently being converted into evidence of no program.
    """
    sub = module.get(section)
    if sub is None:
        return [], "SECTION_MISSING", 0
    if not isinstance(sub, dict):
        return [], "SECTION_INVALID", 0
    raw = sub.get(key)
    if raw is None:
        return [], "FIELD_MISSING", 0
    if not isinstance(raw, list):
        return [], "FIELD_INVALID", 0
    if len(raw) > PROGRAM_ITEMS_LIMIT:
        return [], "OVER_LIMIT_REVIEW", len(raw)
    items = []
    for item in raw:
        if typed:
            if not isinstance(item, dict):
                return [], "ITEM_INVALID", len(raw)
            name, kind = item.get("name"), item.get("type")
            if not isinstance(kind, str) or not kind or len(kind) > 80:
                return [], "ITEM_INVALID", len(raw)
        else:
            name, kind = item, None
        if not isinstance(name, str) or not name.strip() or len(name) > PROGRAM_NAME_LIMIT:
            return [], "ITEM_INVALID", len(raw)
        items.append({"name": name.strip(), "type": kind} if typed else name.strip())
    return items, "PRESENT" if items else "EMPTY", len(raw)


def extract_original_study(raw: bytes, expected: dict[str, str], fetched_at: str) -> dict[str, object]:
    """Identity/shape audit; source content is NOT an independent medical review."""
    if not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("Original registry response size blocked")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError) as error:
        raise ValueError("Original registry response is not JSON") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("protocolSection"), dict):
        raise ValueError("Original registry study protocol missing")
    module = payload["protocolSection"]
    identity = module.get("identificationModule", {})
    status = module.get("statusModule", {})
    if not isinstance(identity, dict) or not isinstance(status, dict):
        raise ValueError("Original registry protocol identity/status invalid")
    nct = expected["nct_id"]
    if identity.get("nctId") != nct:
        raise ValueError("Original registry NCT identity mismatch")
    registry_status = status.get("overallStatus")
    if not isinstance(registry_status, str) or not registry_status or len(registry_status) > 80:
        raise ValueError("Original registry status missing")
    study_title = identity.get("briefTitle")
    if not isinstance(study_title, str) or not study_title or len(study_title) > MAX_TEXT:
        raise ValueError("Original registry title missing")
    design = module.get("designModule") or {}
    sponsor = module.get("sponsorCollaboratorsModule") or {}
    if not isinstance(design, dict) or not isinstance(sponsor, dict):
        raise ValueError("Original registry design/sponsor invalid")
    phases = design.get("phases") or []
    if not isinstance(phases, list) or len(phases) > 5:
        raise ValueError("Original registry phases invalid")
    lead = sponsor.get("leadSponsor") or {}
    if not isinstance(lead, dict):
        raise ValueError("Original registry lead sponsor invalid")
    lead_name = lead.get("name")
    if lead_name is not None and (not isinstance(lead_name, str) or len(lead_name) > 260):
        raise ValueError("Original registry sponsor invalid")
    update_date = status.get("lastUpdatePostDate")
    if update_date is not None and (not isinstance(update_date, str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", update_date)):
        raise ValueError("Original registry update invalid")
    conditions, conditions_state, conditions_total = original_program_field(
        module, "conditionsModule", "conditions")
    interventions, interventions_state, interventions_total = original_program_field(
        module, "armsInterventionsModule", "interventions", typed=True)
    return {
        "registry_study_title": study_title,
        "registry_condition_names": conditions,
        "registry_conditions_field_status": conditions_state,
        "registry_conditions_source_count": conditions_total,
        "registry_interventions": interventions,
        "registry_interventions_field_status": interventions_state,
        "registry_interventions_source_count": interventions_total,
        "nct_id": nct,
        "census_status": expected["status"],
        "current_registry_status": registry_status,
        "status_matches_dated_census": registry_status == expected["status"],
        "phase3_in_current_registry": "PHASE3" in phases,
        "census_ticker": expected["ticker"],
        "census_company": expected["company"],
        "currently_registered_lead_sponsor": lead_name,
        "source_posted_update_date": update_date,
        "source": f"{ORIGIN}/api/v2/studies/{nct}",
        "fetched_at_utc": fetched_at,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_response_bytes": len(raw),
        "verified_us_fda_pdufa": False,
        "verified_current_commercial_development_rights": False,
        "qualified_pipeline": None,
        "fda_approval_probability": None,
    }


def fetch_public_original(row: dict[str, str]) -> dict[str, object]:
    nct = row["nct_id"]
    url = f"{ORIGIN}/api/v2/studies/{nct}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json", "User-Agent": "PDUFA-ReadOnly-Source-Research/1.0",
    }, method="GET")
    with urllib.request.urlopen(req, timeout=15) as reply:
        if reply.status != 200 or reply.geturl() != url:
            raise ValueError("Original source did not return exact-url HTTP 200")
        if "application/json" not in reply.headers.get("content-type", "").lower():
            raise ValueError("Original source did not return JSON")
        raw = reply.read(MAX_BYTES + 1)
    when = datetime.now(timezone.utc).isoformat()
    return extract_original_study(raw, row, when)


def run_pilot(output: Path) -> int:
    sample = dated_census_sample(SOURCE_CSV.read_text(encoding="utf-8-sig"))
    report: dict[str, object] = {
        "type": "EXTERNAL_ORIGINAL_REGISTRY_RESEARCH_PILOT",
        "census_generated_at_utc": "2026-10-26T12:21:15.972309+00:00",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "complete_census_count": 741,
        "selected_status_groups": list(STATUSES),
        "sample_size": len(sample),
        "source_connection_operational": False,
        "source_errors": [],
        "original_source_records": [],
        "qualified_pipeline_total": None,
        "verified_us_fda_pdufa_count": None,
        "validated_approval_probabilities": None,
        "limitations": "Exact-NCT public registry source connectivity only; NOT independently authenticated sponsor rights, ongoing development, FDA action or calibrated approval odds.",
    }
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(_fetch_catching, sample))
    for item in results:
        if "error" in item:
            report["source_errors"].append(item)
        else:
            report["original_source_records"].append(item)
    report["source_connection_operational"] = len(report["source_errors"]) == 0 and len(report["original_source_records"]) == len(STATUSES)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Source pilot: " + str(len(report["original_source_records"]))
          + "/" + str(len(STATUSES)) + " original NCT records fetched and identity-checked.")
    for item in report["original_source_records"]:
        print(str(item["nct_id"]) + " " + str(item["census_status"])
              + " -> " + str(item["current_registry_status"])
              + "; Phase 3 " + str(item["phase3_in_current_registry"])
              + "; source SHA-256 " + str(item["source_sha256"])[:12])
    for error in report["source_errors"]:
        print("UNVERIFIED: " + str(error["nct_id"]) + " " + str(error["error"]))
    print("Qualified Pipeline count remains UNKNOWN; FDA approval probabilities NOT VALIDATED.")
    return 0 if report["source_connection_operational"] else 1


def _fetch_catching(row: dict[str, str]) -> dict[str, object]:
    try:
        return fetch_public_original(row)
    except (urllib.error.URLError, ValueError, TimeoutError, OSError) as error:
        # Omit raw server response bodies, URLs with queries, secrets and stack traces.
        return {"nct_id": row["nct_id"], "error": type(error).__name__}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: check_phase3_original_registry_pilot.py <report-json-path>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run_pilot(Path(sys.argv[1])))
