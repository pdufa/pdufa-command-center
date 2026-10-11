"""Streamlit surface for Stage 1 post-Phase-3 discovery and eligibility."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from post_phase3_unified import COLUMNS, build_queue
from pdufa_display_columns import prepare_pdufa_grid, finance_style
from post_phase3_lifecycle_ui import render_post_phase3_positions


@st.cache_data(ttl=120, show_spinner=False)
def _queue(root, signature, as_of_date):
    # Signature guards file updates; Pacific date prevents yesterday's feed
    # from being treated as current after midnight.
    return build_queue(root, as_of_date)


def render_post_phase3_stage1(root="data", include_positions=True):
    path = Path(root)
    filenames = (
        "step7_live_status.json", "step7_financing_review.csv",
        "step7_pre_phase3_feed.csv", "pdufa_candidates.csv",
        "post_phase3_discoveries.csv",
        "second_financing_status.csv", "step7_market_status.csv",
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
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Candidate records", status["count"])
    m2.metric("Saved trial records", status["saved_trial_rows"])
    m3.metric("GREEN — attested gates", status["green_count"])
    m4.metric("Need source review", status["review_count"])
    m5.metric("Research leads", status["research_leads"])
    st.caption(
        f"Saved source date (Pacific): {status['as_of']} · "
        f"Financing review rows: {status['financing_events']} · "
        f"Saved clinical-trial records scanned: {status['saved_trial_rows']}. "
        "No purchase order or position is created by this page."
    )
    # Identify the actual outstanding SEC verification gap without claiming
    # the saved reference financing history has been rechecked today.
    sec_health = None
    try:
        import json
        health = json.loads((path / "step7_live_status.json").read_text(encoding="utf-8"))
        sec_health = next((item for item in health.get("source_checks", [])
                           if item.get("Source") == "SEC financing recheck"), None)
    except (OSError, ValueError, TypeError):
        pass
    if sec_health and (sec_health.get("Health") == "BLOCKED / PARTIAL" or
                       sec_health.get("Freshness") == "STALE"):
        st.warning(
            f"SEC FINANCING RECHECK IS {sec_health.get('Health', 'PARTIAL')} "
            f"({sec_health.get('Blocked records', 0)} blocked records; "
            f"last check {sec_health.get('Last checked UTC', 'unknown')}). "
            "Historical financing references are NOT current clearance. "
            "Run the compliant SEC audit only when GitHub's SEC_USER_AGENT secret "
            "and source access are configured. Do not override the entry gates."
        )
        st.link_button(
            "CHECK SEC AUDIT WORKFLOW",
            "https://github.com/pdufa/pdufa-command-center/actions/workflows/first10-financing-audit.yml",
            key="postphase3_sec_audit_link",
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
    st.caption(
        "One combined candidate table: exact trial and program identity, eligibility "
        "(GREEN / REVIEW / RED), financing milestones, PDUFA timing, and source-linked "
        "clinical and trading evidence scores. No ordinal ranks or Top 10 list."
    )
    left, middle, right = st.columns([1.1, 1.4, 2])
    with left:
        selector = st.selectbox(
            "Candidate view",
            ["Active research", "All including exited/resolved",
             "GREEN only", "Financing event records", "New clinical readouts"],
            key="postphase3_stage1_view",
        )
    with middle:
        sorting = st.selectbox(
            "Display order (not a ranking)",
            ["Ticker A–Z", "Soonest PDUFA", "Clinical stage / eligibility"],
            key="postphase3_stage1_sort",
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
    # Preserve scores for evidence assessment, but do not rank programs.
    df = df.copy()
    df["_pdufa_sort"] = pd.to_numeric(df["Days to PDUFA"], errors="coerce").fillna(99999)
    if sorting == "Soonest PDUFA":
        df = df.sort_values(["_pdufa_sort", "Ticker", "NCT ID"],
                            ascending=[True, True, True], kind="stable")
    elif sorting == "Clinical stage / eligibility":
        df = df.sort_values(["Entry qualification", "Ticker", "NCT ID"],
                            kind="stable")
    else:
        df = df.sort_values(["Ticker", "NCT ID"], kind="stable")
    df = df.drop(columns=["_pdufa_sort", "Research rank", "Evidence rank"],
                 errors="ignore")
    st.caption(
        f"{len(df)} candidates match. RED WINDOW means do not start a new trade "
        "inside the final seven calendar days; it is not an executed sale. "
        "The separate Stage 2 panel below evaluates only positions you report."
    )
    st.markdown("#### ALL CANDIDATES — STATUS + SCORES + EVIDENCE GAPS")
    display_df = prepare_pdufa_grid(df, view="POST PHASE 3", as_of=today)
    st.dataframe(
        finance_style(display_df.head(250)), use_container_width=True, hide_index=True,
        column_config={
            "Research priority /100": st.column_config.NumberColumn("Research priority /100", format="%d"),
            "Evidence score /100": st.column_config.NumberColumn("Evidence /100", format="%d"),
            "Clinical evidence /30": st.column_config.NumberColumn("Clinical /30", format="%d"),
            "Financing evidence /20": st.column_config.NumberColumn("Financing /20", format="%d"),
            "Trading setup /20": st.column_config.NumberColumn("Setup /20", format="%d"),
            "PDUFA evidence /15": st.column_config.NumberColumn("PDUFA /15", format="%d"),
            "Market activity /10": st.column_config.NumberColumn("Market /10", format="%d"),
            "Company track record /5": st.column_config.NumberColumn("History /5", format="%d"),
            "Registry source": st.column_config.LinkColumn("Registry source"),
            "Phase 3 source": st.column_config.LinkColumn("Phase 3 source"),
            "Financing source": st.column_config.LinkColumn("Financing source"),
            "PDUFA source": st.column_config.LinkColumn("PDUFA source"),
            "F": st.column_config.TextColumn("F", width="small"),
        },
    )
    if len(df) > 250:
        st.caption("Showing first 250 rows for responsiveness. CSV includes every filtered row.")
    st.download_button(
        "EXPORT UNIFIED POST PHASE 3 RESEARCH QUEUE",
        display_df.to_csv(index=False).encode("utf-8"),
        file_name=f"post_phase3_trade_research_{today:%Y%m%d}.csv",
        mime="text/csv",
        key="postphase3_stage1_csv",
    )
    st.caption(
        "Evidence points reward source-supported, attested requirements; 5 points "
        "for company history remain unavailable pending a sourced audit. "
        "Market points reflect recent price, volume and momentum; short interest/float "
        "are NOT independently scored yet. Partial points do not authorize trading."
    )
    st.caption(
        "GREEN means all saved attested gates plus source-linked Phase 3 success and "
        "verified PDUFA date pass. It is research eligibility—not an independently "
        "audited conclusion, investment recommendation or position status."
    )
    if include_positions:
        render_post_phase3_positions(items, root)
