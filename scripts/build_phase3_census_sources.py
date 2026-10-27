#!/usr/bin/env python3
"""Build research pointers from saved exact-NCT/issuer records; never qualify trials.

No network, source promotion, scans, scores or trading operations. --check verifies
that the committed public directory is reproducible from its four source files.
"""
import argparse
import csv
import hashlib
import io
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "new-platform/frontend/public/phase3-census-sources-2026-10-26.json"
INPUTS = (
    "data/phase3_all_years_300m_10b_trials.csv",
    "data/company_registry.csv",
    "data/phase_pipeline_market_caps_census_2026-10-26.csv",
    "config/issuer_sources.json",
)
AS_OF = "2026-10-26T12:21:15.972309+00:00"


def require(condition):
    if not condition:
        raise ValueError("Saved census source identity, URL, date or count mismatch")


def build():
    raw = {name: (ROOT / name).read_bytes() for name in INPUTS}
    rows = lambda name: list(csv.DictReader(io.StringIO(raw[name].decode("utf-8"))))
    trials, registry, caps = [rows(name) for name in INPUTS[:3]]
    issuers = json.loads(raw[INPUTS[3]])
    require(len(trials) == len({r["nct_id"] for r in trials}) == 741)
    tickers = sorted({r["ticker"] for r in trials})
    require(len(tickers) == 130)
    companies = []
    for ticker in tickers:
        require(re.fullmatch(r"[A-Z]{1,7}(?:[.-][A-Z]{1,3})?", ticker))
        records = [r for r in registry if r["ticker"] == ticker]
        quotes = [r for r in caps if r["ticker"] == ticker]
        require(len(records) == len(quotes) == 1)
        company, quote = records[0], quotes[0]
        cik = company["cik10"]
        require(company["status"] == "OK" and re.fullmatch(r"\d{10}", cik) and int(cik) > 0)
        cap = float(quote["market_cap"])
        cap_url = f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks"
        require(quote["market_cap_status"] == "VERIFIED" and 300_000_000 <= cap <= 10_000_000_000)
        require(quote["market_cap_source"] == cap_url)
        checked = datetime.fromisoformat(quote["market_cap_checked_at"])
        require(checked.tzinfo and checked <= datetime.fromisoformat(AS_OF))
        hosts = issuers.get(ticker, {}).get("hosts", [])
        require(isinstance(hosts, list) and len(hosts) == len(set(hosts)))
        for host in hosts:
            require(isinstance(host, str) and re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*\.[a-z]{2,}", host))
        exact_trials = [r for r in trials if r["ticker"] == ticker]
        for row in exact_trials:
            require(re.fullmatch(r"NCT\d{8}", row["nct_id"]))
            require(row["source_url"] == "https://clinicaltrials.gov/study/" + row["nct_id"])
        companies.append({
            "ticker": ticker,
            "company": company["company"],
            "cik": cik,
            "leadSponsorNames": sorted({r["company"] for r in exact_trials}),
            "nctIds": sorted(r["nct_id"] for r in exact_trials),
            "marketCapUsd": cap,
            "marketCapCheckedAt": quote["market_cap_checked_at"],
            "marketCapSourceUrl": cap_url,
            "secFilingsUrl": f"https://www.sec.gov/edgar/browse/?CIK={cik}&owner=exclude",
            "secSubmissionsUrl": f"https://data.sec.gov/submissions/CIK{cik}.json",
            "configuredIssuerHomepages": sorted(f"https://{host}/" for host in hosts),
        })
    return {
        "schemaVersion": 1,
        "scope": "RESEARCH_POINTERS_ONLY",
        "censusAsOf": AS_OF,
        "trialCount": 741,
        "companyCount": 130,
        "inputs": [{"path": name, "sha256": hashlib.sha256(raw[name]).hexdigest()} for name in INPUTS],
        "companies": companies,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            raise SystemExit("Saved census research pointers differ from their source files; rebuild and review.")
        print("741 exact trial mappings / 130 saved issuer-cap records reproducible. No external source recheck or qualification.")
    else:
        OUTPUT.write_text(content, encoding="utf-8")
        print("Built research pointers; all Pipeline/FDA evidence gates remain unchanged.")


if __name__ == "__main__":
    main()
