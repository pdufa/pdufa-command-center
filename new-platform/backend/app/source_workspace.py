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
    "phase_pipeline_market_caps.csv",
    "overnight_scan_status.json", "step7_market_status.csv",
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
_REFRESH_LOCK = threading.Lock()


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


OPTIONAL_SOURCES = frozenset({"watchlist_indicator_signals.csv", "candidate_assessment_reviews.json"})

def fetch(name: str) -> str:
    if name not in SOURCES and name not in OPTIONAL_SOURCES:
        raise ValueError("Unapproved published source path")
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
    candidate = {
        "id": program_id,
        "eventKey": event_key,
        "ticker": ticker,
        "company": first(source, "company"),
        "drug": first(source, "drug"),
        "indication": first(source, "indication"),
        "nctId": first(source, "nct_id"),
        "pdufaDate": target_date,
        # Priority Review belongs to the exact NDA/BLA application, not the ticker.
        # Only an explicit designation AND an FDA-hosted supporting document
        # can produce the verified IMP alert. Do not infer it from PDUFA timing,
        # a Fast Track label, trial status, or an unrelated FDA URL.
        "priorityReview": (
            {
                "status": "FDA_VERIFIED",
                "source": first(source, "priority_review_source_url", "priority_review_evidence_url"),
                "designationDate": first(source, "priority_review_designation_date"),
            }
            if not clinical
            and first(source, "priority_review", "priority_review_designation", "review_designation").upper()
                in {"YES", "PRIORITY", "PRIORITY REVIEW", "PRIORITY_REVIEW", "GRANTED", "CONFIRMED"}
            and re.match(
                r"^https://(?:[a-z0-9-]+\\.)*(?:fda\\.gov|accessdata\\.fda\\.gov)/",
                first(source, "priority_review_source_url", "priority_review_evidence_url"),
                re.I,
            )
            else None
        ),

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
    # Trim repeated nonessential audit columns on clinical registry rows.
    # This API is a candidate-table index, not the canonical source ledger.
    # Exact trial/source URLs, drug, indication, company and stage are retained.
    candidate.pop("sourceRecordType", None)
    if clinical:
        for key in (
            "capSource", "capChecked", "fdaSource", "financingStatus",
            "financingDate", "financingSource", "financingEvidence",
            "approvalProbability", "pValues", "evidenceSummary", "signal",
            "outcome",
        ):
            candidate.pop(key, None)
        if candidate.get("phase3Status") == "NOT VERIFIED":
            candidate.pop("phase3Status", None)
        if candidate.get("checkStatus") in ("NOT VERIFIED", "SOURCE RECORDED"):
            candidate.pop("checkStatus", None)
        # Trial identity already appears as TRIAL|NCT######## in the exact ID;
        # front-end derives the NCT value when opening the trial detail.
        if candidate.get("nctId") and candidate["id"] == "TRIAL|" + candidate["nctId"]:
            candidate.pop("nctId", None)
    return {key: value for key, value in candidate.items() if value is not None and value != ""}


def _fetch_safe(name: str) -> tuple[str, str, str]:
    try:
        return name, fetch(name), ""
    except (HTTPError, URLError, OSError, UnicodeDecodeError, ValueError) as exc:
        return name, "", f"{name}: {type(exc).__name__}"


def gather(today: date | None = None) -> dict:
    now = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    sources: dict = {}
    problems: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(_fetch_safe, SOURCES))
    for name, contents, issue in results:
        sources[name] = contents
        if issue:
            problems.append(issue)
    required_pipeline_sources = (
        "all_phase_trials.csv", "phase_pipeline.csv",
        "phase3_announcements.csv", "pdufa_candidates.csv",
        "fda_review_engine.csv", "prediction_engine_history.csv",
    )
    if any(not sources[name] for name in required_pipeline_sources):
        # Never publish an artificially low Pipeline total when the original
        # Streamlit feeds are temporarily unavailable. workspace() may reuse
        # its previous snapshot marked STALE, rather than losing trials.
        raise RuntimeError("Required PIPELINE source unavailable")

    records = {name: as_rows(sources[name]) for name in SOURCES if name.endswith(".csv")}
    caps = unique(records["phase_pipeline_market_caps.csv"], "ticker")
    funding = unique(records["second_financing_status.csv"], "event_key")
    market = unique(records["step7_market_status.csv"], "ticker")
    # Archived GEM-specific financing rechecks are not active Pipeline gates.
    sec_recheck = {}
    # Legacy GEM cash-runway evidence is archived, not part of POOL qualification.
    runway = {}
    # Source identity is exact event key; duplicate matches are quarantined.
    primary = unique(records["pdufa_candidates.csv"], "event_key")
    fda = unique(records["fda_review_engine.csv"], "event_key")
    history = unique(records["prediction_engine_history.csv"], "event_key")
    for key, row in fda.items():
        primary.setdefault(key, row)
    for key, row in history.items():
        primary.setdefault(key, row)
    # Streamlit's original pipeline_universe.build_universe() is the single
    # source of truth for unique trial/event identities and current stages.
    # In particular, a repeated NCT across two clinical files is ENRICHED,
    # never dropped by unique()'s duplicate quarantine.
    from .pipeline_universe_rules import original_pipeline_universe
    original = original_pipeline_universe(records, now)
    candidates: list[dict] = []
    for exact_id, source in original.items():
        is_clinical = exact_id.startswith(("TRIAL|", "RESULT|"))
        value = make_candidate(source, exact_id, now, caps, funding,
                               clinical=is_clinical)
        if value is None:
            # Streamlit retains unresolved/blank ticker records for auditing.
            # They never qualify for market charts or trading research.
            value = {
                "id": exact_id, "ticker": source.get("ticker", ""),
                "company": source.get("company", ""),
                "drug": source.get("drug", ""),
                "indication": source.get("indication", ""),
                "capInRange": False,
            }
        # Keep the bulk index below Vercel's response limit. The original
        # records above retain the complete evidence; these unused duplicate
        # fields and the NCT already encoded in an exact TRIAL ID added >2 MB.
        value["stage"] = source["stage"]
        # Exact source identity and stage are preserved across all views.
        candidates.append(value)
    trial_count = sum(r["id"].startswith(("TRIAL|", "RESULT|")) for r in candidates)

    # Active POOL and PIPELINE no longer consume legacy GEM JR/GEM ledgers.
    # Historical ledger files, presets and migration history remain archived
    # in the repository; they are not active qualification or scan inputs.
    ledger: dict = {}

    status = {}
    if sources["overnight_scan_status.json"]:
        try:
            audit = json.loads(sources["overnight_scan_status.json"])
            status = {"state": audit.get("status", "UNKNOWN"), "finishedAt": audit.get("finished_at"),
                      "complete": bool(audit.get("complete")),
                      "sources": audit.get("source_checks", {})}
        except (ValueError, TypeError):
            problems.append("overnight_scan_status.json: invalid JSON")

    # Empty compatibility keys preserve old read-only schema without linking
    # GEM stage membership, promotions, historical signals or FS/FA to POOL.
    members = {
        "GEM_JR": {"asOf": "", "rows": [], "history": []},
        "GEM": {"asOf": "", "rows": [], "history": []},
    }
    from .trial_qualification import attach_trial_filter_facts
    attach_trial_filter_facts(candidates, original, funding, sec_recheck, runway, ledger, now)
    missing_trial_feeds = [
        name for name in ("all_phase_trials.csv", "phase_pipeline.csv")
        if not records.get(name)
    ]
    if missing_trial_feeds:
        problems.append("Clinical trial feed unavailable or empty in public GitHub source: " + ", ".join(missing_trial_feeds))
    candidates.sort(key=lambda r: (not bool(r.get("pdufaDate")), r.get("pdufaDate", ""), r["ticker"], r["id"]))
    return {
        "mode": "LIVE_READ_ONLY_GITHUB_SOURCE",
        "asOf": now.isoformat(),
        "fetchedAt": datetime.now(ZoneInfo("UTC")).isoformat(),
        "disclaimer": "Latest published main-branch source data, cached up to 5 minutes; not a confirmed complete live scan or authorization to trade.",
        "marketCapRange": {"min": _MIN, "max": _MAX},
        "trialFilterSchema": 1,
        "pipeline": candidates,
        "members": members,
        "sourceHealth": {
            "state": "PARTIAL" if problems or not status.get("complete") else "COMPLETE_PUBLISHED",
            "issues": problems, "publishedScan": status,
            "clinicalRows": trial_count,
            "regulatoryRows": len(candidates) - trial_count,
            "pipelineSourceParity": {
                "exactPrograms": len(original),
                "clinicalAndResults": trial_count,
                "regulatoryPrograms": len(candidates) - trial_count,
                "comparison": "Original pipeline_universe.build_universe identity and current_stage semantics",
            },
            "technicalMarketTickers": len(market),
            "secRunwayTickers": len(runway),
        },
    }


def _stale_snapshot(snapshot: dict, reason: str, *, refreshing: bool = False) -> dict:
    """Preserve identities while explicitly denying current-source verification."""
    return {
        **snapshot,
        "mode": "STALE_PREVIOUS_FETCH",
        "sourceHealth": {
            **snapshot.get("sourceHealth", {}),
            "state": "STALE",
            "refreshInProgress": refreshing,
            "issues": [*snapshot.get("sourceHealth", {}).get("issues", []), reason],
        },
    }


def workspace(require_fresh: bool = False) -> dict:
    """Serve valid cached sources; optionally await an in-flight refresh.

    Ordinary research calls remain nonblocking and may receive explicit STALE
    source during refresh. The protected interactive POOL request opts in to
    waiting at most 35 seconds for a just-started refresh to finish, so a
    concurrent partial refresh is not treated as a missing POOL. A failed
    refresh still returns STALE and cannot qualify Pipeline candidates.
    """
    with _LOCK:
        cached = _CACHE["payload"]
        if cached is not None and time.monotonic() - _CACHE["as_time"] < 300:
            return cached
    # The interactive authenticated POOL has a strict freshness requirement.
    # Await the one ongoing refresh rather than returning a cached STALE
    # snapshot mid-flight. Never change background assessment semantics.
    acquired = (_REFRESH_LOCK.acquire(timeout=35)
                if require_fresh else _REFRESH_LOCK.acquire(blocking=False))
    if not acquired:
        with _LOCK:
            cached = _CACHE["payload"]
        if cached is not None:
            return _stale_snapshot(cached, "Published-source refresh in progress", refreshing=True)
        # Initial cold start: wait for the first refresh to finish.
        with _REFRESH_LOCK:
            with _LOCK:
                cached = _CACHE["payload"]
            if cached is not None:
                return cached
        # The other refresh failed; attempt our own first fetch.
        return workspace()
    try:
        with _LOCK:
            cached = _CACHE["payload"]
            if cached is not None and time.monotonic() - _CACHE["as_time"] < 300:
                return cached
        try:
            snapshot = gather()
        except Exception as exc:
            LOG.error("PDUFA live published-source refresh failed: %s", type(exc).__name__)
            with _LOCK:
                cached = _CACHE["payload"]
            if cached is not None:
                return _stale_snapshot(cached, "Published-source refresh failed")
            raise
        with _LOCK:
            _CACHE.update(as_time=time.monotonic(), payload=snapshot)
        return snapshot
    finally:
        _REFRESH_LOCK.release()
