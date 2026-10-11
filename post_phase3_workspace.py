"""Single POST PHASE 3 workspace for qualification, positions and backtesting.

Uses only previously installed audited engines and saved CSVs. No stock
orders or implicit financing/corporate evidence certification.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from post_phase3_unified_ui import render_post_phase3_stage1
from post_phase3_unified import build_queue, read_rows
from post_phase3_lifecycle_ui import render_post_phase3_positions
from post_phase3_backfill_queue import build_backfill_queue
from post_phase3_trade_backtest import (
    ENTRY_METHODS, EXIT_DAYS, SUMMARY_FIELDS, day, paired_comparison,
    run_backtest,
)

ROOT = Path(__file__).resolve().parent
PACIFIC = ZoneInfo("America/Los_Angeles")
STAGES = (
    "1 · Discover & qualify",
    "2 · Monitor & exit",
    "3 · Historical backtest",
)


@st.cache_data(ttl=120, show_spinner=False)
def _research_backtest(signature):
    """Hash of file metadata invalidates cached audited evidence preview."""
    root = ROOT / "data"
    events = read_rows(root / "post_phase3_historical_trade_events.csv")
    bars = read_rows(root / "post_phase3_historical_adjusted_ohlcv.csv")
    queue, queue_meta = build_backfill_queue(root)
    scenarios, summary, audit = run_backtest(events, bars)
    matched = paired_comparison(scenarios)
    return queue, queue_meta, scenarios, summary, matched, audit


def _stage3():
    st.markdown("### STAGE 3 — HISTORICAL ENTRY / EXIT RESEARCH")
    st.caption(
        "Four entry methods × exits 30, 14, or 7 calendar days before PDUFA. "
        "Only historically source-verified events and split-adjusted daily prices "
        "can generate simulated returns. No FDA approval-prediction score is "
        "misrepresented as a stock-return backtest."
    )
    root = ROOT / "data"
    files = ("post_phase3_historical_trade_events.csv",
             "post_phase3_historical_adjusted_ohlcv.csv",
             "pdufa_candidates.csv", "second_financing_status.csv",
             "company_registry.csv")
    signature = tuple(
        (name, (root / name).stat().st_mtime_ns if (root / name).exists() else -1)
        for name in files
    )
    try:
        queue, meta, scenarios, summary, matched, audit = _research_backtest(signature)
    except (ValueError, KeyError, TypeError, OSError, ZeroDivisionError):
        st.error("Historical evidence audit failed. No trading returns have been verified.")
        return

    a, b, c, d = st.columns(4)
    a.metric("Historical research leads", len(queue))
    b.metric("Verified event timelines", audit["event_rows"])
    c.metric("Historical OHLCV rows", audit["price_rows"])
    d.metric("Simulated trade scenarios", audit["completed_scenarios"])
    if not audit["completed_scenarios"]:
        st.warning(
            "BACKTEST NOT READY — there are no source-verified historical trades. "
            "The saved current PDUFA/financing ledgers are research references only; "
            "they must not produce a hypothetical win rate."
        )
    elif audit["completed_scenarios"] < 30:
        st.warning(
            "EXPLORATORY SAMPLE — too few scenarios for a reliable comparison. "
            "Early FDA decisions, missing prices and survivor selection remain risks."
        )
    st.caption(
        "Stage 3 compares readout and first-financing benchmarks only "
        "conditionally on later financing completion. They are NOT eligible "
        "entry signals for your post-second-financing strategy."
    )

    st.markdown("#### Historical entry/exit comparison")
    view = st.radio(
        "Research output",
        ["Scenario summary", "Matched-program comparison", "Evidence gaps"],
        key="post_phase3_research_output_v1",
        horizontal=True,
    )
    if view == "Scenario summary":
        df = pd.DataFrame(summary).reindex(columns=SUMMARY_FIELDS)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "EXPORT SCENARIO SUMMARY",
            df.to_csv(index=False).encode("utf-8"),
            file_name="post_phase3_scenario_summary.csv",
            mime="text/csv", key="post_phase3_stage3_summary_export",
        )
    elif view == "Matched-program comparison":
        df = pd.DataFrame(matched)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("Only identical verified programs appear in the matched-method comparison.")
    else:
        st.caption(
            "Grouped by exact program identity and retrospective financing "
            "references. None of these rows is cleared for historical trading simulation."
        )
        columns = (
            "ticker", "drug", "nct_id", "pdufa_date_reference",
            "financing_audit_status_reference", "missing_historical_requirements",
            "next_research_step",
        )
        df = pd.DataFrame(queue).reindex(columns=columns)
        st.dataframe(df, use_container_width=True, hide_index=True, height=380)
    queue_frame = pd.DataFrame(queue)
    st.download_button(
        "EXPORT ALL HISTORICAL EVIDENCE RESEARCH ITEMS",
        queue_frame.to_csv(index=False).encode("utf-8"),
        file_name="post_phase3_historical_source_backfill_queue.csv",
        mime="text/csv", key="post_phase3_stage3_queue_export",
        disabled=queue_frame.empty,
    )
    with st.expander("Historical data templates & methodology"):
        for path, label in (
            ("post_phase3_historical_trade_events.csv", "Event and public-disclosure dates"),
            ("post_phase3_historical_adjusted_ohlcv.csv", "Split-adjusted daily OHLCV"),
        ):
            file = root / path
            if file.exists():
                st.download_button(
                    "DOWNLOAD TEMPLATE — " + label,
                    file.read_bytes(), file_name=path, mime="text/csv",
                    key="postphase3_template_" + path,
                )
        st.caption(
            "Entries use next-session open after verified public evidence; exits use "
            "last close before the respective PDUFA cutoff. Slippage, liquidity, "
            "issuer-specific financing, early FDA actions, and missing-session "
            "fail-closed rules are checked. No brokerage transactions are created."
        )
    st.link_button(
        "OPEN GITHUB BACKTEST RUNS & RESEARCH ARTIFACTS",
        "https://github.com/pdufa/pdufa-command-center/actions/workflows/stage3-trade-backtest.yml",
    )


def render_post_phase3_workspace(root="data"):
    st.markdown("## POST PHASE 3 — TRADING WORKSPACE")
    st.caption(
        "One continuous workflow: verify successful Phase 3 → confirm second "
        "post-readout financing closure → clear entry gates (GREEN) → monitor "
        "reported holdings (YELLOW) → exit by PDUFA −7 days (RED). "
        "Status is evidence-based research, never a buy/sell order."
    )
    choice = st.radio(
        "Post Phase 3 stage",
        STAGES,
        horizontal=True,
        key="post_phase3_workspace_stage_v1",
    )
    if choice == STAGES[0]:
        render_post_phase3_stage1(root=root, include_positions=False)
    elif choice == STAGES[1]:
        st.caption(
            "Positions are user-reported CSV entries, not broker-confirmed. "
            "The same exact-event research queue is used as Stage 1."
        )
        try:
            candidates, status = build_queue(root)
            if not status.get("feed_current"):
                st.warning("Research evidence snapshot is stale; eligibility is unverified.")
        except (OSError, ValueError, TypeError, KeyError):
            candidates = []
            st.warning("Candidate records unavailable; reported trades cannot be matched.")
        render_post_phase3_positions(candidates, root=root)
    else:
        _stage3()
