"""Point-in-time post-Phase-3 equity trading backtest (no Streamlit UI).

Historical FDA approval/CRL accuracy is NOT a stock-return backtest.
Only exact-event, dated, primary-source-linked clinical/financing evidence and
split-adjusted historical OHLCV can produce hypothetical returns. The first
three entry methods are CONDITIONAL comparators for programs that ultimately
completed two financings; their returns cannot measure an unconditional
readout-day strategy (survivorship/selection bias).
"""
from __future__ import annotations

import csv
import math
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, median
from urllib.parse import urlsplit

EVENT_FIELDS = (
    "event_key", "ticker", "nct_id", "issuer_cik", "phase3_readout_date",
    "phase3_public_date", "phase3_result", "clinical_benefit",
    "safety_status", "phase3_source_url", "first_financing_close_date",
    "first_financing_public_date", "first_financing_source_url",
    "second_financing_close_date", "second_financing_public_date",
    "second_financing_source_url", "second_financing_verdict",
    "pdufa_date", "pdufa_public_date", "pdufa_source_url",
    "pdufa_verdict", "pdufa_change_status", "early_fda_action_date",
)
BAR_FIELDS = (
    "ticker", "session", "open", "high", "low", "close", "volume",
    "source_url", "adjustment_status",
)
ENTRY_METHODS = ("READOUT_BENCHMARK", "FIRST_FINANCING_BENCHMARK",
                 "SECOND_FINANCING", "POST_SECOND_FINANCING_BASE")
EXIT_DAYS = (30, 14, 7)
TRADE_FIELDS = (
    "event_key", "ticker", "nct_id", "entry_method", "exit_days_before_pdufa",
    "status", "reason", "entry_signal_date", "entry_date", "exit_target_date",
    "exit_date", "entry_price", "exit_price", "net_return_pct",
    "max_close_drawdown_pct", "holding_sessions", "entry_prior20_dollar_volume",
    "pdufa_date", "early_fda_action_date", "selection_caveat",
)
SUMMARY_FIELDS = (
    "entry_method", "exit_days_before_pdufa", "events_attempted",
    "trades_completed", "early_action_censored", "other_blocked",
    "unique_tickers", "median_net_return_pct", "mean_net_return_pct",
    "win_rate_pct", "median_max_close_drawdown_pct", "status",
)
KEY = re.compile(r"^[A-Z0-9.-]{1,12}\|[A-Z0-9_]+$")
NCT = re.compile(r"^NCT\d{8}$")
TICKER = re.compile(r"^[A-Z0-9.-]{1,12}$")


def read_csv(path):
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error):
        return []


def day(value):
    try:
        v = str(value or "").strip()
        return date.fromisoformat(v) if len(v) == 10 else None
    except ValueError:
        return None


def number(value):
    try:
        n = float(str(value or "").strip())
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def https(url, *, sec=False, cik=None):
    try:
        u = urlsplit(str(url or "").strip())
        if (u.scheme != "https" or not u.hostname or u.username or
                u.password or u.port not in (None, 443)):
            return False
        if sec:
            m = re.match(r"^/Archives/edgar/data/(\\d{1,10})/", u.path)
            return bool(u.hostname.lower() in {"sec.gov", "www.sec.gov"} and
                        m and (cik is None or int(m.group(1)) == int(cik)))
        return True
    except ValueError:
        return False


def validate_event(record):
    """No gate may be inferred from an undated or later-reviewed filing."""
    key = str(record.get("event_key") or "").strip()
    ticker = str(record.get("ticker") or "").strip().upper()
    nct = str(record.get("nct_id") or "").strip()
    cik = str(record.get("issuer_cik") or "").strip()
    if (not KEY.fullmatch(key) or not TICKER.fullmatch(ticker) or
            key.split("|")[0] != ticker or not NCT.fullmatch(nct) or
            not cik.isdigit() or not 1 <= len(cik) <= 10):
        return "UNVERIFIED_EXACT_EVENT_IDENTITY", None
    dates = {k: day(record.get(k)) for k in (
        "phase3_readout_date", "phase3_public_date",
        "first_financing_close_date", "first_financing_public_date",
        "second_financing_close_date", "second_financing_public_date",
        "pdufa_date", "pdufa_public_date")}
    if any(v is None for v in dates.values()):
        return "MISSING_DATED_POINT_IN_TIME_EVIDENCE", None
    d = dates
    if not (d["phase3_readout_date"] <= d["phase3_public_date"]
            and d["phase3_readout_date"] <= d["first_financing_close_date"]
            < d["second_financing_close_date"]
            and d["first_financing_close_date"] <= d["first_financing_public_date"]
            and d["second_financing_close_date"] <= d["second_financing_public_date"]
            and d["pdufa_public_date"] < d["pdufa_date"]):
        return "CONFLICTING_OR_FUTURE_KNOWN_DATES", None
    if not (str(record.get("phase3_result")) == "PRIMARY_MET_VERIFIED"
            and str(record.get("clinical_benefit")) == "MEANINGFUL_VERIFIED"
            and str(record.get("safety_status")) == "NO_MAJOR_UNRESOLVED_VERIFIED"
            and str(record.get("second_financing_verdict")) ==
                "TWO_DISTINCT_POST_PHASE3_CLOSES_VERIFIED"
            and str(record.get("pdufa_verdict")) == "VERIFIED"
            and str(record.get("pdufa_change_status")) == "NONE_DOCUMENTED"):
        return "CLINICAL_FINANCING_OR_REGULATORY_REVIEW", None
    if not (https(record.get("phase3_source_url"))
            and https(record.get("first_financing_source_url"), sec=True, cik=cik)
            and https(record.get("second_financing_source_url"), sec=True, cik=cik)
            and https(record.get("pdufa_source_url"))):
        return "MISSING_PRIMARY_SOURCE_LINK", None
    if (d["second_financing_public_date"] >= d["pdufa_date"] or
            d["phase3_public_date"] >= d["pdufa_date"]):
        return "LATE_DISCLOSURE_NOT_TRADABLE", None
    early = str(record.get("early_fda_action_date") or "").strip()
    early_day = day(early) if early else None
    if early and early_day is None:
        return "INVALID_EARLY_FDA_ACTION_DATE", None
    if early_day and early_day > d["pdufa_date"]:
        return "INVALID_EARLY_FDA_ACTION_DATE", None
    return "", {**d, "early_fda_action_date": early_day}


def bars_by_ticker(bars):
    """Reject a ticker's entire price history on duplicate/invalid daily data."""
    rows = defaultdict(list)
    invalid = set()
    for bar in bars:
        ticker = str(bar.get("ticker") or "").strip().upper()
        if not TICKER.fullmatch(ticker):
            continue
        session = day(bar.get("session"))
        values = {f: number(bar.get(f)) for f in ("open","high","low","close","volume")}
        if (not session or None in values.values() or
                min(values.values()) <= 0 or
                values["low"] > min(values["open"], values["close"]) or
                values["high"] < max(values["open"], values["close"]) or
                values["low"] > values["high"] or
                not https(bar.get("source_url")) or
                str(bar.get("adjustment_status")) != "SPLIT_ADJUSTED_VERIFIED"):
            invalid.add(ticker)
            continue
        rows[ticker].append({"session": session, **values})
    for ticker, subset in list(rows.items()):
        subset.sort(key=lambda x: x["session"])
        if ticker in invalid or len({x["session"] for x in subset}) != len(subset):
            invalid.add(ticker)
            rows.pop(ticker, None)
    return rows, invalid


def prior_liquidity(bars, i, min_daily_dollars):
    """The entry session's volume cannot be used to decide its open entry."""
    prior = bars[max(0, i-20):i]
    if len(prior) < 20:
        return None
    dollars = mean(x["close"] * x["volume"] for x in prior)
    return round(dollars, 2) if dollars >= min_daily_dollars else None


def base_signal(bars, after):
    """At EOD t: last 10 closing prices within 15%; 5/20 volume 0.5–1.25.

    Minimum 10 market sessions strictly after second financing disclosure.
    Signal at t is only executable at next session OPEN, never at t close.
    """
    after_indices = [i for i, b in enumerate(bars) if b["session"] > after]
    for i in after_indices[9:]:
        if i < 24:
            continue
        prior20 = bars[i-24:i-4]
        current5 = bars[i-4:i+1]
        last10 = bars[i-9:i+1]
        if len(prior20) != 20 or len(current5) != 5:
            continue
        base = max(v["close"] for v in last10) / min(v["close"] for v in last10) - 1
        volume_ratio = mean(v["volume"] for v in current5) / mean(v["volume"] for v in prior20)
        if base <= .15 and .5 <= volume_ratio <= 1.25:
            return bars[i]["session"]
    return None


def simulate_event(event, bars, price_invalid=False, *, exit_days=EXIT_DAYS,
                   min_daily_dollars=250_000.0, slippage_bps=10):
    key = str(event.get("event_key") or "")
    ticker = str(event.get("ticker") or "").upper()
    nct = str(event.get("nct_id") or "")
    reason, dates = validate_event(event)
    methods = {}
    if dates:
        clinical = dates["phase3_public_date"]
        pdufa_known = dates["pdufa_public_date"]
        finance1 = dates["first_financing_public_date"]
        finance2 = dates["second_financing_public_date"]
        methods = {
            "READOUT_BENCHMARK": max(clinical, pdufa_known),
            "FIRST_FINANCING_BENCHMARK": max(clinical, finance1, pdufa_known),
            "SECOND_FINANCING": max(clinical, finance2, pdufa_known),
            "POST_SECOND_FINANCING_BASE": None,
        }
        base = base_signal(bars, max(clinical, finance2, pdufa_known)) if bars else None
        methods["POST_SECOND_FINANCING_BASE"] = base
    results = []
    for method in ENTRY_METHODS:
        for window in exit_days:
            record = {k:"" for k in TRADE_FIELDS}
            target = dates["pdufa_date"] - timedelta(days=window) if dates else None
            record.update({
                "event_key": key, "ticker": ticker, "nct_id": nct,
                "entry_method": method, "exit_days_before_pdufa": window,
                "status": "BLOCKED", "reason": reason,
                "pdufa_date": dates["pdufa_date"].isoformat() if dates else "",
                "early_fda_action_date": (dates["early_fda_action_date"].isoformat()
                                          if dates and dates["early_fda_action_date"] else ""),
                "exit_target_date": target.isoformat() if target else "",
                "selection_caveat": "CONDITIONAL_ON_EVENTUAL_TWO_CLOSES"
                if method.endswith("BENCHMARK") else "VERIFIED_SECOND_FINANCING_COHORT",
            })
            if reason:
                results.append(record)
                continue
            if price_invalid or not bars:
                record["reason"] = "PRICE_HISTORY_UNAVAILABLE_OR_INVALID"
                results.append(record)
                continue
            signal = methods[method]
            if signal is None:
                record["reason"] = "NO_POINT_IN_TIME_STABILIZED_BASE"
                results.append(record)
                continue
            record["entry_signal_date"] = signal.isoformat()
            # Do not let the model buy on the closing price of a disclosure day.
            entry_i = next((i for i, b in enumerate(bars) if b["session"] > signal), None)
            exit_i = next((i for i in reversed(range(len(bars)))
                           if bars[i]["session"] <= target), None)
            if entry_i is None or exit_i is None or entry_i >= exit_i:
                record["reason"] = "INSUFFICIENT_ENTRY_TO_EXIT_PRICE_HISTORY"
                results.append(record)
                continue
            first_session, last_session = bars[entry_i]["session"], bars[exit_i]["session"]
            if (first_session > target or
                    # Guard against falsely exiting using a very old bar.
                    (target-last_session).days > 5):
                record["reason"] = "EXIT_SESSION_MISSING"
                results.append(record)
                continue
            dollars = prior_liquidity(bars, entry_i, min_daily_dollars)
            if dollars is None:
                record["reason"] = "PRIOR20_DOLLAR_LIQUIDITY_NOT_VERIFIED"
                results.append(record)
                continue
            record["entry_prior20_dollar_volume"] = dollars
            record["entry_date"] = first_session.isoformat()
            record["exit_date"] = last_session.isoformat()
            if dates["early_fda_action_date"] and dates["early_fda_action_date"] <= last_session:
                record["status"] = "CENSORED_EARLY_FDA_ACTION"
                record["reason"] = "Early regulatory action before scheduled exit; return NOT assumed"
                results.append(record)
                continue
            entry_price = bars[entry_i]["open"]*(1+slippage_bps/10_000)
            exit_price = bars[exit_i]["close"]*(1-slippage_bps/10_000)
            closes = [entry_price]+[b["close"] for b in bars[entry_i:exit_i+1]]
            peak = closes[0]
            worst = 0.0
            for price in closes:
                peak = max(peak, price)
                worst = min(worst, price/peak-1)
            record.update({
                "status": "COMPLETED",
                "reason": "Hypothetical next-session-open to last-before-cutoff-close",
                "entry_price": round(entry_price, 6),
                "exit_price": round(exit_price, 6),
                "net_return_pct": round((exit_price/entry_price-1)*100, 3),
                "max_close_drawdown_pct": round(worst*100, 3),
                "holding_sessions": exit_i-entry_i+1,
            })
            results.append(record)
    return results


def run_backtest(events, bars, *, exit_days=EXIT_DAYS,
                 min_daily_dollars=250_000.0, slippage_bps=10):
    if not all(isinstance(x,int) and 1 <= x <= 90 for x in exit_days):
        raise ValueError("exit_days must be integers 1-90")
    if not isinstance(slippage_bps,(int,float)) or not 0 <= slippage_bps <= 1000:
        raise ValueError("slippage must be 0-1000 basis points")
    if (not isinstance(min_daily_dollars,(int,float)) or
            not math.isfinite(min_daily_dollars) or min_daily_dollars < 0):
        raise ValueError("min_daily_dollars must be nonnegative")
    grouped, invalid = bars_by_ticker(bars)
    keys = Counter(str(r.get("event_key") or "") for r in events)
    results = []
    for event in events:
        key = str(event.get("event_key") or "")
        ticker = str(event.get("ticker") or "").upper()
        rows = simulate_event(event, grouped.get(ticker, []), ticker in invalid,
                              exit_days=exit_days, min_daily_dollars=min_daily_dollars,
                              slippage_bps=slippage_bps)
        if keys[key] != 1:
            for row in rows:
                row.update({"status":"BLOCKED", "reason":"DUPLICATE_EXACT_EVENT_KEY",
                            "entry_price":"", "exit_price":"", "net_return_pct":"",
                            "max_close_drawdown_pct":"", "holding_sessions":""})
        results.extend(rows)
    summary = []
    for method in ENTRY_METHODS:
        for window in exit_days:
            cohort = [r for r in results if r["entry_method"] == method
                      and r["exit_days_before_pdufa"] == window]
            completed = [r for r in cohort if r["status"] == "COMPLETED"]
            vals = [r["net_return_pct"] for r in completed]
            summary.append({
                "entry_method":method, "exit_days_before_pdufa":window,
                "events_attempted": len(cohort),
                "trades_completed":len(completed),
                "early_action_censored":sum(r["status"]=="CENSORED_EARLY_FDA_ACTION" for r in cohort),
                "other_blocked":sum(r["status"]=="BLOCKED" for r in cohort),
                "unique_tickers":len({r["ticker"] for r in completed}),
                "median_net_return_pct":round(median(vals),3) if vals else "",
                "mean_net_return_pct":round(mean(vals),3) if vals else "",
                "win_rate_pct":round(100*sum(v>0 for v in vals)/len(vals),2) if vals else "",
                "median_max_close_drawdown_pct":(
                    round(median(r["max_close_drawdown_pct"] for r in completed),3)
                    if completed else ""),
                "status":("NO_VALID_TRADES" if not completed else
                          "EXPLORATORY_FEWER_THAN_30_TRADES" if len(completed)<30 else
                          "DESCRIPTIVE_NOT_OUT_OF_SAMPLE"),
            })
    reasons = Counter(r["reason"] for r in results if r["status"] != "COMPLETED")
    audit = {
        "event_rows":len(events), "price_rows":len(bars),
        "unique_events":len(set(e.get("event_key","") for e in events)),
        "price_tickers_with_usable_bars":len(grouped),
        "price_tickers_invalid":sorted(invalid),
        "completed_scenarios":sum(r["status"]=="COMPLETED" for r in results),
        "early_action_censored_scenarios":sum(
            r["status"]=="CENSORED_EARLY_FDA_ACTION" for r in results),
        "status":("NOT_READY_NO_EVENT_AND_PRICE_HISTORY" if not events and not bars
                  else "NO_VALID_POINT_IN_TIME_TRADES" if not any(r["status"]=="COMPLETED" for r in results)
                  else "EXPLORATORY_ONLY_NOT_CALIBRATED"),
        "blocker_reasons":dict(sorted(reasons.items())),
        "warnings":[
            "Historical model FDA outcome accuracy is unrelated to equity trade returns.",
            "Benchmark cohorts require eventual second funding; not an unbiased trial-readout population.",
            "Returns are hypothetical, exclude fees/taxes/borrow and do not model intraday gaps.",
            "Early FDA action is censored, not assumed profitable; censoring understates tail risk.",
            "Same-company programs may produce correlated/overlapping hypothetical returns.",
            "These returns are descriptive; an independently frozen chronological holdout is still required.",
        ],
    }
    return results, summary, audit
