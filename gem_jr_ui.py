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
from gem_membership_history import read_history, enrich_stage_rows, departed_stage_rows
from pdufa_table_headers import pdufa_dataframe
from stage_wt_tables import render_stage_wt_tables


def render_gem_jr(root="data"):
    st.markdown("## GEM JR — RESEARCH & QUALIFICATION QUEUE")
    st.caption(
        "PIPELINE → GEM JR → GEM. This is a source review queue, not an entry signal. "
        "GEM promotion still requires exact-program successful Phase 3 results and "
        "two independently SEC-confirmed financing closures after the readout."
    )
    active, held = build_potential_list(Path(root))
    # Promotion is an exact Pipeline ID transition; no ticker-only joins.
    from gem_verified_snapshot import source_cleared_gems
    cleared, historical_gems, _ = source_cleared_gems(root)
    cleared_ids = {str(r.get("Pipeline ID") or "")
                   for r in cleared + historical_gems}
    active = [r for r in active if r.get("Pipeline ID") not in cleared_ids]
    held = [r for r in held if r.get("Pipeline ID") not in cleared_ids]
    # Dates come from a committed scan ledger, never from trial readout dates.
    membership = read_history(root)
    active = enrich_stage_rows(active, "GEM_JR", membership)
    # Preserve the candidate research ordering computed from actual readout
    # and separate SEC evidence leads; this is NOT a buy/approval probability.
    active = [{**row, "Research Priority": i}
              for i, row in enumerate(active, 1)]
    held = enrich_stage_rows(held, "GEM_JR", membership)
    st.caption("DATE FOUND = first GEM JR detection in the membership tracker. "
               "DATE LEFT = departure from the active GEM JR listing after a "
               "validated scan. Earlier history cannot be inferred.")
    a, b = st.columns(2)
    a.metric("Research candidates", len(active))
    b.metric("Timing / resolved holds", len(held))
    fields = (
        "Research Priority", "Ticker", "Drug", "Indication", "NCT ID", "Evidence type",
        "SEC documents rechecked", "Why potential", "Still needed",
        "Clinical source", "Financing SEC source", "Source review date",
        "PDUFA date (saved)", "Timing / resolution", "Exact program", "GEM status",
        "Pipeline ID", "Date Found", "Date Left", "Date Re-entered",
        "Leave Reason", "Listing status",
    )
    # A resolved or expired program must not remain in the ACTIVE trial cards.
    # Archived programs are below, with actual dated scan-observed exits.
    render_trial_hierarchy(active, namespace="gem_jr", title="GEM JR")
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
    render_stage_wt_tables(
        "GEM JR", active, namespace="gem_jr", controls=True)
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
        with st.expander("RECONCILIATION HOLDS — NOT ACTIVE GEM JR", expanded=False):
            st.caption("These expired/resolved source leads are not in active GEM JR. "
                       "A dated PREVIOUS entry appears only if a validated scan "
                       "actually observed the program in GEM JR and later saw it leave.")
            pdufa_dataframe(pd.DataFrame(held).reindex(columns=fields).fillna(""),
                            hide_index=True, use_container_width=True)
    st.caption(
        "Only GEM's original two-benchmark gate assigns GEM eligibility. "
        "Registry postings, claimed financings, stale evidence and these research leads "
        "do not independently clear either benchmark."
    )
    departed = departed_stage_rows(membership, "GEM_JR")
    st.markdown("### GEM JR — PREVIOUS CANDIDATES")
    st.caption("Permanent stage history: exact Pipeline ID, first found, "
               "date left, and reason. PDUFA −3 warns traders but candidates "
               "remain listed until actual PDUFA expiry or FDA resolution.")
    with st.expander(f"OPEN PREVIOUS GEM JR CANDIDATES ({len(departed)})",
                     expanded=False):
        if departed:
            st.dataframe(pd.DataFrame(departed), use_container_width=True, hide_index=True)
        else:
            st.caption("No GEM JR departure has been recorded by a complete scan yet.")
