"""Read-only program-level chart-indicator sheet through PIPELINE -> GEM JR -> GEM -> WT.

Evidence is joined by exact trial/application identity, never by ticker alone.
Market observations are issuer-level, not claimed to validate a drug/program.
WT selections are local browser research tags; T is NOT an executed trade.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from gem_trading_advisory import assess_gem_trade, load_market_rows
from ticker_toggle_panel import _init_browser_selection, clean_ticker

MIN_CAP = 300_000_000
MAX_CAP = 10_000_000_000
STAGE_ORDER = ("PIPELINE", "GEM JR", "GEM")
COLUMNS = (
    "Pipeline ID", "Ticker", "Drug", "Trial / Program", "Current stage",
    "In PIPELINE", "In GEM JR", "In GEM", "GEM JR first found",
    "GEM first found", "Market cap $", "Market-cap gate",
    "WT decision label", "Priority 1 — Price base / support / resistance",
    "Base support $", "Base resistance $", "Base support tests",
    "Priority 2 — Latest volume", "RVOL", "Priority 3 — SMA20 $",
    "SMA50 $", "Priority 4 — ATR(14)", "Priority 5 — Entry $",
    "Stop $", "Target $", "Reward / risk",
    "Priority 6 — VWAP / anchored VWAP", "Priority 7 — Strength vs XBI",
    "Priority 8 — PDUFA / catalyst", "Priority 9 — RSI(14)",
    "Priority 10 — MACD", "Saved EOD close $", "EOD date",
    "Market source", "Market-cap source", "Data completeness / next action",
)


def read_csv(path):
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError, csv.Error):
        return []


def read_membership(path):
    try:
        with Path(path).open(encoding="utf-8") as stream:
            document = json.load(stream)
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        return {}
    stages = document.get("stages")
    return stages if isinstance(stages, dict) else {}


def _text(value):
    return str(value or "").strip()


def _cap(value):
    try:
        parsed = float(value)
        return parsed if parsed > 0 and parsed < float("inf") else None
    except (ValueError, TypeError, OverflowError):
        return None


def _date(value):
    try:
        return date.fromisoformat(_text(value)[:10])
    except (ValueError, TypeError):
        return None


def _program_rows(root):
    """Use exact primary identifiers; never invent a program from a bare ticker."""
    records = {}

    def add(identifier, raw, stage, *, active=True):
        ticker = clean_ticker(raw.get("ticker") or raw.get("Ticker"))
        if not ticker or not identifier:
            return
        previous = records.get(identifier)
        if previous and previous["ticker"] != ticker:
            # Conflicting program ownership: exclude from inferred propagation.
            del records[identifier]
            conflicted.add(identifier)
            return
        if identifier in conflicted:
            return
        if previous is None:
            previous = {"ticker": ticker, "drug": "", "nct": "",
                        "pdufa": "", "stages": set(), "first_jr": "",
                        "first_gem": ""}
            records[identifier] = previous
        for source, target in (("drug", "drug"), ("nct_id", "nct"),
                               ("pdufa_date", "pdufa")):
            if not previous[target] and _text(raw.get(source)):
                previous[target] = _text(raw[source])
        if active:
            previous["stages"].add(stage)
        if stage == "GEM JR":
            previous["first_jr"] = previous["first_jr"] or _text(raw.get("first_found"))
        if stage == "GEM":
            previous["first_gem"] = previous["first_gem"] or _text(raw.get("first_found"))

    conflicted = set()
    # Include identified trial programs even before promotion; the in-Pipeline
    # flag is a source observation, not proof a later stage has passed its gates.
    for raw in read_csv(root / "phase_pipeline.csv"):
        nct = _text(raw.get("nct_id"))
        if nct.startswith("NCT"):
            add("TRIAL|" + nct, raw, "PIPELINE")
    # Application identities in the existing stage ledger are APPLICATION|event_key.
    for raw in read_csv(root / "pdufa_candidates.csv"):
        event = _text(raw.get("event_key"))
        if event:
            add("APPLICATION|" + event, raw, "PIPELINE")
    for source_stage, displayed_stage in (("GEM_JR", "GEM JR"), ("GEM", "GEM")):
        data = read_membership(root / "gem_stage_membership.json").get(source_stage, {})
        entries = data.get("entries", {}) if isinstance(data, dict) else {}
        if not isinstance(entries, dict):
            continue
        for identifier, raw in entries.items():
            if isinstance(raw, dict):
                add(identifier, raw, displayed_stage,
                    active=_text(raw.get("status")).upper() == "ACTIVE"
                    and not _text(raw.get("left_date")))
    return records


def build_chart_indicator_rows(data_root, as_of, watch=(), trade=()):
    """Build the display/export without market network calls or fabricated metrics."""
    if not isinstance(as_of, date):
        raise TypeError("as_of must be a date")
    root = Path(data_root)
    programs = _program_rows(root)
    market = load_market_rows(root)
    caps = {}
    for raw in read_csv(root / "phase_pipeline_market_caps.csv"):
        ticker = clean_ticker(raw.get("ticker"))
        if ticker and ticker not in caps and _text(raw.get("market_cap_status")) == "VERIFIED":
            caps[ticker] = raw
    watching = {t for v in watch if (t := clean_ticker(v))}
    trading = {t for v in trade if (t := clean_ticker(v))}
    profiles = {}
    output = []
    for identifier, program in sorted(programs.items()):
        ticker = program["ticker"]
        if ticker not in profiles:
            profiles[ticker] = assess_gem_trade(
                {"Ticker": ticker, "_eligible": False}, market, {}, as_of)
        p = profiles[ticker]
        stages = program["stages"]
        current = next((s for s in reversed(STAGE_ORDER) if s in stages),
                       "STAGE UNVERIFIED / HISTORICAL")
        cap_record = caps.get(ticker, {})
        cap = _cap(cap_record.get("market_cap"))
        cap_gate = ("UNVERIFIED" if cap is None else
                    "WITHIN $300M–$10B" if MIN_CAP <= cap <= MAX_CAP
                    else "OUTSIDE $300M–$10B")
        label = ("W + T — CHECK" if ticker in watching and ticker in trading
                 else "T — TRADING RESEARCH" if ticker in trading
                 else "W — WATCHLIST" if ticker in watching else "NOT TAGGED")
        macd = p["macd"]
        event = _date(program["pdufa"])
        catalyst = (f"{event.isoformat()} ({(event - as_of).days:+d} days; "
                    "verify FDA source)" if event else "UNVERIFIED / NO SAVED DATE")
        gaps = []
        if not p["fresh"]:
            gaps.append("Daily EOD unavailable, stale or source-unverified")
        if cap is None:
            gaps.append("Market cap unverified")
        elif cap_gate.startswith("OUTSIDE"):
            gaps.append("Outside project market-cap filter")
        gaps += ["ATR needs verified OHLC", "VWAP needs intraday data",
                 "Relative strength needs XBI series",
                 "R:R needs manual entry/stop/target plan"]
        if not event:
            gaps.append("Catalyst date not verified")
        output.append({
            "Pipeline ID": identifier,
            "Ticker": ticker,
            "Drug": program["drug"] or "UNVERIFIED",
            "Trial / Program": program["nct"] or identifier,
            "Current stage": current,
            "In PIPELINE": "YES" if "PIPELINE" in stages else "NOT RECORDED",
            "In GEM JR": "YES" if "GEM JR" in stages else "NO",
            "In GEM": "YES" if "GEM" in stages else "NO",
            "GEM JR first found": program["first_jr"],
            "GEM first found": program["first_gem"],
            "Market cap $": cap,
            "Market-cap gate": cap_gate,
            "WT decision label": label,
            "Priority 1 — Price base / support / resistance": p["base"]["status"],
            "Base support $": p["base"]["support"],
            "Base resistance $": p["base"]["resistance"],
            "Base support tests": p["base"]["touches"],
            "Priority 2 — Latest volume": p["bars"][-1]["volume"] if p["bars"] else None,
            "RVOL": p["rvol"] if p["fresh"] else None,
            "Priority 3 — SMA20 $": p["sma20"] if p["fresh"] else None,
            "SMA50 $": p["sma50"] if p["fresh"] else None,
            "Priority 4 — ATR(14)": "UNAVAILABLE — OHLC REQUIRED",
            "Priority 5 — Entry $": None,
            "Stop $": None,
            "Target $": None,
            "Reward / risk": "NO VERIFIED TRADE PLAN",
            "Priority 6 — VWAP / anchored VWAP": "UNAVAILABLE — INTRADAY REQUIRED",
            "Priority 7 — Strength vs XBI": "UNAVAILABLE — XBI DATA REQUIRED",
            "Priority 8 — PDUFA / catalyst": catalyst,
            "Priority 9 — RSI(14)": p["rsi"] if p["fresh"] else None,
            "Priority 10 — MACD": (
                "BULLISH" if macd["bullish"] else "BEARISH"
            ) if p["fresh"] and macd else "UNAVAILABLE / INSUFFICIENT DATA",
            "Saved EOD close $": p["close"] if p["fresh"] else None,
            "EOD date": p["date"].isoformat() if p["fresh"] else "",
            "Market source": p["source"] if p["fresh"] else "",
            "Market-cap source": cap_record.get("market_cap_source", ""),
            "Data completeness / next action": "; ".join(gaps),
        })
    return output


def render_chart_indicator_sheet(data_root="data", *, as_of=None):
    """WT view: one program-level indicator sheet, with safe read-only export."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    as_of = as_of or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    st.markdown("### CHART INDICATOR DATA SHEET — PIPELINE TO WT")
    st.caption(
        "One row per exact trial/application. Stage history stays attached to "
        "the program while W/T is a ticker-level browser label. The sheet is "
        "research only: T never places a trade or certifies a GEM entry gate."
    )
    _init_browser_selection("chart_indicator_lineage_sheet")
    rows = build_chart_indicator_rows(
        data_root, as_of, st.session_state.get("watchlist", []),
        st.session_state.get("trading_tickers", []))
    if not rows:
        st.info("No source-identified saved PIPELINE/GEM programs available.")
        return
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stage = st.selectbox("Stage", ["ALL", "PIPELINE", "GEM JR", "GEM"],
                             key="chart_sheet_stage")
    with c2:
        tag = st.selectbox("WT label", ["ALL", "W — WATCHLIST",
                            "T — TRADING RESEARCH", "NOT TAGGED"],
                           key="chart_sheet_wt")
    with c3:
        find = st.text_input("Ticker / program search", key="chart_sheet_find").strip().upper()
    with c4:
        cap_filter = st.selectbox(
            "Market cap", ["WITHIN $300M–$10B", "ALL", "OUTSIDE $300M–$10B",
                           "UNVERIFIED"], key="chart_sheet_cap")
    filtered = [
        r for r in rows
        if (cap_filter == "ALL" or r["Market-cap gate"] == cap_filter)
        and (stage == "ALL" or r["Current stage"] == stage)
        and (tag == "ALL" or r["WT decision label"] == tag)
        and (not find or find in r["Ticker"] or find in r["Pipeline ID"].upper()
             or find in r["Drug"].upper())
    ]
    st.caption(
        f"{len(filtered):,} of {len(rows):,} program records. Market-cap filter: "
        "$300M to $10B. OUTSIDE and UNVERIFIED are shown, not silently promoted. "
        "Indicator values require recent verified saved market data."
    )
    st.dataframe(pd.DataFrame(filtered, columns=COLUMNS), use_container_width=True,
                 hide_index=True, height=390)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(filtered)
    st.download_button(
        "DOWNLOAD FILTERED CHART INDICATOR SHEET (CSV)",
        data=output.getvalue(), file_name=f"pdufa_chart_indicator_sheet_{as_of.isoformat()}.csv",
        mime="text/csv", key="chart_indicator_sheet_export")
    st.caption(
        "This is a snapshot of saved data and browser-local W/T selections. "
        "ATR, VWAP, XBI strength, stops and targets stay unavailable until "
        "their actual inputs exist. No broker orders are placed."
    )
