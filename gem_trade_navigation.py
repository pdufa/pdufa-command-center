"""Stable GEM-to-WT navigation, separate from the shared browser toggle module.

Streamlit Cloud can retain ticker_toggle_panel in sys.modules across code
reloads. A dedicated module avoids importing a newly-added attribute from a
stale cached module, while reusing existing stable W/T list operations.
"""
import streamlit as st

from ticker_toggle_panel import _toggle, clean_ticker


def open_trade_workspace(ticker):
    """Select trading research and open WT; never transmit broker orders."""
    symbol = clean_ticker(ticker)
    if not symbol:
        return
    members = {clean_ticker(v) for v in st.session_state.get("trading_tickers", [])}
    if symbol not in members:
        _toggle(symbol, "trade")
    st.session_state["selected_ticker"] = symbol
    st.session_state["pdufa_subtab"] = "WT"
