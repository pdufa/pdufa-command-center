"""Small read-only program-specific WT technical lookup.

WT can include any published Pipeline exact trial, not only the 19 GEM records.
The GEM factor engine is reused; identical stock EOD data may be shared by
several trial IDs, but clinical/financing eligibility is NEVER copied between
programs based on ticker.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import threading
import time

from .source_workspace import as_rows, fetch, unique, workspace
from .gem_research_adapter import analyze_member, parse_runway

LOG = logging.getLogger(__name__)
_CONTEXT_LOCK = threading.Lock()
_CONTEXT: dict = {"at": 0.0, "data": None}
_NAMES = (
    "step7_market_status.csv",
    "pdufa_candidates.csv",
    "fda_review_engine.csv",
    "prediction_engine_history.csv",
    "second_financing_status.csv",
    "gem_two_close_recheck.csv",
    "gem_runway_evidence.json",
)


def _fetch_one(name: str) -> tuple[str, str, str]:
    try:
        return name, fetch(name), ""
    except (OSError, ValueError, UnicodeError) as exc:
        return name, "", type(exc).__name__


def _context() -> dict:
    with _CONTEXT_LOCK:
        if _CONTEXT["data"] is not None and time.monotonic() - _CONTEXT["at"] < 300:
            return _CONTEXT["data"]
        with ThreadPoolExecutor(max_workers=7) as executor:
            files = list(executor.map(_fetch_one, _NAMES))
        data, missing = {}, []
        for name, value, issue in files:
            data[name] = value
            if issue:
                missing.append(name + ": " + issue)
        rows = {name: as_rows(data[name]) for name in _NAMES if name.endswith(".csv")}
        events = unique(rows["pdufa_candidates.csv"], "event_key")
        for name in ("fda_review_engine.csv", "prediction_engine_history.csv"):
            for key, row in unique(rows[name], "event_key").items():
                events.setdefault(key, row)
        result = {
            "market": unique(rows["step7_market_status.csv"], "ticker"),
            "events": events,
            "financing": unique(rows["second_financing_status.csv"], "event_key"),
            "recheck": unique(rows["gem_two_close_recheck.csv"], "event_key"),
            "runway": parse_runway(data["gem_runway_evidence.json"]),
            "missingSources": missing,
        }
        _CONTEXT.update(at=time.monotonic(), data=result)
        return result


def for_exact_program(exact_key: str) -> dict:
    if not exact_key.startswith(("APPLICATION|", "TRIAL|")):
        raise ValueError("Invalid exact program")
    snapshot = workspace()
    for stage in ("GEM", "GEM_JR"):
        for row in snapshot.get("members", {}).get(stage, {}).get("rows", []):
            if row.get("id") == exact_key and "technical" in row:
                # Return GEM's actual existing score, not a separate WT formula.
                return {
                    "source": "SAME_GEM_JR_GEM_PROFILE",
                    "stage": stage,
                    "technical": row["technical"],
                    "asOf": snapshot.get("asOf"),
                    "scope": "Exact program; market bars represent ticker-level observations.",
                }
    row = next((r for r in snapshot.get("pipeline", []) if r.get("id") == exact_key), None)
    if row is None:
        return {
            "source": "PUBLISHED_PROGRAM_NOT_CURRENT",
            "technical": None, "asOf": snapshot.get("asOf"),
            "scope": "Historical program identity retained. No current trial evidence.",
        }
    context = _context()
    event_key = row.get("eventKey") or ""
    event = context["events"].get(event_key, {}) if exact_key.startswith("APPLICATION|") else {}
    # A trial with the same ticker NEVER inherits an application-level event,
    # positive endpoint, second financing, or regulatory certainty.
    from datetime import date
    from zoneinfo import ZoneInfo
    from datetime import datetime
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    analysis_row = dict(row)
    if exact_key.startswith("TRIAL|"):
        analysis_row["nctId"] = exact_key.split("|", 1)[1]
    try:
        technical = analyze_member(
            analysis_row, event,
            context["financing"].get(event_key, {}) if event else {},
            context["recheck"].get(event_key, {}) if event else {},
            context["market"], context["runway"].get(row["ticker"]),
            (snapshot.get("sourceHealth") or {}).get("publishedScan") or {},
            today,
        )
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        LOG.warning("WT exact research unavailable: %s", type(exc).__name__)
        return {
            "source": "WT_MARKET_RESEARCH_UNAVAILABLE",
            "technical": None,
            "asOf": snapshot.get("asOf"),
            "missingSources": context["missingSources"],
        }
    return {
        "source": "ORIGINAL_GEM_INDICATOR_MODEL_ON_EXACT_PIPELINE_TRIAL",
        "technical": technical,
        "asOf": snapshot.get("asOf"),
        "missingSources": context["missingSources"],
        "scope": ("Market indicators are ticker-level and may be shared; Phase 3 "
                  "and financing gates remain exact-program only; no orders authorized."),
    }
