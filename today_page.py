"""Pipeline Phase 3 Daily report: conservative, traceable research views."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote_plus
import pandas as pd
import streamlit as st
from financing_stage import add_financing_column
from stages import StageIndex, add_stage_column

TZ = ZoneInfo("America/Los_Angeles")
def first(frame, *names):
    lookup = {str(c).lower().replace(" ","_"): c for c in frame.columns}
    for n in names:
        if n.lower().replace(" ","_") in lookup:
            return frame[lookup[n.lower().replace(" ","_")]]
    return pd.Series([""] * len(frame), index=frame.index)

def dates(frame, *names):
    return pd.to_datetime(first(frame, *names).astype("string").str.slice(0, 10), errors="coerce").dt.date

def assemble(live, pipeline, financing):
    frames = []
    for frame, origin in ((live, "MASTER"), (pipeline, "PHASE 3 PIPELINE")):
        if frame is None or frame.empty: continue
        x = frame.copy().reset_index(drop=True)
        x["Source List"] = origin
        frames.append(x)
    if not frames: return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined["Ticker"] = first(combined, "ticker", "symbol").fillna("").astype(str).str.upper()
    combined["Drug"] = first(combined, "drug", "drug_name").fillna("").astype(str)
    combined["Indication"] = first(combined, "indication", "disease").fillna("").astype(str)
    combined["Company"] = first(combined, "company", "company_name").fillna("").astype(str)
    combined["Event Key"] = first(combined, "event_key").fillna("").astype(str)
    combined["Our Score"] = first(combined, "trade_score", "our_score", "our_trade_pdufa_score")
    combined["Phase 3 Result"] = first(combined, "phase3_result", "phase_3_result", "primary_endpoint_result", "phase3_results")
    combined["Result Source"] = first(combined, "phase3_results_source", "phase3_source", "results_source")
    combined["Result Posted"] = dates(combined, "phase3_results_posted_at", "phase3_result_published_at", "phase3_results_date")
    combined["Other Indications"] = first(combined, "other_indications", "pipeline_indications", "therapeutic_areas")
    combined["Runway Before (mo)"] = first(combined, "pre_financing_runway_months", "cash_runway_months")
    combined["Runway After (mo)"] = first(combined, "post_financing_runway_months", "runway_after_financing_months")
    combined["Financing Evidence"] = first(combined, "second_financing_source", "financing_source")
    combined["Financing Search"] = combined["Company"].where(combined["Company"].str.strip().ne(""), combined["Ticker"]).map(lambda s: "https://www.google.com/search?q=" + quote_plus(str(s) + " financing") if str(s).strip() else "")
    combined["Entry Gate"] = first(combined, "entry_gate", "green_light_entry_gate")
    combined["Score Change"] = first(combined, "score_change", "trade_score_change")
    combined["Last Verified"] = first(combined, "verified_as_of", "last_verified", "last_checked_at")
    combined["Evidence Type"] = first(combined, "source_type", "record_source")
    combined["Verification Mark"] = first(combined, "verification_status", "phase3_status")
    combined["Evidence Notes"] = first(combined, "source_list_note")
    combined["Trial ID"] = first(combined, "nct_id")
    # Preserve missing evidence instead of promoting unknown financing to finished.
    try:
        combined = add_financing_column(combined, index=StageIndex(financing.to_dict("records") if financing is not None and not financing.empty else []))
    except (ValueError, TypeError, KeyError):
        combined["FINANCING"] = "REVIEW / UNVERIFIED"
    combined["Research Status"] = combined["Result Source"].fillna("").astype(str).str.strip().map(lambda x: "SOURCE LINKED" if x.startswith("http") else "REVIEW / SOURCE MISSING")
    # Program identity is deliberately kept distinct across drugs and indications.
    combined = combined.drop_duplicates(subset=["Ticker","Drug","Indication","Trial ID","Result Posted"], keep="last")
    return combined

def _today_watchlist_controls(frame):
    """Keep ticker-level Watchlist management without 2,000+ Streamlit toggles."""
    watchlist = {str(t).strip().upper() for t in st.session_state.setdefault("watchlist", []) if str(t).strip()}
    choices = sorted({str(t).strip().upper() for t in frame["Ticker"] if str(t).strip() and str(t).strip().upper() not in {"NAN", "NONE"}})
    st.markdown("### WATCHLIST — ADD / REMOVE TICKER")
    st.caption("Watchlist is ticker-based across the app. Different clinical programs for the same stock remain separate records in the result tables.")
    selected = st.selectbox(
        "Search ticker", options=choices, index=None, placeholder="Find a ticker...",
        key="today_watchlist_ticker_v2", disabled=not choices,
    )
    left, right = st.columns(2)
    with left:
        add = st.button("ADD TO WATCHLIST", key="today_watch_add_v2", use_container_width=True,
                        disabled=not selected or selected in watchlist)
    with right:
        remove = st.button("REMOVE FROM WATCHLIST", key="today_watch_remove_v2", use_container_width=True,
                           disabled=not selected or selected not in watchlist)
    if add and selected:
        st.session_state["watchlist"] = sorted(watchlist | {selected})
        st.rerun()
    if remove and selected:
        st.session_state["watchlist"] = sorted(watchlist - {selected})
        st.rerun()
    st.caption(f"Watchlist currently contains {len(watchlist)} tickers.")


def render_today(live, pipeline, financing):
    now = datetime.now(TZ)
    yesterday = now.date() - timedelta(days=1)
    st.subheader("DAILY PHASE 3 RESULT REPORT")
    st.caption(f"Pacific reporting date: {now:%Y-%m-%d} · Yesterday: {yesterday} · Data is sourced from stored project files; opening this page does not run an overnight web scan.")
    data = assemble(live, pipeline, financing)
    if data.empty:
        st.warning("No source records loaded. Check the master and Phase 3 pipeline files.")
        return
    # Normalize the entire column to a comparable Pacific-local calendar date.
    posted = pd.to_datetime(data["Result Posted"].astype("string").str.slice(0, 10), errors="coerce").dt.date
    top = data.loc[posted.eq(yesterday)].copy()
    top = top.loc[top["Result Source"].fillna("").astype(str).str.startswith("http")]
    phase3 = pd.to_datetime(first(data, "phase3_date", "phase3_readout_date", "phase3_results_date").astype("string").str.slice(0, 10), errors="coerce").dt.date
    status = first(data, "phase3_status", "current_stage").fillna("").astype(str).str.upper()
    eligible = status.str.contains("RESULTS_VERIFIED|RESULTS_REVIEW", regex=True) | (data["Result Source"].fillna("").astype(str).str.startswith("http") & posted.notna())
    # The cumulative report covers the tracked result universe, not only rows with an explicit
    # Phase 3 readout date. Keep qualification transparent for every record.
    data["Post–Phase 3 Evidence"] = eligible.map({True: "RECORDED POST–PHASE 3", False: "REVIEW — PHASE 3 NOT VERIFIED"})
    bottom = data.loc[eligible].copy()
    # Show count of records separately from unique companies, since multiple
    # trials / indications can refer to the same ticker.
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Yesterday: source-linked posts", len(top))
    m2.metric("Recorded Phase 3 result rows", len(bottom))
    m3.metric("Unique result tickers", bottom["Ticker"].loc[bottom["Ticker"].str.len().gt(0)].nunique())
    m4.metric("Rows missing result-source links", int(data["Research Status"].ne("SOURCE LINKED").sum()))
    if bottom.empty:
        st.warning("No post–Phase 3 results qualified from the saved evidence.")
    else:
        bottom = bottom.sort_values("Result Posted", ascending=False, na_position="last", kind="stable")
    _today_watchlist_controls(data)
    fields = ["Ticker","Company","Drug","Indication","Phase 3 Result","Result Posted","Our Score","Score Change","Entry Gate","FINANCING","Runway Before (mo)","Runway After (mo)","Other Indications","Result Source","Financing Evidence","Financing Search","Last Verified","Research Status","Evidence Type","Verification Mark","Evidence Notes","Trial ID","Post–Phase 3 Evidence","Source List"]
    def show(frame, table_key):
        if frame.empty:
            st.info("No verified matching records in currently stored files.")
            return
        shown = frame[[c for c in fields if c in frame]].copy()
        st.dataframe(shown.style.map(lambda v: "background-color: #c7f2cd; color: #102c13" if str(v) == "FINISHED" else ("background-color: #fff0a6; color: #342900" if str(v) in ("STARTED","RUNNING") else ("background-color: #ffc8c8; color: #481313" if str(v) == "ANNOUNCED" else "")), subset=["FINANCING"]), use_container_width=True, hide_index=True, column_config={"Financing Search": st.column_config.LinkColumn("Financing Search"), "Result Source": st.column_config.LinkColumn("Result Source"), "Financing Evidence": st.column_config.LinkColumn("Financing Evidence")})
    st.subheader("TOP — Phase 3 results posted yesterday")
    st.caption("A posted registry result may still need clinical interpretation; a source link is not proof of a positive primary endpoint.")
    if top.empty:
        st.warning("No verified yesterday Phase 3 posts are currently ingested. The Phase 3 pipeline source file is empty or lacks dated, source-linked result announcements; this is an intake gap, not proof that no results were published.")
    show(top, "top")
    st.subheader("BOTTOM — Cumulative Phase 3 result records (verified and review)")
    show(bottom, "bottom")
    st.caption("Rows are ordered by most recent result-post date. They represent trial-result records, not deduplicated drugs or confirmed positive outcomes. FINANCING: red announced, yellow started/running, green verified finished. Unverified stays uncolored. Post-financing runway is not inferred without evidence.")
    st.download_button("EXPORT PHASE 3 DAILY CSV", data.to_csv(index=False).encode("utf-8"), file_name=f"phase3_daily_{now:%Y%m%d}.csv", mime="text/csv")
