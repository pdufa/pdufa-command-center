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

from .legacy_gem_base_analysis import detect_closing_base, base_chart_frame


TRADE_COLUMNS = [
    "Trade assessment", "Trading rationale", "EOD as of", "EOD close",
    "SMA 20", "SMA 50", "RSI 14", "RVOL", "20D $ volume",
    "Prior 20D closing low", "Trading data gaps",
    "Base status", "Base support", "Base resistance", "Base support touches",
    "Base width %", "Base contraction ratio", "Base volume ratio",
    "Base breakout RVOL",
    "Entry Score /100", "Entry Coverage /100", "Entry Score Status",
    "Exit Risk /100", "Exit Coverage /100", "Exit Risk Status",
    "Entry Score Breakdown", "Exit Risk Breakdown",
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
    base = detect_closing_base(bars if consistency else [], fresh=fresh)
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
        missing = ("Successful exact-program Phase 3 result not independently verified. "
                   "A second financing closure is optional; risk checks remain separate.")
        call, reason = "WAIT — PHASE 3 NOT VERIFIED", missing
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
        "base": base,
        "source": record.get("market_source") if consistency else None,
        "gaps": "; ".join(gaps),
    }



def _score_gem_trade(row, profile, status):
    """Independent *provisional* trading scores, never the GEM quality rank.

    A component without source evidence is not zero; its entire weight stays
    outside the coverage numerator. Price-only bars cannot furnish an actual
    stop, ATR, spread or executable reward-to-risk. No observed score is a BUY.
    """
    entry, exit_risk = [], []

    def factor(bucket, label, weight, points, evidence):
        if points is not None and not (0 <= points <= weight):
            raise ValueError("GEM factor outside its declared weight")
        bucket.append((label, weight, points, evidence))

    def summary(bucket):
        coverage = sum(weight for _, weight, points, _ in bucket if points is not None)
        total = sum(points for _, _, points, _ in bucket if points is not None)
        # Suppress numeric scores if less than half the weight is auditable.
        return (int(total) if coverage >= 50 else None, coverage)

    p = profile
    close, sma20, sma50 = p["close"], p["sma20"], p["sma50"]
    bars = p["bars"]
    rv, dv = p["rvol"], p["dollar_volume"]
    support = p["support"]
    days = row.get("Days to PDUFA")
    days_verified = (row.get("PDUFA Date Verified") is True and
                     isinstance(days, int) and not isinstance(days, bool))
    risks = str(row.get("Risks / Evidence Gaps") or "").lower()
    negative = ("verified phase 3 negative outcome" in risks or
                "conflicting clinical/regulatory evidence" in risks)
    dilution = "new or unresolved dilution" in risks
    diluted_unknown = "dilution exposure not independently cleared" in risks
    low_runway = "under 12 months" in risks
    resolved = "fda event already resolved" in risks
    is_exit_warning = (
        "EXIT / FDA DECISION WARNING" in str(row.get("GEM Status") or "")
        or (days_verified and days <= 3) or resolved
    )
    market_current = bool(p["fresh"] and status.get("feed_current")
                          and status.get("sec_financing_source_current"))
    if not market_current:
        return {
            "entry": None, "entry_coverage": 0,
            "entry_status": "UNAVAILABLE — RECHECK EOD / CLINICAL / SEC SOURCES",
            "exit_risk": None, "exit_coverage": 0,
            "exit_status": ("HARD EXIT WARNING — REVIEW NOW" if is_exit_warning
                            else "UNAVAILABLE — RECHECK EOD / CLINICAL / SEC SOURCES"),
            "entry_factors": [], "exit_factors": [],
        }

    if close is not None and sma20 is not None and sma50 is not None:
        trend = (10 if close >= sma20 else 0) + (10 if close >= sma50 else 0)
        trend += 5 if sma20 >= sma50 else 0
        factor(entry, "Price trend", 25, trend, "Close vs SMA20/SMA50; SMA20 vs SMA50")
        factor(exit_risk, "Deteriorating trend", 15,
               (10 if close < sma20 else 0) + (5 if sma20 < sma50 else 0),
               "Below SMA20; SMA20 below SMA50")
    else:
        factor(entry, "Price trend", 25, None, "Need 50 verified daily closes")
        factor(exit_risk, "Deteriorating trend", 15, None, "Need SMA20 and SMA50")

    if rv is not None and dv is not None:
        factor(entry, "Volume / liquidity", 20,
               (10 if rv >= 1.5 else 0) + (10 if dv >= 5_000_000 else 0),
               "RVOL >=1.5x; 20D average dollar volume >=$5M")
        pressure = (len(bars) >= 2 and close is not None and sma20 is not None
                    and close < bars[-2]["close"] and close < sma20 and rv >= 1.5)
        factor(exit_risk, "Selling pressure / liquidity", 10,
               (5 if pressure else 0) + (5 if dv < 5_000_000 else 0),
               "High-volume downtrend; dollar liquidity <$5M")
    else:
        factor(entry, "Volume / liquidity", 20, None, "Missing RVOL or average $ volume")
        factor(exit_risk, "Selling pressure / liquidity", 10, None,
               "Missing verified relative / dollar volume")

    if close is not None and support is not None and sma20 is not None and len(bars) >= 21:
        # Daily-close proxies are NOT an intraday stop, support or fill.
        prior_high = max(b["close"] for b in bars[-21:-1])
        location = (10 if support <= close <= support * 1.12 else 0)
        location += 10 if support <= close <= prior_high * 1.05 else 0
        factor(entry, "Price location (close proxy)", 20, location,
               "Within 12% above prior 20D closing low; not >5% above 20D high")
        factor(exit_risk, "20D closing-support break", 15,
               15 if close < support else 0,
               "Latest close below previous 20D closing low")
    else:
        factor(entry, "Price location (close proxy)", 20, None,
               "Need 21 verified daily closes")
        factor(exit_risk, "20D closing-support break", 15, None,
               "Need previous 20-session closing low")

    factor(entry, "Trade plan / spread / reward-risk", 20, None,
           "No validated ATR, quotes, stop and target in saved GEM feed")
    factor(exit_risk, "Position-specific stop violation", 15, None,
           "No confirmed held position and broker stop price")
    if days_verified:
        timing = (15 if 30 <= days <= 90 else 10 if 91 <= days <= 180
                  else 7 if 14 <= days <= 29 else 0)
        factor(entry, "Verified PDUFA timing", 15, timing, f"{days} days until PDUFA")
        urgency = (25 if days <= 3 else 20 if days <= 7
                   else 12 if days <= 14 else 5 if days <= 30 else 0)
        factor(exit_risk, "PDUFA decision proximity", 25, urgency,
               f"{days} days until source-verified date")
    elif resolved:
        factor(entry, "Verified PDUFA timing", 15, None,
               "Resolved FDA event; not a new entry")
        factor(exit_risk, "PDUFA decision proximity", 25, 25,
               "Recorded FDA decision / no pre-event entry")
    else:
        factor(entry, "Verified PDUFA timing", 15, None,
               "Exact PDUFA date unverified or unknown")
        factor(exit_risk, "PDUFA decision proximity", 25, None,
               "Exact PDUFA date unverified or unknown")

    if negative:
        news_points = 20
    elif dilution:
        news_points = 15
    elif low_runway:
        news_points = 10
    elif diluted_unknown:
        news_points = None
    elif "no flagged issue in saved data" in risks:
        news_points = 0
    else:
        news_points = None
    factor(exit_risk, "Clinical / financing risk", 20, news_points,
           "Clinical conflict/failure, dilution or runway risk; unknown stays unscored")

    entry_total, entry_coverage = summary(entry)
    exit_total, exit_coverage = summary(exit_risk)
    if row.get("_eligible") is not True or negative:
        entry_total = None
        entry_status = "NOT ELIGIBLE — VERIFIED PHASE 3 / CLINICAL RISK"
    elif is_exit_warning:
        entry_total = None
        entry_status = "NO NEW ENTRY — PDUFA EXIT / FDA DECISION"
    elif p["recommendation"].startswith("EXIT RISK"):
        entry_total = None
        entry_status = "NO NEW ENTRY — PRICE SUPPORT WARNING"
    elif entry_total is None:
        entry_status = "UNAVAILABLE — LESS THAN 50/100 SOURCE COVERAGE"
    else:
        entry_status = f"PROVISIONAL — {entry_coverage}/100 COVERED; NO BUY SIGNAL"

    if is_exit_warning or p["recommendation"].startswith("EXIT RISK"):
        exit_status = "HARD EXIT WARNING — REVIEW NOW; SCORE DOES NOT OVERRIDE"
    elif exit_total is None:
        exit_status = "UNAVAILABLE — LESS THAN 50/100 SOURCE COVERAGE"
    else:
        exit_status = f"PROVISIONAL WATCH RISK — {exit_coverage}/100 COVERED; NO POSITION ASSUMED"
    return {
        "entry": entry_total, "entry_coverage": entry_coverage,
        "entry_status": entry_status,
        "exit_risk": exit_total, "exit_coverage": exit_coverage,
        "exit_status": exit_status,
        "entry_factors": entry, "exit_factors": exit_risk,
    }


def attach_trade_fields(rows, market_rows, status, today):
    """Provide the SAME source-gated assessment for every displayed/exported GEM."""
    enriched = []
    for row in rows:
        profile = assess_gem_trade(row, market_rows, status, today)
        scores = _score_gem_trade(row, profile, status)
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
            "Base status": profile["base"]["status"],
            "Base support": profile["base"]["support"],
            "Base resistance": profile["base"]["resistance"],
            "Base support touches": profile["base"]["touches"],
            "Base width %": profile["base"]["width_pct"],
            "Base contraction ratio": profile["base"]["contraction"],
            "Base volume ratio": profile["base"]["volume_ratio"],
            "Base breakout RVOL": profile["base"]["breakout_rvol"],
            "Entry Score /100": scores["entry"],
            "Entry Coverage /100": scores["entry_coverage"],
            "Entry Score Status": scores["entry_status"],
            "Exit Risk /100": scores["exit_risk"],
            "Exit Coverage /100": scores["exit_coverage"],
            "Exit Risk Status": scores["exit_status"],
            "Entry Score Breakdown": "; ".join(
                f"{name}: {value if value is not None else 'N/A'}/{weight}"
                for name, weight, value, _ in scores["entry_factors"]),
            "Exit Risk Breakdown": "; ".join(
                f"{name}: {value if value is not None else 'N/A'}/{weight}"
                for name, weight, value, _ in scores["exit_factors"]),
        })
        enriched.append(entry)
    return enriched


def render_base_formation_chart(profile, *, compact=False):
    """Visible support/resistance, SMA20/SMA50, volume and fail-closed base status."""
    import pandas as pd
    import streamlit as st

    base = profile["base"]
    st.markdown("**20-SESSION BASE FORMATION — DAILY-CLOSE OBSERVATIONS**")
    state = base["status"]
    if state.startswith("SUPPORT BREAK"):
        st.warning(state)
    elif state.startswith("STALE") or state.startswith("NOT AVAILABLE"):
        st.info(state)
    else:
        st.caption("BASE STATUS: " + state + " — screen only, not confirmed accumulation or an entry signal")
    bars = profile["bars"]
    if not bars:
        st.info("No consistent source-linked saved daily close/volume series. Base chart withheld.")
        return
    frame = pd.DataFrame(base_chart_frame(bars, base)).set_index("date")
    st.line_chart(
        frame[["Close", "SMA 20", "SMA 50",
               "Base support (closing)", "Base resistance (closing)"]],
        height=240 if compact else 285, use_container_width=True,
    )
    st.caption(
        "Support and resistance are rolling levels computed from the preceding "
        "20 daily closes at each plotted session (no future-price lookahead). "
        "They appear only over the most recent 21 sessions. "
        "These are closing-price proxies, not intraday support/resistance or executable stops."
    )
    money = lambda value: "$" + format(value, ",.2f") if value is not None else "NOT AVAILABLE"
    scalar = lambda value, unit="": format(value, ",.2f") + unit if value is not None else "NOT AVAILABLE"
    measurements = [
        {"Check": "Closing support / resistance", "Observed": money(base["support"]) + " / " + money(base["resistance"]),
         "Interpretation": "20 previous sessions; approximate zone rather than exact intraday level"},
        {"Check": "Separated support tests", "Observed": str(base["touches"]) if base["touches"] is not None else "NOT AVAILABLE",
         "Interpretation": "Touches within 3% of the closing low, at least 3 sessions apart; prefer 2+"},
        {"Check": "Range width", "Observed": scalar(base["width_pct"], "%"),
         "Interpretation": "Illustrative tighter range <=18%; not a validated threshold"},
        {"Check": "Price-range contraction", "Observed": scalar(base["contraction"], "×"),
         "Interpretation": "Latest 5 close-range vs preceding 10; <=0.75× suggests contraction"},
        {"Check": "Volume dry-up", "Observed": scalar(base["volume_ratio"], "×"),
         "Interpretation": "Latest 5 average volume vs prior 15; <=0.85× suggests declining participation"},
        {"Check": "Breakout volume", "Observed": scalar(base["breakout_rvol"], "×"),
         "Interpretation": "Current day's volume vs previous 20 sessions; 1.5× is illustrative"},
    ]
    st.dataframe(pd.DataFrame(measurements), hide_index=True, use_container_width=True,
                 height=245 if compact else 270)
    with st.expander("SHOW SAVED DAILY VOLUME BARS", expanded=False):
        st.bar_chart(frame[["Volume"]], height=150, use_container_width=True)
    st.caption(
        "Data: " + (str(profile["source"]) if profile["source"] else "UNVERIFIED") +
        " · EOD: " + (str(profile["date"]) if profile["date"] else "UNKNOWN") +
        (" · RECENT" if profile["fresh"] else " · STALE / UNVERIFIED") +
        ". True ATR needs high/low/close, VWAP needs appropriate intraday data, "
        "and genuine support tests require reviewing the TradingView candlesticks. "
        "A potential base never overrides clinical, SEC, or entry-risk gates."
    )


def render_base_chart_for_ticker(ticker, market_rows, today, *, compact=True):
    """Same base view for GEM JR and GEM, without claiming benchmark eligibility."""
    profile = assess_gem_trade(
        {"Ticker": ticker, "_eligible": False}, market_rows, {}, today,
    )
    render_base_formation_chart(profile, compact=compact)


def render_gem_trade_panel(row, market_rows, status, today):
    """Detailed per-stock Streamlit price chart, entry/exit metrics and reasons."""
    import pandas as pd
    import streamlit as st

    p = assess_gem_trade(row, market_rows, status, today)
    scored = _score_gem_trade(row, p, status)
    st.markdown("**ENTRY / EXIT MONITOR — " + p["recommendation"] + "**")
    st.markdown(
        f"**GEM Quality: {row.get('GEM Score /100') if row.get('_eligible') else 'UNSCORED'}/100"
        f"  ·  Entry: {scored['entry'] if scored['entry'] is not None else 'N/A'}/100"
        f"  ·  Exit risk: {scored['exit_risk'] if scored['exit_risk'] is not None else 'N/A'}/100**"
    )
    st.caption("ENTRY: " + scored["entry_status"] + " · EXIT: " + scored["exit_status"])
    with st.expander("ENTRY / EXIT SCORING FACTORS + MISSING EVIDENCE", expanded=False):
        for label, fields in (("Entry strength", scored["entry_factors"]),
                              ("Exit risk", scored["exit_factors"])):
            st.markdown("**" + label + "**")
            st.dataframe(pd.DataFrame([
                {"Factor": name,
                 "Earned": points if points is not None else "NOT AVAILABLE",
                 "Maximum": weight, "Rule / source limitation": evidence}
                for name, weight, points, evidence in fields
            ]), hide_index=True, use_container_width=True)
        st.caption("Coverage measures observable weight, not predictive confidence. "
                   "No ATR, spread, broker stop or position-sized risk has been inferred.")
    st.caption(p["reason"] + " · Research only; no orders or assumed positions.")
    st.caption("Saved EOD market source: " + (str(p["source"]) if p["source"] else
                                             "unverified / unavailable") +
               " · As of: " + (str(p["date"]) if p["date"] else "unknown") +
               (" · STALE / CHECK SOURCE" if not p["fresh"] else " · recent saved EOD"))
    render_base_formation_chart(p)
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
        ("Base formation status", p["base"]["status"],
         "Research-only detection from validated daily close/volume"),
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
