"""Step 7: source-dated PRE PHASE 3 dashboard feed.

No external request is made by the Streamlit display. Scheduled collectors
produce the source files. Every event and trial keeps its original identity.
Do not infer a successful Phase 3 from a registry result-posted date; do not
infer a second financing close from an SEC form or a ticker-only match.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

NCT = re.compile(r"^NCT\d{8}$")
FRESH_HOURS = {
    "Clinical trial pipeline": 48,
    "Phase 3 result intake": 48,
    "Pre-readout protocol": 72,
    "Market capitalization": 72,
    "SEC financing recheck": 48,
}
LIVE_STATES = {"COMPLETE", "COMPLETE WITH WARNINGS"}


def read_csv(path):
    if not Path(path).exists():
        return []
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as fh:
            return [{k: str(v or "").strip() for k, v in r.items() if k is not None}
                    for r in csv.DictReader(fh)]
    except (OSError, csv.Error, UnicodeError):
        return []


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}


def timestamp(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def freshness(when, now, hours):
    at = timestamp(when)
    if at is None:
        return "NO TIMESTAMP"
    age = (now - at).total_seconds() / 3600
    if age < -1:
        return "INVALID FUTURE TIMESTAMP"
    if age < 0:
        age = 0
    return "RECENT" if age <= hours else "STALE"


def latest_value(rows, key):
    return max((r.get(key, "") for r in rows if timestamp(r.get(key))), default="")


def as_of_date(value):
    return str(value or "")[:10]


def status_check(name, state, completed, now, extra="", blocked=0):
    progress = str(state or "").strip().upper()
    freshness_value = freshness(completed, now, FRESH_HOURS[name])
    if blocked:
        health = "BLOCKED / PARTIAL"
    elif progress not in LIVE_STATES:
        health = "PARTIAL / UNKNOWN"
    elif freshness_value != "RECENT":
        health = freshness_value
    elif progress == "COMPLETE WITH WARNINGS":
        health = "RECENT WITH WARNINGS"
    else:
        health = "RECENT"
    return {
        "Source": name, "Collector status": progress or "UNKNOWN",
        "Freshness": freshness_value, "Health": health,
        "Last checked UTC": completed or "", "Details": extra,
        "Blocked records": blocked,
    }


def is_valid_source(url):
    return str(url or "").startswith("https://")


def build_snapshot(root, now=None):
    """Return trial rows, exact-event financing rows, and source-health manifest."""
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    trial_rows = read_csv(root / "phase_pipeline.csv")
    protocols = read_csv(root / "pre_readout_protocols.csv")
    caps = read_csv(root / "phase_pipeline_market_caps.csv")
    financing = read_csv(root / "second_financing_status.csv")
    rechecks = read_csv(root / "recheck_status.csv")
    trial_state = read_json(root / "phase_pipeline_state.json")
    p3_state = read_json(root / "phase3_intake_status.json")
    protocol_state = read_json(root / "pre_readout_intake_status.json")

    cap_by_ticker = {}
    for row in caps:
        ticker = row.get("ticker", "").upper()
        if ticker and (ticker not in cap_by_ticker
                       or row.get("market_cap_checked_at", "") > cap_by_ticker[ticker].get("market_cap_checked_at", "")):
            cap_by_ticker[ticker] = row
    protocol_by_nct = {}
    for row in protocols:
        nct = row.get("nct_id", "").upper()
        if NCT.fullmatch(nct) and (nct not in protocol_by_nct
                                    or row.get("checked_at", "") > protocol_by_nct[nct].get("checked_at", "")):
            protocol_by_nct[nct] = row
    recheck_by_event = {r.get("event_key", ""): r for r in rechecks if r.get("event_key")}
    seen = set()
    trials = []
    for row in trial_rows:
        ticker, nct = row.get("ticker", "").upper(), row.get("nct_id", "").upper()
        if not ticker or not NCT.fullmatch(nct) or (ticker, nct) in seen:
            continue
        phases = {p.strip().upper() for p in re.split(r"[,|/]", row.get("phases", ""))}
        if not phases.intersection({"PHASE1", "EARLY_PHASE1", "PHASE2", "PHASE3"}):
            continue
        seen.add((ticker, nct))
        label = "Phase 2/3" if {"PHASE2", "PHASE3"}.issubset(phases) else (
            "Phase 3" if "PHASE3" in phases else
            "Phase 2" if "PHASE2" in phases else "Phase 1")
        cap = cap_by_ticker.get(ticker, {})
        cap_fresh = freshness(cap.get("market_cap_checked_at"), now, 72)
        cap_number = None
        try:
            cap_number = float(cap.get("market_cap", ""))
        except (ValueError, TypeError):
            pass
        cap_ok = (cap.get("market_cap_status", "").upper() == "VERIFIED"
                  and cap_fresh == "RECENT" and cap_number is not None and cap_number > 0)
        cap_state = ("VERIFIED RECENT" if cap_ok else
                     "STALE" if cap_number is not None and cap_fresh == "STALE"
                     else "UNVERIFIED")
        if cap_ok and not (300_000_000 <= cap_number <= 10_000_000_000):
            cap_state = "OUTSIDE $300M–$10B"
        p = protocol_by_nct.get(nct, {})
        p_fresh = freshness(p.get("checked_at"), now, 72)
        registry_results = bool(row.get("results_first_posted"))
        # Do not turn a registry milestone into positive efficacy or an issuer readout.
        trial_check = freshness(row.get("checked_at"), now, 48)
        completion = row.get("primary_completion", "")
        candidate = {
            "Ticker": ticker, "Company": row.get("company", ""),
            "Drug": row.get("drug", ""), "Indication": row.get("indication", ""),
            "NCT ID": nct, "Trial phase": label, "Registry status": row.get("trial_status", ""),
            "Registry primary completion": completion,
            "Registry results posted": row.get("results_first_posted", ""),
            "Issuer Phase 3 readout": "NOT VERIFIED HERE",
            "Research category": ("RESULT POSTED — CLINICAL REVIEW" if registry_results
                                  else "PHASE 3 RESEARCH" if "PHASE3" in phases else "PRE PHASE 3 WATCH"),
            "Company/program identity": row.get("program_identity_status", "") or "REVIEW",
            "Registry check": trial_check,
            "Protocol check": p_fresh if "PHASE3" in phases else "NOT REQUIRED FOR PHASE 2 WATCH",
            "Market cap USD": cap_number if cap_ok else None,
            "Market cap state": cap_state,
            "Market source": cap.get("market_cap_source", "") if cap_ok else "",
            "Market cap as of UTC": cap.get("market_cap_checked_at", ""),
            "NCT source": row.get("source_url", ""),
            "Last trial check UTC": row.get("checked_at", ""),
            "ENTRY READY": "NO — mandatory clinical, financing and market gates unverified",
            "_sort": (
                0 if "PHASE3" in phases and not registry_results else
                1 if "PHASE3" in phases else 2,
                0 if trial_check == "RECENT" else 1,
                completion or "9999-99-99",
                ticker, nct,
            ),
        }
        trials.append(candidate)
    trials.sort(key=lambda r: r["_sort"])
    for row in trials:
        row.pop("_sort", None)

    events = []
    for fin in financing:
        key = fin.get("event_key", "")
        if not key:
            continue
        rec = recheck_by_event.get(key, {})
        status = fin.get("second_financing_audit_status", "") or "UNVERIFIED"
        check = freshness(rec.get("completed_at_utc"), now, 48)
        sec = rec.get("financing_status", "").upper()
        blocked = ("BLOCKED" in sec or "ERROR" in sec or sec in {"", "NOT_CHECKED", "SOURCE_UNAVAILABLE"})
        historical = (status == "VERIFIED_SECOND_POST_PHASE3_FINANCING"
                      and fin.get("second_financing_closed", "").upper() == "YES"
                      and as_of_date(fin.get("first_financing_date")) < as_of_date(fin.get("second_financing_date"))
                      and is_valid_source(fin.get("first_financing_source"))
                      and is_valid_source(fin.get("second_financing_source")))
        events.append({
            "Ticker": key.split("|", 1)[0],
            "Exact financing event": key,
            "Historical second closing": "DOCUMENTED — RECHECK REQUIRED" if historical else "NOT VERIFIED",
            "Source scan": sec or "NOT RUN",
            "Recheck freshness": check,
            "First financing date": fin.get("first_financing_date", ""),
            "Second financing date": fin.get("second_financing_date", ""),
            "First source": fin.get("first_financing_source", ""),
            "Second source": fin.get("second_financing_source", ""),
            "Audit status": status,
            "Current gate": "REVIEW — historical financing is not live entry clearance",
            "Why blocked": ("SEC recheck blocked or missing; historical sources retained"
                            if blocked else "Fresh full clinical, safety, dilution, price and volume gates not verified"),
        })
    events.sort(key=lambda r: (r["Ticker"], r["Exact financing event"]))

    sec_blocked = sum(1 for r in rechecks if
                      "BLOCKED" in r.get("financing_status", "").upper()
                      or "ERROR" in r.get("financing_status", "").upper())
    checks = [
        status_check("Clinical trial pipeline", trial_state.get("status"),
                     trial_state.get("finished_at"), now,
                     extra=f"{len(trials)} exact ticker+NCT records; scope is not exhaustive"),
        status_check("Phase 3 result intake", p3_state.get("status"),
                     p3_state.get("finished_at"), now,
                     extra=f"{p3_state.get('stored_results', '?')} saved registry records; not independently adjudicated readouts"),
        status_check("Pre-readout protocol", protocol_state.get("status"),
                     protocol_state.get("as_of"), now,
                     extra=f"{len(protocols)} exact NCT protocol records; issuer readout remains unchecked"),
        status_check("Market capitalization", "COMPLETE" if caps else "UNKNOWN",
                     latest_value(caps, "market_cap_checked_at"), now,
                     extra=f"{sum(r.get('market_cap_status', '').upper() == 'VERIFIED' for r in caps)} provider-labeled quotes; price/volume not included"),
        status_check("SEC financing recheck", "PARTIAL" if sec_blocked else "COMPLETE" if rechecks else "UNKNOWN",
                     latest_value(rechecks, "completed_at_utc"), now,
                     extra=f"{len(financing)} historical event records; SEC access may be blocked",
                     blocked=sec_blocked),
    ]
    return trials, events, {
        "generated_at_utc": now.isoformat(timespec="seconds"),
        "source_checks": checks,
        "trial_rows": len(trials), "financing_events": len(events),
        "entry_ready_count": 0,
        "entry_gate_note": "NO is intentional until independent source-verified Phase 3 success, clinically meaningful benefit, safety, current second financing closure, stable base, normalized volume and dilution conditions can all be confirmed.",
        "scope_note": "Saved scheduled-collector snapshots, not tick-by-tick market data. SEC failures are not masked.",
    }


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
