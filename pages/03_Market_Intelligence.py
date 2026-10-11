"""Step 5 — standalone Streamlit market intelligence, not PRE PHASE 3."""
from datetime import date
import json
import sqlite3

import pandas as pd
import streamlit as st

from market_step5 import (
    DEFAULT_DB, EXTRA_BOUNDS, PHASES, clean_ticker, evaluate_market,
    fetch_stooq_daily, financial_context_asof, parse_ohlcv, rankings,
    read_history, save_snapshot,
)
from sec_step4 import DEFAULT_DB as SEC_DB, load_registry

st.set_page_config(page_title="Market Intelligence · Step 5", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.stApp{background:#dff5e1;color:#17301d}
[data-testid="stMetric"],[data-testid="stDataFrame"],[data-testid="stForm"]{
background:#fff;border:2px solid #000;border-radius:12px;padding:8px}
.block-container{max-width:1550px}
</style>""", unsafe_allow_html=True)

st.title("📈 Market Intelligence & Stock Ranking — STEP 5")
st.caption("Technical price/volume setup and source-labeled research · NOT an FDA approval probability")
st.warning("PRE PHASE 3 stays blank. This is a separate research page. "
           "Scores are technical snapshots, not predictions of clinical results, "
           "price appreciation, short squeezes or FDA decisions.")

try:
    identities = load_registry()
except (OSError, ValueError, UnicodeError) as exc:
    st.error(f"Unable to read SEC company registry: {exc}")
    st.stop()
tickers = sorted(t for t, item in identities.items()
                 if item.get("cik") and not item.get("conflict"))
if not tickers:
    st.warning("No uniquely matched tickers in data/company_registry.csv.")
    st.stop()

with st.form("market_step5_research"):
    left, right = st.columns([2, 2])
    with left:
        ticker = st.selectbox("Registered biotech ticker", options=tickers)
        st.caption("Issuer: " + identities[ticker]["company"])
        phase_label = st.radio(
            "Which Phase 3 trading period?",
            ["PRE RESULTS — Phase 3 results not yet released",
             "POST RESULTS — Phase 3 results published"], horizontal=False)
        phase = PHASES[0] if phase_label.startswith("PRE") else PHASES[1]
        as_of = st.date_input("Analyze as of (no future data)", value=date.today(),
                              max_value=date.today())
    with right:
        phase_url = st.text_input("Evidence URL for claimed phase status (HTTPS)",
                                  placeholder="https://clinicaltrials.gov/study/NCT...")
        phase_date = st.date_input("Publication / observation date of phase evidence",
                                    value=as_of, max_value=as_of)
        readout = st.text_input("Actual Phase 3 readout publication date (POST only)",
                                placeholder="YYYY-MM-DD; leave blank for PRE")
        pdufa = st.text_input("Verified PDUFA date (POST only; optional)",
                             placeholder="YYYY-MM-DD")
        pdufa_url = st.text_input("PDUFA evidence URL (HTTPS, required if date entered)",
                                  placeholder="https://www.fda.gov/...")
        pdufa_source_date = st.date_input("PDUFA source publication / verification date",
                                          value=as_of, max_value=as_of)

    st.markdown("#### Market data source")
    price_source = st.radio(
        "Choose data source (never fetch automatically)",
        ["Fetch delayed US EOD bars from Stooq",
         "Upload dated OHLCV CSV (Date,Open,High,Low,Close,Volume)"],
        help="Stooq is an unofficial research price feed: symbol/issuer identity and "
             "split/dividend adjustments require independent review.")
    uploaded = st.file_uploader("CSV for uploaded-source mode", type=["csv"],
                                 disabled=not price_source.startswith("Upload"))
    uploaded_url = st.text_input("Uploaded CSV provenance URL (HTTPS, for audit)",
                                 placeholder="https://your-data-provider.example/...",
                                 disabled=not price_source.startswith("Upload"))

    with st.expander("Optional market intelligence: short interest, days-to-cover, IV, ownership, borrow fees"):
        st.caption("Enter numbers only when supported by an HTTPS source and an observation "
                   "date. Stale/missing values are excluded, never treated as zero. "
                   "Short interest, options and holdings do NOT affect the technical score.")
        optional_frame = pd.DataFrame([{"Indicator": k, "Value": None,
            "Date YYYY-MM-DD": "", "Source HTTPS URL": ""} for k in EXTRA_BOUNDS])
        optional_edited = st.data_editor(optional_frame, use_container_width=True,
                                         hide_index=True, disabled=["Indicator"],
                                         num_rows="fixed")
    analyze = st.form_submit_button("FETCH / ANALYZE & SAVE MARKET SNAPSHOT")

if analyze:
    with st.spinner("Reading dated market evidence and evaluating technical indicators…"):
        try:
            if price_source.startswith("Fetch"):
                bars, source = fetch_stooq_daily(ticker, as_of)
            else:
                if uploaded is None:
                    raise ValueError("Select a CSV file before analysis")
                if not uploaded_url.strip().startswith("https://"):
                    raise ValueError("Provide a source URL for uploaded prices")
                bars = parse_ohlcv(uploaded.getvalue().decode("utf-8-sig"), as_of)
                source = {"provider": "UPLOADED OHLCV CSV — RESEARCHER SUPPLIED",
                          "source_url": uploaded_url.strip(),
                          "issuer_mapping": "REVIEW — instrument identity unverified",
                          "price_adjustments": "Unknown; corporate actions need review"}
            extras = {}
            for _, item in optional_edited.iterrows():
                key = item["Indicator"]
                v = item["Value"]
                if pd.notna(v) and str(v).strip() != "":
                    extras[key] = {"value": v, "date": str(item["Date YYYY-MM-DD"]),
                                   "url": str(item["Source HTTPS URL"])}
            snapshot = evaluate_market(
                ticker, bars, as_of, phase,
                phase_evidence={"url": phase_url.strip(),
                                "date": phase_date.isoformat()},
                readout_date=readout.strip() or None,
                pdufa_date=pdufa.strip() or None,
                pdufa_evidence={"url": pdufa_url.strip(),
                                "date": pdufa_source_date.isoformat()},
                extras=extras, source=source)
            snapshot["company_registry"] = {
                "ticker": ticker, "cik": identities[ticker]["cik"],
                "company": identities[ticker]["company"],
                "mapping_note": "CIK mapping is separate from price-provider symbol validation"}
            if SEC_DB.exists():
                snapshot["step4_financial_context"] = financial_context_asof(ticker, as_of)
            row_id = save_snapshot(snapshot)
            st.success(f"Saved Step 5 audit revision #{row_id}. "
                       f"{snapshot['score_status']}")
        except (OSError, ValueError, RuntimeError, UnicodeError, sqlite3.Error) as exc:
            st.error(f"Market scan not saved: {exc}. No values have been fabricated.")

try:
    personal = read_history(ticker=ticker)
    complete = read_history()
except (OSError, sqlite3.Error) as exc:
    st.error(f"Unable to read market history: {exc}")
    st.stop()

st.markdown("### Same-date, same-phase candidate ranking")
ranking = rankings(complete, as_of.isoformat(), phase)
if ranking:
    st.dataframe(pd.DataFrame(ranking), use_container_width=True, hide_index=True)
else:
    st.info("No scored market snapshots for this date and Phase 3 period. "
            "An evidence-dated phase review and at least 31 recent price sessions are required.")
st.caption("PRE and POST rankings are never mixed. The ranking represents dated technical "
           "setup only; it does not imply FDA approval, Phase 3 success or a profitable trade.")

st.markdown(f"### {ticker} — most recent saved research")
if not personal:
    st.info("No snapshots saved for this ticker. Run an analysis to populate history.")
    st.stop()

selected = json.loads(personal[0]["payload_json"])
st.caption("Saved " + personal[0]["captured_utc"] + " · Analysis as-of " + selected["as_of"]
           + " · Instrument: " + selected["source"].get("provider", "UNKNOWN"))
col1, col2, col3, col4 = st.columns(4)
with col1:
    val = selected.get("technical_score_0_100")
    st.metric("Technical setup score", "NOT SCORED" if val is None else f"{val:.2f} / 100")
with col2:
    st.metric("Phase 3 window", selected["phase"].replace("_", " "))
with col3:
    st.metric("30-session return", str(selected["market_indicators"].get(
        "momentum_30_session_pct", "NOT VERIFIED")) + "%" if
        selected["market_indicators"].get("momentum_30_session_pct") is not None else "NOT VERIFIED")
with col4:
    st.metric("Relative volume", selected["market_indicators"].get(
        "relative_volume_vs_prior20", "NOT VERIFIED"))
st.caption("PDUFA window: " + selected["pdufa_window"])
st.caption("Phase verification: " + selected["phase_status"])
if selected["review_flags"]:
    st.warning("Review: " + "; ".join(selected["review_flags"]))
if selected.get("market_indicators"):
    st.markdown("#### Price, volume, trend and realized-volatility evidence")
    st.dataframe(pd.DataFrame(
        [{"Indicator": k, "As-of result": v} for k, v in
         selected["market_indicators"].items()]), use_container_width=True, hide_index=True)
if selected.get("technical_factor_points"):
    st.markdown("#### Score attribution")
    st.dataframe(pd.DataFrame(
        [{"Factor": k, "Points earned": value,
          "Maximum": selected["weights"][k]} for k, value in
         selected["technical_factor_points"].items()]),
         use_container_width=True, hide_index=True)
st.markdown("#### Short interest, IV, institutional ownership and borrow availability")
st.dataframe(pd.DataFrame([{"Indicator": k,
     "Status": selected["coverage"][k],
     "Value": (selected["extra_market_observations"].get(k) or {}).get("value"),
     "Evidence": (selected["extra_market_observations"].get(k) or {}).get("url")}
    for k in EXTRA_BOUNDS]), use_container_width=True, hide_index=True)
st.caption("Optional observations are researcher supplied and source-dated, not automated paid-feed data. "
           "Ownership filings can lag; they are not proof of current buying.")

if selected.get("step4_financial_context"):
    st.markdown("#### Step 4 finance context (not part of Step 5 score)")
    st.json(selected["step4_financial_context"])

st.markdown("### Score history and change attribution")
selected_phase_history = [json.loads(r["payload_json"]) for r in reversed(personal)
                          if json.loads(r["payload_json"]).get("phase") == selected["phase"]]
score_history = [
    {"As of": r["as_of"], "Score": r["technical_score_0_100"]}
    for r in selected_phase_history if r.get("technical_score_0_100") is not None]
if score_history:
    timeline = pd.DataFrame(score_history).drop_duplicates("As of", keep="last")
    st.line_chart(timeline.set_index("As of"))
else:
    st.caption("No scored history for this phase.")
if len(selected_phase_history) >= 2:
    previous = selected_phase_history[-2]
    if previous.get("technical_factor_points") and selected.get("technical_factor_points"):
        differences = [
            {"Factor": k, "Point change":
             round(selected["technical_factor_points"][k] -
                   previous["technical_factor_points"].get(k, 0), 2)}
            for k in selected["technical_factor_points"]]
        st.dataframe(pd.DataFrame(differences), use_container_width=True, hide_index=True)

with st.expander("Full research evidence and source audit"):
    st.json({"source": selected["source"], "phase_evidence": selected["phase_evidence"],
             "pdufa_evidence": selected["pdufa_evidence"],
             "recent_bars": selected["recent_bars_used"],
             "observed_market_factors": selected["extra_market_observations"]})
st.download_button("DOWNLOAD STEP 5 AUDIT HISTORY (JSON)",
                   json.dumps(complete, indent=2), "market_step5_history.json",
                   mime="application/json")
st.caption("Local SQLite audit storage is NOT durable on Streamlit Community Cloud. "
           "Export periodically or attach persistent Postgres/object storage.")
