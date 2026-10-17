"""Exact-program GEM JR / GEM evidence and trading research adapter.

Uses the original verified Streamlit analytical functions verbatim, without its UI.
Scores remain unavailable whenever source health, positive Phase 3 evidence,
second SEC financing, or end-of-day market observations cannot be verified.
"""
from __future__ import annotations

from datetime import date
import json

from .legacy_gem_trading_advisory import assess_gem_trade, _score_gem_trade
from .legacy_gem_runway_gate import assess_runway

POSITIVE = {"VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED"}
SEC_PASS = "VERIFIED_SECOND_POST_PHASE3_FINANCING"
RESOLVED = {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}


def _day(raw):
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except (TypeError, ValueError):
        return None


def _source(url):
    return isinstance(url, str) and url.startswith("https://") and len(url) <= 2000


def _float(value, digits=3):
    if isinstance(value, (int, float)):
        return round(value, digits)
    return None


def _factors(tuples):
    return [
        {"label": label, "weight": weight, "earned": earned, "evidence": evidence}
        for label, weight, earned, evidence in tuples
    ]


def verify_benchmarks(row, event, financing, recheck, today):
    """Conservative: never infer independent deals from a summary label alone."""
    readout = _day(event.get("phase3_date"))
    first = _day(financing.get("first_financing_date"))
    second = _day(financing.get("second_financing_date"))
    phase3 = bool(
        row.get("id") == "APPLICATION|" + str(event.get("event_key") or "")
        and row.get("ticker") == (event.get("ticker") or "").upper()
        and (event.get("phase3_status") or "").upper() in POSITIVE
        and readout and readout <= today and _source(event.get("trial_evidence_url"))
        and event.get("nct_id") and row.get("nctId") == event.get("nct_id")
    )
    chronological = bool(readout and first and second and
                         readout < first < second <= today)
    sec = bool(
        chronological
        and financing.get("second_financing_audit_status") == SEC_PASS
        and recheck.get("first_sec_status") == "VERIFIED"
        and recheck.get("second_sec_status") == "VERIFIED"
        and _source(recheck.get("first_sec_url"))
        and _source(recheck.get("second_sec_url"))
        and recheck.get("gem_entry_authorized") == "YES"
    )
    return {
        "phase3": phase3,
        "secondFinancing": sec,
        "bothConfirmed": bool(phase3 and sec),
        "readoutDate": readout.isoformat() if readout else "",
        "firstClose": first.isoformat() if first else "",
        "secondClose": second.isoformat() if second else "",
        "warning": (
            "Source-verified positive Phase 3 and both SEC-funded post-readout closes"
            if phase3 and sec
            else "One or both positive entry benchmarks are not currently independently cleared"
        ),
    }


def analyze_member(row, event, financing, recheck, market, runway, source_status, today):
    ticker = row["ticker"]
    benchmarks = verify_benchmarks(row, event or {}, financing or {}, recheck or {}, today)
    pd_date = _day(row.get("pdufaDate"))
    days = (pd_date - today).days if pd_date else None
    verified_date = (
        (event or {}).get("pdufa_confirmation", "").startswith("VERIFIED")
        and _source((event or {}).get("pdufa_evidence_url"))
    )
    risk = []
    if days is not None and days <= 3:
        risk.append("FDA decision within 3 days or past exit window")
    if event and str(event.get("outcome") or "").upper() in RESOLVED:
        risk.append("FDA event already resolved")
    if (event or {}).get("new_dilution_flag", "").upper() in {"YES", "TRUE", "UNRESOLVED"}:
        risk.append("New or unresolved dilution")
    if not benchmarks["bothConfirmed"]:
        risk.append("Exact-program Phase 3/financing entry benchmarks unverified")
    if not source_status.get("complete"):
        risk.append("Global published scan is partial or stale")

    eod_status = {
        "feed_current": bool(source_status.get("complete")),
        "sec_financing_source_current": bool(source_status.get("complete")),
    }
    trading_row = {
        "Ticker": ticker,
        "_eligible": benchmarks["bothConfirmed"],
        "Days to PDUFA": days,
        "PDUFA Date Verified": bool(verified_date),
        "GEM Status": "EXIT / FDA DECISION WARNING" if (days is not None and days <= 3) else "",
        "Risks / Evidence Gaps": "; ".join(risk),
    }
    profile = assess_gem_trade(trading_row, market, eod_status, today)
    scores = _score_gem_trade(trading_row, profile, eod_status)
    # Same GEM weighted model on verified EOD observations, separately from
    # eligibility. Never interpret observed indicator points as a BUY signal.
    indicator_status = {"feed_current": bool(profile["fresh"]),
                        "sec_financing_source_current": bool(profile["fresh"])}
    indicator_row = {**trading_row, "_eligible": True, "GEM Status": ""}
    observed = _score_gem_trade(indicator_row, profile, indicator_status)
    second_close = benchmarks["secondClose"] if benchmarks["secondFinancing"] else None
    cash = assess_runway(ticker, runway, as_of=today, second_close=second_close)
    base = profile["base"]
    return {
        "benchmarks": benchmarks,
        "tradeCall": profile["recommendation"],
        "tradeReason": profile["reason"],
        "marketDate": profile["date"].isoformat() if profile["date"] else "",
        "marketSource": profile["source"] if profile["source"] else "",
        "eodFresh": profile["fresh"],
        "close": _float(profile["close"]),
        "sma20": _float(profile["sma20"]),
        "sma50": _float(profile["sma50"]),
        "rsi14": _float(profile["rsi"]),
        "rvol": _float(profile["rvol"]),
        "avgDollarVolume20": _float(profile["dollar_volume"], 0),
        "closingSupport20": _float(profile["support"]),
        "macd": (
            {key: _float(v) if key != "bullish" else bool(v) for key, v in profile["macd"].items()}
            if profile["macd"] is not None else None
        ),
        "base": {
            "status": base["status"],
            "support": _float(base["support"]),
            "resistance": _float(base["resistance"]),
            "touches": base["touches"],
            "widthPct": _float(base["width_pct"]),
            "contractionRatio": _float(base["contraction"]),
            "volumeRatio": _float(base["volume_ratio"]),
            "breakoutRvol": _float(base["breakout_rvol"]),
        },
        "dataGaps": profile["gaps"],
        # Expose observed factor points even when coverage is below the 50/100
        # threshold for publishing a formal score. These are not 100-point scores.
        "indicatorEntryObservedPoints": sum(v for _, _, v, _ in observed["entry_factors"] if v is not None),
        "indicatorExitObservedPoints": sum(v for _, _, v, _ in observed["exit_factors"] if v is not None),
        "indicatorEntry": observed["entry"],
        "indicatorEntryCoverage": observed["entry_coverage"],
        "indicatorExitRisk": observed["exit_risk"],
        "indicatorExitCoverage": observed["exit_coverage"],
        "indicatorEntryFactors": _factors(observed["entry_factors"]),
        "indicatorExitFactors": _factors(observed["exit_factors"]),
        "indicatorModel": "SAME_GEM_WEIGHTED_EOD_MODEL_RESEARCH_ONLY",
        "indicatorDisclaimer": "Observable GEM technical points only; clinical eligibility and full FDA/SEC survey must still pass.",
        "entry": scores["entry"],
        "entryCoverage": scores["entry_coverage"],
        "entryStatus": scores["entry_status"],
        "exitRisk": scores["exit_risk"],
        "exitCoverage": scores["exit_coverage"],
        "exitStatus": scores["exit_status"],
        "entryFactors": _factors(scores["entry_factors"]),
        "exitFactors": _factors(scores["exit_factors"]),
        "runwayMonths": cash["Cash runway (months)"],
        "runwayGate": cash["Cash runway gate"],
        "runwayReason": cash["Cash runway reason"],
        "runwaySource": cash["Cash runway source"],
        "runwayAsOf": cash["Cash runway as of"],
        "riskAlerts": risk,
        "researchOnly": True,
    }


def parse_runway(data: str) -> dict:
    if not data:
        return {}
    try:
        obj = json.loads(data)
        if obj.get("source") != "SEC_STEP4_COMPANYFACTS" or obj.get("schema_version") != 1:
            return {}
        snapshots, duplicate = {}, set()
        for item in obj.get("snapshots") or []:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker") or "").upper()
            if not ticker:
                continue
            if ticker in snapshots:
                duplicate.add(ticker)
            else:
                snapshots[ticker] = item
        for ticker in duplicate:
            snapshots.pop(ticker, None)
        return snapshots
    except (ValueError, TypeError, AttributeError):
        return {}
