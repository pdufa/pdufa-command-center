#!/usr/bin/env python3
"""Fetch historical split-adjusted Alpaca bars into a REVIEW-ONLY staging CSV.

The output cannot be consumed as VERIFIED by the trading backtest until ticker
identity, provider response, corporate actions and price gaps are audited.
Secrets come from environment variables; they are never written to disk.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FIELDS = ("ticker","session","open","high","low","close","volume",
          "source_url","adjustment_status")
SYMBOL = re.compile(r"^[A-Z0-9.-]{1,12}$")
API_BASE = "https://data.alpaca.markets/v2/stocks"


def request_bars(symbol, start, end, asof, key, secret, feed="sip",
                 fetch=None):
    if not SYMBOL.fullmatch(symbol):
        raise ValueError("Invalid ticker")
    if start >= end:
        raise ValueError("Start must precede end")
    # Used only for authentic daily historical prices; not a live quote.
    endpoint = API_BASE+"/"+symbol+"/bars"
    results=[]
    token=None
    seen_tokens=set()
    fetch=fetch or urlopen
    while True:
        params={"timeframe":"1Day","start":start,"end":end,"asof":asof,
                "adjustment":"split","feed":feed,"limit":"10000"}
        if token:
            params["page_token"]=token
        req=Request(endpoint+"?"+urlencode(params),
                    headers={"APCA-API-KEY-ID":key,
                             "APCA-API-SECRET-KEY":secret,
                             "Accept":"application/json"})
        try:
            with fetch(req,timeout=30) as response:
                data=json.load(response)
        except HTTPError as exc:
            raise RuntimeError("Alpaca HTTP status "+str(exc.code)) from None
        except URLError:
            raise RuntimeError("Alpaca connection failed") from None
        if not isinstance(data,dict) or not isinstance(data.get("bars"),list):
            raise ValueError("Unexpected Alpaca stock-bars payload")
        for item in data["bars"]:
            if not all(x in item for x in ("t","o","h","l","c","v")):
                raise ValueError("Missing OHLCV field")
            session=str(item["t"])[:10]
            date.fromisoformat(session)
            results.append({
                "ticker":symbol,"session":session,
                "open":item["o"],"high":item["h"],"low":item["l"],
                "close":item["c"],"volume":item["v"],
                "source_url":endpoint,
                "adjustment_status":"PENDING_TICKER_AND_SPLIT_AUDIT",
            })
        token=data.get("next_page_token")
        if not token:
            break
        if token in seen_tokens:
            raise ValueError("Repeated Alpaca pagination token")
        seen_tokens.add(token)
        if len(seen_tokens)>500:
            raise ValueError("Too many paginated pages")
    dates=[x["session"] for x in results]
    if len(dates)!=len(set(dates)):
        raise ValueError("Duplicate session from provider")
    if any(x["session"]<start or x["session"]>=end for x in results):
        raise ValueError("Out-of-window provider bar")
    results.sort(key=lambda x:x["session"])
    return results


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbols",required=True,
                   help="Comma-separated historic tickers, NOT current GEM list")
    p.add_argument("--start",default="2024-07-01")
    p.add_argument("--end",default="2026-01-01")
    p.add_argument("--asof",default="2025-12-31")
    p.add_argument("--feed",choices=("sip","iex"),default="sip")
    p.add_argument("--output",default="output/gem_2025_alpaca_review.csv")
    args=p.parse_args(argv)
    # Strict validation before credentials/network.
    symbols=[s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols or len(symbols)!=len(set(symbols)) or not all(
            SYMBOL.fullmatch(s) for s in symbols):
        p.error("Use unique, valid historical stock symbols")
    try:
        start=date.fromisoformat(args.start)
        end=date.fromisoformat(args.end)
        asof=date.fromisoformat(args.asof)
    except ValueError:
        p.error("Dates must be ISO YYYY-MM-DD")
    key=os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
    secret=os.environ.get("APCA_API_SECRET_KEY") or os.environ.get("ALPACA_SECRET_KEY")
    if not key or not secret:
        p.error("Required Alpaca environment credentials are missing")
    rows=[]
    for symbol in symbols:
        try:
            rows.extend(request_bars(symbol,start.isoformat(),end.isoformat(),
                                     asof.isoformat(),key,secret,feed=args.feed))
        except (ValueError,RuntimeError) as exc:
            # Do not log credentials, request headers or secret URL values.
            print(symbol+": data unavailable ("+str(exc)+")",file=sys.stderr)
            return 2
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"review_status":"PROVENANCE_AUDIT_REQUIRED",
                      "feed":args.feed,"symbols":symbols,"bars":len(rows),
                      "output":str(out)},sort_keys=True))
    return 0


if __name__=="__main__":
    sys.exit(main())
