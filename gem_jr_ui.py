"""Research-only GEM JR stage: independent Phase 3 and financing evidence leads.

No record is promoted or scored as an eligible GEM here. All underlying
clinical readout, SEC financing and historical backtesting modules are retained.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from gem_trading_advisory import load_market_rows, render_base_chart_for_ticker
import pandas as pd
import streamlit as st
from gem_potential_list import build_potential_list
from gem_trial_hierarchy_ui import render_trial_hierarchy
from pdufa_table_headers import pdufa_dataframe


def render_gem_jr(root="data"):
    st.markdown("## GEM JR — RESEARCH & QUALIFICATION QUEUE")
    st.caption(
        "PIPELINE → GEM JR → GEM. This is a source review queue, not an entry signal. "
        "GEM promotion still requires exact-program successful Phase 3 results and "
        "two independently SEC-confirmed financing closures after the readout."
    )
    active, held = build_potential_list(Path(root))
    a, b = st.columns(2)
    a.metric("Research candidates", len(active))
    b.metric("Timing / resolved holds", len(held))
    fields = (
        "Ticker", "Drug", "Indication", "NCT ID", "Evidence type",
        "SEC documents rechecked", "Why potential", "Still needed",
        "Clinical source", "Financing SEC source", "Source review date",
        "PDUFA date (saved)", "Timing / resolution", "Exact program", "GEM status",
    )
    render_trial_hierarchy(active + held, namespace="gem_jr", title="GEM JR")
    if active:
        st.markdown("### CANDIDATES REQUIRING VERIFICATION")
        frame = pd.DataFrame(active).reindex(columns=fields).fillna("")
        pdufa_dataframe(
            frame, hide_index=True, use_container_width=True,
            column_config={
                "Clinical source": st.column_config.LinkColumn("Clinical source"),
                "Financing SEC source": st.column_config.LinkColumn("Financing SEC source"),
            },
        )
        st.download_button("EXPORT GEM JR RESEARCH",
                           frame.to_csv(index=False).encode("utf-8"),
                           file_name="gem_jr_research.csv", mime="text/csv",
                           key="gem_jr_research_export")
    else:
        st.info("No active source-linked Phase 3 / financing leads in the saved research evidence.")
    if active:
        with st.expander("GEM JR — OPEN STOCK BASE / SUPPORT CHART", expanded=False):
            tickers = sorted({str(x.get("Ticker") or "").upper().strip()
                              for x in active if x.get("Ticker")})
            chosen = st.selectbox("Research stock to chart", tickers,
                                  key="gem_jr_base_stock")
            render_base_chart_for_ticker(
                chosen, load_market_rows(root),
                datetime.now(ZoneInfo("America/Los_Angeles")).date(),
            )
            st.caption("GEM JR candidates remain UNVERIFIED research leads. "
                       "Chart data availability never clears Phase 3 or financing benchmarks.")
    if held:
        with st.expander("RESOLVED EVENTS / PDUFA TIMING HOLDS", expanded=False):
            pdufa_dataframe(pd.DataFrame(held).reindex(columns=fields).fillna(""),
                            hide_index=True, use_container_width=True)
    st.caption(
        "Only GEM's original two-benchmark gate assigns GEM eligibility. "
        "Registry postings, claimed financings, stale evidence and these research leads "
        "do not independently clear either benchmark."
    )
