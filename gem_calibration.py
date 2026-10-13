"""Point-in-time GEM score validation against historical equity returns.

No approval probability or expected trading return is inferred from FDA outcomes.
Only independently dated public evidence + verified split-adjusted OHLCV may
create a trade; no synthetic or retrospectively selected score is accepted as
a verified live prediction. Holdout performance is reported only after a
chronological, same-ticker-excluded split with explicit sample gates.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, timedelta
from math import ceil, isfinite
from statistics import mean, median

from gem_scans import WEIGHTS as LIVE_WEIGHTS
from trade_window import MIN_NEW_ENTRY_DAYS, calendar_exit_target
from post_phase3_trade_backtest import (
    bars_by_ticker, day, https, number, prior_liquidity,
)

SNAPSHOT_FIELDS = (
    "event_key", "ticker", "nct_id", "issuer_cik", "stage", "signal_date",
    "phase3_public_date", "phase3_source_url",
    "second_financing_public_date", "second_financing_source_url",
    "pdufa_date", "pdufa_public_date", "pdufa_source_url",
    "market_source_url", "early_fda_action_date",
    "phase3_verdict", "financing_verdict", "no_unresolved_dilution",
    "price_base_verdict", "normalized_volume_verdict",
    "market_quote_verdict", "pdufa_verdict", "conflict_flag",
    "Clinical evidence /30", "Financing evidence /20",
    "Trading setup /20", "PDUFA evidence /15", "Market activity /10",
)
CAPS = {
    "Clinical evidence /30": 30,
    "Financing evidence /20": 20,
    "Trading setup /20": 20,
    "PDUFA evidence /15": 15,
    "Market activity /10": 10,
}
STAGES = tuple(LIVE_WEIGHTS)
MIN_TRAIN = 30
MIN_HOLDOUT = 15
MIN_TRAIN_MONTHS = 4
MIN_HOLDOUT_MONTHS = 2
COST_BPS_PER_SIDE = 10
MIN_PRIOR_DOLLARS = 250_000
COMPLETE = "COMPLETE"
OTHER = "BLOCKED"


def _text(raw):
    return str(raw or "").strip()


def _numeric_points(row):
    output = {}
    for col, max_points in CAPS.items():
        raw = _text(row.get(col))
        value = number(raw)
        if not raw or value is None or not 0 <= value <= max_points:
            return None
        output[col] = value
    return output


def _sec_for_cik(url, cik):
    return bool(_text(cik).isdigit() and
                https(url, sec=True, cik=_text(cik)))


def validate_snapshot(row, as_of):
    """Fail closed for stale, duplicate, future, or untraceable features."""
    key, ticker, nct = (_text(row.get(k)) for k in ("event_key", "ticker", "nct_id"))
    stage = _text(row.get("stage"))
    signal = day(row.get("signal_date"))
    if stage not in STAGES or not key.startswith(ticker + "|") or not ticker:
        return "BAD_STAGE_OR_EXACT_EVENT_ID", None
    if len(nct) != 11 or not nct.startswith("NCT") or not nct[3:].isdigit():
        return "MISSING_EXACT_NCT", None
    if signal is None or signal > as_of:
        return "MISSING_OR_FUTURE_SIGNAL_DATE", None
    points = _numeric_points(row)
    if points is None:
        return "SCORE_COMPONENTS_MISSING_OR_OUT_OF_RANGE", None
    clinical_public = day(row.get("phase3_public_date"))
    if not clinical_public or clinical_public > signal or not https(row.get("phase3_source_url")):
        return "NO_POINT_IN_TIME_PHASE3_SOURCE", None
    if _text(row.get("phase3_verdict")) != "PRIMARY_MET_BENEFIT_SAFETY_VERIFIED":
        return "CLINICAL_GATE_UNVERIFIED", None
    if points["Clinical evidence /30"] != 30:
        return "CLINICAL_POINTS_NOT_ALL_ATTESTED", None
    if (_text(row.get("price_base_verdict")) != "VERIFIED" or
            _text(row.get("normalized_volume_verdict")) != "VERIFIED" or
            points["Trading setup /20"] != 20):
        return "PRICE_BASE_OR_VOLUME_GATE_UNVERIFIED", None
    if (_text(row.get("market_quote_verdict")) != "SOURCED_RECENT" or
            not https(row.get("market_source_url")) or
            points["Market activity /10"] < 4):
        return "MARKET_SOURCE_OR_QUOTE_MISSING", None
    if _text(row.get("conflict_flag")).upper() not in ("NONE", "NO", "FALSE", "0", "PASS"):
        return "UNRESOLVED_EVIDENCE_CONFLICT", None
    finance_public = day(row.get("second_financing_public_date"))
    if stage in ("Post-Financing", "PDUFA"):
        if (finance_public is None or clinical_public > finance_public or
                finance_public > signal or
                not _sec_for_cik(row.get("second_financing_source_url"),
                                 row.get("issuer_cik"))):
            return "FINANCING_PUBLICATION_OR_SEC_IDENTITY_UNVERIFIED", None
        if (_text(row.get("financing_verdict")) != "TWO_DISTINCT_POST_PHASE3_CLOSES_VERIFIED" or
                _text(row.get("no_unresolved_dilution")) != "YES" or
                points["Financing evidence /20"] != 20):
            return "TWO_CLOSES_OR_DILUTION_GATE_UNVERIFIED", None
    pdufa = day(row.get("pdufa_date"))
    pdufa_public = day(row.get("pdufa_public_date"))
    if stage in ("Post-Financing", "PDUFA"):
        if (pdufa is None or pdufa_public is None or
                pdufa_public > signal or pdufa_public >= pdufa or
                not https(row.get("pdufa_source_url")) or
                _text(row.get("pdufa_verdict")) != "VERIFIED"):
            return "PDUFA_SOURCE_OR_PUBLICATION_MISSING", None
        if (pdufa - signal).days < MIN_NEW_ENTRY_DAYS:
            return "INSIDE_PDUFA_MINUS_3_EXIT_WINDOW", None
    if stage == "PDUFA" and points["PDUFA evidence /15"] != 15:
        return "PDUFA_EVIDENCE_SCORE_NOT_VERIFIED", None
    early = _text(row.get("early_fda_action_date"))
    early_date = day(early) if early else None
    if early and early_date is None:
        return "INVALID_EARLY_FDA_DATE", None
    if pdufa and early_date and early_date > pdufa:
        return "INVALID_EARLY_FDA_DATE", None
    return "", {
        "stage": stage, "signal": signal, "pdufa": pdufa,
        "early_fda": early_date, "points": points, "ticker":ticker, "nct":nct,
        "event_key":key,
    }


def candidate_weights(stage):
    """Small, predefined hypothesis family; not a hindsight grid search."""
    original = dict(LIVE_WEIGHTS[stage])
    hypotheses = {"LIVE_V1": original}
    def transfer(name, src, dst, pts=10):
        if original.get(src, 0) >= pts:
            alt = dict(original)
            alt[src] -= pts
            alt[dst] = alt.get(dst, 0) + pts
            hypotheses[name] = alt
    transfer("CLINICAL_PLUS_10", "Market activity /10", "Clinical evidence /30")
    transfer("MARKET_PLUS_10", "Clinical evidence /30", "Market activity /10")
    transfer("SETUP_PLUS_10", "Clinical evidence /30", "Trading setup /20")
    if stage == "PDUFA":
        transfer("FDA_PLUS_10", "Clinical evidence /30", "PDUFA evidence /15")
    if stage == "Post-Financing":
        transfer("FINANCING_PLUS_10", "Trading setup /20", "Financing evidence /20")
    return hypotheses


def score(points, weights):
    return round(sum(points[k] / CAPS[k] * weight
                     for k, weight in weights.items()), 6)


def _simulate(row, decoded, bars, *, as_of, slippage_bps, min_daily_dollars):
    if not bars:
        return OTHER, "NO_VERIFIED_HISTORICAL_BARS", None
    signal = decoded["signal"]
    i = next((j for j, x in enumerate(bars) if x["session"] > signal), None)
    if i is None or (bars[i]["session"] - signal).days > 7:
        return OTHER, "NO_NEXT_SESSION_OPEN_AFTER_SIGNAL", None
    liquidity = prior_liquidity(bars, i, min_daily_dollars)
    if liquidity is None:
        return OTHER, "INSUFFICIENT_PRIOR20_LIQUIDITY", None
    if decoded["stage"] == "Phase 3":
        # 30 trading sessions, counted from next-session entry through exit.
        last = i + 29
        if last >= len(bars):
            return OTHER, "NOT_YET_30_HISTORICAL_SESSIONS", None
    else:
        target = calendar_exit_target(decoded["pdufa"])
        last = next((j for j in reversed(range(len(bars)))
                     if bars[j]["session"] <= target), None)
        if last is None or last <= i or (target - bars[last]["session"]).days > 5:
            return OTHER, "PDUFA_MINUS_3_EXIT_PRICE_UNAVAILABLE", None
    if any((bars[j+1]["session"] - bars[j]["session"]).days > 7
           for j in range(i, last)):
        return OTHER, "MISSING_PRICE_SESSIONS", None
    entry, exit_ = bars[i], bars[last]
    if exit_["session"] > as_of:
        return OTHER, "FUTURE_PRICE_LOOKAHEAD_BLOCKED", None
    early = decoded["early_fda"]
    if early and early <= exit_["session"]:
        return OTHER, "CENSORED_EARLY_FDA_ACTION", None
    buy = entry["open"] * (1 + slippage_bps/10_000)
    sell = exit_["close"] * (1 - slippage_bps/10_000)
    prices = [buy] + [bar["close"] for bar in bars[i:last+1]]
    peak, worst = prices[0], 0.
    for close in prices:
        peak = max(peak, close)
        worst = min(worst, close / peak - 1)
    outcome = {
        "event_key":decoded["event_key"], "ticker":decoded["ticker"],
        "stage":decoded["stage"], "signal_date":signal.isoformat(),
        "entry_date":entry["session"].isoformat(),
        "exit_date":exit_["session"].isoformat(),
        "holding_sessions":last-i+1, "entry_prior20_dollars":liquidity,
        "net_return_pct":round(100*(sell/buy-1), 4),
        "max_close_drawdown_pct":round(100*worst, 4),
        "points":decoded["points"], "month":signal.strftime("%Y-%m"),
    }
    return COMPLETE, "", outcome


def _cohorts(rows, weights):
    bymonth=defaultdict(list)
    for row in rows:
        bymonth[row["month"]].append(row)
    top, bottom, gains = [], [], []
    for month, cohort in sorted(bymonth.items()):
        if len(cohort) < 3:
            continue
        ordered = sorted(cohort, key=lambda r: (
            -score(r["points"], weights), r["ticker"], r["event_key"]
        ))
        k=max(1, len(ordered)//3)
        top_return=mean(r["net_return_pct"] for r in ordered[:k])
        low_return=mean(r["net_return_pct"] for r in ordered[-k:])
        top.append(top_return)
        bottom.append(low_return)
        gains.append(top_return-low_return)
    return {
        "competitive_months":len(gains),
        "mean_top_minus_bottom_percentage_points":(
            round(mean(gains), 4) if gains else None),
        "mean_top_return_pct":round(mean(top), 4) if top else None,
        "mean_bottom_return_pct":round(mean(bottom), 4) if bottom else None,
    }


def _summary(rows, weights):
    returns=[r["net_return_pct"] for r in rows]
    dd=[r["max_close_drawdown_pct"] for r in rows]
    return {
        "unique_events":len({r["event_key"] for r in rows}),
        "unique_tickers":len({r["ticker"] for r in rows}),
        "median_return_pct":round(median(returns), 4) if returns else None,
        "mean_return_pct":round(mean(returns), 4) if returns else None,
        "win_rate_pct":round(100*sum(x>0 for x in returns)/len(returns), 2) if returns else None,
        "median_max_drawdown_pct":round(median(dd), 4) if dd else None,
        **_cohorts(rows, weights),
    }


def calibrate(snapshots, price_bars, *, as_of=None,
              slippage_bps=COST_BPS_PER_SIDE, min_daily_dollars=MIN_PRIOR_DOLLARS):
    as_of = as_of or date.today()
    if not isinstance(as_of, date) or isinstance(as_of, __import__("datetime").datetime):
        raise ValueError("as_of must be a date")
    if (not isfinite(slippage_bps) or slippage_bps < 0 or slippage_bps > 1000 or
            not isfinite(min_daily_dollars) or min_daily_dollars < 0):
        raise ValueError("Invalid execution friction or liquidity")
    valid_bars=[b for b in price_bars if (day(b.get("session")) or date.max) <= as_of]
    bars_by, invalid_bars=bars_by_ticker(valid_bars)
    counts=Counter((_text(r.get("stage")), _text(r.get("event_key")),
                    _text(r.get("signal_date"))) for r in snapshots)
    reasons=Counter()
    successful=[]
    for row in snapshots:
        identity=(_text(row.get("stage")), _text(row.get("event_key")),
                  _text(row.get("signal_date")))
        if counts[identity]!=1:
            reasons["DUPLICATE_SNAPSHOT_IDENTITY"]+=1
            continue
        reason, decoded=validate_snapshot(row, as_of)
        if reason:
            reasons[reason]+=1
            continue
        if decoded["ticker"] in invalid_bars:
            reasons["INVALID_PRICE_BAR_HISTORY"]+=1
            continue
        status,reason,trade=_simulate(row,decoded,bars_by.get(decoded["ticker"],[]),
            as_of=as_of,slippage_bps=slippage_bps,
            min_daily_dollars=min_daily_dollars)
        if status!=COMPLETE:
            reasons[reason]+=1
        else:
            successful.append(trade)
    # One ticker in the same stage/month must not be double counted.
    cohortcounts=Counter((r["stage"],r["month"],r["ticker"]) for r in successful)
    filtered=[]
    for r in successful:
        if cohortcounts[(r["stage"],r["month"],r["ticker"])]!=1:
            reasons["SAME_TICKER_MULTIPLE_PROGRAMS_PER_MONTH"]+=1
        else:
            filtered.append(r)
    stages={}
    for stage in STAGES:
        rows=sorted((r for r in filtered if r["stage"]==stage),
                    key=lambda r:(r["signal_date"],r["ticker"],r["event_key"]))
        alternatives=candidate_weights(stage)
        if not rows:
            stages[stage]={
                "status":"NO_VERIFIED_HISTORICAL_TRADES",
                "completed_trades":0, "calibrated":False,
                "live_weights":dict(LIVE_WEIGHTS[stage]),
                "train":_summary([],LIVE_WEIGHTS[stage]),
                "holdout":_summary([],LIVE_WEIGHTS[stage]),
                "selected_hypothesis":None,
            }
            continue
        months=sorted({r["month"] for r in rows})
        # Entire final calendar months are untouched; no random event mixing.
        split=max(1, int(len(months)*.75))
        cutoff=months[min(split,len(months)-1)]
        train=[r for r in rows if r["month"]<cutoff]
        train_tickers={r["ticker"] for r in train}
        holdout=[r for r in rows if r["month"]>=cutoff and
                 r["ticker"] not in train_tickers]
        repeats=sum(r["month"]>=cutoff and r["ticker"] in train_tickers for r in rows)
        # Strict gates can fix most feature scores to their maximum.
        # Without multiple varying score dimensions, no weight change can
        # demonstrate independent ranking improvement.
        varying_components = [
            field for field in LIVE_WEIGHTS[stage]
            if len({r["points"][field] for r in train}) >= 2
        ]
        eligible=(len({r["ticker"] for r in train})>=MIN_TRAIN and
                  len({r["ticker"] for r in holdout})>=MIN_HOLDOUT and
                  len(varying_components) >= 2 and
                  _cohorts(train,LIVE_WEIGHTS[stage])["competitive_months"]>=MIN_TRAIN_MONTHS and
                  _cohorts(holdout,LIVE_WEIGHTS[stage])["competitive_months"]>=MIN_HOLDOUT_MONTHS)
        # Never pick weights based on holdout performance.
        rankings=sorted(
            ((hypothesis,_cohorts(train,weights)) for hypothesis,weights
             in alternatives.items()),
            key=lambda pair: (
                - (pair[1]["mean_top_minus_bottom_percentage_points"]
                   if pair[1]["mean_top_minus_bottom_percentage_points"] is not None
                   else float("-inf")),
                pair[0]!="LIVE_V1", pair[0]
            )
        )
        chosen=rankings[0][0] if eligible else None
        report={
            "status":("EXPLORATORY_HOLDOUT_VALIDATED_NOT_PRODUCTION_APPROVED"
                      if eligible else
                      "INSUFFICIENT_SCORE_DISCRIMINATION"
                      if len(varying_components) < 2 else
                      "INSUFFICIENT_INDEPENDENT_COHORT_DATA"),
            "varying_score_components":varying_components,
            "completed_trades":len(rows), "unique_tickers":len({r["ticker"] for r in rows}),
            "calibrated":bool(eligible),
            "train_months":len({r["month"] for r in train}),
            "holdout_months":len({r["month"] for r in holdout}),
            "excluded_repeat_ticker_holdout":repeats,
            "chronological_holdout_start_month":cutoff,
            "train":_summary(train,alternatives[chosen] if chosen else LIVE_WEIGHTS[stage]),
            "holdout":_summary(holdout,alternatives[chosen] if chosen else LIVE_WEIGHTS[stage]),
            "live_weights":dict(LIVE_WEIGHTS[stage]),
            "selected_hypothesis":chosen,
            "proposed_weights_NOT_DEPLOYED":alternatives[chosen] if chosen else None,
        }
        if eligible:
            report["baseline_holdout"]=_summary(holdout,LIVE_WEIGHTS[stage])
            report["holdout_top_spread_improvement_pp"]=round(
                report["holdout"]["mean_top_minus_bottom_percentage_points"] -
                report["baseline_holdout"]["mean_top_minus_bottom_percentage_points"],4)
            report["note"]="One untouched chronological evaluation; repeat on later forward cohorts before any production promotion."
        stages[stage]=report
    status=("NO_HISTORICAL_FEATURES_OR_PRICES"
            if not snapshots or not price_bars else
            "NO_VERIFIED_HISTORICAL_TRADES" if not filtered else
            "NO_STAGE_PASSES_HOLDOUT_REQUIREMENTS"
            if not any(s["calibrated"] for s in stages.values()) else
            "EXPLORATORY_STAGE_CALIBRATION_AVAILABLE_NOT_DEPLOYED")
    return {
        "schema_version":1, "as_of":as_of.isoformat(), "status":status,
        "snapshot_rows":len(snapshots), "price_rows":len(price_bars),
        "valid_completed_trades":len(filtered),
        "invalid_price_tickers":sorted(invalid_bars),
        "excluded_reasons":dict(sorted(reasons.items())),
        "minimums":{"train_unique_tickers":MIN_TRAIN,
                    "holdout_unique_tickers":MIN_HOLDOUT,
                    "train_competitive_months":MIN_TRAIN_MONTHS,
                    "holdout_competitive_months":MIN_HOLDOUT_MONTHS},
        "slippage_per_side_bps":slippage_bps,
        "min_prior20_dollar_volume":min_daily_dollars,
        "stages":stages,
        "warnings":[
            "Source URLs and publication dates require independent primary-document verification; a supplied string alone is not proof.",
            "Prospective source snapshots must represent the full candidate universe, including losers and delisted issuers.",
            "Stage-specific horizons differ: Phase 3 exits after 30 actual sessions; Post-Financing and PDUFA exit at PDUFA minus 3 calendar days.",
            "Early FDA action scenarios are censored and may omit tail losses; paired outcomes may share issuer exposure.",
            "Strict gates can leave only market activity varying; score weights cannot be tuned meaningfully without at least two independently varying predictors.",
            "Train-only small hypothesis search followed by chronological holdout is exploratory, not evidence of perfection.",
            "Live GEM score weights are NEVER automatically changed by these reports.",
        ],
    }
