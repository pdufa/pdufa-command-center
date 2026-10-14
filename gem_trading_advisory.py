"""Evidence-gated, read-only entry/exit observations for every GEM program.

Market metrics use only the SAVED per-ticker daily closes and volumes.
No OHLC, quotes, positions, order routing, or simulated/live trade prices.
Missing data is never inferred, and research status is never a BUY order.
"""
from __future__ import annotations

import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path


TRADE_COLUMNS = [
    "Trade assessment", "Trading rationale", "EOD as of", "EOD close",
    "SMA 20", "SMA 50", "RSI 14", "RVOL", "20D $ volume",
    "Prior 20D closing low", "Trading data gaps",
]


def _number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _safe_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _days_since_session(last, today):
    if last is None or last > today:
        return None
    current = last + timedelta(days=1)
    count = 0
    while current <= today:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return count


def load_market_rows(root="data"):
    """Load source-labeled EOD rows by exact ticker, refusing duplicates."""
    path = Path(root) / "step7_market_status.csv"
    if not path.is_file():
        return {}
    by_ticker, duplicates = {}, set()
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                ticker = str(record.get("ticker") or "").strip().upper()
                if not ticker:
                    continue
                if ticker in by_ticker:
                    duplicates.add(ticker)
                else:
                    by_ticker[ticker] = record
    except (OSError, UnicodeError, csv.Error):
        return {}
    for ticker in duplicates:
        del by_ticker[ticker]
    return by_ticker


def _bars(record, today):
    if not record:
        return []
    try:
        values = json.loads(record.get("price_bars_json") or "[]")
    except (ValueError, TypeError):
        return []
    if not isinstance(values, list):
        return []
    result = []
    seen = set()
    for value in values:
        if not isinstance(value, dict):
            return []
        day = _safe_date(value.get("date"))
        close = _number(value.get("close"))
        volume = _number(value.get("volume"))
        if (day is None or day > today or day in seen or close is None
                or close <= 0 or volume is None or volume < 0):
            return []
        result.append({"date": day, "close": close, "volume": volume})
        seen.add(day)
    result.sort(key=lambda x: x["date"])
    return result


def _rsi_14(prices):
    if len(prices) < 15:
        return None
    changes = [b - a for a, b in zip(prices, prices[1:])]
    avg_gain = sum(max(x, 0.0) for x in changes[:14]) / 14
    avg_loss = sum(max(-x, 0.0) for x in changes[:14]) / 14
    for move in changes[14:]:
        avg_gain = (avg_gain * 13 + max(move, 0.0)) / 14
        avg_loss = (avg_loss * 13 + max(-move, 0.0)) / 14
    if avg_loss == 0:
        return 100.0 if avg_gain else 50.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def _ema(values, period):
    if len(values) < period:
        return []
    start = sum(values[:period]) / period
    out = [None] * (period - 1) + [start]
    weight = 2 / (period + 1)
    for price in values[period:]:
        out.append(price * weight + out[-1] * (1 - weight))
    return out


def _macd(prices):
    # 60 sessions gives the EMA-26/9 signal a usable warm-up.
    if len(prices) < 60:
        return None
    fast, slow = _ema(prices, 12), _ema(prices, 26)
    lines = [fast[i] - slow[i] for i in range(25, len(prices))]
    signal = _ema(lines, 9)
    return {"macd": lines[-1], "signal": signal[-1],
            "bullish": lines[-1] > signal[-1]}


def assess_gem_trade(row, market_rows, status, today):
    """Separate clinical eligibility, market confirmation and exit warnings."""
    if not isinstance(today, date):
        raise TypeError("today must be a date")
    ticker = str(row.get("Ticker") or "").strip().upper()
    record = market_rows.get(ticker)
    bars = _bars(record, today)
    closes = [x["close"] for x in bars]
    eod = _safe_date(record.get("last_session")) if record else None
    consistency = bool(bars and eod == bars[-1]["date"]
                       and record.get("market_status") == "MARKET_UPDATED"
                       and str(record.get("market_source") or "").startswith("https://")
                       and _number(record.get("last_close_usd")) is not None
                       and abs(_number(record["last_close_usd"]) - closes[-1]) < 0.02)
    lag = _days_since_session(eod, today)
    fresh = bool(consistency and lag is not None and lag <= 2)
    price = closes[-1] if consistency else None
    sma20 = sum(closes[-20:]) / 20 if consistency and len(closes) >= 20 else None
    sma50 = sum(closes[-50:]) / 50 if consistency and len(closes) >= 50 else None
    rsi = _rsi_14(closes) if consistency else None
    rvol = _number(record.get("relative_volume")) if consistency else None
    if rvol is not None and rvol < 0:
        rvol = None
    dollar_volume = (sum(x["close"] * x["volume"] for x in bars[-20:]) / 20
                     if consistency and len(bars) >= 20 else None)
    support = min(closes[-21:-1]) if consistency and len(closes) >= 21 else None
    macd = _macd(closes) if consistency else None
    eligible = row.get("_eligible") is True
    fundamental_current = bool(status.get("feed_current")
                               and status.get("sec_financing_source_current"))
    exit_warning = "EXIT / FDA DECISION WARNING" in str(row.get("GEM Status") or "")
    breakdown = bool(price is not None and support is not None and price < support)
    if exit_warning:
        call, reason = ("EXIT RISK — REVIEW NOW",
                        "FDA timing/resolution warning; check positions and news immediately.")
    elif not eligible:
        missing = ("Phase 3 result and/or distinct second financing close "
                   "not independently verified for this exact program.")
        call, reason = "WAIT — BENCHMARKS UNVERIFIED", missing
    elif not fundamental_current:
        call, reason = ("WAIT — SOURCE RECHECK",
                        "Clinical/SEC source refresh is partial or stale.")
    elif not fresh:
        call, reason = ("WAIT — REFRESH MARKET DATA",
                        "Saved daily close/volume unavailable, inconsistent, or old.")
    elif breakdown:
        call, reason = ("EXIT RISK — SUPPORT BREAK",
                        "Latest close fell below prior 20-session closing low; review exposure.")
    elif any(v is None for v in (price, sma20, rsi, rvol, dollar_volume)):
        call, reason = ("WAIT — TECHNICAL DATA INCOMPLETE",
                        "Price, 20-day trend, RSI, volume or liquidity unverified.")
    elif dollar_volume < 5_000_000:
        call, reason = ("WATCH — THIN LIQUIDITY",
                        "20-day average close × shares traded is below $5M.")
    elif price < sma20:
        call, reason = ("WAIT — TREND NOT CONFIRMED",
                        "Price below its 20-session simple moving average.")
    elif rvol < 1.5:
        call, reason = ("WATCH — VOLUME NOT CONFIRMED",
                        "Relative volume below the illustrative 1.5× entry threshold.")
    elif not 45 <= rsi <= 65:
        call, reason = ("WATCH — RSI OUTSIDE BAND",
                        "RSI outside the illustrative 45–65 preferred entry band.")
    else:
        call, reason = ("ENTRY SETUP — MANUAL REVIEW",
                        "20-day trend, volume, RSI and liquidity pass provisional checks; "
                        "50-day trend, VWAP, ATR, spread and position risk still need review.")
    gaps = []
    if not consistency:
        gaps.append("EOD source/price unverified")
    if not fresh:
        gaps.append("EOD stale or missing")
    if sma50 is None:
        gaps.append("SMA50: need 50 closes")
    if macd is None:
        gaps.append("MACD: need 60 closes")
    gaps.extend(("ATR: no high/low", "VWAP: no intraday bars",
                 "Spread: no bid/ask", "R:R: no trade plan",
                 "Sector strength: no benchmark comparison"))
    return {
        "recommendation": call, "reason": reason, "date": eod if consistency else None,
        "fresh": fresh, "close": price, "sma20": sma20, "sma50": sma50,
        "rsi": rsi, "rvol": rvol, "dollar_volume": dollar_volume,
        "support": support, "macd": macd, "bars": bars if consistency else [],
        "source": record.get("market_source") if consistency else None,
        "gaps": "; ".join(gaps),
    }


def attach_trade_fields(rows, market_rows, status, today):
    """Provide the SAME source-gated assessment for every displayed/exported GEM."""
    enriched = []
    for row in rows:
        profile = assess_gem_trade(row, market_rows, status, today)
        entry = dict(row)
        entry.update({
            "Trade assessment": profile["recommendation"],
            "Trading rationale": profile["reason"],
            "EOD as of": str(profile["date"]) if profile["date"] else None,
            "EOD close": profile["close"],
            "SMA 20": profile["sma20"],
            "SMA 50": profile["sma50"],
            "RSI 14": profile["rsi"],
            "RVOL": profile["rvol"],
            "20D $ volume": profile["dollar_volume"],
            "Prior 20D closing low": profile["support"],
            "Trading data gaps": profile["gaps"],
        })
        enriched.append(entry)
    return enriched


def render_gem_trade_panel(row, market_rows, status, today):
    """Detailed per-stock Streamlit price chart, entry/exit metrics and reasons."""
    import pandas as pd
    import streamlit as st

    p = assess_gem_trade(row, market_rows, status, today)
    st.markdown("**ENTRY / EXIT MONITOR — " + p["recommendation"] + "**")
    st.caption(p["reason"] + " · Research only; no orders or assumed positions.")
    st.caption("Saved EOD market source: " + (str(p["source"]) if p["source"] else
                                             "unverified / unavailable") +
               " · As of: " + (str(p["date"]) if p["date"] else "unknown") +
               (" · STALE / CHECK SOURCE" if not p["fresh"] else " · recent saved EOD"))
    if p["bars"]:
        data = pd.DataFrame(p["bars"]).set_index("date")[["close"]].rename(
            columns={"close": "Closing price"})
        data["SMA 20"] = data["Closing price"].rolling(20).mean()
        st.line_chart(data, height=210, use_container_width=True)
    else:
        st.info("No consistent saved EOD series for this ticker; chart withheld.")
    fmt = lambda v, d=2: f"{v:,.{d}f}" if v is not None else "NOT AVAILABLE"
    rows = [
        ("Latest saved close", "$" + fmt(p["close"]) if p["close"] is not None else "NOT AVAILABLE",
         "Reference close only; not an executable quote"),
        ("Trend / 20-day SMA", fmt(p["sma20"]), "Prefer price above and holding"),
        ("50-day SMA", fmt(p["sma50"]), "Prefer above/reclaim; requires 50 saved sessions"),
        ("Relative volume", fmt(p["rvol"]) + "×" if p["rvol"] is not None else "NOT AVAILABLE",
         "Preferred entry ≥ 1.5×; illustrative threshold"),
        ("RSI (14)", fmt(p["rsi"], 1), "Preferred entry 45–65; overbought reversals warrant review"),
        ("20-day average $ volume", "$" + fmt(p["dollar_volume"], 0)
         if p["dollar_volume"] is not None else "NOT AVAILABLE",
         "Prefer ≥ $5M for tradability; not a hard GEM gate"),
        ("Previous 20-day closing low", "$" + fmt(p["support"]) if p["support"] is not None
         else "NOT AVAILABLE", "Closing-price support proxy, not intraday support/stop"),
        ("MACD / signal", ("BULLISH" if p["macd"]["bullish"] else "BEARISH")
         if p["macd"] is not None else "NOT AVAILABLE", "60+ sessions needed for indicator warm-up"),
        ("VWAP / ATR / spread", "NOT AVAILABLE", "No intraday bars, highs/lows or bid/ask; cannot infer"),
        ("Profit and stop plan", "NOT AVAILABLE", "2R/3R exits require a real entry and risk stop"),
        ("PDUFA manual exit", str(row.get("Planned Exit (-3 days)") or "NOT VERIFIED"),
         "Existing GEM planned exit: three calendar days before PDUFA; FDA can act early"),
    ]
    st.dataframe(pd.DataFrame(rows, columns=("Trading metric", "Observation", "Entry / exit interpretation")),
                 use_container_width=True, hide_index=True)
    st.caption("Indicator bands are unvalidated screening heuristics, not approval "
               "probabilities or advice to buy/sell. Data gaps: " + p["gaps"])
