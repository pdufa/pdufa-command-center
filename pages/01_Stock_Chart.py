import json
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from gem_trading_advisory import load_market_rows, render_base_chart_for_ticker
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from stages import chart_programs, add_stage_column
from table_groups import begin_table_render, grouped_dataframe

st.set_page_config(page_title="PDUFA Stock Chart", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")
begin_table_render()

st.markdown("""
<style>
.stApp{background:#dff5e1;color:#111}
.block-container{padding-top:.7rem;max-width:1550px}
.chart-shell{background:#fff;border:2px solid #000;border-radius:16px;padding:10px}
@media(max-width:768px){.block-container{padding:.45rem .45rem 3rem!important}}
</style>
""", unsafe_allow_html=True)

def clean_ticker(value):
    value = str(value or "").upper().strip()
    value = re.sub(r"[^A-Z0-9.\-]", "", value)
    return value[:12]

qp = st.query_params
requested_ticker = clean_ticker(qp.get("ticker", ""))
if st.session_state.get("_chart_requested_ticker") != requested_ticker:
    st.session_state["stock_chart_ticker"] = requested_ticker or "AAPL"
    st.session_state["_chart_requested_ticker"] = requested_ticker
ticker = clean_ticker(st.text_input("Ticker", max_chars=12, key="stock_chart_ticker"))
if not ticker:
    st.stop()
if requested_ticker != ticker:
    qp["ticker"] = ticker
    st.session_state["_chart_requested_ticker"] = ticker

st.title(f"{ticker} — Stock Chart")
programs = chart_programs(ticker, Path(__file__).resolve().parents[1] / "data")
if programs:
    stage_rows = add_stage_column(pd.DataFrame(programs), source=pd.DataFrame(programs))
    stage_display = stage_rows[[c for c in ("ticker", "STAGE", "DAYS TO PDUFA", "drug", "indication", "pdufa_date") if c in stage_rows]].rename(columns={"ticker": "Ticker", "drug": "Drug", "indication": "Indication", "pdufa_date": "PDUFA Date"})
    grouped_dataframe(stage_display, use_container_width=True, hide_index=True)
else:
    grouped_dataframe(pd.DataFrame([{"Ticker": ticker, "STAGE": "UNKNOWN — REVIEW"}]), use_container_width=True, hide_index=True)
st.caption(
    "TradingView candlesticks with volume, VWAP, SMA, EMA and ATR. "
    "Use the chart's drawing toolbar to outline a possible base (rectangle) and "
    "mark support/resistance; set the moving-average periods to 20 and 50 in TradingView. "
    "A separately computed close-only base overlay appears below when verified EOD data exists."
)

symbol = f"NASDAQ:{ticker}"
widget = {
    "autosize": False,
    "width": "100%",
    "height": 780,
    "symbol": symbol,
    "interval": "D",
    "timezone": "America/Los_Angeles",
    "theme": "light",
    "style": "1",
    "locale": "en",
    "allow_symbol_change": False,
    "calendar": False,
    "hide_side_toolbar": False,
    "hide_volume": False,
    "withdateranges": True,
    "details": True,
    "hotlist": False,
    "support_host": "https://www.tradingview.com",
    "studies": [
        "VWAP@tv-basicstudies",
        "MAExp@tv-basicstudies",
        "MASimple@tv-basicstudies",
        "ATR@tv-basicstudies"
    ]
}
html = f"""
<div class="tradingview-widget-container" style="height:780px;width:100%">
  <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
  {json.dumps(widget)}
  </script>
</div>
"""
components.html(html, height=800, scrolling=False)

with st.expander("BASE FORMATION — VERIFIED SAVED DAILY CLOSE & VOLUME", expanded=True):
    render_base_chart_for_ticker(
        ticker, load_market_rows(Path(__file__).resolve().parents[1] / "data"),
        datetime.now(ZoneInfo("America/Los_Angeles")).date(),
        compact=False,
    )
st.caption(
    "TradingView's intraday candles, ATR and VWAP are provided by TradingView and may differ "
    "from delayed saved EOD closing-price proxies. Automatically injecting Pine Script "
    "or drawing rectangles into this public TradingView embed is not supported. "
    "PDUFA-specific event markers await independently verified event overlays."
)

