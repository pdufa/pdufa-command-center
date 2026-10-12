"""Compact ticker Watch/Trading toggles shared by PDUFA #2, #3, and #4.

Ticker-level manual labels only. Trading means added to the user's research
trading list; it is NOT a broker transaction, entry-gate pass, or trade signal.
Browser local storage is per browser/device, not a cloud portfolio database.
"""
import json
import math
import re

import pandas as pd
import streamlit as st

STORAGE_KEY = "pdufa_watch_trading_v1"
ROWS_PER_PAGE = 7
TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,12}$")


def clean_ticker(value):
    if value is None or value is pd.NA or (isinstance(value, float) and pd.isna(value)):
        return ""
    ticker = str(value).strip().upper()
    return ticker if TICKER_PATTERN.fullmatch(ticker) else ""


def ticker_universe(records):
    """Unique ticker symbols; trial/event duplicates never create extra buttons."""
    if isinstance(records, pd.DataFrame):
        column = next((c for c in ("Ticker", "ticker", "symbol") if c in records), None)
        values = records[column].tolist() if column else []
    else:
        values = [r.get("Ticker") or r.get("ticker") or r.get("symbol")
                  for r in (records or []) if isinstance(r, dict)]
    return sorted({ticker for val in values if (ticker := clean_ticker(val))})


def parse_saved(value):
    """Read only our expected localStorage format; ignore malformed browser data."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return None
    if not isinstance(value, dict) or value.get("version") != 1:
        return None
    result = {}
    for category in ("watch", "trade"):
        vals = value.get(category)
        if not isinstance(vals, list):
            return None
        result[category] = sorted({t for val in vals if (t := clean_ticker(val))})
    return result


def serialize_selections(state):
    return json.dumps({
        "version": 1,
        "watch": sorted({t for val in state.get("watchlist", []) if (t := clean_ticker(val))}),
        "trade": sorted({t for val in state.get("trading_tickers", []) if (t := clean_ticker(val))}),
    }, separators=(",", ":"))


def toggle_membership(existing, ticker):
    ticker = clean_ticker(ticker)
    members = {t for v in existing if (t := clean_ticker(v))}
    if not ticker:
        return sorted(members)
    if ticker in members:
        members.remove(ticker)
    else:
        members.add(ticker)
    return sorted(members)


def _toggle(ticker, category):
    key = "watchlist" if category == "watch" else "trading_tickers"
    st.session_state[key] = toggle_membership(st.session_state.get(key, []), ticker)
    st.session_state["_ticker_selections_dirty"] = True


def _init_browser_selection(panel_id):
    """Restore per-browser selections without blocking the Streamlit script.

    Component values are asynchronous. A new user selection always wins over
    a later-returning browser read, and only successful clicks write storage.
    """
    st.session_state.setdefault("watchlist", [])
    st.session_state.setdefault("trading_tickers", [])
    try:
        from streamlit_js_eval import streamlit_js_eval
        raw = streamlit_js_eval(
            js_expressions=f"localStorage.getItem({json.dumps(STORAGE_KEY)})",
            key=f"pdufa_ticker_read_{panel_id}", want_output=True,
        )
        if st.session_state.get("_ticker_selections_dirty"):
            st.session_state["_ticker_selections_hydrated"] = True
        # Inline table buttons write the same browser storage without executing
        # a Python widget callback. Reconcile it on each Streamlit rerun, not
        # only the first hydration, while keeping a fresh native click authoritative.
        if not st.session_state.get("_ticker_selections_dirty"):
            parsed = parse_saved(raw)
            if parsed is not None:
                st.session_state["watchlist"] = parsed["watch"]
                st.session_state["trading_tickers"] = parsed["trade"]
                st.session_state["_ticker_selections_hydrated"] = True
        if st.session_state.pop("_ticker_selections_dirty", False):
            counter = int(st.session_state.get("_ticker_storage_revision", 0)) + 1
            st.session_state["_ticker_storage_revision"] = counter
            payload = serialize_selections(st.session_state)
            expression = (
                f"localStorage.setItem({json.dumps(STORAGE_KEY)}, "
                f"{json.dumps(payload)})"
            )
            streamlit_js_eval(
                js_expressions=expression, want_output=False,
                key=f"pdufa_ticker_write_{panel_id}_{counter}",
            )
        return True
    except (ImportError, AttributeError, RuntimeError, ValueError, TypeError):
        return False


def render_ticker_toggle_panel(panel_id, records, *, title=""):
    """Visible compact list with real +/- Streamlit buttons, paged for 700+ tickers.

    Call at the beginning of each section, not once per trial. Selections are
    shared by ticker across every PDUFA tab in this Streamlit browser session.
    """
    panel_id = re.sub(r"[^a-z0-9_]", "_", str(panel_id).lower())
    tickers = ticker_universe(records)
    st.markdown("""
    <style>
    div[class*="st-key-ticker_toggles_"] .stButton button {
      min-height:24px!important; height:24px!important; padding:0 4px!important;
      border:1px solid #333!important; border-radius:4px!important;
      font-size:13px!important; font-weight:800!important; line-height:1!important;
      width:34px!important; min-width:34px!important;
    }
    div[class*="st-key-ticker_toggles_"] .stButton button[kind="primary"] {
      background:#22863a!important; color:white!important; border-color:#18632c!important;
    }
    div[class*="st-key-ticker_toggles_"] .stButton button[kind="secondary"] {
      background:#fff!important; color:#111!important; border-color:#777!important;
    }
    div[class*="st-key-ticker_toggles_"] [data-testid="stHorizontalBlock"] {
      gap:4px!important; align-items:center!important;
    }
    </style>
    """, unsafe_allow_html=True)
    with st.container(key=f"ticker_toggles_{panel_id}"):
        if title:
            st.markdown("**" + title + "**")
        storage_available = _init_browser_selection(panel_id)
        if not tickers:
            st.caption("No valid ticker symbols in this section.")
            return
        watch = {clean_ticker(v) for v in st.session_state.get("watchlist", [])}
        trade = {clean_ticker(v) for v in st.session_state.get("trading_tickers", [])}
        st.caption(f"Watch {len(watch)} · Trading {len(trade)} · green − selected / white + add")
        filter_text = st.text_input(
            "Filter ticker", key=f"ticker_toggles_query_{panel_id}",
            label_visibility="collapsed", placeholder="Find ticker...",
        ).strip().upper()
        matched = [t for t in tickers if filter_text in t]
        if not matched:
            st.caption("No matching ticker.")
            return
        pages = max(1, math.ceil(len(matched) / ROWS_PER_PAGE))
        page_key = f"ticker_toggles_page_{panel_id}"
        selected_page = st.session_state.get(page_key, 1)
        if not isinstance(selected_page, int) or selected_page < 1 or selected_page > pages:
            st.session_state[page_key] = 1
        if pages > 1:
            st.selectbox("Page", range(1, pages + 1), key=page_key,
                         format_func=lambda value: f"{value} / {pages}")
        page = st.session_state.get(page_key, 1)
        first = (page - 1) * ROWS_PER_PAGE
        head = st.columns([2.1, 1, 1], gap="small")
        head[0].markdown("**Ticker**")
        head[1].markdown("**Watch**")
        head[2].markdown("**Trade**")
        for symbol in matched[first:first + ROWS_PER_PAGE]:
            cols = st.columns([2.1, 1, 1], gap="small")
            cols[0].markdown("**" + symbol + "**")
            with cols[1]:
                st.button("−" if symbol in watch else "+",
                          help=("Remove" if symbol in watch else "Add") + " " + symbol + " from Watchlist",
                          type="primary" if symbol in watch else "secondary",
                          key=f"ticker_toggle_{panel_id}_watch_{symbol}",
                          on_click=_toggle, args=(symbol, "watch"))
            with cols[2]:
                st.button("−" if symbol in trade else "+",
                          help=("Remove" if symbol in trade else "Add") + " " + symbol + " from Trading list (no broker orders)",
                          type="primary" if symbol in trade else "secondary",
                          key=f"ticker_toggle_{panel_id}_trade_{symbol}",
                          on_click=_toggle, args=(symbol, "trade"))
        if not storage_available:
            st.caption("Browser storage unavailable: selections last only for this session.")
        else:
            st.caption("Saved in this browser only; use the same device to see selections after a refresh.")
