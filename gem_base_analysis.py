"""Conservative base-formation observations from verified daily close/volume.

Not an OHLC support-zone detector, institutional accumulation signal, or
trade recommendation. Levels are computed solely from the PREVIOUS 20 closes
and do not peek at today's close when defining resistance/support.
"""
from __future__ import annotations

from statistics import mean


def detect_closing_base(bars, *, fresh=False):
    """Evaluate one possible 20-session base using EOD close/volume only.

    All bars must already be validated and chronologically sorted by the
    market source parser. Current bar is excluded from the base boundaries.
    These screening heuristics are illustrative, not backtested thresholds.
    """
    empty = {
        "status": "NOT AVAILABLE — NEED 21 VERIFIED DAILY CLOSES",
        "support": None, "resistance": None, "touches": None,
        "width_pct": None, "contraction": None, "volume_ratio": None,
        "breakout_rvol": None, "confirmed_breakout": False,
        "support_break": False,
    }
    if len(bars) < 21:
        return empty
    history = bars[-21:-1]
    closes = [float(x["close"]) for x in history]
    volumes = [float(x["volume"]) for x in history]
    now_close = float(bars[-1]["close"])
    now_volume = float(bars[-1]["volume"])
    support, resistance = min(closes), max(closes)
    if support <= 0 or any(v < 0 for v in volumes) or now_volume < 0:
        return empty
    width = (resistance - support) / support * 100
    # Distinct support TESTS require leaving the 3% band and then
    # re-entering at least three sessions later. Consecutive days parked at
    # support are one test, not several independent buyer defenses.
    separated = []
    in_zone_before = False
    for i, price in enumerate(closes):
        in_zone = price <= support * 1.03
        if in_zone and not in_zone_before and (not separated or i - separated[-1] >= 3):
            separated.append(i)
        in_zone_before = in_zone
    recent = closes[-5:]
    earlier = closes[-15:-5]
    recent_range = max(recent) - min(recent)
    earlier_range = max(earlier) - min(earlier)
    contraction = (recent_range / earlier_range
                   if earlier_range > 0 else None)
    prior15_avg = mean(volumes[-15:])
    recent5_avg = mean(float(x["volume"]) for x in bars[-5:])
    volume_ratio = (recent5_avg / prior15_avg
                    if prior15_avg > 0 else None)
    avg20 = mean(volumes)
    breakout_rvol = now_volume / avg20 if avg20 > 0 else None
    broke_up = now_close > resistance * 1.01
    broke_down = now_close < support * 0.99
    confirmed_breakout = bool(broke_up and breakout_rvol is not None
                              and breakout_rvol >= 1.5)
    support_break = bool(broke_down)
    if not fresh:
        status = "STALE / UNVERIFIED EOD — NO CURRENT BASE SIGNAL"
    elif support_break:
        status = "SUPPORT BREAK — REVIEW"
    elif confirmed_breakout:
        status = "BREAKOUT CANDIDATE — VOLUME CONFIRMED"
    elif broke_up:
        status = "ABOVE BASE — BREAKOUT VOLUME NOT CONFIRMED"
    elif (len(separated) >= 2 and width <= 18 and
          contraction is not None and contraction <= 0.75 and
          volume_ratio is not None and volume_ratio <= 0.85):
        status = "BASE FORMING — PRELIMINARY"
    elif len(separated) >= 2 and width <= 18:
        status = "POSSIBLE BASE — MONITOR"
    else:
        status = "NO CLEAR BASE"
    return {
        "status": status, "support": support, "resistance": resistance,
        "touches": len(separated), "width_pct": round(width, 2),
        "contraction": round(contraction, 2) if contraction is not None else None,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "breakout_rvol": round(breakout_rvol, 2) if breakout_rvol is not None else None,
        "confirmed_breakout": confirmed_breakout if fresh else False,
        "support_break": support_break if fresh else False,
    }


def base_chart_frame(bars, base):
    """DataFrame-friendly price rows, with base levels only in the latest 21 days.

    Never draw current support/resistance across earlier history, where those
    levels would be look-ahead information.
    """
    rows = []
    for i, bar in enumerate(bars):
        history = [float(x["close"]) for x in bars[max(0, i - 49):i + 1]]
        in_range = i >= len(bars) - 21
        rows.append({
            "date": bar["date"],
            "Close": bar["close"],
            "SMA 20": mean(history[-20:]) if len(history) >= 20 else None,
            "SMA 50": mean(history[-50:]) if len(history) >= 50 else None,
            "Base support (closing)": base["support"] if in_range else None,
            "Base resistance (closing)": base["resistance"] if in_range else None,
            "Volume": bar["volume"],
        })
    return rows
