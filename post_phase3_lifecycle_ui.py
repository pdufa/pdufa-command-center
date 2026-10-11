"""Streamlit Stage 2 read-only position-monitoring UI.

User journal stays in the current Streamlit session only. Do NOT put private
position data in this repository or pretend a CSV upload executes trades.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from pdufa_table_headers import pdufa_dataframe

from post_phase3_lifecycle import (
    DISPLAY_FIELDS, monitor_positions, parse_journal, template_csv,
)
from post_phase3_unified import read_rows

PACIFIC = ZoneInfo("America/Los_Angeles")


def render_post_phase3_positions(candidates, root="data", ticker=None):
    root = Path(root)
    today = datetime.now(PACIFIC).date()
    st.markdown("### STAGE 2 — GREEN ENTRY → YELLOW HOLD → RED EXIT WATCH")
    st.caption(
        "Trading lifecycle (distinct from FINANCING CYCLE): GREEN means entry "
        "gates attested; YELLOW monitors a USER-REPORTED open position; RED "
        "requires an exit or shows one you recorded. No brokerage connection, "
        "no order placement, and no claim a scheduled exit has executed."
    )
    st.download_button(
        "DOWNLOAD BLANK POSITION JOURNAL CSV",
        template_csv(), file_name="post_phase3_position_journal_template.csv",
        mime="text/csv", key="phase3_journal_template_v1",
    )
    uploaded = st.file_uploader(
        "LOAD YOUR POSITION JOURNAL CSV — in-session monitoring only",
        type=["csv"], key="phase3_position_journal_upload_v1",
        help="This upload is only processed in this Streamlit session. Do not add a private portfolio to the public GitHub repository.",
    )
    if uploaded is None:
        st.info(
            "No actual positions have been supplied. GREEN research candidates "
            "are not assumed to be owned; YELLOW and RED position statuses "
            "remain empty until you upload a filled trade journal."
        )
        return

    try:
        journal = parse_journal(uploaded.getvalue())
    except ValueError as exc:
        st.error(f"Journal rejected: {exc}")
        return
    if not journal:
        st.info("Blank journal received — no reported open or exited trades.")
        return
    try:
        results, counts = monitor_positions(
            journal, candidates,
            read_rows(root / "step7_market_status.csv"), today,
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        st.error(f"Could not evaluate journal; positions remain unverified ({type(exc).__name__}).")
        return

    a, b, c, d = st.columns(4)
    a.metric("User-reported trades", counts["total"])
    b.metric("YELLOW — open", counts["open"])
    c.metric("RED — attention", counts["due"])
    d.metric("RED — exits recorded", counts["recorded_exits"])
    if counts["review"]:
        st.warning(
            f"{counts['review']} journal rows need identification or PDUFA source review. "
            "They are not labeled as confirmed holdings or compliant entries."
        )
    if counts["due"]:
        st.error(
            "RED ACTION REQUIRED: the cutoff has been reached or the recorded "
            "FDA event needs urgent review. This app cannot sell shares. "
            "Confirm actual execution directly with your broker."
        )
    st.caption(
        "Entry/exit fills are YOUR CSV reports, not brokerage verified. EOD marks "
        "are displayed only for source-dated recent quotes and do not include "
        "fees, spreads or intraday changes. A historical GREEN at entry cannot "
        "be verified from today's eligibility alone."
    )
    frame = pd.DataFrame(results).reindex(columns=DISPLAY_FIELDS)
    if ticker:
        frame = frame.loc[
            frame["Ticker"].fillna("").astype(str).str.strip().str.upper().eq(ticker)
        ]
        st.caption(
            f"Table focus: {ticker}. Portfolio totals and exit alerts above still "
            "cover every reported position in your journal."
        )
    filter_choice = st.selectbox(
        "Position monitor view",
        ["All positions", "Action required (RED or REVIEW)", "Open YELLOW", "Exited"],
        key="phase3_journal_view_v1",
    )
    if filter_choice == "Action required (RED or REVIEW)":
        frame = frame.loc[
            frame["Trade lifecycle"].str.startswith("REVIEW") |
            (frame["Trade lifecycle"].str.startswith("RED") &
             ~frame["Trade lifecycle"].str.contains("EXIT RECORDED"))
        ]
    elif filter_choice == "Open YELLOW":
        frame = frame.loc[frame["Trade lifecycle"].str.startswith("YELLOW")]
    elif filter_choice == "Exited":
        frame = frame.loc[frame["Trade lifecycle"].str.contains("EXIT RECORDED")]
    pdufa_dataframe(
        frame, use_container_width=True, hide_index=True,
        column_config={"Market quote source": st.column_config.LinkColumn("Market quote source")},
    )
    st.download_button(
        "EXPORT POSITION MONITOR SNAPSHOT",
        frame.to_csv(index=False).encode("utf-8"),
        file_name=f"post_phase3_position_watch_{today:%Y%m%d}.csv",
        mime="text/csv", key="phase3_journal_snapshot_v1",
    )
    st.caption(
        "The export contains the user-uploaded position details. Keep it private. "
        "Closing this session may clear the journal; no automated private portfolio "
        "sync or notifications are connected yet."
    )
