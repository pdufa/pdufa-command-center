#!/usr/bin/env python3
"""Batch read the 677 non-pilot Phase 3 study records from ClinicalTrials.gov.

Research only: this does not qualify Pipeline members, verify company licensing,
establish FDA PDUFA dates, or calculate approval odds. Uses the public API's
filter.ids list endpoint, NOT 677 separate HTTP calls.

- Preserve the exact dated 741-NCT census and its 64 previously reviewed IDs.
- Fetch all 677 others in 28 bounded GETs (25 NCTs per request).
- Reconcile each returned record to the exact requested NCT and saved census.
- Check the API data version both before and after batch retrieval.
- Withhold source-complete status on any failure or non-coherent version.
- Never write to the website, scanners, trading, or original research census.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from check_phase3_original_registry_pilot import (
    ORIGIN, SOURCE_CSV, extract_original_study,
)
from check_phase3_64_original_sources import (
    SAMPLE_LIMIT, CENSUS_COUNT, select_64_original_studies,
)

BATCH_SIZE = 25
EXPECTED_REMAINING = 677
MAX_RESPONSE_BYTES = 2_500_000
MAX_VERSION_BYTES = 10_000
MAX_WORKERS = 2
ENDPOINT = ORIGIN + "/api/v2/studies"
VERSION = ORIGIN + "/api/v2/version"
SNAPSHOT_AT = "2026-10-26T12:21:15.972309+00:00"


def select_remaining_677(csv_text: str) -> list[dict[str, str]]:
    """Full census integrity precheck and exact disjointness with pilot-64."""
    pilot = select_64_original_studies(csv_text)
    # select_64_original_studies already verifies the entire 741 census through
    # dated_census_sample (IDs/statuses/source URLs and 130 tickers).
    import csv
    rows = list(csv.DictReader(csv_text.splitlines()))
    pilot_ids = {row["nct_id"] for row in pilot}
    remaining = [row for row in rows if row["nct_id"] not in pilot_ids]
    if (len(rows) != CENSUS_COUNT
        or len(pilot) != SAMPLE_LIMIT or len(pilot_ids) != SAMPLE_LIMIT
        or len(remaining) != EXPECTED_REMAINING
        or len({row["nct_id"] for row in remaining}) != EXPECTED_REMAINING
        or pilot_ids.intersection(row["nct_id"] for row in remaining)):
        raise ValueError("Cannot reconcile remaining 677 original trial IDs")
    return remaining


def fixed_json_get(url: str, max_bytes: int) -> bytes:
    if not url.startswith(ORIGIN + "/api/v2/"):
        raise ValueError("Unapproved clinical registry source origin")
    request = urllib.request.Request(url, method="GET", headers={
        "Accept": "application/json",
        "User-Agent": "PDUFA-Bounded-Original-Registry-Research/1.0",
    })
    with urllib.request.urlopen(request, timeout=18) as response:
        if (response.status != 200 or response.geturl() != url
            or "application/json" not in response.headers.get("content-type", "").lower()):
            raise ValueError("Clinical registry response identity or content type failed")
        raw = response.read(max_bytes + 1)
    if not raw or len(raw) > max_bytes:
        raise ValueError("Original registry batch exceeded size limit")
    return raw


def registry_version() -> dict[str, str]:
    raw = fixed_json_get(VERSION, MAX_VERSION_BYTES)
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Unrecognized clinical registry version response")
    timestamp = data.get("dataTimestamp")
    api_version = data.get("apiVersion")
    if (not isinstance(timestamp, str)
        or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T[\d:.+-]+Z?", timestamp)
        or not isinstance(api_version, str) or not 0 < len(api_version) <= 30):
        raise ValueError("Unrecognized clinical registry data timestamp/version")
    return {"dataTimestamp": timestamp, "apiVersion": api_version}


def bulk_group_url(group: list[dict[str, str]]) -> str:
    if not 1 <= len(group) <= BATCH_SIZE:
        raise ValueError("Unbounded original registry batch size")
    ids = [r["nct_id"] for r in group]
    if len(set(ids)) != len(ids) or any(not re.fullmatch(r"NCT\d{8}", x) for x in ids):
        raise ValueError("Duplicate/invalid exact study ID in request")
    return ENDPOINT + "?" + urllib.parse.urlencode({
        "filter.ids": ",".join(ids), "format": "json", "pageSize": str(len(ids)),
    })


def reconcile_bulk_group(
    payload: object, group: list[dict[str, str]], checked_at: str,
) -> list[dict[str, object]]:
    """Detect missing, duplicate, out-of-request, cross-NCT and forged data."""
    if not isinstance(payload, dict) or payload.get("nextPageToken"):
        raise ValueError("Incomplete original registry batch pagination")
    studies = payload.get("studies")
    if not isinstance(studies, list) or len(studies) > len(group):
        raise ValueError("Original registry batch study-count overflow")
    requested = {r["nct_id"]: r for r in group}
    if len(requested) != len(group):
        raise ValueError("Original registry batch requested duplicates")
    returned: dict[str, dict[str, object]] = {}
    for study in studies:
        if not isinstance(study, dict):
            raise ValueError("Original registry study was not an object")
        section = study.get("protocolSection")
        identity = section.get("identificationModule") if isinstance(section, dict) else None
        nct = identity.get("nctId") if isinstance(identity, dict) else None
        if not isinstance(nct, str) or nct not in requested or nct in returned:
            raise ValueError("Original registry batch cross-NCT or duplicate response")
        # These bytes are reproducible CANONICAL JSON of the returned study
        # object. They are *not* the raw bytes of /studies/{nct} endpoint.
        canonical = json.dumps(
            study, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        if len(canonical) > 800_000:
            raise ValueError("Original registry record exceeded size bound")
        observation = extract_original_study(canonical, requested[nct], checked_at)
        if (observation["nct_id"] != nct
            or observation["qualified_pipeline"] is not None
            or observation["fda_approval_probability"] is not None
            or observation["verified_us_fda_pdufa"] is not False
            or observation["verified_current_commercial_development_rights"] is not False):
            raise ValueError("Original source incorrectly promoted Pipeline/FDA")
        observation["canonical_returned_study_sha256"] = hashlib.sha256(canonical).hexdigest()
        observation.pop("source_sha256", None)
        observation["source_retrieval_method"] = "batch_filter_ids"
        returned[nct] = observation

    results: list[dict[str, object]] = []
    for row in group:
        if row["nct_id"] in returned:
            results.append(returned[row["nct_id"]])
        else:
            results.append({
                "nct_id": row["nct_id"], "error": "NOT_RETURNED_BY_ORIGINAL_REGISTRY",
            })
    return results


def fetch_group(group: list[dict[str, str]]) -> list[dict[str, object]]:
    url = bulk_group_url(group)
    checked = datetime.now(timezone.utc).isoformat()
    raw = fixed_json_get(url, MAX_RESPONSE_BYTES)
    return reconcile_bulk_group(json.loads(raw), group, checked)


def safe_fetch_group(group: list[dict[str, str]]) -> list[dict[str, object]]:
    try:
        return fetch_group(group)
    except (ValueError, urllib.error.URLError, TimeoutError, OSError, UnicodeError):
        # Do not treat an unverified page as partially qualified. Preserve
        # one unresolved row for EACH missing original NCT.
        return [{"nct_id": row["nct_id"], "error": "BATCH_SOURCE_UNVERIFIED"}
                for row in group]


def summarize_677(
    remaining: list[dict[str, str]], results: list[dict[str, object]],
    before: dict[str, str] | None, after: dict[str, str] | None,
) -> dict[str, object]:
    if len(remaining) != EXPECTED_REMAINING or len(results) != EXPECTED_REMAINING:
        raise ValueError("Original registry 677-study research was incomplete")
    requested_ids = [row["nct_id"] for row in remaining]
    if len(set(requested_ids)) != EXPECTED_REMAINING:
        raise ValueError("Duplicate NCT IDs in remaining census")
    if any(r.get("nct_id") != nct for r, nct in zip(results, requested_ids)):
        raise ValueError("Original source results reordered or forged")
    returned = []
    failures = []
    for row, result in zip(remaining, results):
        if "error" in result:
            if result["error"] not in (
                "NOT_RETURNED_BY_ORIGINAL_REGISTRY", "BATCH_SOURCE_UNVERIFIED"
            ):
                raise ValueError("Unknown source failure disposition")
            failures.append({"nct_id": row["nct_id"], "reason": result["error"]})
            continue
        if (result.get("source") != ORIGIN + "/api/v2/studies/" + row["nct_id"]
            or result.get("census_status") != row["status"]
            or result.get("census_ticker") != row["ticker"]
            or result.get("source_retrieval_method") != "batch_filter_ids"
            or not isinstance(result.get("canonical_returned_study_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", result["canonical_returned_study_sha256"])
            or result.get("qualified_pipeline") is not None
            or result.get("fda_approval_probability") is not None
            or result.get("verified_us_fda_pdufa") is not False
            or result.get("verified_current_commercial_development_rights") is not False):
            raise ValueError("Original source integrity or non-promotion check failed")
        returned.append(result)
    stable_version = (
        before is not None and after is not None
        and before.get("dataTimestamp") == after.get("dataTimestamp")
        and before.get("apiVersion") == after.get("apiVersion")
    )
    report = {
        "type": "RESEARCH_ONLY_REMAINING_677_ORIGINAL_STUDIES",
        "census_created_at_utc": SNAPSHOT_AT,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "census_total": 741,
        "already_checked_pilot_sample_ncts": 64,
        "requested_remaining_ids": requested_ids,
        "requested_remaining_count": EXPECTED_REMAINING,
        "exact_registry_studies_retrieved": len(returned),
        "source_unavailable_count": len(failures),
        "registry_version_before": before,
        "registry_version_after": after,
        "registry_version_stable": stable_version,
        "status_differences_from_census": [
            row["nct_id"] for row in returned
            if row.get("status_matches_dated_census") is not True
        ],
        "phase3_not_currently_reported": [
            row["nct_id"] for row in returned
            if row.get("phase3_in_current_registry") is not True
        ],
        "source_failures": failures,
        "source_observations": returned,
        "all_remaining_source_ids_retrieved": (
            len(returned) == EXPECTED_REMAINING and not failures
            and stable_version
        ),
        "qualified_pipeline_count": None,
        "verified_us_fda_pdufa_count": None,
        "validated_fda_approval_probabilities": None,
        "limitations": (
            "ClinicalTrials.gov public-source registry content only. The 677 "
            "canonical study hashes are from individually serialized studies "
            "returned in batch JSON, not independently signed source originals. "
            "All 741 still require actual issuer/rights, drug-indication, "
            "FDA review, PDUFA and mandatory-restriction verification."
        ),
    }
    return report


def run_remaining(output: Path) -> int:
    remaining = select_remaining_677(SOURCE_CSV.read_text(encoding="utf-8-sig"))
    before = None
    after = None
    version_error = False
    try:
        before = registry_version()
    except (ValueError, urllib.error.URLError, TimeoutError, OSError, UnicodeError):
        version_error = True
    groups = [
        remaining[i:i + BATCH_SIZE] for i in range(0, len(remaining), BATCH_SIZE)
    ]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        batch_results = list(pool.map(safe_fetch_group, groups))
    results = [row for batch in batch_results for row in batch]
    try:
        after = registry_version()
    except (ValueError, urllib.error.URLError, TimeoutError, OSError, UnicodeError):
        version_error = True
    report = summarize_677(remaining, results, before, after)
    if version_error:
        report["all_remaining_source_ids_retrieved"] = False
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "Remaining original registry coverage: "
        + str(report["exact_registry_studies_retrieved"]) + "/677 exact studies, "
        + str(report["source_unavailable_count"]) + " unresolved, "
        + str(len(groups)) + " bounded batch calls."
    )
    print("API data version stable:", report["registry_version_stable"])
    print("Status differences:", len(report["status_differences_from_census"]))
    print("Phase 3 not currently reported:", len(report["phase3_not_currently_reported"]))
    print("Source report stored; qualified Pipeline and FDA approval odds UNVERIFIED.")
    return 0 if report["all_remaining_source_ids_retrieved"] else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: check_phase3_remaining_677_sources.py <report-json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run_remaining(Path(sys.argv[1])))
