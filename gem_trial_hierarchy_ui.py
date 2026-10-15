"""Shared three-level clinical trial drill-down for GEM JR and GEM.

Display only existing saved evidence; do not infer a trial result or eligibility.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st


def _value(row, *names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip() and str(value).lower() != "nan":
            return str(value).strip()
    return "NOT AVAILABLE"


def render_trial_hierarchy(records, *, namespace, title):
    """Level 1 ticker -> Level 2 drug/indication -> Level 3 exact trial evidence."""
    st.markdown("#### " + title + " — THREE-LEVEL TRIAL TABLE")
    st.caption("Level 1 COMPANY → Level 2 DRUG / INDICATION → Level 3 TRIAL / SOURCE EVIDENCE. "
               "Missing results or documents are shown as NOT AVAILABLE, never assumed verified.")
    rows = [dict(record) for record in records if isinstance(record, dict)]
    if not rows:
        st.info("No saved clinical trial evidence for this block.")
        return

    ticker_map = {}
    for row in rows:
        ticker = _value(row, "Ticker")
        ticker_map.setdefault(ticker, []).append(row)
    ticker = st.selectbox("LEVEL 1 — COMPANY / TICKER", sorted(ticker_map),
                          key=namespace + "_trial_company")

    program_map = {}
    for row in ticker_map[ticker]:
        key = (_value(row, "Drug"), _value(row, "Indication"))
        program_map.setdefault(key, []).append(row)
    programs = sorted(program_map)
    program = st.selectbox(
        "LEVEL 2 — DRUG / INDICATION", programs,
        format_func=lambda item: " · ".join(item),
        key=namespace + "_trial_program",
    )
    selected = program_map[program]
    st.markdown("**LEVEL 3 — EXACT TRIALS AND VERIFIED EVIDENCE**")
    output = []
    for row in selected:
        output.append({
            "Trial ID": _value(row, "NCT ID", "Trial ID"),
            "Exact program": _value(row, "Exact program"),
            "Pipeline ID": _value(row, "Pipeline ID"),
            "Date Found": _value(row, "Date Found"),
            "Date Left": str(row.get("Date Left") or "CURRENT / NOT EXITED"),
            "Date Re-entered": str(row.get("Date Re-entered") or ""),
            "Listing status": _value(row, "Listing status"),
            "Leave Reason": str(row.get("Leave Reason") or ""),
            "Evidence / status": _value(row, "Evidence type", "GEM status", "Review status"),
            "Phase 3 readout": _value(row, "Phase 3 date", "Phase 3 readout date"),
            "Clinical source": _value(row, "Clinical source", "Phase 3 source", "Primary clinical source"),
            "Financing SEC source": _value(row, "Financing SEC source", "Second SEC source"),
            "First financing close": _value(row, "First close", "Financing close #1"),
            "Second financing close": _value(row, "Second close", "Financing close #2"),
            "PDUFA date": _value(row, "PDUFA saved", "PDUFA date (saved)", "PDUFA (saved)"),
            "Evidence gaps": _value(row, "Still needed", "Missing evidence / next actions"),
        })
    st.dataframe(pd.DataFrame(output), hide_index=True, use_container_width=True,
                 column_config={
                     "Clinical source": st.column_config.LinkColumn("Clinical source"),
                     "Financing SEC source": st.column_config.LinkColumn("Financing SEC source"),
                 })
    st.caption(f"{len(selected)} saved exact-program record(s) for {ticker} / {program[0]}. "
               "Clinical trials remain research evidence; no automatic promotion or trades.")
