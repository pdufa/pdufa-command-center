"""Candidate-by-candidate three-level Pipeline-identified GEM JR / GEM cards.

Level 1: exact Pipeline trial identity with independent visible W and T buttons.
Level 2: actual qualification observations/benchmarks (never invented scores).
Level 3: dated primary clinical/SEC/FDA evidence and outstanding gaps.

W/T controls are per displayed program, backed by the shared ticker-level browser
selection. Multiple trials from one company share the ticker toggle; clinical,
financing and qualification observations never share evidence by ticker alone.
"""
from __future__ import annotations

import hashlib
import math
import pandas as pd
import streamlit as st
from ticker_toggle_panel import _toggle, clean_ticker


PAGE_SIZE = 12


def _value(row, *names):
    for name in names:
        v = row.get(name)
        if v is None:
            continue
        if isinstance(v, float) and not math.isfinite(v):
            continue
        text = str(v).strip()
        if text and text.lower() not in {"nan", "none", "nat", "<na>"}:
            return text
    return "NOT VERIFIED / NOT AVAILABLE"


def trial_card_rows(records):
    """Retain distinct Pipeline trials, refuse ambiguous source identities."""
    result, seen = [], set()
    for record in records:
        if not isinstance(record, dict):
            continue
        pid = _value(record, "Pipeline ID")
        ticker = clean_ticker(record.get("Ticker"))
        if pid == "NOT VERIFIED / NOT AVAILABLE" or not ticker:
            continue
        key = (pid, ticker)
        if key in seen:
            continue
        seen.add(key)
        result.append(record)
    return result


def _benchmark_rows(record, *, junior):
    if junior:
        return [
            {"Monitored item": "Phase 3 readout / result",
             "Observed": _value(record, "Phase 3 status", "Evidence type"),
             "Source": _value(record, "Clinical source", "Phase 3 source")},
            {"Monitored item": "First financing close",
             "Observed": _value(record, "First close", "Financing close #1"),
             "Source": _value(record, "First SEC source")},
            {"Monitored item": "Second financing close",
             "Observed": _value(record, "Second close", "Financing close #2",
                                "SEC documents rechecked"),
             "Source": _value(record, "Financing SEC source", "Second SEC source")},
            {"Monitored item": "GEM promotion status",
             "Observed": "AWAITING TWO VERIFIED BENCHMARKS",
             "Source": _value(record, "Still needed")},
        ]
    return [
        {"Monitored item": "1. Successful Phase 3 results",
         "Observed": _value(record, "Phase 3 status", "Two-benchmark status"),
         "Source": _value(record, "Phase 3 source", "Clinical source")},
        {"Monitored item": "2. Second post-readout financing closed",
         "Observed": _value(record, "Second close", "Financing close #2"),
         "Source": _value(record, "Second SEC source", "Financing SEC source")},
        {"Monitored item": "First financing (separate deal)",
         "Observed": _value(record, "First close", "Financing close #1"),
         "Source": _value(record, "First SEC source")},
        {"Monitored item": "Qualification (not trade approval)",
         "Observed": _value(record, "Two-benchmark status"),
         "Source": _value(record, "Source review as of")},
    ]


def _source_rows(r):
    return [
        {"Evidence item": "Pipeline program ID", "Saved value": _value(r, "Pipeline ID"),
         "Source / link": "Canonical Pipeline", "Date": _value(r, "Date Found")},
        {"Evidence item": "Clinical trial ID", "Saved value": _value(r, "NCT ID"),
         "Source / link": _value(r, "Clinical source", "Phase 3 source"),
         "Date": _value(r, "Phase 3 date", "Phase 3 readout date")},
        {"Evidence item": "Phase 3 result evidence",
         "Saved value": _value(r, "Evidence type", "Phase 3 status"),
         "Source / link": _value(r, "Clinical source", "Phase 3 source"),
         "Date": _value(r, "Source review date", "Phase 3 date")},
        {"Evidence item": "Financing #1",
         "Saved value": _value(r, "First close", "Financing close #1"),
         "Source / link": _value(r, "First SEC source"),
         "Date": _value(r, "First close", "Financing close #1")},
        {"Evidence item": "Financing #2",
         "Saved value": _value(r, "Second close", "Financing close #2"),
         "Source / link": _value(r, "Financing SEC source", "Second SEC source"),
         "Date": _value(r, "Second close", "Financing close #2")},
        {"Evidence item": "PDUFA date",
         "Saved value": _value(r, "PDUFA saved", "PDUFA date (saved)"),
         "Source / link": _value(r, "PDUFA source"), "Date": ""},
        {"Evidence item": "Missing evidence / action",
         "Saved value": _value(r, "Still needed", "Missing evidence / next actions"),
         "Source / link": "", "Date": ""},
        {"Evidence item": "GEM JR / GEM observed first",
         "Saved value": _value(r, "Date Found"),
         "Source / link": "Persistent stage membership ledger", "Date": ""},
        {"Evidence item": "Last stage departure",
         "Saved value": str(r.get("Date Left") or "CURRENT / NOT RECORDED"),
         "Source / link": _value(r, "Leave Reason"), "Date": ""},
    ]


def render_trial_hierarchy(records, *, namespace, title):
    """Each exact Pipeline program has its own visible W/T and 3-level evidence."""
    st.markdown("#### " + title + " — THREE-LEVEL TRIAL TABLE")
    st.caption(
        "Level 1 TRIAL / COMPANY → Level 2 BENCHMARKS OR RESEARCH RESULTS "
        "→ Level 3 EXACT SEC / CLINICAL / FDA SOURCES. "
        "W and T are separate buttons on EACH trial row, but the saved "
        "Watch/Trading selection is ticker-wide in this browser; "
        "no order is placed and no GEM eligibility is granted."
    )
    rows = trial_card_rows(records)
    if not rows:
        st.info("No active Pipeline-linked trial evidence for this stage.")
        return
    n_pages = max(1, math.ceil(len(rows) / PAGE_SIZE))
    if n_pages > 1:
        page = st.selectbox(
            "Trial card page", range(1, n_pages + 1),
            format_func=lambda x: f"Page {x} of {n_pages}",
            key=namespace + "_hierarchy_page")
    else:
        page = 1
    start = (page - 1) * PAGE_SIZE
    visible = rows[start:start + PAGE_SIZE]
    st.caption(f"Showing {start + 1}–{start + len(visible)} of {len(rows)} individual programs")
    watch = {clean_ticker(v) for v in st.session_state.get("watchlist", [])}
    trade = {clean_ticker(v) for v in st.session_state.get("trading_tickers", [])}
    junior = title.strip().upper() == "GEM JR"
    for r in visible:
        ticker = clean_ticker(r.get("Ticker"))
        pid = _value(r, "Pipeline ID")
        uid = hashlib.sha256((namespace + "|" + pid).encode("utf-8")).hexdigest()[:16]
        with st.container(border=True, key=namespace + "_program_" + uid):
            label, w, t = st.columns([6, 0.8, 0.8], gap="small", vertical_alignment="center")
            with label:
                st.markdown("**" + ticker + " · " + _value(r, "Drug") +
                            " · " + _value(r, "Indication") + "**")
                st.caption("PIPELINE ID " + pid + " · NCT " +
                           _value(r, "NCT ID") + " · FOUND " +
                           _value(r, "Date Found") +
                           " · PDUFA " + _value(r, "PDUFA saved", "PDUFA date (saved)"))
            with w:
                st.button("W", key=namespace + "_watch_" + uid,
                          type="primary" if ticker in watch else "secondary",
                          help="Toggle Watchlist for " + ticker +
                               " (shared by all trials with this ticker)",
                          on_click=_toggle, args=(ticker, "watch"))
            with t:
                st.button("T", key=namespace + "_trade_" + uid,
                          type="primary" if ticker in trade else "secondary",
                          help="Toggle Trading Research for " + ticker +
                               " (ticker-wide; not a broker order)",
                          on_click=_toggle, args=(ticker, "trade"))
            with st.expander("OPEN THREE LEVELS — ACTUAL CANDIDATE EVIDENCE",
                             expanded=False):
                st.markdown("**LEVEL 1 — EXACT PROGRAM & LIST STATUS**")
                st.dataframe(pd.DataFrame([{
                    "Pipeline ID": pid, "Ticker": ticker,
                    "Drug": _value(r, "Drug"),
                    "Indication": _value(r, "Indication"),
                    "Trial ID": _value(r, "NCT ID"),
                    "Date found": _value(r, "Date Found"),
                    "Date left": str(r.get("Date Left") or "ACTIVE / NOT RECORDED"),
                    "Current status": _value(r, "GEM status",
                                             "Two-benchmark status", "Listing status"),
                }]), hide_index=True, use_container_width=True)
                st.markdown("**LEVEL 2 — WHAT THIS CANDIDATE RECEIVED / VERIFIED**")
                st.dataframe(pd.DataFrame(_benchmark_rows(r, junior=junior)),
                             hide_index=True, use_container_width=True)
                st.markdown("**LEVEL 3 — UNDERLYING EVIDENCE, DATES & NEXT ACTIONS**")
                st.dataframe(pd.DataFrame(_source_rows(r)), hide_index=True,
                             use_container_width=True)
                if not junior:
                    st.caption("Actual six-factor GEM /100 calculations and "
                               "source input breakdowns remain in the full "
                               "GEM THREE-LEVEL VERIFIED MASTER below.")
