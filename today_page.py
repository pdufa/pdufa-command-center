"""TODAY: conservative, source-traceable Phase 3 and post-readout daily view."""
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

def _today_watch_change(switch_key, ticker):
    selected = bool(st.session_state.get(switch_key, False))
    current = list(st.session_state.get("watchlist", []))
    if selected and ticker not in current:
        current.append(ticker)
    elif not selected:
        current = [x for x in current if x != ticker]
    st.session_state["watchlist"] = current


def render_today(live, pipeline, financing):
    now = datetime.now(TZ)
    yesterday = now.date() - timedelta(days=1)
    st.title("TODAY")
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
    # TODAY bottom is the full tracked universe, not only rows with an explicit
    # Phase 3 readout date. Keep qualification transparent for every record.
    data["Post–Phase 3 Evidence"] = eligible.map({True: "RECORDED POST–PHASE 3", False: "REVIEW — PHASE 3 NOT VERIFIED"})
    bottom = data.loc[eligible].copy()
    st.metric("Yesterday's source-linked Phase 3 posts", len(top))
    st.metric("Phase 3 result records (not unique drugs)", len(bottom))
    st.metric("Recorded post–Phase 3", int(eligible.sum()))
    if bottom.empty:
        st.warning("No post–Phase 3 results qualified from the saved evidence.")
    st.metric("Rows needing result-source review", int(data["Research Status"].ne("SOURCE LINKED").sum()))
    fields = ["Ticker","Company","Drug","Indication","Phase 3 Result","Result Posted","Our Score","Score Change","Entry Gate","FINANCING","Runway Before (mo)","Runway After (mo)","Other Indications","Result Source","Financing Evidence","Financing Search","Last Verified","Research Status","Evidence Type","Verification Mark","Evidence Notes","Trial ID","Post–Phase 3 Evidence","Source List"]
    def show(frame, table_key):
        if frame.empty:
            st.info("No verified matching records in currently stored files.")
            return
        shown = frame[[c for c in fields if c in frame]].copy()
        st.markdown("**MOVE TO WATCHLIST — turn on to add, off to remove**")
        watch = st.session_state.setdefault("watchlist", [])
        for row_num, (_, item) in enumerate(frame.iterrows()):
            ticker = str(item.get("Ticker", "")).strip().upper()
            if not ticker or ticker in ("NAN", "NONE"):
                continue
            name = str(item.get("Drug", "")).strip()
            switch_key = f"today_watch_{table_key}_{row_num}_{ticker}"
            st.toggle(f"{ticker} — {name}", value=ticker in watch,
                      key=switch_key, on_change=_today_watch_change,
                      args=(switch_key, ticker))
        st.dataframe(shown.style.map(lambda v: "background-color: #c7f2cd; color: #102c13" if str(v) == "FINISHED" else ("background-color: #fff0a6; color: #342900" if str(v) in ("STARTED","RUNNING") else ("background-color: #ffc8c8; color: #481313" if str(v) == "ANNOUNCED" else "")), subset=["FINANCING"]), use_container_width=True, hide_index=True, column_config={"Financing Search": st.column_config.LinkColumn("Financing Search"), "Result Source": st.column_config.LinkColumn("Result Source"), "Financing Evidence": st.column_config.LinkColumn("Financing Evidence")})
    st.subheader("TOP — Phase 3 results posted yesterday")
    if top.empty:
        st.warning("No verified yesterday Phase 3 posts are currently ingested. The Phase 3 pipeline source file is empty or lacks dated, source-linked result announcements; this is an intake gap, not proof that no results were published.")
    show(top, "top")
    st.subheader("BOTTOM — Cumulative Phase 3 result records (verified and review)")
    show(bottom, "bottom")
    st.caption("The bottom table lists trial-result records, not deduplicated unique drugs or confirmed positive outcomes. FINANCING: red announced, yellow started/running, green verified finished. Unverified records remain uncolored for review. Runway after financing is not inferred without a documented estimate.")
    st.download_button("Export TODAY", data.to_csv(index=False).encode("utf-8"), file_name=f"today_{now:%Y%m%d}.csv", mime="text/csv")
