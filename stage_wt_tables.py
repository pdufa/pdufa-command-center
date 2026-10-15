"""Stage-scoped WT watchlist and trading-research tables.

The W/T tags are ticker-level browser selections shared with the existing WT
dashboard. The *rows* are always restricted to the supplying stage records;
no GEM JR lead becomes GEM eligible because of a tag or a matching ticker.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from ticker_toggle_panel import clean_ticker, render_ticker_toggle_panel

FIELDS = (
    "Pipeline ID", "Ticker", "Drug", "Trial / Program", "Stage", "PDUFA",
    "Date Found", "Date Left", "Leave Reason", "Listing status",
    "Evidence / Qualification", "Missing / Next action",
)


def _value(row, *names):
    """Return a printable first nonempty source value without inventing facts."""
    for name in names:
        value = row.get(name)
        if value is None:
            continue
        try:
            if bool(pd.isna(value)):
                continue
        except (ValueError, TypeError):
            continue
        string = str(value).strip()
        if string and string.lower() not in {"nan", "nat", "none", "<na>"}:
            return string
    return ""


def stage_rows(records, stage):
    """Keep exact program rows from the stage, not ticker-level surrogate joins."""
    if isinstance(records, pd.DataFrame):
        source = records.to_dict("records")
    else:
        source = list(records or [])
    result, seen = [], set()
    for item in source:
        if not isinstance(item, dict):
            continue
        ticker = clean_ticker(_value(item, "Ticker", "ticker", "symbol"))
        if not ticker:
            continue
        trial = _value(item, "NCT ID", "nct_id")
        program = _value(item, "Exact program", "Exact Program / Event",
                         "record_id", "event_key", "Pipeline ID")
        drug = _value(item, "Drug", "drug")
        # A ticker can legitimately have several exact programs. Do not merge
        # their source claims or silently drop different trial identities.
        identity = (ticker, program or trial or drug,
                    _value(item, "Indication", "indication"))
        if identity in seen:
            continue
        seen.add(identity)
        result.append({
            "Pipeline ID": _value(item, "Pipeline ID", "record_id"),
            "Ticker": ticker,
            "Drug": drug,
            "Trial / Program": trial or program,
            "Stage": stage,
            "Date Found": _value(item, "Date Found"),
            "Date Left": _value(item, "Date Left"),
            "Leave Reason": _value(item, "Leave Reason"),
            "Listing status": _value(item, "Listing status"),
            "PDUFA": _value(item, "PDUFA saved", "PDUFA date (saved)",
                            "PDUFA Date", "pdufa_date", "PDUFA Target"),
            "Evidence / Qualification": (
                _value(item, "Trade status", "GEM status", "GEM Status",
                       "Evidence type", "evidence_status", "Evidence Status",
                       "current_stage", "Current Stage")
                or "NOT VERIFIED"),
            "Missing / Next action": _value(item, "Still needed",
                                           "Missing / recheck needed",
                                           "Risks / Evidence Gaps",
                                           "evidence_note", "Evidence Note"),
        })
    return result


def selected_stage_rows(records, stage, watch, trade):
    """Stage-limited W and T tables; never add stocks absent from stage input."""
    source = stage_rows(records, stage)
    watch_symbols = {t for value in watch if (t := clean_ticker(value))}
    trade_symbols = {t for value in trade if (t := clean_ticker(value))}
    return {
        "watch": [r for r in source if r["Ticker"] in watch_symbols],
        "trade": [r for r in source if r["Ticker"] in trade_symbols],
        "available_tickers": sorted({r["Ticker"] for r in source}),
    }


def render_stage_wt_tables(stage, records, *, namespace, controls=True):
    """Reuse the existing shared W/T toggles; display two scoped read-only tables."""
    key = "stage_wt_" + namespace
    with st.container(border=True, key=key):
        st.markdown("### WT — WATCHLIST & TRADING RESEARCH")
        st.caption(
            f"{stage}: only saved programs belonging to this stage. "
            "W and T are browser-saved ticker labels shared with the main WT tab, "
            "not trades, rankings, approvals, or a new pipeline record."
        )
        if controls:
            render_ticker_toggle_panel(
                namespace + "_wt", records, title="ADD / REMOVE W AND T LABELS")
        selected = selected_stage_rows(
            records, stage,
            st.session_state.get("watchlist", []),
            st.session_state.get("trading_tickers", []),
        )
        for name, label in (("watch", "WATCHLIST"),
                            ("trade", "TRADING RESEARCH — NO ORDERS")):
            entries = selected[name]
            st.markdown(f"**{label} · {len(entries):,} stage programs**")
            if entries:
                st.dataframe(
                    pd.DataFrame(entries, columns=FIELDS),
                    use_container_width=True, hide_index=True,
                    height=min(360, 38 + len(entries) * 36),
                )
            else:
                st.caption("No tagged tickers in this stage. Use W/T above or in "
                           "the main WT tab; stage membership is never inferred.")
        st.caption("One ticker may have multiple exact programs. W/T is shared "
                   "by ticker, while qualification and evidence remain per program.")
