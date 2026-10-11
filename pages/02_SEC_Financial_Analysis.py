"""Step 4 standalone Streamlit financial research page.

No edits or writes to PDUFA/clinical trial screens. No SEC calls until clicked.
"""
import json
import os
import sqlite3

import pandas as pd
import streamlit as st

from sec_step4 import DEFAULT_DB, load_registry, read_history, scan_one

st.set_page_config(page_title="SEC Financial Analysis · Step 4", page_icon="📑",
                   layout="wide")
st.markdown(
    """<style>
    .stApp{background:#dff5e1;color:#17301d}
    [data-testid="stMetric"],[data-testid="stDataFrame"]{
      background:#fff;border:2px solid #000;border-radius:12px;padding:8px
    }
    .block-container{max-width:1500px}
    </style>""",
    unsafe_allow_html=True,
)
st.title("📑 SEC Financial Analysis — STEP 4")
st.caption("Independent financial research · SEC EDGAR · Cash runway · Dilution and financing review")
st.warning("Financing filings are only review leads. S-3, 424B5 and 8-K filings do NOT by themselves confirm a completed financing. This page does not set PDUFA or Phase 3 financing milestones.")

try:
    registry = load_registry()
except (OSError, ValueError, UnicodeError) as exc:
    st.error(f"Could not load the SEC ticker/CIK registry: {exc}")
    st.stop()

tickers = sorted(t for t, value in registry.items()
                 if value.get("cik") and not value.get("conflict"))
st.caption(f"{len(tickers):,} unique ticker–CIK issuer identities available. SEC XBRL coverage varies.")
if not tickers:
    st.warning("No unique issuer identities are present; review the company_registry.csv source.")
    st.stop()

user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
try:
    configured_secret = st.secrets.get("SEC_USER_AGENT", "")
    if configured_secret:
        user_agent = str(configured_secret).strip()
except (FileNotFoundError, KeyError, AttributeError):
    pass
ready = bool(user_agent and "@" in user_agent and len(user_agent) >= 12)
if not ready:
    st.info("SEC access requires SEC_USER_AGENT set to an identifiable application and real contact email in Streamlit Secrets (or environment). Example format: PDUFA-Research contact@yourdomain.example. No SEC request will run without this setting.")

left, right = st.columns([3, 2])
with left:
    ticker = st.selectbox("Select company ticker", options=tickers)
with right:
    identity = registry[ticker]
    st.caption(f"Company: {identity['company']}")
    st.caption(f"SEC CIK: {identity['cik']}")

with st.form("sec_step4_retrieve"):
    pressed = st.form_submit_button("FETCH SEC FILINGS AND SAVE REVISION", disabled=not ready)
if pressed:
    with st.spinner(f"Contacting SEC for {ticker}; this may take a few seconds"):
        try:
            row_id, report = scan_one(ticker, registry=registry, user_agent=user_agent)
            st.success(f"SEC results saved as revision #{row_id}.")
        except (OSError, RuntimeError, ValueError, sqlite3.Error, TypeError) as exc:
            st.error(f"SEC scan failed: {exc}. No financial values were fabricated.")

try:
    history = read_history(ticker=ticker)
    all_history = read_history()
except (OSError, sqlite3.Error) as exc:
    st.error(f"Local financial history could not be read: {exc}")
    st.stop()

if not history:
    st.info("No stored SEC financial snapshot for this ticker. Configure SEC_USER_AGENT and click FETCH, or select a previously scanned ticker.")
    st.stop()

report = json.loads(history[0]["payload_json"])
st.caption("Last SEC observation: " + history[0]["observed_at_utc"] +
           " · XBRL as-of: " + report["as_of"] +
           " · local Streamlit storage is NOT a durable database")
m1, m2, m3, m4 = st.columns(4)
fmt_money = lambda v: "NOT VERIFIED" if v is None else f"${v / 1e6:,.2f}M"
with m1:
    st.metric("SEC reported cash", fmt_money(report["cash_usd"]))
with m2:
    st.metric("Monthly operating cash burn", fmt_money(report["monthly_operating_burn_usd"]))
with m3:
    runway = report["runway_months_cash_only"]
    st.metric("Estimated runway (cash only)", "NOT VERIFIED" if runway is None else f"{runway:,.1f} mo")
with m4:
    st.metric("Runway risk", report["cash_runway_risk"])
st.caption("Cash runway is an estimate from cash and reported cash flow—not a forward forecast. Short-term investments are separately reported and never automatically assumed to be liquid.")

st.markdown("### Financial statement data")
frame = pd.DataFrame([
    {"Measurement": "Cash", "Value": fmt_money(report["cash_usd"])},
    {"Measurement": "Short-term investments (not added to runway)", "Value": fmt_money(report["short_term_investments_usd"])},
    {"Measurement": "Operating cash flow (reported period)", "Value": fmt_money(report["operating_cash_flow_usd"])},
    {"Measurement": "Cash-flow months", "Value": report["operating_cash_flow_months"] or "NOT VERIFIED"},
    {"Measurement": "Revenue (not necessarily product sales)", "Value": fmt_money(report["company_revenue_usd"])},
    {"Measurement": "Product sales separately confirmed", "Value": "NOT VERIFIED"},
    {"Measurement": "Current debt (partial coverage)", "Value": fmt_money(report["current_debt_usd"])},
    {"Measurement": "Noncurrent debt (partial coverage)", "Value": fmt_money(report["noncurrent_debt_usd"])},
    {"Measurement": "Shares outstanding", "Value": ("NOT VERIFIED" if report["shares_outstanding"] is None
                                                      else f"{report['shares_outstanding']:,.0f}")},
    {"Measurement": "Previous shares outstanding", "Value": ("NOT VERIFIED" if report["previous_shares_outstanding"] is None
                                                               else f"{report['previous_shares_outstanding']:,.0f}")},
    {"Measurement": "Change in reported shares (not necessarily dilution)", "Value":
         ("NOT VERIFIED" if report["shares_change_pct"] is None else f"{report['shares_change_pct']:+,.2f}%")},
    {"Measurement": "Cash-only runway risk index /100 (higher = more risk)", "Value":
         ("NOT SCORED" if report["runway_risk_index_0_100"] is None
          else str(report["runway_risk_index_0_100"]))},
    {"Measurement": "Financing closure", "Value": report["financing_closed"]},
    {"Measurement": "ATM activity", "Value": report["active_atm"]},
    {"Measurement": "Financial composite score", "Value": "NOT SCORED"},
])
st.dataframe(frame, use_container_width=True, hide_index=True)

if report.get("review_flags"):
    st.warning("Source / period review: " + "; ".join(report["review_flags"]))
st.markdown("### Financing filings to review")
if report.get("filing_review_queue"):
    st.dataframe(pd.DataFrame(report["filing_review_queue"]), use_container_width=True,
                 hide_index=True, column_config={"source_url": st.column_config.LinkColumn("SEC filing")})
else:
    st.caption("No matching filing metadata in the retrieved recent SEC index. This does not establish that financing did not occur.")

with st.expander("Source evidence and method"):
    st.json(report["evidence"])
    st.caption(report["method"])
    st.caption(report["financial_score_note"])
    st.caption(report["runway_risk_index_note"])
    st.caption(report["shares_change_note"])

st.markdown("### Historical SEC snapshots")
cols = ["id", "observed_at_utc", "as_of", "content_sha256"]
st.dataframe(pd.DataFrame(history)[cols], use_container_width=True, hide_index=True)
st.download_button("DOWNLOAD FULL SEC AUDIT HISTORY (JSON)", data=json.dumps(all_history, indent=2),
                   file_name="sec_step4_audit_history.json", mime="application/json")
st.caption("Snapshots are append-only by content. Export regularly or configure an external persistent database; Streamlit Community Cloud local files may be deleted on restart/redeployment.")
