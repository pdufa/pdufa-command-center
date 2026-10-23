#!/usr/bin/env python3
"""Bounded, rotating SEC and optional Alpaca intake for the shared field catalog.

Uses existing source parsers; all remote endpoints are read-only. This writes
dedicated research caches only, never canonical closing/list/qualification data.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"scripts"))
from shared_enrichment import build, day, read_json, unique
from sec_step4 import load_registry, scan_one
from app.alpaca_market_chart import _credentials, _feed, _parse_bars


def atomic(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, separators=(",", ":"), allow_nan=False)+"\n")
    tmp.replace(path)


def alpaca_bars(ticker, now):
    credentials = _credentials()
    if credentials is None:
        raise ValueError("ALPACA_NOT_CONFIGURED")
    today = now.astimezone(ZoneInfo("America/New_York")).date()
    query = urlencode(dict(timeframe="1Day", start=(today-timedelta(days=505)).isoformat(),
                           end=(today+timedelta(days=1)).isoformat(), limit=1000,
                           adjustment="split", feed=_feed(), sort="asc"))
    source = "https://data.alpaca.markets/v2/stocks/"+quote(ticker, safe="")+"/bars?"+query
    req = Request(source, headers={"APCA-API-KEY-ID": credentials[0], "APCA-API-SECRET-KEY": credentials[1], "Accept": "application/json"})
    with urlopen(req, timeout=18) as response:
        blob = response.read(1_700_001)
    if len(blob) > 1_700_000:
        raise ValueError("MARKET_RESPONSE_TOO_LARGE")
    payload = json.loads(blob)
    if payload.get("next_page_token"):
        raise ValueError("MARKET_HISTORY_INCOMPLETE")
    bars = _parse_bars(payload, ticker, now)
    if not bars:
        raise ValueError("MARKET_HISTORY_EMPTY")
    return dict(ticker=ticker, provider="ALPACA", feed=_feed().upper(), adjustment="split",
                source=source, checkedAt=now.isoformat(), session=bars[-1]["date"], bars=bars)


def collect(data_dir, *, limit=25, now=None, scanner=scan_one, market_fetcher=alpaca_bars):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("America/Los_Angeles")).date()
    data_dir = Path(data_dir)
    _, shards = build(data_dir, today=today, now=now.isoformat())
    registry = load_registry(data_dir/"company_registry.csv")
    symbols = sorted(t for t in shards if t in registry and not registry[t].get("conflict"))
    financial_path, market_path = data_dir/"shared_financials.json", data_dir/"shared_market.json"
    previous = read_json(financial_path, {})
    saved = unique(previous.get("snapshots", []), "ticker")
    recent = unique(read_json(data_dir/"gem_runway_evidence.json", {}).get("snapshots", []), "ticker")
    for symbol, snapshot in recent.items():
        if snapshot.get("as_of", "") > saved.get(symbol, {}).get("as_of", ""):
            saved[symbol] = snapshot
    attempts = dict(previous.get("lastAttempt", {}))
    def due(symbol):
        stamp = day(saved.get(symbol, {}).get("as_of"))
        return not stamp or not 0 <= (today-stamp).days <= 7
    queue = sorted((s for s in symbols if due(s)), key=lambda s: (attempts.get(s, ""), saved.get(s, {}).get("as_of", ""), s))
    agent = os.getenv("SEC_USER_AGENT", "")
    failures, collected = [], 0
    selected = queue[:limit] if "@" in agent and len(agent.strip()) >= 12 else []
    for symbol in selected:
        attempts[symbol] = now.isoformat()
        try:
            _, snap = scanner(symbol, registry=registry, user_agent=agent,
                              db_path=data_dir/"shared_enrichment_financials.sqlite3", as_of=today)
            if snap.get("ticker") != symbol or snap.get("as_of") != today.isoformat():
                raise ValueError("SEC_IDENTITY_MISMATCH")
            saved[symbol] = snap
            collected += 1
        except Exception as exc:
            # Exception text can contain transport details; record type only.
            failures.append(dict(ticker=symbol, status="SEC_SOURCE_UNAVAILABLE", errorType=type(exc).__name__))
    financial = dict(schemaVersion=1, generatedAt=now.isoformat(), status="PARTIAL" if failures or len(queue)>collected else "COMPLETE",
                     attempted=len(selected), collected=collected, remaining=sum(due(s) for s in symbols),
                     configuration="CONFIGURED" if selected or "@" in agent else "SEC_CONTACT_NOT_CONFIGURED",
                     failures=failures, lastAttempt=attempts, snapshots=[saved[s] for s in sorted(saved)])
    atomic(financial_path, financial)
    old_market = read_json(market_path, {})
    markets = unique(old_market.get("snapshots", []), "ticker")
    market_attempts = dict(old_market.get("lastAttempt", {}))
    def market_due(symbol):
        stamp = day(markets.get(symbol, {}).get("checkedAt"))
        return not stamp or stamp != today
    market_queue = sorted((s for s in symbols if market_due(s)), key=lambda s: (market_attempts.get(s, ""), s))
    configured = _credentials() is not None
    market_failures, market_successes = [], 0
    for symbol in market_queue[:limit] if configured else []:
        market_attempts[symbol] = now.isoformat()
        try:
            snap = market_fetcher(symbol, now)
            if snap.get("ticker") != symbol:
                raise ValueError("MARKET_IDENTITY_MISMATCH")
            markets[symbol] = snap
            market_successes += 1
        except Exception as exc:
            market_failures.append(dict(ticker=symbol, status="ALPACA_UNAVAILABLE", errorType=type(exc).__name__))
    market = dict(schemaVersion=1, generatedAt=now.isoformat(), status="PARTIAL" if market_failures or len(market_queue)>market_successes else "COMPLETE",
                  configuration="CONFIGURED" if configured else "ALPACA_NOT_CONFIGURED", feed=_feed().upper(),
                  attempted=min(limit, len(market_queue)) if configured else 0, collected=market_successes,
                  remaining=sum(market_due(s) for s in symbols), failures=market_failures, lastAttempt=market_attempts,
                  snapshots=[markets[s] for s in sorted(markets)])
    atomic(market_path, market)
    return dict(financial={k: v for k, v in financial.items() if k not in ("snapshots", "lastAttempt")},
                market={k: v for k, v in market.items() if k not in ("snapshots", "lastAttempt")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT/"data")
    parser.add_argument("--max-tickers", type=int, default=25)
    args = parser.parse_args()
    if not 1 <= args.max_tickers <= 75:
        parser.error("--max-tickers must be 1–75")
    print(json.dumps(collect(args.data_dir, limit=args.max_tickers)))
