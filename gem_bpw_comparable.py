"""GEM versus BiopharmaWatch-style *capability coverage* audit.

No access to BPW paywalled API/outputs is assumed; this is NOT a head-to-head
prediction/returns backtest or a percentage similarity to BPW's algorithms.
Returns are neither simulated nor inferred from missing price histories.
"""
from __future__ import annotations

import csv
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
POLICY = "EXACTLY TWO ENTRY BENCHMARKS: VERIFIED PHASE 3 RESULTS RELEASE AND VERIFIED SECOND POST-READOUT FINANCING CLOSE"
CAPABILITIES = (
    ("clinical", "Phase 3 results and trial evidence", "PARTIAL", "Verified trial readout; endpoint depth depends on source adjudication"),
    ("financing", "Two separate post-Phase-3 financing closes", "CUSTOM", "GEM-specific eligibility rule verified from source attestations"),
    ("fda", "FDA/PDUFA timing and event dates", "PARTIAL", "Source-linked decision date and exit horizon; not BPW historical PoA"),
    ("runway", "SEC cash runway and burn", "PARTIAL", "Cash-only financial-source estimate; not an independent cash forecast"),
    ("dilution", "Financing/dilution risk observations", "PARTIAL", "Source statuses and warnings; incomplete issuer coverage"),
    ("market", "Price and volume momentum", "PARTIAL", "Daily market observations; no proprietary options-flow feed"),
    ("hedge", "Specialist funds' quarterly 13F ownership", "PARTIAL", "Four manager roster, not BPW's wider specialist universe"),
    ("market_cap", "Public market-cap reference", "PARTIAL", "Company-level market-cap file; no rNPV/commercial valuation"),
    ("insider", "SEC Form 4 open-market insider trading", "NOT VERIFIED", "Requires a separate issuer-insider collector and source matching"),
    ("options", "Options, implied volatility and unusual flow", "NOT AVAILABLE", "No licensed options chain/Greeks dataset"),
    ("poa", "Probability of FDA approval", "NOT AVAILABLE", "No validated indication-specific PoA scorecard"),
    ("historical", "Financing-to-PDUFA historical return backtest", "NOT VALIDATED", "Validated linked event, price and financing history insufficient"),
    ("rnpv", "Risk-adjusted pipeline valuation", "NOT AVAILABLE", "Requires efficacy/indication, commercial and probability inputs"),
    ("ma", "M&A targeting and deal probabilities", "NOT AVAILABLE", "Separate buyout research is not a validated GEM rank input"),
)


def _number(v):
    try:
        if v is None or isinstance(v, bool) or str(v).strip() == "":
            return None
        n = float(v)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _csv_rows(path):
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    except (OSError, UnicodeError, csv.Error, ValueError):
        return []


def _calendar_date(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except (TypeError, ValueError):
        return None


def _market_caps(root, as_of):
    good = {}
    for row in _csv_rows(Path(root) / "phase_pipeline_market_caps.csv"):
        d = _calendar_date(row.get("market_cap_checked_at"))
        cap = _number(row.get("market_cap"))
        ticker = str(row.get("ticker") or "").upper().strip()
        if (ticker and row.get("market_cap_status") == "VERIFIED"
                and isinstance(cap, float) and cap > 0
                and d and 0 <= (as_of-d).days <= 14
                and str(row.get("market_cap_source") or "").startswith("https://")):
            good[ticker] = cap
    return good


def _status_count(rows, predicate):
    return sum(1 for row in rows if predicate(row))


def build_comparable(root, scans, *, as_of, hedge_report=None):
    """As-of audited comparison; source failures never become inferred scores."""
    root = Path(root)
    if not isinstance(as_of, date) or isinstance(as_of, datetime):
        raise ValueError("as_of must be a date")
    if not isinstance(scans, list):
        raise ValueError("scans must be a list of GEM observations")
    caps = _market_caps(root, as_of)
    hedge_report = hedge_report if isinstance(hedge_report, dict) else {}
    row_count = len(scans)
    eligible = [r for r in scans if r.get("Two-benchmark eligible") is True]
    phase3 = _status_count(scans, lambda r:
        r.get("Benchmark 1 — Phase 3 released") == "PASS — VERIFIED RESULTS RELEASE")
    financing = _status_count(scans, lambda r:
        r.get("Benchmark 2 — Financing #2 closed") == "PASS — TWO POST-READOUT CLOSES")
    fda = _status_count(scans, lambda r:
        r.get("PDUFA verification") == "VERIFIED — SOURCE LINKED")
    runway = _status_count(scans, lambda r:
        _number(r.get("Cash runway (months)")) is not None
        and str(r.get("Cash runway gate") or "").startswith(("PASS", "HOLD")))
    dilution = _status_count(scans, lambda r:
        r.get("GEM 3 dilution status") == "NO NEW DILUTION FLAG IN SAVED SOURCE")
    market = _status_count(scans, lambda r:
        _number(r.get("Market activity /10")) is not None
        and _number(r.get("Market activity /10")) >= 4
        and str(r.get("Rating status") or "") != "NOT RATED — SNAPSHOT STALE")
    hedge = _status_count(scans, lambda r:
        r.get("Hedge-fund signal") == "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS")
    cap = _status_count(scans, lambda r:
        str(r.get("Ticker") or "").strip().upper() in caps)
    # Flag the existence of a dataset separately from a *validated strategy
    # simulation*. Empty CSV headers or unlinked historical trades do not count.
    historical_raw = len(_csv_rows(root/"post_phase3_historical_trade_events.csv"))
    historical_bars = len(_csv_rows(root/"post_phase3_historical_adjusted_ohlcv.csv"))
    matrix = []
    observed = {"clinical": phase3, "financing": financing, "fda": fda,
                "runway": runway, "dilution": dilution, "market": market,
                "hedge": hedge, "market_cap": cap,
                "insider": 0, "options": 0, "poa": 0,
                "historical": 0, "rnpv": 0, "ma": 0}
    for key, title, baseline, caveat in CAPABILITIES:
        count = observed[key]
        matrix.append({
            "key": key, "capability": title, "state": baseline,
            "observed_gem_rows": count,
            "total_gem_rows": row_count,
            "data_coverage_pct": round(100*count/row_count, 1) if row_count else None,
            "caveat": caveat,
        })
    candidate_rows = []
    for row in sorted(eligible, key=lambda r: (
            r.get("Two-benchmark rank") or 999999, str(r.get("Ticker") or ""))):
        ticker = str(row.get("Ticker") or "").strip().upper()
        candidate_rows.append({
            "Ticker": ticker, "Drug": str(row.get("Drug") or ""),
            "Exact event": str(row.get("Exact event") or ""),
            "Entry benchmark 1 verified": "YES",
            "Entry benchmark 2 verified": "YES",
            "GEM priority rank": row.get("Two-benchmark rank"),
            "GEM priority score /100": row.get("Two-benchmark priority /100"),
            "Phase 3 quality": row.get("Phase 3 quality /30"),
            "Cash runway months": row.get("Cash runway (months)"),
            "Hedge-fund managers holding": row.get("Hedge-fund managers holding"),
            "Hedge-fund managers adding": row.get("Hedge-fund managers adding"),
            "Market capitalization USD": caps.get(ticker),
            "PDUFA date": row.get("PDUFA date"),
            "Risk flags": row.get("Two-benchmark risk flags"),
            "BPW PoA score": None,
            "BPW approval/outperformance similarity": "NOT CALCULABLE WITHOUT LICENSED DATA",
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of_pacific": as_of.isoformat(),
        "comparison": "GEM SAVED-SOURCE COVERAGE VS BPW ADVERTISED CAPABILITIES",
        "policy": POLICY,
        "bpw_access": "PUBLIC FEATURE DESCRIPTIONS ONLY — NO BPW API KEY OR PRIVATE OUTPUTS",
        "same_input_score_comparison_performed": False,
        "similarity_percentage_supported": False,
        "strategy_returns_validated": False,
        "gem_observed_program_rows": row_count,
        "gem_two_benchmark_eligible": len(eligible),
        "gem_phase3_results_verified": phase3,
        "gem_second_closings_verified": financing,
        "hedge_fund_manager_roster": hedge_report.get("manager_count", 0),
        "hedge_fund_managers_complete": hedge_report.get("managers_complete", 0),
        "hedge_fund_source_status": hedge_report.get("collector_status", "UNVERIFIED"),
        "historical_linked_event_rows": historical_raw,
        "historical_price_bar_rows": historical_bars,
        "capability_matrix": matrix,
        "ranked_two_benchmark_candidates": candidate_rows,
        "unvalidated_gaps": [
            "No direct BPW proprietary PoA, options/Greeks, rNPV or conviction-weighted scores",
            "No SEC Form 4 insider scanner currently integrated",
            "Only four selected specialist managers currently tracked",
            "Two-benchmark financing-to-PDUFA backtesting not validated",
            "A coverage audit cannot establish superiority or prediction accuracy",
        ],
    }
