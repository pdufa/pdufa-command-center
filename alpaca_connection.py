"""Read-only Alpaca paper account and IEX market-data diagnostics.

Credentials are read from Streamlit Secrets at request time. No orders are
submitted, no personal account fields are displayed, and no secret value is
ever written to the Streamlit page or application logs.
"""


def load_paper_credentials(secrets):
    """Return ((key, secret), None) or (None, safe_setup_message)."""
    try:
        api_key = str(secrets.get("ALPACA_API_KEY", "") or "").strip()
        secret_key = str(secrets.get("ALPACA_SECRET_KEY", "") or "").strip()
        paper = secrets.get("ALPACA_PAPER", True)
    except (FileNotFoundError, KeyError):
        return None, (
            "No Streamlit Secrets configuration was found. Add ALPACA_API_KEY, "
            "ALPACA_SECRET_KEY and ALPACA_PAPER = true in your app's Secrets settings."
        )

    if not (paper is True or
            (isinstance(paper, str) and paper.strip().lower() == "true")):
        return None, (
            "Alpaca connection blocked: ALPACA_PAPER must be true. "
            "This dashboard does not enable live brokerage access."
        )

    if not api_key or not secret_key:
        return None, (
            "Alpaca keys are not both configured. Save ALPACA_API_KEY and "
            "ALPACA_SECRET_KEY in Streamlit app Secrets (not GitHub)."
        )

    if api_key.startswith("YOUR_") or secret_key.startswith("YOUR_"):
        return None, "Replace the ALPACA_* placeholder values with your paper keys in Streamlit Secrets."

    return (api_key, secret_key), None


def _safe_failure(exc):
    """Translate common Alpaca errors without exposing request/credential data."""
    status_code = getattr(exc, "status_code", None)
    if str(status_code) in ("401", "403"):
        return "Alpaca rejected access. Check that the saved keys belong to your PAPER account."
    if str(status_code) == "429":
        return "Alpaca rate limit reached. Try the test later."
    return "The request failed. Check your Alpaca paper keys, API permissions, and network availability."


def verify_paper_account(api_key, secret_key, client_factory=None):
    """Only GET /account on the paper endpoint; never submit an order."""
    try:
        if client_factory is None:
            from alpaca.trading.client import TradingClient
            client_factory = TradingClient
        client = client_factory(api_key=api_key, secret_key=secret_key, paper=True)
        account = client.get_account()
        if account is None:
            return False, "Alpaca returned no paper account information."
        return True, "Paper Trading authentication succeeded (read-only)."
    except Exception as exc:
        return False, _safe_failure(exc)


def verify_iex_market_data(api_key, secret_key, client_factory=None, request_factory=None):
    """Request a single SPY IEX bar; not a consolidated market-data validation."""
    try:
        if client_factory is None:
            from alpaca.data.historical import StockHistoricalDataClient
            client_factory = StockHistoricalDataClient
        if request_factory is None:
            from alpaca.data.requests import StockLatestBarRequest
            from alpaca.data.enums import DataFeed
            request_factory = lambda: StockLatestBarRequest(
                symbol_or_symbols="SPY", feed=DataFeed.IEX
            )
        client = client_factory(api_key=api_key, secret_key=secret_key)
        latest = client.get_stock_latest_bar(request_factory())
        if not latest or not latest.get("SPY"):
            return False, "Alpaca returned no SPY IEX bar. The feed may be unavailable."
        return True, "SPY IEX market-data request succeeded (read-only; IEX is not the full market)."
    except Exception as exc:
        return False, _safe_failure(exc)


def render_alpaca_connection_panel():
    """Display safe operator-initiated diagnostics in PDUFA > WT."""
    import streamlit as st

    with st.expander("ALPACA — PAPER CONNECTION STATUS", expanded=False):
        st.caption(
            "Read-only API checks. Paper Trading only. No orders or account balances "
            "are requested for display. Existing TradingView charts remain unchanged."
        )
        credentials, setup_message = load_paper_credentials(st.secrets)
        if setup_message:
            st.warning(setup_message)
            st.caption(
                "In Streamlit Community Cloud: open the app menu → Settings → Secrets, "
                "save the keys, then restart the app if necessary."
            )
            return

        st.success("Alpaca paper credentials found in Streamlit Secrets (values hidden).")
        left, right = st.columns(2)
        with left:
            if st.button("TEST PAPER CONNECTION", key="alpaca_test_paper_account"):
                ok, message = verify_paper_account(*credentials)
                if ok:
                    st.success(message)
                else:
                    st.error(message)
        with right:
            if st.button("TEST SPY MARKET DATA (IEX)", key="alpaca_test_iex_data"):
                ok, message = verify_iex_market_data(*credentials)
                if ok:
                    st.success(message)
                else:
                    st.error(message)
        st.caption(
            "These tests do not feed GEM scores or nightly scans yet. An IEX-only "
            "feed cannot be assumed to provide consolidated volume/price signals."
        )
