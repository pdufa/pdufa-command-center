"""Research-only GEM entry/exit signal replay. Not an order generator.

Only source-attested, point-in-time event rows accepted by the existing
Stage-3 validator and verified split-adjusted daily OHLCV can be replayed.
The thresholds are HYPOTHESES, not empirically optimized or live buy signals.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, median

from post_phase3_trade_backtest import (
    bars_by_ticker, day, number, prior_liquidity, read_csv, validate_event,
)

ROOT = Path(__file__).resolve().parent
TRADE_FIELDS = (
    "event_key", "ticker", "pdufa_date", "score_threshold", "volume_threshold",
    "base_atr_width", "exit_days", "status", "reason", "entry_signal_date",
    "entry_date", "entry_price", "entry_score", "initial_stop", "exit_date",
    "exit_price", "exit_reason", "net_return_pct", "holding_sessions",
    "max_adverse_excursion_pct", "capture_of_runup_pct",
)
SUMMARY_FIELDS = (
    "score_threshold", "volume_threshold", "base_atr_width", "exit_days",
    "attempted", "completed", "no_signal", "blocked", "censored",
    "win_rate_pct", "mean_return_pct", "median_return_pct",
    "profit_factor", "mean_max_adverse_excursion_pct", "status",
)


def atr_at(bars, i, length=14):
    """ATR known only after session i closes."""
    if i < length:
        return None
    values = []
    for j in range(i-length+1, i+1):
        x, prev = bars[j], bars[j-1]["close"]
        values.append(max(x["high"]-x["low"], abs(x["high"]-prev),
                          abs(x["low"]-prev)))
    return mean(values)


def score_at(bars, i, pdufa, *, rvol_min=1.5, base_width=3.0):
    """A complete EOD signal evaluated without next-session information."""
    if i < 50 or i+1 >= len(bars):
        return None
    x = bars[i]
    atr = atr_at(bars, i)
    base = bars[i-10:i]  # last 10 COMPLETED days, excludes breakout day
    vol20 = mean(y["volume"] for y in bars[i-20:i])
    if not atr or atr <= 0 or vol20 <= 0:
        return None
    high = max(y["high"] for y in base)
    low = min(y["low"] for y in base)
    rvol = x["volume"]/vol20
    if (high-low > base_width*atr or rvol < rvol_min or
            x["close"] < high + 0.1*atr):
        return None
    remaining = (pdufa-x["session"]).days
    if not 7 <= remaining <= 180:
        return None
    sma20 = mean(y["close"] for y in bars[i-19:i+1])
    sma50 = mean(y["close"] for y in bars[i-49:i+1])
    stop = low - 0.25*atr
    if stop <= 0:
        return None
    # Score components mirror the categories, not the exact live algorithm.
    trend = 25 if x["close"] >= sma20 >= sma50 else 0
    volume = 20 if rvol >= 1.5 else 10
    location = 20 if x["close"] >= high + 0.1*atr else 0
    timing = 15 if 14 <= remaining <= 120 else 8
    score = trend+volume+location+timing
    return {"score_before_risk":score, "stop":stop, "atr":atr,
            "signal_close":x["close"]}


def first_signal(bars, event_dates, *, threshold, volume_threshold,
                 base_atr_width, min_dollars):
    second_public = event_dates["second_financing_public_date"]
    pdufa = event_dates["pdufa_date"]
    cutoff = pdufa-timedelta(days=3)
    for i, x in enumerate(bars[:-1]):
        if x["session"] <= second_public:
            continue
        # Ten distinct observed trading sessions strictly after financing.
        if sum(second_public < y["session"] <= x["session"] for y in bars) < 10:
            continue
        if x["session"] >= cutoff or not prior_liquidity(bars, i, min_dollars):
            continue
        s = score_at(bars, i, pdufa, rvol_min=volume_threshold,
                     base_width=base_atr_width)
        if not s:
            continue
        nextbar = bars[i+1]
        if nextbar["session"] >= cutoff:
            continue
        entry = nextbar["open"]
        # Gap/chase filter at the actual next open; no next-day volume used.
        if entry > s["signal_close"]+0.5*s["atr"] or entry <= s["stop"]:
            continue
        risk = entry-s["stop"]
        risk_ok = (0.5*s["atr"] <= risk <= 3*s["atr"] and risk/entry <= .08)
        score = s["score_before_risk"]+(20 if risk_ok else 0)
        if not risk_ok or score < threshold:
            continue
        return i, score, s["stop"]
    return None


def replay_trade(bars, signal, pdufa, early_action, exit_days, slip_bps):
    i, score, start_stop = signal
    entry_i = i+1
    entry = bars[entry_i]["open"]*(1+slip_bps/10000)
    cutoff = pdufa-timedelta(days=exit_days)
    scheduled = [y["session"] for y in bars if y["session"] <= cutoff]
    scheduled_exit = max(scheduled) if scheduled else None
    if scheduled_exit is None or (cutoff-scheduled_exit).days > 5:
        return {"status":"BLOCKED", "reason":"MISSING_CUTOFF_PRICE_DATA",
                "entry_score":score, "entry_price":round(entry,4)}
    stops = start_stop
    peak_close = bars[entry_i]["open"]
    worst_low = entry
    peak_high = entry
    below20 = 0
    for j in range(entry_i, len(bars)):
        b = bars[j]
        if b["session"] > cutoff:
            break
        if j > entry_i and (b["session"]-bars[j-1]["session"]).days > 7:
            return {"status":"BLOCKED", "reason":"UNAUDITED_PRICE_SESSION_GAP",
                    "entry_score":score, "entry_price":round(entry,4)}
        if early_action and b["session"] >= early_action:
            return {"status":"CENSORED", "reason":"EARLY_FDA_ACTION",
                    "entry_score":score, "entry_price":round(entry,4)}
        worst_low = min(worst_low, b["low"])
        peak_high = max(peak_high, b["high"])
        reason = None
        fill = None
        if b["low"] <= stops:
            reason = "STOP_OR_TRAILING_STOP"
            fill = min(b["open"], stops)  # adverse opening gap
        elif b["session"] == scheduled_exit:
            reason = "MANDATORY_PDUFA_CUTOFF"
            fill = b["close"]
        elif j > entry_i and j >= 19:
            sma20 = mean(y["close"] for y in bars[j-19:j+1])
            below20 = below20+1 if b["close"] < sma20 else 0
            if below20 >= 2 and j+1 < len(bars):
                nxt = bars[j+1]
                if nxt["session"] <= cutoff:
                    if early_action and nxt["session"] >= early_action:
                        return {"status":"CENSORED", "reason":"EARLY_FDA_ACTION",
                                "entry_score":score, "entry_price":round(entry,4)}
                    reason = "TWO_CLOSES_BELOW_SMA20"
                    fill = nxt["open"]
        if reason:
            net_exit = fill*(1-slip_bps/10000)
            ret = 100*(net_exit/entry-1)
            runup = peak_high/entry-1
            capture = (net_exit/entry-1)/runup*100 if runup > 0 else None
            return {
                "status":"COMPLETED", "reason":"", "entry_score":score,
                "entry_price":round(entry,4), "exit_date":(
                    bars[j+1]["session"].isoformat()
                    if reason == "TWO_CLOSES_BELOW_SMA20"
                    else b["session"].isoformat()),
                "exit_price":round(net_exit,4), "exit_reason":reason,
                "net_return_pct":round(ret,3), "holding_sessions":(
                    j+1-entry_i if reason == "TWO_CLOSES_BELOW_SMA20"
                    else j-entry_i),
                "max_adverse_excursion_pct":round(
                    100*(worst_low/entry-1),3),
                "capture_of_runup_pct":(
                    round(capture,2) if capture is not None else ""),
            }
        # EOD ATR/peak is applied to NEXT session, never backdated.
        peak_close = max(peak_close, b["close"])
        atr = atr_at(bars, j)
        if atr:
            stops = max(stops, peak_close-2*atr)
    return {"status":"BLOCKED", "reason":"NO_EXIT_SESSION",
            "entry_score":score, "entry_price":round(entry,4)}


def run(events, raw_bars, *, year=2025, as_of=date(2026,10,17),
        score_thresholds=(60,70,80), volume_thresholds=(1.25,1.5,2.0),
        base_widths=(2.0,3.0,4.0), exit_days=(14,3),
        min_dollars=250000, slip_bps=10):
    prices, invalid = bars_by_ticker(raw_bars)
    candidates = [x for x in events
                  if day(x.get("pdufa_date")) and
                  day(x["pdufa_date"]).year == year]
    duplicate_keys = Counter(x.get("event_key") for x in candidates)
    trials = []
    variants = [(score, vol, width, days)
                for score in score_thresholds for vol in volume_thresholds
                for width in base_widths for days in exit_days]
    for event in candidates:
        reason, dates = validate_event(event)
        ticker = str(event.get("ticker") or "").strip().upper()
        if duplicate_keys[event.get("event_key")] > 1:
            reason = "DUPLICATE_EXACT_EVENT_KEY"
        if ticker in invalid:
            reason = "INVALID_PRICE_HISTORY"
        if not reason and not prices.get(ticker):
            reason = "MISSING_SPLIT_ADJUSTED_OHLCV"
        if not reason and dates["pdufa_date"] > as_of:
            reason = "FUTURE_PDUFA_NOT_COMPLETED"
        early = dates["early_fda_action_date"] if dates else None
        if not reason and early and early <= dates["second_financing_public_date"]:
            reason = "FDA_ACTION_BEFORE_ENTRY_ELIGIBILITY"
        for threshold, vol, width, exit_day in variants:
            row = {f:"" for f in TRADE_FIELDS}
            row.update(event_key=event.get("event_key",""), ticker=ticker,
                       pdufa_date=event.get("pdufa_date",""),
                       score_threshold=threshold, volume_threshold=vol,
                       base_atr_width=width, exit_days=exit_day)
            if reason:
                row.update(status="BLOCKED",reason=reason)
            else:
                history = prices[ticker]
                sig = first_signal(history, dates, threshold=threshold,
                                   volume_threshold=vol, base_atr_width=width,
                                   min_dollars=min_dollars)
                if sig is None:
                    row.update(status="NO_SIGNAL",
                               reason="NO_QUALIFYING_ENTRY_BEFORE_CUTOFF")
                else:
                    i,score,stop = sig
                    row.update(entry_signal_date=history[i]["session"].isoformat(),
                               entry_date=history[i+1]["session"].isoformat(),
                               initial_stop=round(stop,4))
                    # If entry follows an early FDA action, no simulated fill.
                    if early and early <= history[i+1]["session"]:
                        row.update(status="CENSORED",
                                   reason="EARLY_FDA_ACTION_BEFORE_ENTRY")
                    elif history[i+1]["session"] > dates["pdufa_date"]-timedelta(days=exit_day):
                        row.update(status="NO_SIGNAL",reason="ENTRY_AFTER_EXIT_CUTOFF")
                    else:
                        row.update(replay_trade(history,sig,dates["pdufa_date"],
                                                early,exit_day,slip_bps))
            trials.append(row)
    summaries = []
    for threshold, vol, width, exit_day in variants:
        group = [r for r in trials if (r["score_threshold"],
                 r["volume_threshold"],r["base_atr_width"],r["exit_days"])
                 == (threshold,vol,width,exit_day)]
        completed = [r for r in group if r["status"]=="COMPLETED"]
        returns = [r["net_return_pct"] for r in completed]
        gains = sum(max(x,0) for x in returns)
        losses = -sum(min(x,0) for x in returns)
        summaries.append(dict(
            score_threshold=threshold,volume_threshold=vol,
            base_atr_width=width,exit_days=exit_day,attempted=len(group),
            completed=len(completed),
            no_signal=sum(r["status"]=="NO_SIGNAL" for r in group),
            blocked=sum(r["status"]=="BLOCKED" for r in group),
            censored=sum(r["status"]=="CENSORED" for r in group),
            win_rate_pct=round(100*sum(x>0 for x in returns)/len(returns),2)
                if returns else "",
            mean_return_pct=round(mean(returns),3) if returns else "",
            median_return_pct=round(median(returns),3) if returns else "",
            profit_factor=round(gains/losses,3) if losses else "",
            mean_max_adverse_excursion_pct=round(mean(
                r["max_adverse_excursion_pct"] for r in completed),3)
                if completed else "",
            status="EXPLORATORY_UNDER_30" if len(completed) < 30
                   else "DESCRIPTIVE_NOT_OUT_OF_SAMPLE",
        ))
    audit = {
        "year":year,"as_of":as_of.isoformat(),
        "candidate_event_rows":len(candidates),
        "audited_event_rows":len({r["event_key"] for r in trials
                                  if r["status"]!="BLOCKED"}),
        "price_rows":len(raw_bars),
        "variants":len(variants),
        "completed_trades":sum(r["status"]=="COMPLETED" for r in trials),
        "unique_event_keys_with_completed_scenarios":len({
            r["event_key"] for r in trials if r["status"]=="COMPLETED"
        }),
        "blocked_trades":sum(r["status"]=="BLOCKED" for r in trials),
        "no_signal_trades":sum(r["status"]=="NO_SIGNAL" for r in trials),
        "censored_trades":sum(r["status"]=="CENSORED" for r in trials),
        "limitations": [
            "Research-only hypothetical trades; no actual fills, fees, taxes or halted-market simulation.",
            "Source URL syntax and dates are validated, but primary documents still require manual event-level audit.",
            "Only supplied PDUFA events are replayed; an incomplete 2025 universe causes selection bias.",
            "Signals use one-day bars; intraday sequence and stop execution are uncertain.",
            "Parameter grid is exploratory; no optimal settings or predictive GREEN claim without chronological holdout.",
            "Early FDA actions censor hypothetical returns and remain in counts.",
            "No trades are submitted and live GEM weights/statuses are unchanged.",
        ],
        "status":"NO_VERIFIED_HISTORICAL_BACKTEST" if
            not any(r["status"]=="COMPLETED" for r in trials)
            else "EXPLORATORY_RESEARCH_ONLY",
    }
    return trials,summaries,audit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events",default="data/post_phase3_historical_trade_events.csv")
    p.add_argument("--bars",default="data/post_phase3_historical_adjusted_ohlcv.csv")
    p.add_argument("--year",type=int,default=2025)
    p.add_argument("--output-dir",default="output/gem_historical_signal_2025")
    args=p.parse_args(argv)
    trials, summaries, audit = run(read_csv(args.events), read_csv(args.bars),
                                   year=args.year)
    dest=Path(args.output_dir)
    dest.mkdir(parents=True,exist_ok=True)
    for name, fields, rows in (
        ("per_event_signals.csv",TRADE_FIELDS,trials),
        ("parameter_grid_summary.csv",SUMMARY_FIELDS,summaries),
    ):
        with (dest/name).open("w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
    (dest/"readiness.json").write_text(
        json.dumps(audit,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(audit,sort_keys=True))


if __name__ == "__main__":
    main()
