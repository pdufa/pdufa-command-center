"""Fail-closed reconciliation for NCT IDs newly found in the live TOOLS POOL.

The checked-in trial CSV is a snapshot, not a permanent membership ceiling.
Newly appearing studies must be independently verified against the official
ClinicalTrials.gov v2 study endpoint before a public POOL snapshot is published.
Never silently accept missing baseline studies or arbitrary backend identities.
"""
from __future__ import annotations
import json
import re
import urllib.request

CTG_BASE = "https://clinicaltrials.gov/api/v2/studies/"
MAX_NEW_STUDIES = 20
_NCT = re.compile(r"NCT\d{8}\Z")
_ROW_ID = re.compile(r"TRIAL\|(NCT\d{8})\Z")


def fetch_official_nct(nct):
    """Fetch official public trial metadata; deliberately send no app auth."""
    if not _NCT.fullmatch(nct):
        raise ValueError("Invalid official NCT identity")
    url = CTG_BASE + nct
    req = urllib.request.Request(
        url, headers={"Accept": "application/json",
                      "User-Agent": "pdufa-tools-nct-source-parity/1"})
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200 or not response.headers.get(
                "Content-Type", "").lower().startswith("application/json"):
            raise ValueError("Official ClinicalTrials.gov response was not JSON: " + nct)
        body = response.read(1_500_001)
        if len(body) > 1_500_000:
            raise ValueError("Oversize official ClinicalTrials.gov record: " + nct)
    return json.loads(body)


def verify_recent_nct_additions(live_ncts, baseline_ncts, rows, fetcher=None):
    """Return audited additions. Never remove baseline NCTs to make counts fit.

    fetcher is injectable for isolated, network-free regression tests.
    """
    added = sorted(live_ncts - baseline_ncts)
    missing = sorted(baseline_ncts - live_ncts)
    if missing:
        raise ValueError("POOL_SOURCE_NCT_MISSING_BASELINE_COUNT=" +
                         str(len(missing)) + " IDS=" + str(missing[:20]))
    if not added:
        return []
    if len(added) > MAX_NEW_STUDIES:
        raise ValueError("POOL_NCT_UNEXPECTED_MASS_ADD_LIMIT " + str(len(added)) +
                         " IDS=" + str(added[:20]))
    candidates = {}
    for row in rows:
        rid = row.get("id", "") if isinstance(row, dict) else ""
        match = _ROW_ID.fullmatch(rid) if isinstance(rid, str) else None
        if match and match.group(1) in added:
            if match.group(1) in candidates:
                raise ValueError("POOL_DUPLICATE_UNVERIFIED_NCT " + match.group(1))
            candidates[match.group(1)] = row
    if len(candidates) != len(added):
        raise ValueError("POOL_NEW_NCT_MISSING_LIVE_ROW")
    get_record = fetcher if fetcher is not None else fetch_official_nct
    verified = []
    for nct in added:
        if not _NCT.fullmatch(nct):
            raise ValueError("POOL_INVALID_ADDED_NCT")
        record = get_record(nct)
        if not isinstance(record, dict):
            raise ValueError("POOL_OFFICIAL_CTG_INVALID_RECORD " + nct)
        protocol = record.get("protocolSection") or {}
        identity = protocol.get("identificationModule") or {}
        design = protocol.get("designModule") or {}
        official_phases = design.get("phases") or []
        if identity.get("nctId") != nct or design.get("studyType") != "INTERVENTIONAL" or (
            not isinstance(official_phases, list) or
            not official_phases or
            not all(isinstance(p, str) for p in official_phases)
        ):
            raise ValueError("POOL_OFFICIAL_CTG_IDENTITY_OR_DESIGN_INVALID " + nct)
        source_numbers = set(re.findall(r"[1-4]", " ".join(official_phases)))
        live_stage = candidates[nct].get("stage") or ""
        live_numbers = set(re.findall(r"[1-4]", live_stage)) if isinstance(live_stage, str) else set()
        if not source_numbers or not live_numbers or source_numbers.isdisjoint(live_numbers):
            raise ValueError("POOL_OFFICIAL_CTG_PHASE_MISMATCH " + nct)
        verified.append({
            "nctId": nct,
            "clinicalTrialsGovUrl": "https://clinicaltrials.gov/study/" + nct,
            "source": "INDEPENDENT_OFFICIAL_CT_GOV_V2_IDENTITY_AND_PHASE",
            "officialPhases": official_phases,
        })
    return verified
