"""Read-only source adapter for the new dashboard.

Fetches the *published* GitHub main-branch source files over HTTPS with a TTL.
No imports from Streamlit, no writes to its repo, no market/broker orders.
A missing clinical feed is never silently represented as complete coverage.
"""
from __future__ import annotations

import csv
import io
from concurrent.futures import ThreadPoolExecutor
import json
import logging
import math
import re
import threading
import time
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

LOG = logging.getLogger(__name__)
GITHUB = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/"
SOURCES = (
    "phase_pipeline.csv", "all_phase_trials.csv", "phase3_announcements.csv",
    "pdufa_candidates.csv", "fda_review_engine.csv", "prediction_engine_history.csv",
    "drug_metadata.csv", "second_financing_status.csv",
    "phase_pipeline_market_caps.csv", "gem_stage_membership.json",
    "overnight_scan_status.json",
)
STAGES = (
    "Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3",
    "Phase 3", "Phase 3 Results", "NDA/BLA Submission", "FDA Acceptance",
    "PDUFA Decision", "Post-Decision", "Phase 4", "Not Applicable", "Unknown",
)
CLOSED = {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,14}$")
NCT = re.compile(r"^NCT\d{8}$")
_MIN, _MAX = 300_000_000, 10_000_000_000
_CACHE: dict = {"as_time": 0.0, "payload": None}
_LOCK = threading.Lock()


def clean(value) -> str:
    raw = str(value or "").strip()
    return "" if raw.lower() in ("nan", "nat", "none", "<na>") else raw


def first(row: dict, *keys: str) -> str:
    return next((clean(row.get(key)) for key in keys if clean(row.get(key))), "")


def dated(raw) -> date | None:
    try:
        return date.fromisoformat(clean(raw)[:10])
    except ValueError:
        return None


def num(raw) -> int | None:
    try:
        n = float(raw)
        return int(n) if math.isfinite(n) and n > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


def unique(rows: list[dict], field: str) -> dict:
    result, dupes = {}, set()
    for row in rows:
        key = clean(row.get(field))
        if not key:
            continue
        if key in result:
            dupes.add(key)
        result.setdefault(key, row)
    for key in dupes:
        result.pop(key, None)
    return result


def phase_label(raw) -> str:
    val = clean(raw).upper().replace(" ", "")
    tokens = set(filter(None, re.split(r"[|,/]", val)))
    if tokens == {"PHASE1", "PHASE2"}:
        return "Phase 1/2"
    if tokens == {"PHASE2", "PHASE3"}:
        return "Phase 2/3"
    return {
        "EARLY_PHASE1": "Early Phase 1", "PHASE1": "Phase 1",
        "PHASE2": "Phase 2", "PHASE3": "Phase 3", "PHASE4": "Phase 4",
        "NA": "Not Applicable",
    }.get(val, "Unknown")


def fetch(name: str) -> str:
    assert name in SOURCES
    request = Request(
        GITHUB + name,
        headers={"User-Agent": "PDUFA-new-read-only-source-adapter/1.0", "Accept": "text/plain"},
    )
    with urlopen(request, timeout=12) as response:
        content = response.read(8_000_001)
        if len(content) > 8_000_000:
            raise ValueError("Source exceeds safe size cap")
        return content.decode("utf-8-sig")


def as_rows(data: str) -> list[dict]:
    return [dict(row) for row in csv.DictReader(io.StringIO(data))]


def make_candidate(source: dict, program_id: str, now: date,
                   caps: dict, funding: dict, *, clinical=False) -> dict | None:
    ticker = first(source, "ticker").upper()
    if not TICKER.fullmatch(ticker):
        return None
    event_key = first(source, "event_key")
    cap_data = caps.get(ticker, {})
    market_cap = num(cap_data.get("market_cap")) or num(source.get("market_cap"))
    phase = first(source, "phase", "phases")
    outcome = first(source, "outcome", "actual_fda_decision").upper()
    target_date = first(source, "pdufa_date")
    if clinical:
        stage = phase_label(phase)
        results = dated(first(source, "results_posted", "results_first_posted"))
        if stage == "Phase 3" and results and results <= now and first(source, "source_url").startswith("https://"):
            stage = "Phase 3 Results"
    elif outcome in CLOSED or (dated(source.get("decision_date")) and dated(source.get("decision_date")) <= now):
        stage = "Post-Decision"
    elif dated(target_date):
        stage = "PDUFA Decision"
    elif dated(source.get("fda_acceptance_date")):
        stage = "FDA Acceptance"
    elif dated(source.get("nda_submission_date")):
        stage = "NDA/BLA Submission"
    elif dated(source.get("phase3_date")) and first(source, "trial_evidence_url").startswith("https://"):
        stage = "Phase 3 Results"
    else:
        stage = "Unknown"
    finance = funding.get(event_key, {}) if event_key else {}
    return {
        "id": program_id,
        "eventKey": event_key,
        "ticker": ticker,
        "company": first(source, "company"),
        "drug": first(source, "drug"),
        "indication": first(source, "indication"),
        "nctId": first(source, "nct_id"),
        "pdufaDate": target_date,
        "phase3Date": first(source, "phase3_date", "results_posted", "results_first_posted"),
        "phase3Status": first(source, "phase3_status", "verification_status") or "NOT VERIFIED",
        "phase3Source": first(source, "trial_evidence_url", "source_url"),
        "stage": stage,
        "outcome": outcome,
        "marketCap": market_cap,
        "capInRange": market_cap is not None and _MIN <= market_cap <= _MAX,
        "capChecked": first(cap_data, "market_cap_checked_at"),
        "capSource": first(cap_data, "market_cap_source"),
        "financingStatus": first(finance, "second_financing_audit_status") or "NOT VERIFIED",
        "financingDate": first(finance, "second_financing_date"),
        "financingSource": first(finance, "second_financing_source"),
        "financingEvidence": first(finance, "second_financing_evidence_note"),
        "fdaSource": first(source, "pdufa_evidence_url", "source_url"),
        "lastChecked": first(source, "last_checked", "checked_at"),
        "approvalProbability": first(source, "approval_probability"),
        "checkStatus": first(source, "check_status", "evidence_status") or "NOT VERIFIED",
        "pValues": first(source, "reported_p_values"),
        "evidenceSummary": first(source, "evidence_summary", "evidence_note"),
        "signal": first(source, "signal"),
        "sourceRecordType": "Registered trial" if clinical else "Regulatory program",
    }


def _fetch_safe(name: str) -> tuple[str, str, str]:
    try:
        return name, fetch(name), ""
    except (HTTPError, URLError, OSError, UnicodeDecodeError, ValueError) as exc:
        return name, "", f"{name}: {type(exc).__name__}"


def gather() -> dict:
    now = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    sources: dict = {}
    problems: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(_fetch_safe, SOURCES))
    for name, contents, issue in results:
        sources[name] = contents
        if issue:
            problems.append(issue)
    if not sources["gem_stage_membership.json"] or not sources["pdufa_candidates.csv"]:
        raise RuntimeError("Required candidate or stage-membership source is unavailable")

    records = {name: as_rows(sources[name]) for name in SOURCES if name.endswith(".csv")}
    caps = unique(records["phase_pipeline_market_caps.csv"], "ticker")
    funding = unique(records["second_financing_status.csv"], "event_key")
    # Source identity is exact event key; duplicate matches are quarantined.
    primary = unique(records["pdufa_candidates.csv"], "event_key")
    fda = unique(records["fda_review_engine.csv"], "event_key")
    history = unique(records["prediction_engine_history.csv"], "event_key")
    for key, row in fda.items():
        primary.setdefault(key, row)
    for key, row in history.items():
        primary.setdefault(key, row)
    candidates: list[dict] = []
    for key, row in primary.items():
        value = make_candidate(row, "APPLICATION|" + key, now, caps, funding)
        if value:
            candidates.append(value)

    trial_sources = records["all_phase_trials.csv"] + records["phase_pipeline.csv"]
    trials = unique([
        t for t in trial_sources if NCT.fullmatch(first(t, "nct_id").upper())
    ], "nct_id")
    for nct, row in trials.items():
        trial = make_candidate(row, "TRIAL|" + nct, now, caps, funding, clinical=True)
        if trial:
            candidates.append(trial)

    by_id = {r["id"]: r for r in candidates}
    ledger = json.loads(sources["gem_stage_membership.json"])
    if ledger.get("schema_version") != 1:
        raise ValueError("Unsupported GEM membership source schema")

    members: dict = {}
    for stage in ("GEM_JR", "GEM"):
        detail = ledger.get("stages", {}).get(stage, {})
        rows = []
        for exact_id, entry in detail.get("entries", {}).items():
            if (entry.get("status") != "ACTIVE" or exact_id != entry.get("pipeline_id")
                    or not exact_id.startswith(("APPLICATION|", "TRIAL|"))):
                continue
            ticker = first(entry, "ticker").upper()
            if not TICKER.fullmatch(ticker):
                continue
            source = by_id.get(exact_id, {})
            if source and source["ticker"] != ticker:
                source = {}
            rows.append({
                **source,
                "id": exact_id, "ticker": ticker,
                "drug": first(entry, "drug") or source.get("drug", ""),
                "nctId": first(entry, "nct_id") or source.get("nctId", ""),
                "pdufaDate": first(entry, "pdufa_date") or source.get("pdufaDate", ""),
                "firstFound": first(entry, "first_found"),
                "lastSeen": first(entry, "last_seen"),
                "membershipStatus": "ACTIVE IN PUBLISHED STAGE LEDGER",
                "candidateLinked": bool(source),
            })
        members[stage] = {
            "asOf": first(detail, "last_complete_snapshot"),
            "rows": sorted(rows, key=lambda v: (v["ticker"], v["id"])),
        }
    status = {}
    if sources["overnight_scan_status.json"]:
        try:
            audit = json.loads(sources["overnight_scan_status.json"])
            status = {"state": audit.get("status", "UNKNOWN"), "finishedAt": audit.get("finished_at"),
                      "complete": bool(audit.get("complete")),
                      "sources": audit.get("source_checks", {})}
        except (ValueError, TypeError):
            problems.append("overnight_scan_status.json: invalid JSON")
    missing_trial_feeds = [
        name for name in ("all_phase_trials.csv", "phase_pipeline.csv")
        if not records.get(name)
    ]
    if missing_trial_feeds:
        problems.append("Clinical trial feed unavailable or empty in public GitHub source: " + ", ".join(missing_trial_feeds))
    candidates.sort(key=lambda r: (r["pdufaDate"] == "", r["pdufaDate"], r["ticker"], r["id"]))
    return {
        "mode": "LIVE_READ_ONLY_GITHUB_SOURCE",
        "asOf": now.isoformat(),
        "fetchedAt": datetime.now(ZoneInfo("UTC")).isoformat(),
        "disclaimer": "Latest published Streamlit main-branch data, cached up to 5 minutes; not a confirmed complete live scan or authorization to trade.",
        "marketCapRange": {"min": _MIN, "max": _MAX},
        "pipeline": candidates,
        "members": members,
        "sourceHealth": {
            "state": "PARTIAL" if problems or not status.get("complete") else "COMPLETE_PUBLISHED",
            "issues": problems, "publishedScan": status,
            "clinicalRows": len(trials),
            "regulatoryRows": len(candidates) - len(trials),
        },
    }


def workspace() -> dict:
    with _LOCK:
        clock = time.monotonic()
        if _CACHE["payload"] is not None and clock - _CACHE["as_time"] < 300:
            return _CACHE["payload"]
        try:
            snapshot = gather()
        except Exception as exc:
            LOG.error("PDUFA live published-source refresh failed: %s", type(exc).__name__)
            if _CACHE["payload"] is not None:
                old = dict(_CACHE["payload"])
                old["mode"] = "STALE_PREVIOUS_FETCH"
                old["sourceHealth"] = {**old.get("sourceHealth", {}), "state": "STALE",
                                       "issues": old.get("sourceHealth", {}).get("issues", []) + ["Published-source refresh failed"]}
                return old
            raise
        _CACHE.update(as_time=clock, payload=snapshot)
        return snapshot
