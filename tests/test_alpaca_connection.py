"""Offline regression tests for the read-only Alpaca connection panel."""

import unittest
from types import SimpleNamespace

from alpaca_connection import (
    load_paper_credentials,
    verify_paper_account,
    verify_iex_market_data,
)


GOOD = {
    "ALPACA_API_KEY": "test-paper-id",
    "ALPACA_SECRET_KEY": "test-paper-secret",
    "ALPACA_PAPER": True,
}


class TestAlpacaConnection(unittest.TestCase):
    def test_missing_secrets(self):
        credentials, message = load_paper_credentials({})
        self.assertIsNone(credentials)
        self.assertIn("not both configured", message)

    def test_missing_secrets_file(self):
        class MissingSecrets:
            def get(self, *_args, **_kwargs):
                raise FileNotFoundError("missing")
        credentials, message = load_paper_credentials(MissingSecrets())
        self.assertIsNone(credentials)
        self.assertIn("No Streamlit Secrets", message)

    def test_block_live_mode(self):
        credentials, message = load_paper_credentials({**GOOD, "ALPACA_PAPER": False})
        self.assertIsNone(credentials)
        self.assertIn("blocked", message)

    def test_block_live_mode_string(self):
        credentials, message = load_paper_credentials({**GOOD, "ALPACA_PAPER": "false"})
        self.assertIsNone(credentials)
        self.assertIn("blocked", message)

    def test_read_both_paper_keys(self):
        self.assertEqual(load_paper_credentials(GOOD), (
            ("test-paper-id", "test-paper-secret"), None
        ))

    def test_placeholder_is_rejected(self):
        credentials, message = load_paper_credentials({
            **GOOD, "ALPACA_API_KEY": "YOUR_API_KEY_ID"
        })
        self.assertIsNone(credentials)
        self.assertIn("placeholder", message)

    def test_paper_account_is_read_only(self):
        calls = []
        class FakeTradingClient:
            def __init__(self, **kwargs):
                calls.append(kwargs)
            def get_account(self):
                calls.append("get_account")
                return SimpleNamespace(status="ACTIVE", account_number="redacted")
        ok, message = verify_paper_account(
            GOOD["ALPACA_API_KEY"], GOOD["ALPACA_SECRET_KEY"],
            client_factory=FakeTradingClient
        )
        self.assertTrue(ok)
        self.assertEqual(calls[-1], "get_account")
        self.assertIs(calls[0]["paper"], True)
        self.assertNotIn("account_number", message)
        self.assertNotIn("redacted", message)

    def test_safe_error_does_not_expose_secret(self):
        class FakeClient:
            def __init__(self, **_kwargs):
                pass
            def get_account(self):
                raise RuntimeError("test-paper-secret should never be displayed")
        ok, message = verify_paper_account(
            GOOD["ALPACA_API_KEY"], GOOD["ALPACA_SECRET_KEY"],
            client_factory=FakeClient
        )
        self.assertFalse(ok)
        self.assertNotIn("test-paper-secret", message)

    def test_market_data_single_symbol(self):
        calls = []
        class FakeDataClient:
            def __init__(self, **kwargs):
                calls.append(kwargs)
            def get_stock_latest_bar(self, request):
                calls.append(request)
                return {"SPY": SimpleNamespace(close=1)}
        ok, message = verify_iex_market_data(
            GOOD["ALPACA_API_KEY"], GOOD["ALPACA_SECRET_KEY"],
            client_factory=FakeDataClient,
            request_factory=lambda: "SPY-IEX-REQUEST"
        )
        self.assertTrue(ok)
        self.assertEqual(calls[-1], "SPY-IEX-REQUEST")
        self.assertIn("IEX", message)

    def test_market_data_missing_bar(self):
        class FakeDataClient:
            def __init__(self, **_kwargs):
                pass
            def get_stock_latest_bar(self, _request):
                return {}
        ok, _ = verify_iex_market_data(
            "a", "b", client_factory=FakeDataClient,
            request_factory=lambda: object()
        )
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
