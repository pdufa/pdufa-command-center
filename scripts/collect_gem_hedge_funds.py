#!/usr/bin/env python3
"""Download source-backed 13F XML holdings for four SEC-identified biotech managers.

SEC manager CIK + current and previous complete 13F-HR information tables.
This is a capped long-holdings comparison, not a live-trade or global 13F feed.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gem_hedge_funds import (DATA_FILE, SCHEMA, day, tracked_issuers,  # noqa: E402
                             summarize_filings)

SEC_API = "https://data.sec.gov"
SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data"
MAX_READ = 2_500_000


def sec_get(url, user_agent, *, opener=urlopen):
    if not isinstance(user_agent, str) or "@" not in user_agent or len(user_agent.strip()) < 12:
        raise ValueError("Verified SEC_USER_AGENT with contact email required")
    if not (re.fullmatch(r"https://data\.sec\.gov/submissions/CIK[0-9]{10}\.json", url)
            or re.fullmatch(
                r"https://www\.sec\.gov/Archives/edgar/data/[0-9]+/[0-9]+/"
                r"[A-Za-z0-9_.\-]{1,100}", url,
            )):
        raise ValueError("SEC URL is not an approved filings/data endpoint")
    req = Request(url, headers={
        "User-Agent": user_agent, "Accept": "application/json, application/xml, text/xml",
        "Accept-Encoding": "identity",
    })
    with opener(req, timeout=30) as stream:
        body = stream.read(MAX_READ + 1)
        if len(body) > MAX_READ:
            raise ValueError("SEC 13F response exceeds capped source size")
        return body


def _leaf(tag):
    return str(tag).split("}")[-1].lower()


def _child(node, wanted):
    for child in node:
        if _leaf(child.tag) == wanted.lower():
            return child
    return None


def _field(node, key):
    found = _child(node, key)
    return "".join(found.itertext()).strip() if found is not None else ""


def parse_information_table(body):
    """Reject malformed XML; count only reportable long-share common equity."""
    try:
        root = ET.fromstring(body)
    except (ET.ParseError, TypeError) as exc:
        raise ValueError("Invalid SEC Form 13F XML information table") from exc
    if _leaf(root.tag) not in ("informationtable", "infotable"):
        raise ValueError("Unexpected XML 13F root; information table not verified")
    results = []
    for node in root:
        if _leaf(node.tag) != "infotable":
            continue
        if _field(node, "putCall"):
            continue
        title = _field(node, "titleOfClass").upper()
        if not (title.startswith(("COM", "ORD", "SHS", "CL A", "CL B", "SPONSORED ADS",
                                  "SPON ADS", "SPONSORED ADR", "ADR", "ADS"))
                or title in ("SH", "SHARES", "COMMON SHARES")):
            continue
        amount = _child(node, "shrsOrPrnAmt")
        if amount is None or _field(amount, "sshPrnamtType").upper() != "SH":
            continue
        raw = _field(amount, "sshPrnamt")
        if not re.fullmatch(r"[0-9]+(?:\.0+)?", raw):
            continue
        shares = int(raw.split(".")[0])
        cusip = _field(node, "cusip").upper().replace(" ", "")
        issuer = _field(node, "nameOfIssuer")
        if (not re.fullmatch(r"[A-Z0-9]{9}", cusip)
                or not issuer or shares <= 0):
            continue
        results.append({"issuer": issuer, "cusip": cusip,
                        "shares": shares, "class": title})
    return results


def filing_inventory(submissions, cik, *, as_of):
    if (not isinstance(submissions, dict)
            or str(submissions.get("cik") or "").lstrip("0") != str(int(cik))):
        raise ValueError("SEC manager submissions CIK mismatch")
    recent = submissions.get("filings", {}).get("recent", {})
    fields = ("form", "filingDate", "reportDate", "accessionNumber")
    if not isinstance(recent, dict) or any(not isinstance(recent.get(k), list) for k in fields):
        raise ValueError("SEC submissions missing required filing fields")
    filings = {}
    amended_periods = set()
    counts = [len(recent[k]) for k in fields]
    if len(set(counts)) != 1:
        raise ValueError("SEC submission arrays incomplete")
    for form, filed, period, acc in zip(*(recent[k] for k in fields)):
        when, end = day(filed), day(period)
        if (not when or not end or when > as_of or when < end
                or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(acc))
                or (as_of - end).days < 0):
            continue
        if form == "13F-HR/A":
            amended_periods.add(end)
        elif form == "13F-HR":
            previous = filings.get(end)
            if previous is None or when > previous["filed"]:
                filings[end] = {"period": end, "filed": when, "accession": acc}
    # Ignoring amendments would fabricate a complete comparison.
    for period in amended_periods:
        filings.pop(period, None)
    return sorted(filings.values(), key=lambda row: row["period"], reverse=True)[:2]


def get_holdings(cik, filing, agent, *, fetch=sec_get):
    directory = (
        f"{SEC_ARCHIVE}/{int(cik)}/{filing['accession'].replace('-', '')}"
    )
    time.sleep(0.15)
    idx = json.loads(fetch(directory + "/index.json", agent))
    files = idx.get("directory", {}).get("item", [])
    if not isinstance(files, list):
        raise ValueError("13F filing directory cannot be verified")
    matches = []
    for item in files:
        name = str(item.get("name") or "") if isinstance(item, dict) else ""
        if (re.fullmatch(r"[A-Za-z0-9_.\-]{1,100}", name)
                and name.lower().endswith(".xml")
                and ("info" in name.lower() or "table" in name.lower())
                and "primary" not in name.lower()):
            matches.append(name)
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous SEC 13F XML information table")
    time.sleep(0.15)
    url = directory + "/" + matches[0]
    positions = parse_information_table(fetch(url, agent))
    if not positions:
        raise ValueError("SEC 13F table contains no validated common-share positions")
    return {"holdings": positions, "url": url}


def manager_roster(path, limit=8):
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except (OSError, ValueError, UnicodeError, csv.Error):
        return []
    result = []
    seen = set()
    for row in rows[:limit]:
        cik = str(row.get("cik") or "").strip()
        name = str(row.get("manager_name") or "").strip()
        proof = str(row.get("sec_proof_url") or "")
        if (not cik.isdigit() or not 1 <= int(cik) < 10**10
                or not name or cik in seen or
                not proof.startswith("https://www.sec.gov/Archives/edgar/data/")):
            continue
        seen.add(cik)
        result.append({"cik": f"{int(cik):010d}", "name": name,
                       "proof": proof})
    return result


def collect(root, *, as_of, agent, fetch=sec_get):
    root = Path(root)
    roster = manager_roster(root / "gem_hedge_fund_managers.csv")
    issuer_map = tracked_issuers(root)
    loaded = []
    for manager in roster:
        cik = manager["cik"]
        observed = {"cik": cik, "name": manager["name"],
                    "source": manager["proof"], "status": "ERROR"}
        try:
            time.sleep(0.15)
            uri = f"{SEC_API}/submissions/CIK{cik}.json"
            submissions = json.loads(fetch(uri, agent))
            selected = filing_inventory(submissions, cik, as_of=as_of)
            if len(selected) != 2:
                raise ValueError("Two completed, non-amended 13F report quarters unavailable")
            if not 85 <= (selected[0]["period"] - selected[1]["period"]).days <= 98:
                raise ValueError("Previous 13F quarter missing; cannot infer share delta")
            if (as_of - selected[0]["period"]).days > 200:
                raise ValueError("Latest 13F period too old")
            new = get_holdings(cik, selected[0], agent, fetch=fetch)
            old = get_holdings(cik, selected[1], agent, fetch=fetch)
            observed.update({
                "status": "COMPLETE",
                "current": new, "previous": old,
                "latest_period": selected[0]["period"].isoformat(),
                "prior_period": selected[1]["period"].isoformat(),
                "latest_filing": selected[0]["filed"].isoformat(),
                "source": new["url"],
                "current_url": new["url"],
                "previous_url": old["url"],
            })
        except (OSError, ValueError, RuntimeError, KeyError, TypeError, json.JSONDecodeError) as exc:
            observed["error"] = str(exc)[:250]
        loaded.append(observed)

    rows, reports = summarize_filings(issuer_map, loaded, as_of=as_of)
    good = sum(row["status"] == "COMPLETE" for row in reports)
    report = {
        "schema_version": SCHEMA,
        "source": "SEC_13F_XML_INFO_TABLE",
        "as_of_pacific": as_of.isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manager_count": len(roster), "managers_complete": good,
        "collector_status": (
            "COMPLETE — SELECTED FUNDS ONLY" if good == len(roster) and good else
            "PARTIAL — MANAGER SOURCE FAILURES" if good else
            "BLOCKED — NO VERIFIED 13F MANAGERS"
        ),
        "reports": reports, "records": rows,
        "matched_ticker_count": len(rows),
        "limitations": (
            "Selected managers only; exact normalized SEC issuer name and common "
            "class CUSIP, not fuzzy ticker matching. Latest and prior distinct "
            "report quarters required. Quarterly holdings delayed up to 45 days "
            "after quarter end; missing matches are NOT zero ownership."
        ),
    }
    root.mkdir(parents=True, exist_ok=True)
    target = root / DATA_FILE
    temp = target.with_name(target.name + ".tmp")
    temp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(target)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--as-of")
    args = parser.parse_args(argv)
    from zoneinfo import ZoneInfo
    today = day(args.as_of) if args.as_of else datetime.now(
        ZoneInfo("America/Los_Angeles")).date()
    if today is None:
        parser.error("--as-of must be YYYY-MM-DD")
    agent = os.getenv("SEC_USER_AGENT", "")
    try:
        report = collect(args.data_dir, as_of=today, agent=agent)
    except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
        parser.error("SEC 13F collector failed closed: " + str(exc))
    print(json.dumps({key: report[key] for key in (
        "collector_status", "manager_count", "managers_complete",
        "matched_ticker_count",
    )}, sort_keys=True))
    return 0 if report["manager_count"] and report["managers_complete"] == report["manager_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
