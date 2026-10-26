#!/usr/bin/env python3
"""Manage a PAPER Alpaca GEM watchlist; never submit brokerage orders.

Explicit operator add only; the daily scan only uses read-only GET methods.
GitHub Actions secrets are separate from Streamlit Cloud secrets.
"""
from __future__ import annotations
import argparse
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PAPER_URL = "https://paper-api.alpaca.markets"
DEFAULT_NAME = "GEM DAILY MONITOR"
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


class AlpacaUnavailable(RuntimeError):
    pass


def paper_credentials(env=None):
    env = env if env is not None else os.environ
    if str(env.get("ALPACA_PAPER","true")).lower() != "true":
        raise AlpacaUnavailable("Paper-only monitor: ALPACA_PAPER must be true")
    key = env.get("ALPACA_API_KEY") or env.get("APCA_API_KEY_ID")
    secret = env.get("ALPACA_SECRET_KEY") or env.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise AlpacaUnavailable("Missing paper credentials in runtime environment")
    return str(key), str(secret)


def paper_json(method, path, *, credentials, payload=None, opener=None):
    if not path.startswith("/v2/watchlists"):
        raise ValueError("Watchlist endpoint only")
    fetch = opener or urlopen
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        PAPER_URL + path, method=method, data=body,
        headers={
            "APCA-API-KEY-ID": credentials[0],
            "APCA-API-SECRET-KEY": credentials[1],
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body is not None else {})
        }
    )
    try:
        with fetch(request, timeout=25) as result:
            return json.load(result)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise AlpacaUnavailable(f"Alpaca paper watchlist returned HTTP {exc.code}") from None
    except (URLError, TimeoutError):
        raise AlpacaUnavailable("Unable to reach Alpaca paper watchlist API") from None
    except (ValueError, TypeError):
        raise AlpacaUnavailable("Malformed Alpaca paper watchlist response") from None


def get_watchlist(name=DEFAULT_NAME, *, credentials, opener=None):
    if not name or len(name) > 80:
        raise ValueError("Watchlist name is required (up to 80 characters)")
    return paper_json("GET", "/v2/watchlists:by_name?"+urlencode({"name":name}),
                      credentials=credentials,opener=opener)


def add_symbol(symbol, *, name=DEFAULT_NAME, credentials, opener=None):
    """The ONLY account-write operation is explicitly invoked by the operator."""
    symbol = symbol.strip().upper()
    if not SYMBOL.fullmatch(symbol):
        raise ValueError("Invalid US-equity ticker symbol")
    existing = get_watchlist(name, credentials=credentials, opener=opener)
    if existing is None:
        return paper_json("POST", "/v2/watchlists",
                          credentials=credentials,
                          payload={"name":name,"symbols":[symbol]},opener=opener)
    if symbol in {str(a.get("symbol","")).upper()
                  for a in existing.get("assets",[]) if isinstance(a,dict)}:
        return existing
    return paper_json("POST",
                      "/v2/watchlists:by_name?"+urlencode({"name":name}),
                      credentials=credentials,payload={"symbol":symbol},
                      opener=opener)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--add", required=True,
                   help="Ticker to add by explicit operator action only")
    p.add_argument("--name",default=DEFAULT_NAME)
    args=p.parse_args(argv)
    try:
        credentials=paper_credentials()
        result=add_symbol(args.add,name=args.name,credentials=credentials)
        if not isinstance(result,dict):
            raise AlpacaUnavailable("Watchlist response not confirmed")
        names={str(a.get("symbol","")).upper()
               for a in result.get("assets",[]) if isinstance(a,dict)}
        if args.add.strip().upper() not in names:
            raise AlpacaUnavailable("Alpaca did not confirm the symbol in this watchlist")
    except (ValueError,AlpacaUnavailable) as exc:
        p.exit(2,str(exc)+"\n")
    print(json.dumps({"status":"ADDED_OR_ALREADY_WATCHED",
                      "ticker":args.add.upper(),
                      "watchlist":args.name,
                      "market_orders_submitted":0}))


if __name__=="__main__":
    main()
