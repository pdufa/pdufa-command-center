"""Streamlit surface for Stage 1 post-Phase-3 discovery and eligibility."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from post_phase3_unified import COLUMNS, build_queue
from post_phase3_lifecycle_ui import render_post_phase3_positions


@st.cache_data(ttl=120, show_spinner=False)
def _queue(root, signature, as_of_date):
    # Signature guards file updates; Pacific date prevents yesterday's feed
    # from being treated as current after midnight.
    return build_queue(root, as_of_date)


def render_post_phase3_stage1(root="data"):
    path = Path(root)
    filenames = (
        "step7_live_status.json", "step7_financing_review.csv",
        "step7_pre_phase3_feed.csv", "pdufa_candidates.csv",
        "post_phase3_discoveries.csv",
        "second_financing_status.csv",
    )
    signature = tuple(
        (name, (path / name).stat().st_mtime_ns if (path / name).exists() else 0)
        for name in filenames
    )
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    try:
        items, status = _queue(str(path), signature, today)
    except (OSError, ValueError, TypeError, KeyError, pd.errors.ParserError):
        st.error("Unified Stage 1 source load failed. No candidates have been cleared.")
        return

    st.markdown("### STAGE 1 — PHASE 3 → FINANCING #2 → GREEN ENTRY")
    st.caption(
        "Combined saved regulatory events, result-posted Phase 3 trial leads and "
        "independently sourced research leads. Exact event financing joins only. "
        "Research leads do NOT demonstrate successful Phase 3 or closed financing."
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Candidate records", status["count"])
    m2.metric("GREEN — attested gates", status["green_count"])
    m3.metric("Need source review", status["review_count"])
    m4.metric("Research leads", status["research_leads"])
    st.caption(
        f"Saved source date (Pacific): {status['as_of']} · "
        f"Financing review rows: {status['financing_events']} · "
        f"Saved clinical-trial records scanned: {status['saved_trial_rows']}. "
        "No purchase order or position is created by this page."
    )
    if not status["feed_current"]:
        st.warning(
            "DAILY SNAPSHOT EXPIRED — clinical and financing rows remain visible "
            "for research, but NONE can become GREEN until refreshed."
        )
    if status["green_count"] == 0:
        st.info(
            "NO ENTRY-READY CANDIDATES. Missing clinical, financing, "
            "dilution, market, or PDUFA evidence must be verified first. "
            "SEC access failures do not become passing gates."
        )

    if not items:
        st.warning("No valid Stage 1 rows loaded; check the saved feeds.")
        return
    df = pd.DataFrame(items).reindex(columns=COLUMNS)
    left, right = st.columns([1, 2])
    with left:
        selector = st.selectbox(
            "Candidate view",
            ["Active research", "All including exited/resolved",
             "GREEN only", "Financing event records", "New clinical readouts"],
            key="postphase3_stage1_view",
        )
    with right:
        query = st.text_input(
            "Find ticker, drug, indication or NCT",
            key="postphase3_stage1_search",
            placeholder="e.g., NCT or ticker",
        ).strip()
    if selector == "Active research":
        df = df.loc[~df["Entry qualification"].str.startswith("EXCLUDED")]
    elif selector == "GREEN only":
        df = df.loc[df["Entry qualification"].str.startswith("GREEN")]
    elif selector == "Financing event records":
        df = df.loc[df["Exact event"].ne("")]
    elif selector == "New clinical readouts":
        df = df.loc[df["Source lane"].ne("SAVED REGULATORY PIPELINE")]
    if query:
        mask = (
            df[["Ticker", "Drug", "Indication", "NCT ID"]]
            .fillna("").astype(str)
            .apply(lambda c: c.str.contains(query, case=False, regex=False))
            .any(axis=1)
        )
        df = df.loc[mask]
    st.caption(
        f"{len(df)} candidates match. RED WINDOW means do not start a new trade "
        "inside the final seven calendar days; it is not an executed sale. "
        "YELLOW running and RED position-exit tracking will use an actual trade journal in Stage 2."
    )
    st.dataframe(
        df.head(250), use_container_width=True, hide_index=True,
        column_config={
            "Registry source": st.column_config.LinkColumn("Registry source"),
            "Phase 3 source": st.column_config.LinkColumn("Phase 3 source"),
            "Financing source": st.column_config.LinkColumn("Financing source"),
            "PDUFA source": st.column_config.LinkColumn("PDUFA source"),
        },
    )
    if len(df) > 250:
        st.caption("Showing first 250 rows for responsiveness. CSV includes every filtered row.")
    st.download_button(
        "EXPORT UNIFIED POST PHASE 3 RESEARCH QUEUE",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"post_phase3_trade_research_{today:%Y%m%d}.csv",
        mime="text/csv",
        key="postphase3_stage1_csv",
    )
    st.caption(
        "GREEN means all saved attested gates plus source-linked Phase 3 success and "
        "verified PDUFA date pass. It is research eligibility—not an independently "
        "audited conclusion, investment recommendation or position status."
    )
    render_post_phase3_positions(items, root)
