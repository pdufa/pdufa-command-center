"""Pure research-only price/volume signals; no recommendation or trading side effects."""
from __future__ import annotations

from math import isfinite


def summarize_daily_bars(bars: list[dict]) -> dict:
    """Return auditable IEX-only signals; missing or invalid data is never imputed."""
    clean = []
    for bar in bars:
        try:
            close, volume = float(bar["close"]), float(bar["volume"])
        except (KeyError, TypeError, ValueError):
            continue
        if isfinite(close) and isfinite(volume) and close > 0 and volume >= 0:
            clean.append((close, volume))
    if len(clean) < 20:
        return {"status": "INSUFFICIENT_DATA", "validBars": len(clean),
                "return20Pct": None, "averageVolume20": None, "volumeRatio20": None}
    window = clean[-20:]
    baseline = clean[-20][0]
    avg_volume = sum(v for _, v in window) / 20
    return {"status": "OK", "validBars": len(clean),
            "return20Pct": round(100 * (clean[-1][0] / baseline - 1), 4),
            "averageVolume20": round(avg_volume, 4),
            "volumeRatio20": round(clean[-1][1] / avg_volume, 4) if avg_volume > 0 else None,
            "scope": "IEX_ONLY_NOT_CONSOLIDATED",
            "researchOnly": True, "recommendation": None}
