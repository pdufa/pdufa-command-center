"""Visible readiness, execution outcomes and calibration checks for the GEMS scans.

Never apply new weights merely because an exploratory historical score won.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from gem_calibration import SNAPSHOT_FIELDS, STAGES, calibrate
from post_phase3_trade_backtest import BAR_FIELDS, read_csv

SOURCE_FILES = (
    "gem_historical_snapshots.csv",
    "post_phase3_historical_adjusted_ohlcv.csv",
)


@st.cache_data(ttl=120, show_spinner=False)
def _report(root, signature, date_today):
    base = Path(root)
    snapshots = read_csv(base / SOURCE_FILES[0])
    bars = read_csv(base / SOURCE_FILES[1])
    return calibrate(snapshots, bars, as_of=date_today)


def render_gem_calibration(root="data"):
    st.markdown("### HISTORICAL GEM CALIBRATION — PDUFA −3")
    st.caption(
        "Independent Phase 3, Post-Financing and PDUFA ranking validation. "
        "Your post-financing strategy begins after publicly verified completion "
        "of financing #2 and exits no later than 3 calendar days before PDUFA. "
        "Phase 3 is independently studied over 30 trading sessions, not "
        "presented as part of your post-financing trading window."
    )
    p = Path(root)
    signature = tuple(
        (name, (p / name).stat().st_mtime_ns if (p / name).exists() else -1)
        for name in SOURCE_FILES
    )
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    try:
        report = _report(str(p), signature, today)
    except (ValueError, TypeError, OSError, KeyError, ZeroDivisionError):
        st.error("GEM calibration audit failed. No tuned weights are authorized.")
        return
    top = st.columns(3)
    top[0].metric("Verified event snapshots", report["snapshot_rows"])
    top[1].metric("Adjusted price observations", report["price_rows"])
    top[2].metric("Valid completed trades", report["valid_completed_trades"])
    if not report["valid_completed_trades"]:
        st.warning(
            "BACKTEST NOT READY: dated historical GEM score snapshots and "
            "verified split-adjusted prices have not produced an auditable "
            "completed trade. No trading return, win rate or optimized GEM "
            "weights are inferred from current scan rows or FDA outcomes."
        )
    else:
        st.info(
            "Hypothetical trades reflect point-in-time evidence, next-session "
            "entry, PDUFA −3 exit, slippage, liquidity, and early FDA decisions. "
            "A valid backtest alone does not authorize production ranking changes."
        )
    st.caption("Audit status: " + report["status"].replace("_", " "))
    rows = []
    for stage in STAGES:
        x = report["stages"][stage]
        holdout = x["holdout"]
        rows.append({
            "GEM classification":stage,
            "Stage readiness":x["status"].replace("_", " "),
            "Verified trades":x["completed_trades"],
            "Holdout stocks":holdout["unique_tickers"],
            "Holdout win rate %":holdout["win_rate_pct"],
            "Holdout median return %":holdout["median_return_pct"],
            "Holdout median drawdown %":holdout["median_max_drawdown_pct"],
            "Holdout top-vs-bottom pp":holdout["mean_top_minus_bottom_percentage_points"],
            "Weights live": "UNCHANGED",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.link_button(
        "VIEW NIGHTLY GEM CALIBRATION AUDITS / RESEARCH QUEUE",
        "https://github.com/pdufa/pdufa-command-center/actions/workflows/pdufa-gem-calibration-audit.yml",
    )
    with st.expander("Full audit, missing inputs and methodology", expanded=False):
        st.json(report)
        st.caption(
            "Historical features must be saved with a contemporaneous public "
            "signal date, exact trial and SEC issuer identity, verified PDUFA "
            "publication dates and no look-ahead. Historical FDA decision "
            "accuracy is not a substitute for observed stock returns."
        )
    st.download_button(
        "DOWNLOAD GEM CALIBRATION AUDIT",
        pd.Series(report).to_json(indent=2),
        file_name="gem_calibration_readiness.json",
        mime="application/json",
        key="gem_calibration_audit_export",
    )
    with st.expander("Historical evidence input templates"):
        for name, label, headers in (
            (SOURCE_FILES[0], "GEM point-in-time scores and evidence", SNAPSHOT_FIELDS),
            (SOURCE_FILES[1], "Split-adjusted dated equity prices", BAR_FIELDS),
        ):
            file = p / name
            value = file.read_bytes() if file.is_file() else (
                ",".join(headers) + "\n").encode("utf-8")
            st.download_button(
                "DOWNLOAD — " + label, data=value,
                file_name=name, mime="text/csv",
                key="gem_calibration_template_" + name,
            )
    st.caption(
        "No GEM weights are auto-deployed. Historical-data gaps, surviving-issuer "
        "bias, simultaneous clinical events, early FDA actions, publication "
        "timestamps and transaction costs require review before promotion."
    )
