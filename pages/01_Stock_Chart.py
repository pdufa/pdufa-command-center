import json
import re
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="PDUFA Stock Chart", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

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
ticker = clean_ticker(qp.get("ticker", ""))
if not ticker:
    ticker = clean_ticker(st.text_input("Ticker", value="AAPL", max_chars=12))
if not ticker:
    st.stop()

st.title(f"{ticker} — Stock Chart")
st.caption("Interactive candlestick chart. Default technical studies: volume, moving averages, RSI, MACD and Bollinger Bands.")

symbol = f"NASDAQ:{ticker}"
widget = {
    "autosize": True,
    "symbol": symbol,
    "interval": "D",
    "timezone": "America/Los_Angeles",
    "theme": "light",
    "style": "1",
    "locale": "en",
    "allow_symbol_change": True,
    "calendar": False,
    "hide_side_toolbar": False,
    "withdateranges": True,
    "details": True,
    "hotlist": False,
    "support_host": "https://www.tradingview.com",
    "studies": [
        "Volume@tv-basicstudies",
        "MASimple@tv-basicstudies",
        "MAExp@tv-basicstudies",
        "RSI@tv-basicstudies",
        "MACD@tv-basicstudies",
        "BB@tv-basicstudies"
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

st.info("PDUFA-specific event markers (Phase 3, financing, NDA/BLA, PDUFA and FDA decision) are the next overlay layer; they will use the Command Center's verified event data.")
