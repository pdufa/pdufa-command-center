"""Read-only program-level chart-indicator sheet through PIPELINE -> GEM JR -> GEM -> WT.

Evidence is joined by exact trial/application identity, never by ticker alone.
Market observations are issuer-level, not claimed to validate a drug/program.
WT selections are local browser research tags; T is NOT an executed trade.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from gem_trading_advisory import assess_gem_trade, load_market_rows
from indicator_target_spec import EXTRA_FIELDS, TARGETS
from ticker_toggle_panel import _init_browser_selection, clean_ticker

MIN_CAP = 300_000_000
MAX_CAP = 10_000_000_000
STAGE_ORDER = ("PIPELINE", "GEM JR", "GEM")
BASE_COLUMNS = (
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

# Pair each observed metric immediately with its target.  The other five
# categories are inserted before the chart indicators, not dropped.
_SPLIT = BASE_COLUMNS.index("WT decision label") + 1
SOURCE_COLUMNS = (*BASE_COLUMNS[:_SPLIT], *EXTRA_FIELDS, *BASE_COLUMNS[_SPLIT:])
COLUMNS = tuple(
    name for field in SOURCE_COLUMNS
    for name in ((field, f"TARGET — {field}") if field in TARGETS else (field,))
)


def _reported(value, *, limit=180):
    """Preserve saved source fields without asserting primary verification."""
    value = _text(value)
    return ("REPORTED / RECHECK: " + value[:limit]) if value else "UNVERIFIED / MISSING"


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
    # Streamlit's shared dashboard day is a pandas.Timestamp. Normalize it
    # before subtracting a plain datetime.date catalyst; otherwise
    # date - Timestamp raises TypeError for saved PDUFA programs.
    if isinstance(as_of, pd.Timestamp):
        as_of = as_of.date()
    if not isinstance(as_of, date):
        raise TypeError("as_of must be a date")
    root = Path(data_root)
    programs = _program_rows(root)
    # This key is already used by the application source ledger.  Never join
    # Phase 3 results from a different program merely because tickers match.
    exact_fundamentals = {
        "APPLICATION|" + _text(item.get("event_key")): item
        for item in read_csv(root / "pdufa_candidates.csv")
        if _text(item.get("event_key"))
    }
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
        raw = exact_fundamentals.get(identifier, {})
        days = (event - as_of).days if event else None
        evidence = {
            "CLINICAL — Phase 3 primary endpoint": _reported(raw.get("phase3_status")),
            "CLINICAL — Statistical significance": _reported(raw.get("reported_p_values")),
            "CLINICAL — Clinical efficacy": "UNVERIFIED — PRIMARY EVIDENCE REVIEW",
            "CLINICAL — Safety / adverse events": "UNVERIFIED — BENEFIT-RISK REVIEW",
            "CLINICAL — FDA approval probability": _reported(raw.get("approval_probability")),
            "CLINICAL — Regulatory / CMC risk": (
                "Recorded conflict flag: " + _text(raw.get("conflict_flag")) +
                " — NOT complete FDA clearance"
                if _text(raw.get("conflict_flag")) else "UNVERIFIED — FDA / CMC REVIEW"),
            "FINANCIAL — Second post-Phase 3 financing": (
                _reported(raw.get("financing_status")) +
                " — separate SEC verification required"),
            "FINANCIAL — Cash runway (months)": "UNVERIFIED — CASH / BURN EVIDENCE NEEDED",
            "FINANCIAL — Dilution / ATM / warrants": _reported(raw.get("new_dilution_flag")),
            "FINANCIAL — Catalyst window (days)": (
                f"{days:+d} days from SAVED date; verification required"
                if days is not None else "UNVERIFIED / NO SAVED DATE"),
            "FINANCIAL — Valuation / opportunity": "UNVERIFIED — VALUATION ANALYSIS",
            "FINANCIAL — Trading liquidity (20D $)": (
                p["dollar_volume"] if p["fresh"] else None),
            "PARTICIPATION — Short interest (%)": (
                _reported(raw.get("short_interest")) + " — units/source recheck"),
            "PARTICIPATION — Free float": _reported(raw.get("shares_float")),
            "PARTICIPATION — Short days to cover": (
                _reported(raw.get("short_ratio")) + " — definition/source recheck"),
            "PARTICIPATION — Institutional accumulation": (
                "UNVERIFIED — ownership percentage is not accumulation"),
            "PARTICIPATION — Insider open-market buying": "UNVERIFIED — FORM 4 REVIEW",
            "PARTICIPATION — Buyout evidence": "UNVERIFIED — STRATEGIC EVIDENCE",
            "DECISION — Candidate eligibility": "NOT ASSESSED — VERIFY PROGRAM GATES",
            "DECISION — Entry score (/100)": None,
            "DECISION — Exit risk score (/100)": None,
            "DECISION — Hard stop / invalidation": "NOT PLANNED — NO POSITION ASSUMED",
            "DECISION — Profit objective": "NOT PLANNED — NO TARGET ASSUMED",
            "DECISION — Catalyst exit rule": (
                f"REFERENCE ONLY: {(event - timedelta(days=3)).isoformat()}"
                if event else "UNVERIFIED — PDUFA DATE NEEDED"),
        }
        row = {
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
        }
        row.update(evidence)
        row.update({f"TARGET — {field}": target for field, target in TARGETS.items()})
        output.append(row)
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
    # Keep the main overview compact.  Detailed actual-vs-target measurements
    # appear as a vertical data sheet for one exact program below.
    overview = ["Pipeline ID", "Ticker", "Drug", "Current stage",
                "Market cap $", "TARGET — Market cap $", "Market-cap gate",
                "WT decision label", "Priority 1 — Price base / support / resistance",
                "TARGET — Priority 1 — Price base / support / resistance",
                "RVOL", "TARGET — RVOL",
                "Priority 8 — PDUFA / catalyst",
                "TARGET — Priority 8 — PDUFA / catalyst"]
    st.dataframe(pd.DataFrame(filtered, columns=overview), use_container_width=True,
                 hide_index=True, height=350)
    if filtered:
        # Bound the per-program selector to keep Streamlit responsive on the
        # full universe.  A ticker/program search narrows the available rows.
        choices = filtered[:250]
        if len(filtered) > len(choices):
            st.caption("Showing the first 250 programs in the detail selector. "
                       "Use the ticker / program search above for others.")
        selected_by_id = {row["Pipeline ID"]: row for row in choices}
        def label_for(identifier):
            candidate = selected_by_id[identifier]
            return (f'{candidate["Ticker"]} · {candidate["Drug"]} · '
                    f'{candidate["Current stage"]} · {identifier}')

        selected_id = st.selectbox(
            "VIEW ALL INDICATORS + TARGET LEVELS FOR ONE PROGRAM",
            list(selected_by_id),
            format_func=label_for, key="chart_sheet_program",
        )
        selected_row = selected_by_id[selected_id]
        detail = []
        for field in SOURCE_COLUMNS:
            if field not in TARGETS:
                continue
            group = (field.split(" — ", 1)[0]
                     if field.startswith(("CLINICAL — ", "FINANCIAL — ",
                                          "PARTICIPATION — ", "DECISION — "))
                     else "TECHNICAL CHART" if field.startswith(("Priority ",
                         "Base ", "RVOL", "SMA", "Stop ", "Target ", "Reward "))
                     else "ELIGIBILITY / CHART")
            detail.append({
                "Category": group,
                "Indicator": field,
                "Current / source observation": selected_row.get(field),
                "Target / acceptable level": selected_row[f"TARGET — {field}"],
            })
        st.dataframe(pd.DataFrame(detail), use_container_width=True,
                     hide_index=True, height=570)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(filtered)
    st.download_button(
        "DOWNLOAD FILTERED CHART INDICATOR SHEET (CSV)",
        data=output.getvalue(), file_name=f"pdufa_chart_indicator_sheet_{as_of.isoformat()}.csv",
        mime="text/csv", key="chart_indicator_sheet_export")
    st.caption(
        "Targets marked PROJECT / GEM GATE are policy requirements; ILLUSTRATIVE, "
        "PREFERENCE and OPTIONAL targets are NOT validated trading thresholds. "
        "A missing source cannot be counted as a pass. "
        "This is a snapshot of saved data and browser-local W/T selections. "
        "ATR, VWAP, XBI strength, stops and targets stay unavailable until "
        "their actual inputs exist. No broker orders are placed."
    )
