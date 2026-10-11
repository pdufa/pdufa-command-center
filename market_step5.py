"""Step 5: source-aware end-of-day biotech market setup research.

Technical setup scores are not clinical success, regulatory approval, trading
advice or forward price-appreciation probabilities. PRE/POST result states
must be supported by dated user-reviewed evidence. No look-ahead prices.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sqlite3
import statistics
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sec_step4 import load_registry, read_history as read_sec_history

ROOT = Path(__file__).resolve().parent
DEFAULT_DB = ROOT / "data" / "market_step5_history.sqlite3"
PHASES = ("PRE_RESULTS", "POST_RESULTS")
WEIGHTS = {
    "PRE_RESULTS": {"momentum_30": 25, "relative_volume": 20,
                    "trend_20": 20, "dollar_liquidity": 15, "volatility_risk": 20},
    "POST_RESULTS": {"momentum_30": 20, "relative_volume": 25,
                     "trend_20": 20, "dollar_liquidity": 20, "volatility_risk": 15},
}
EXTRA_MAX_AGE_DAYS = {"short_interest_pct_float": 45, "days_to_cover": 45,
                      "implied_volatility_pct": 7, "institutional_holding_change_pct": 110,
                      "borrow_fee_pct": 7}
EXTRA_BOUNDS = {"short_interest_pct_float": (0, 100),
                "days_to_cover": (0, 10000), "implied_volatility_pct": (0, 5000),
                "institutional_holding_change_pct": (-100, 10000),
                "borrow_fee_pct": (0, 10000)}


def clean_ticker(value):
    ticker = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{1,9}(?:[.-][A-Z0-9]{1,4})?", ticker):
        raise ValueError("Ticker contains unsupported characters")
    return ticker


def date_value(value):
    try:
        return value if isinstance(value, date) and not isinstance(value, datetime) else date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def https_source(value):
    return bool(re.fullmatch(r"https://[A-Za-z0-9.-]+(?::443)?(?:/[^\s]*)?", str(value or "").strip(), re.I))


def source_date(value, cutoff):
    d = date_value(value)
    return bool(d and d <= cutoff)


def phase_check(phase, as_of, evidence=None, readout_date=None):
    """A claimed phase needs an as-of eligible dated source; never infer it from price."""
    if phase not in PHASES:
        return "REVIEW — PHASE NOT CONFIRMED"
    evidence = evidence or {}
    if not (https_source(evidence.get("url")) and source_date(evidence.get("date"), as_of)):
        return "REVIEW — MISSING DATED PHASE EVIDENCE"
    actual = date_value(readout_date)
    if phase == "POST_RESULTS":
        if not actual or actual > as_of:
            return "REVIEW — PUBLISHED PHASE 3 READOUT DATE REQUIRED"
        if date_value(evidence["date"]) < actual:
            return "REVIEW — PHASE EVIDENCE PREDATES READOUT"
    elif actual is not None:
        return "REVIEW — PRE-READOUT CANNOT USE AN ACTUAL RESULTS DATE"
    return "REVIEWED — RESEARCHER ASSERTION (NOT INDEPENDENTLY VERIFIED)"


def pdufa_window(phase, as_of, pdufa_date=None, evidence=None):
    if phase != "POST_RESULTS":
        return "NOT APPLICABLE — BEFORE RESULTS"
    event = date_value(pdufa_date)
    evidence = evidence or {}
    if not (event and https_source(evidence.get("url")) and source_date(evidence.get("date"), as_of)):
        return "REVIEW — PDUFA DATE NOT SOURCE VERIFIED"
    remaining = (event - as_of).days
    if remaining < 0:
        return "PAST PDUFA DATE — REVALIDATE"
    if remaining == 0:
        return "DECISION DATE"
    if remaining <= 13:
        return "13–1 DAYS"
    if remaining <= 30:
        return "30–14 DAYS"
    if remaining <= 60:
        return "60–31 DAYS"
    if remaining <= 90:
        return "90–61 DAYS"
    return "OVER 90 DAYS"


def parse_ohlcv(csv_text, as_of=None):
    """Parse named EOD OHLCV columns. Duplicate dates, invalid rows fail closed."""
    if not isinstance(csv_text, str) or len(csv_text) > 2_000_000:
        raise ValueError("Missing or oversized CSV price data")
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    cols = {str(k).strip().lower(): k for k in (reader.fieldnames or []) if k}
    if not {"date", "open", "high", "low", "close", "volume"}.issubset(cols):
        raise ValueError("CSV must have Date,Open,High,Low,Close,Volume")
    cutoff = date_value(as_of) if as_of else datetime.now(timezone.utc).date()
    if cutoff is None:
        raise ValueError("Invalid as-of date")
    unique = {}
    total = 0
    for row in reader:
        total += 1
        if total > 10000:
            raise ValueError("Price CSV exceeds 10,000 observations")
        stamp = date_value(row.get(cols["date"]))
        if stamp is None:
            raise ValueError("Invalid price date")
        if stamp > cutoff:
            continue
        if stamp in unique:
            raise ValueError(f"Duplicate trading-date bar {stamp}")
        try:
            numbers = {k: float(row.get(cols[k], "")) for k in ("open", "high", "low", "close", "volume")}
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Bad price or volume on {stamp}") from exc
        if (not all(math.isfinite(v) for v in numbers.values())
                or any(numbers[k] <= 0 for k in ("open", "high", "low", "close"))
                or numbers["volume"] < 0):
            raise ValueError(f"Invalid nonfinite/nonpositive price or negative volume on {stamp}")
        if numbers["low"] > numbers["high"] or not (numbers["low"] <= numbers["close"] <= numbers["high"]):
            raise ValueError(f"Inconsistent high/low/close on {stamp}")
        unique[stamp] = {"date": stamp.isoformat(), **numbers}
    return [unique[key] for key in sorted(unique)]


def fetch_stooq_daily(ticker, as_of=None, opener=urlopen, tries=2):
    """Optional delayed EOD price discovery. Stooq is not exchange-certified."""
    t = clean_ticker(ticker)
    until = date_value(as_of) if as_of else datetime.now(timezone.utc).date()
    if until is None or until > datetime.now(timezone.utc).date():
        raise ValueError("As-of cannot be in the future")
    start = until - timedelta(days=420)
    # Stooq US feed supports dotted class-share symbols; do not infer exchange identity.
    url = "https://stooq.com/q/d/l/?" + urlencode({
        "s": t.lower() + ".us", "i": "d",
        "d1": start.strftime("%Y%m%d"), "d2": until.strftime("%Y%m%d")})
    req = Request(url, headers={"User-Agent": "PDUFA-Research/1.0 public-market-data",
                                "Accept": "text/csv"})
    for attempt in range(tries):
        try:
            with opener(req, timeout=18) as response:
                payload = response.read(1_000_001)
            if len(payload) > 1_000_000:
                raise RuntimeError("Oversized price provider response")
            text = payload.decode("utf-8-sig")
            bars = parse_ohlcv(text, until)
            if not bars:
                raise RuntimeError("No price bars available; ticker/venue feed needs review")
            return bars, {"provider": "STOOQ DELAYED EOD (NOT EXCHANGE-VERIFIED)",
                          "source_url": url, "price_adjustments": "Provider conventions not independently confirmed",
                          "issuer_mapping": "REVIEW — US symbol does not independently confirm underlying issuer"}
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, ValueError, RuntimeError) as exc:
            if attempt < tries - 1 and isinstance(exc, (URLError, TimeoutError, OSError)) and not isinstance(exc, HTTPError):
                time.sleep(1.0)
                continue
            raise RuntimeError(f"EOD price retrieval failed: {exc}. No market score saved.") from exc
    raise RuntimeError("EOD provider unavailable")


def _bucket(v, cuts):
    for cutoff, score in cuts:
        if v < cutoff:
            return score
    return cuts[-1][1]


def _factors(momentum, relative_volume, trend, dollar_volume, volatility):
    return {
        "momentum_30": _bucket(momentum, [(-.2, 0), (0, .25), (.1, .65), (.3, 1), (.6, .75), (math.inf, .45)]),
        "relative_volume": _bucket(relative_volume, [(.5, .15), (.85, .35), (1.2, .55), (2.5, 1), (4, .75), (math.inf, .4)]),
        "trend_20": _bucket(trend, [(-.1, 0), (0, .35), (.15, 1), (.3, .65), (math.inf, .35)]),
        "dollar_liquidity": _bucket(dollar_volume, [(250_000, 0), (1_000_000, .2), (5_000_000, .6), (20_000_000, .9), (math.inf, 1)]),
        "volatility_risk": _bucket(volatility, [(.35, 1), (.65, .85), (1.0, .55), (1.8, .2), (math.inf, 0)]),
    }


def _extra(evidence, as_of):
    """Optional, source-attested figures; missing/stale inputs are omitted, not 0."""
    clean = {}
    issues = []
    for key, (low, high) in EXTRA_BOUNDS.items():
        input_record = (evidence or {}).get(key)
        if input_record is None or input_record == "":
            continue
        if not isinstance(input_record, dict):
            issues.append(f"{key}: expected a value, source URL and dated observation")
            continue
        try:
            value = float(input_record.get("value"))
        except (TypeError, ValueError):
            issues.append(f"{key}: invalid numeric value")
            continue
        observed = date_value(input_record.get("date"))
        url = input_record.get("url")
        if (not math.isfinite(value) or not low <= value <= high or observed is None or observed > as_of
                or (as_of - observed).days > EXTRA_MAX_AGE_DAYS[key] or not https_source(url)):
            issues.append(f"{key}: missing, stale, future, implausible or unsourced — excluded")
            continue
        clean[key] = {"value": value, "date": observed.isoformat(), "url": url,
                      "disclaimer": "Researcher-entered observation, independently unverified"}
    return clean, issues


def evaluate_market(ticker, bars, as_of, phase, phase_evidence=None,
                    readout_date=None, pdufa_date=None, pdufa_evidence=None,
                    extras=None, source=None):
    """Score dated, technically sufficient price data only after phase evidence review.

    No Phase 3 outcome or FDA forecast is used. Same as-of bar cutoff governs
    all features, evidence and publication dates; no future-price leakage.
    """
    ticker = clean_ticker(ticker)
    cutoff = date_value(as_of)
    if cutoff is None or cutoff > datetime.now(timezone.utc).date():
        raise ValueError("As-of must be a valid date, not in the future")
    normalized = parse_ohlcv("Date,Open,High,Low,Close,Volume\n" +
                             "\n".join(",".join(str(b[k]) for k in
                                      ("date", "open", "high", "low", "close", "volume"))
                                      for b in bars), cutoff)
    status = phase_check(phase, cutoff, phase_evidence, readout_date)
    extra, extra_issues = _extra(extras, cutoff)
    report = {
        "ticker": ticker, "as_of": cutoff.isoformat(), "phase": phase, "phase_status": status,
        "phase_evidence": phase_evidence or {}, "readout_date": readout_date or None,
        "pdufa_date": pdufa_date or None, "pdufa_evidence": pdufa_evidence or {},
        "pdufa_window": pdufa_window(phase, cutoff, pdufa_date, pdufa_evidence),
        "source": source or {"provider": "USER-SUPPLIED CSV (UNVERIFIED)", "source_url": ""},
        "technical_score_0_100": None, "score_status": "NOT SCORED",
        "score_type": "MARKET TECHNICAL RESEARCH ONLY — NOT FDA PROBABILITY",
        "weights": WEIGHTS.get(phase), "market_indicators": {},
        "technical_factor_points": {}, "extra_market_observations": extra,
        "coverage": {k: ("OBSERVED" if k in extra else "NOT VERIFIED")
                     for k in EXTRA_BOUNDS},
        "review_flags": extra_issues, "bar_count_as_of": len(normalized),
        "recent_bars_used": normalized[-40:],
    }
    if len(normalized) < 31:
        report["review_flags"].append("Need at least 31 distinct trading sessions; score withheld")
        return report
    last = normalized[-1]
    latest = date_value(last["date"])
    report["market_indicators"]["last_close_usd"] = last["close"]
    report["market_indicators"]["last_market_session"] = last["date"]
    if (cutoff - latest).days > 7:
        report["review_flags"].append("Latest price bar is older than 7 calendar days; score withheld")
        return report
    baseline = normalized[-31]["close"]
    earlier20 = normalized[-21:-1]
    avg_vol = statistics.mean(b["volume"] for b in earlier20)
    if baseline <= 0 or avg_vol <= 0:
        report["review_flags"].append("Zero/invalid price baseline or historical volume")
        return report
    closes20 = [b["close"] for b in normalized[-20:]]
    ma20 = statistics.mean(closes20)
    log_returns = [math.log(normalized[i]["close"] / normalized[i - 1]["close"])
                   for i in range(len(normalized) - 19, len(normalized))]
    annualized_vol = statistics.stdev(log_returns) * math.sqrt(252)
    indicators = {
        "momentum_30_session_pct": round((last["close"] / baseline - 1) * 100, 3),
        "relative_volume_vs_prior20": round(last["volume"] / avg_vol, 3),
        "close_vs_sma20_pct": round((last["close"] / ma20 - 1) * 100, 3),
        "avg_dollar_volume_20_usd": round(statistics.mean(b["close"] * b["volume"] for b in earlier20), 2),
        "annualized_historical_volatility_20_pct": round(annualized_vol * 100, 3),
        "latest_daily_volume": last["volume"],
    }
    report["market_indicators"].update(indicators)
    # Reject insufficiently verified stage but retain observed metrics for review.
    if not status.startswith("REVIEWED"):
        report["review_flags"].append(status)
        return report
    values = _factors(
        indicators["momentum_30_session_pct"] / 100,
        indicators["relative_volume_vs_prior20"],
        indicators["close_vs_sma20_pct"] / 100,
        indicators["avg_dollar_volume_20_usd"],
        indicators["annualized_historical_volatility_20_pct"] / 100)
    weight = WEIGHTS[phase]
    points = {k: round(weight[k] * v, 2) for k, v in values.items()}
    report["technical_factor_points"] = points
    report["technical_score_0_100"] = round(sum(points.values()), 2)
    report["score_status"] = "REVIEWED TECHNICAL SCORE — PHASE AND INSTRUMENT NOT INDEPENDENTLY VERIFIED"
    if indicators["momentum_30_session_pct"] > 60:
        report["review_flags"].append("Price run-up over 60% across 30 sessions; chase/mean-reversion risk")
    if indicators["avg_dollar_volume_20_usd"] < 1_000_000:
        report["review_flags"].append("Low average dollar liquidity; slippage risk")
    return report


def financial_context_asof(ticker, as_of, sec_db=None):
    """Context-only Step 4 risk; no scoring or post-as-of financial lookahead."""
    cutoff = date_value(as_of)
    if cutoff is None:
        return None
    rows = read_sec_history(sec_db, ticker) if sec_db is not None else read_sec_history(ticker=ticker)
    for row in rows:
        item = json.loads(row["payload_json"])
        stamp = date_value(item.get("as_of"))
        if stamp is None or stamp > cutoff:
            continue
        # Only use underlying filed evidence available on or before observation.
        sources = item.get("evidence") or {}
        if any(date_value(v.get("filed")) and date_value(v["filed"]) > cutoff
               for v in sources.values() if isinstance(v, dict)):
            continue
        return {"cash_runway_risk": item.get("cash_runway_risk"),
                "cash_runway_months": item.get("runway_months_cash_only"),
                "financial_as_of": stamp.isoformat(),
                "note": "Context only. Cash-runway index excluded from technical setup score."}
    return None


def _connection(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("""CREATE TABLE IF NOT EXISTS market_step5_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        captured_utc TEXT NOT NULL,
        ticker TEXT NOT NULL,
        phase TEXT NOT NULL,
        as_of TEXT NOT NULL,
        checksum TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        UNIQUE(ticker, phase, as_of, checksum)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS market_step5_ticker ON market_step5_history(ticker,as_of,id)")
    return db


def save_snapshot(report, db_path=DEFAULT_DB):
    data = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)
    sha = hashlib.sha256(data.encode("utf-8")).hexdigest()
    with _connection(db_path) as db:
        db.execute("""INSERT OR IGNORE INTO market_step5_history
            (captured_utc,ticker,phase,as_of,checksum,payload_json) VALUES(?,?,?,?,?,?)""",
            (datetime.now(timezone.utc).isoformat(), report["ticker"], report["phase"],
             report["as_of"], sha, data))
        row = db.execute("""SELECT id FROM market_step5_history WHERE ticker=?
            AND phase=? AND as_of=? AND checksum=?""",
            (report["ticker"], report["phase"], report["as_of"], sha)).fetchone()
        return int(row["id"])


def read_history(db_path=DEFAULT_DB, ticker=None):
    with _connection(db_path) as db:
        if ticker:
            rows = db.execute("SELECT * FROM market_step5_history WHERE ticker=? ORDER BY id DESC",
                              (clean_ticker(ticker),)).fetchall()
        else:
            rows = db.execute("SELECT * FROM market_step5_history ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def rankings(history, as_of, phase):
    """Apples-to-apples scores: same analysis date and same phase only."""
    by_ticker = {}
    for row in history:
        report = json.loads(row["payload_json"])
        if report.get("as_of") != str(as_of) or report.get("phase") != phase:
            continue
        if report.get("technical_score_0_100") is None:
            continue
        ticker = clean_ticker(report["ticker"])
        if ticker not in by_ticker or row["id"] > by_ticker[ticker][0]:
            by_ticker[ticker] = (row["id"], report)
    ranked = sorted((x[1] for x in by_ticker.values()),
                    key=lambda r: (-r["technical_score_0_100"], r["ticker"]))
    return [{"rank": i + 1, "ticker": r["ticker"],
             "phase": phase, "score": r["technical_score_0_100"],
             "as_of": str(as_of), "last_close": r["market_indicators"].get("last_close_usd"),
             "relative_volume": r["market_indicators"].get("relative_volume_vs_prior20"),
             "source_status": r["source"].get("issuer_mapping", "USER CSV — UNVERIFIED")}
            for i, r in enumerate(ranked)]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Step 5 manually triggered delayed-EOD research")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument("--phase-url", required=True, help="Source documenting phase state")
    parser.add_argument("--phase-date", required=True, help="Date of phase source")
    parser.add_argument("--readout-date", help="Actual Phase 3 results publication, POST only")
    parser.add_argument("--as-of", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--csv", type=Path, help="Local OHLCV CSV (instead of EOD provider)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)
    reg = load_registry()
    ticker = clean_ticker(args.ticker)
    if ticker not in reg or reg[ticker].get("conflict"):
        parser.error("Ticker lacks unique registered SEC issuer identity")
    if args.csv:
        bars = parse_ohlcv(args.csv.read_text(encoding="utf-8-sig"), args.as_of)
        source = {"provider": "USER-SUPPLIED CSV (UNVERIFIED)", "source_url": "",
                  "issuer_mapping": "REVIEW — manually supplied price instrument"}
    else:
        bars, source = fetch_stooq_daily(ticker, args.as_of)
    report = evaluate_market(ticker, bars, args.as_of, args.phase,
                             phase_evidence={"url": args.phase_url, "date": args.phase_date},
                             readout_date=args.readout_date, source=source)
    row_id = save_snapshot(report, args.db)
    print(json.dumps({"revision": row_id, "ticker": ticker,
                      "technical_score": report["technical_score_0_100"],
                      "review_flags": report["review_flags"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
