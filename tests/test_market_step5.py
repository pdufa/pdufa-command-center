"""Step 5 offline market intelligence regression tests; never make live web requests."""
import csv
import io
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError

from market_step5 import (
    EXTRA_BOUNDS, WEIGHTS, _extra, clean_ticker, evaluate_market, fetch_stooq_daily,
    financial_context_asof, parse_ohlcv, pdufa_window, phase_check, rankings,
    read_history, save_snapshot,
)
from sec_step4 import save_snapshot as save_sec_snapshot

AS_OF = date(2026, 10, 10)
SOURCE = {"url": "https://clinicaltrials.gov/study/NCT01234567", "date": "2026-10-01"}
POST_SOURCE = {"url": "https://example.org/clinical-p3-readout", "date": "2026-10-05"}
PDUFA_SOURCE = {"url": "https://www.fda.gov/drugs", "date": "2026-10-02"}


def sample_bars(end=date(2026, 10, 9), n=42):
    dates = []
    d = end
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d)
        d -= timedelta(days=1)
    result = []
    for i, d in enumerate(reversed(dates)):
        close = 6.0 + 0.06 * i
        result.append({"date": d.isoformat(), "open": round(close - .05, 3),
                       "high": round(close + .5, 3), "low": round(close - .6, 3),
                       "close": round(close, 3), "volume": 300000 + i * 6000})
    return result


def as_csv(bars):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["date", "open", "high", "low", "close", "volume"])
    writer.writeheader()
    writer.writerows(bars)
    return buf.getvalue()


def pre(bars=None, ticker="ABCD", **kwargs):
    return evaluate_market(ticker, bars if bars is not None else sample_bars(), AS_OF, "PRE_RESULTS",
                           phase_evidence=SOURCE, **kwargs)


def post(bars=None, ticker="ABCD", **kwargs):
    return evaluate_market(ticker, bars if bars is not None else sample_bars(), AS_OF,
                           "POST_RESULTS", phase_evidence=POST_SOURCE,
                           readout_date="2026-09-25", **kwargs)


class MarketStep5Tests(unittest.TestCase):
    def test_schema_and_price_integrity_fail_closed(self):
        self.assertEqual(len(parse_ohlcv(as_csv(sample_bars()), AS_OF)), 42)
        with self.assertRaises(ValueError):
            parse_ohlcv("Date,Close\n2026-10-09,8\n", AS_OF)
        with self.assertRaises(ValueError):
            parse_ohlcv(as_csv(sample_bars() + [sample_bars()[-1]]), AS_OF)
        rows = sample_bars()
        rows[4] = {**rows[4], "volume": -100}
        with self.assertRaises(ValueError):
            parse_ohlcv(as_csv(rows), AS_OF)
        rows = sample_bars()
        rows[5] = {**rows[5], "low": rows[5]["high"] + 1}
        with self.assertRaises(ValueError):
            parse_ohlcv(as_csv(rows), AS_OF)
        self.assertEqual(clean_ticker("aBcD"), "ABCD")
        with self.assertRaises(ValueError):
            clean_ticker("ABCD/us")

    def test_pre_market_score_is_only_technical(self):
        r = pre()
        self.assertGreater(r["technical_score_0_100"], 0)
        self.assertLessEqual(r["technical_score_0_100"], 100)
        self.assertEqual(sum(WEIGHTS["PRE_RESULTS"].values()), 100)
        self.assertEqual(sum(r["technical_factor_points"].values()),
                         r["technical_score_0_100"])
        self.assertEqual(r["pdufa_window"], "NOT APPLICABLE — BEFORE RESULTS")
        self.assertIn("NOT FDA", r["score_type"])
        self.assertIn("RESEARCHER ASSERTION", r["phase_status"])
        self.assertIsNone(r["extra_market_observations"].get("borrow_fee_pct"))

    def test_post_phase_has_distinct_weights_and_date_window(self):
        r = post(pdufa_date="2026-12-01", pdufa_evidence=PDUFA_SOURCE)
        self.assertEqual(r["pdufa_window"], "60–31 DAYS")
        self.assertGreater(r["technical_score_0_100"], 0)
        self.assertEqual(sum(WEIGHTS["POST_RESULTS"].values()), 100)
        self.assertNotEqual(r["weights"], pre()["weights"])

    def test_pdufa_windows_inclusive(self):
        for days, expected in [(100, "OVER 90 DAYS"), (90, "90–61 DAYS"),
                               (61, "90–61 DAYS"), (60, "60–31 DAYS"),
                               (31, "60–31 DAYS"), (30, "30–14 DAYS"),
                               (14, "30–14 DAYS"), (13, "13–1 DAYS"),
                               (1, "13–1 DAYS"), (0, "DECISION DATE"),
                               (-1, "PAST PDUFA DATE — REVALIDATE")]:
            d = (AS_OF + timedelta(days=days)).isoformat()
            self.assertEqual(pdufa_window("POST_RESULTS", AS_OF, d, PDUFA_SOURCE),
                             expected, days)

    def test_missing_phase_evidence_rejects_score_but_retains_metrics(self):
        r = evaluate_market("ABCD", sample_bars(), AS_OF, "PRE_RESULTS")
        self.assertIsNone(r["technical_score_0_100"])
        self.assertIsNotNone(r["market_indicators"].get("momentum_30_session_pct"))
        self.assertIn("MISSING DATED PHASE EVIDENCE", r["phase_status"])

    def test_post_requires_actual_readout_and_no_lookahead_evidence(self):
        self.assertIn("REVIEW", phase_check("POST_RESULTS", AS_OF, SOURCE))
        self.assertIn("REVIEW", phase_check("POST_RESULTS", AS_OF, POST_SOURCE,
                                          "2026-11-01"))
        self.assertIn("REVIEW", phase_check("POST_RESULTS", AS_OF,
                                          {"url": POST_SOURCE["url"], "date": "2026-08-01"},
                                          "2026-09-25"))
        self.assertIn("REVIEW", phase_check("PRE_RESULTS", AS_OF, SOURCE,
                                          "2026-09-25"))
        future = {"url": SOURCE["url"], "date": "2026-12-01"}
        self.assertIsNone(evaluate_market("ABCD", sample_bars(), AS_OF,
                         "PRE_RESULTS", phase_evidence=future)["technical_score_0_100"])

    def test_price_future_data_is_excluded_not_leaked(self):
        base = sample_bars()
        future = {**base[-1], "date": "2026-10-15", "close": 500.0,
                  "open": 499.0, "high": 501.0, "low": 498.0, "volume": 99999999}
        a = pre(base)
        b = pre(base + [future])
        self.assertEqual(a["technical_score_0_100"], b["technical_score_0_100"])
        self.assertEqual(a["market_indicators"], b["market_indicators"])
        self.assertEqual(len(b["recent_bars_used"]), 40)

    def test_stale_price_and_insufficient_sessions_not_ranked(self):
        r = pre(sample_bars(end=date(2026, 9, 15)))
        self.assertIsNone(r["technical_score_0_100"])
        self.assertIn("older than 7", " ".join(r["review_flags"]))
        r = pre(sample_bars(n=30))
        self.assertIsNone(r["technical_score_0_100"])
        self.assertIn("31", " ".join(r["review_flags"]))

    def test_optional_indicators_require_provenance_and_freshness(self):
        extras = {"short_interest_pct_float": {
            "value": 22.1, "url": "https://www.finra.org/", "date": "2026-09-28"},
                  "implied_volatility_pct": {
                      "value": 150, "url": "http://example.com", "date": "2026-10-09"},
                  "borrow_fee_pct": {
                      "value": 99999, "url": "https://example.com", "date": "2026-10-09"},
                  "institutional_holding_change_pct": {
                      "value": 14, "url": "https://www.sec.gov/", "date": "2026-01-15"}}
        r = pre(extras=extras)
        self.assertIn("short_interest_pct_float", r["extra_market_observations"])
        self.assertEqual(r["coverage"]["short_interest_pct_float"], "OBSERVED")
        self.assertEqual(r["coverage"]["implied_volatility_pct"], "NOT VERIFIED")
        self.assertEqual(r["coverage"]["borrow_fee_pct"], "NOT VERIFIED")
        self.assertEqual(r["coverage"]["institutional_holding_change_pct"], "NOT VERIFIED")
        self.assertEqual(len(r["review_flags"]), 3)
        self.assertAlmostEqual(r["technical_score_0_100"], pre()["technical_score_0_100"])

    def test_stooq_fake_network_parse_and_http_errors(self):
        price_csv = as_csv(sample_bars())
        class Response:
            def __init__(self, data):
                self.data = data
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self, max_bytes):
                return self.data
        calls = []
        def fake(req, timeout):
            calls.append(req.full_url)
            return Response(price_csv.encode())
        bars, source = fetch_stooq_daily("ABCD", AS_OF, opener=fake)
        self.assertEqual(len(bars), 42)
        self.assertIn("stooq.com/q/d/l", calls[0])
        self.assertIn("REVIEW", source["issuer_mapping"])
        def blocked(req, timeout):
            raise HTTPError(req.full_url, 403, "Forbidden", None, None)
        with self.assertRaises(RuntimeError):
            fetch_stooq_daily("ABCD", AS_OF, opener=blocked)
        with self.assertRaises(ValueError):
            fetch_stooq_daily("ABCD", "2099-01-01", opener=fake)

    def test_database_revision_idempotency_and_rankings_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "market.sqlite3"
            r = pre()
            id1 = save_snapshot(r, path)
            self.assertEqual(save_snapshot(r, path), id1)
            second = post()
            save_snapshot(second, path)
            other = pre(ticker="EFGH")
            save_snapshot(other, path)
            future = dict(r, as_of="2026-10-09")
            save_snapshot(future, path)
            r_changed = json.loads(json.dumps(r))
            r_changed["technical_score_0_100"] = 99
            save_snapshot(r_changed, path)
            rows = read_history(path)
            self.assertEqual(len(rows), 5)
            score_rows = rankings(rows, AS_OF.isoformat(), "PRE_RESULTS")
            self.assertEqual(len(score_rows), 2)
            self.assertEqual(score_rows[0]["ticker"], "ABCD")
            self.assertEqual(score_rows[0]["score"], 99)
            self.assertEqual(len(rankings(rows, AS_OF.isoformat(), "POST_RESULTS")), 1)
            self.assertEqual(read_history(path, "EFGH")[0]["ticker"], "EFGH")

    def test_financial_asof_does_not_leak_future_sec_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sec.sqlite"
            item = {
                "ticker": "ABCD", "cik": "0001234567", "as_of": "2026-10-08",
                "cash_runway_risk": "HIGH", "runway_months_cash_only": 4.1,
                "evidence": {"cash": {"filed": "2026-10-07"}}}
            save_sec_snapshot(item, path)
            self.assertIsNone(financial_context_asof("ABCD", "2026-09-01", path))
            self.assertEqual(financial_context_asof("ABCD", "2026-10-10", path)["cash_runway_months"], 4.1)
            future = dict(item)
            future["as_of"] = "2026-10-09"
            future["evidence"] = {"cash": {"filed": "2026-11-01"}}
            save_sec_snapshot(future, path)
            self.assertEqual(financial_context_asof("ABCD", "2026-10-10", path)["financial_as_of"],
                             "2026-10-08")


if __name__ == "__main__":
    unittest.main()
