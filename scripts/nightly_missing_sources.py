#!/usr/bin/env python3
"""PDUFA missing-source intake, scoped evidence review, and coverage audit.

Runs event-specific live rechecks using the existing fail-closed engine; also
checks the full SEC company registry and discovers issuer news independently.
New source observations are artifacts, not automatic approvals or trade signals.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "reports" / "missing_sources"
CATS = {
    "FDA": ["pdufa_date"],
    "SEC": ["financing", "ownership_insiders"],
    "FINANCIAL": ["cash_runway"],
    "MARKET": ["market_data"],
}
STATUS_MAP = {
    "FDA": ["pdufa_date"],
    "SEC": ["financing", "ownership_insiders"],
    "FINANCIAL": ["cash_runway"],
    "MARKET": ["market_data"],
    "ISSUER": [],
}
FULL_SOURCE_FAMILIES = [
    "ClinicalTrials.gov", "FDA actions and application identity",
    "SEC financing/ownership", "issuer primary announcements",
    "cash and financial runway", "market quotes/volume",
    "short interest/IV/borrow when obtainable", "company-level reconciliation",
]


def now():
    return datetime.now(timezone.utc).isoformat()


def read_rows(path):
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def write_rows(path, rows, names):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def candidates(data_dir):
    return [r for r in read_rows(data_dir / "pdufa_candidates.csv")
            if r.get("event_key") and r.get("ticker")]


def registry(data_dir):
    return [r for r in read_rows(data_dir / "company_registry.csv")
            if r.get("ticker")]


def http_bytes(url, *, agent, timeout=15, accept="application/json"):
    request = urllib.request.Request(url, headers={
        "User-Agent": agent, "Accept": accept})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(3_000_001)


def failure_label(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP_" + str(exc.code)
    if isinstance(exc, TimeoutError):
        return "TIMEOUT"
    if isinstance(exc, urllib.error.URLError):
        return "NETWORK_UNAVAILABLE"
    return type(exc).__name__[:60]


def sec_registry(data_dir, out, agent):
    """SEC filings inventory for ALL registry CIKs; never infer offering closed."""
    companies = registry(data_dir)
    rows = []
    consecutive_403 = 0
    for company in companies:
        ticker = company.get("ticker", "").strip().upper()
        cik = re.sub(r"\D", "", company.get("cik10", "")).zfill(10)
        item = {"ticker": ticker, "cik10": cik, "status": "NOT_CHECKED",
                "latest_filing_form": "", "latest_filing_date": "",
                "filing_count_recent": "", "source_url": "", "note": ""}
        if not re.fullmatch(r"\d{10}", cik) or cik == "0000000000":
            item["status"] = "MISSING_CIK"
        elif consecutive_403 >= 3:
            item["status"] = "NOT_ATTEMPTED_SEC_403"
            item["note"] = "SEC blocked three consecutive requests; do not hammer provider"
        else:
            url = "https://data.sec.gov/submissions/CIK" + cik + ".json"
            item["source_url"] = url
            try:
                payload = json.loads(http_bytes(url, agent=agent))
                recent = payload.get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                dates = recent.get("filingDate", [])
                item["status"] = "FILINGS_INDEX_CHECKED"
                item["latest_filing_form"] = forms[0] if forms else ""
                item["latest_filing_date"] = dates[0] if dates else ""
                item["filing_count_recent"] = len(forms)
                item["note"] = "Index only; offering closure and exhibit content NOT verified"
                consecutive_403 = 0
            except Exception as exc:
                label = failure_label(exc)
                item["status"] = "SEC_SOURCE_BLOCKED_" + label
                consecutive_403 = consecutive_403 + 1 if label == "HTTP_403" else 0
            time.sleep(0.15)
        rows.append(item)
    path = out / "sec_registry_inventory.csv"
    write_rows(path, rows, list(rows[0]) if rows else [
        "ticker", "cik10", "status", "latest_filing_form",
        "latest_filing_date", "filing_count_recent", "source_url", "note"])
    counts = Counter(r["status"] for r in rows)
    return {"registry_companies": len(companies),
            "companies_checked": counts["FILINGS_INDEX_CHECKED"],
            "companies_due": len(companies),
            "sec_registry_status_counts": dict(counts),
            "sec_registry_output": str(path),
            "sec_global_403": consecutive_403 >= 3}


def issuer_discovery(data_dir, out):
    """Google News RSS discovery only, NOT verified issuer IR press releases."""
    events = candidates(data_dir)
    by_ticker = {r["ticker"]: r for r in events}
    rows = []
    states = Counter()
    for ticker, event in sorted(by_ticker.items()):
        company = event.get("company", "").strip()
        query = '"' + (company or ticker)[:85] + '" (clinical trial OR FDA OR financing OR results)'
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
            "q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        try:
            payload = http_bytes(url, agent="PDUFA-Research/1.0 (RSS discovery)",
                                 accept="application/rss+xml, application/xml",
                                 timeout=18)
            root = ET.fromstring(payload)
            items = root.findall("./channel/item")[:5]
            states["FEED_FETCHED"] += 1
            for item in items:
                title = (item.findtext("title") or "").strip()[:300]
                link = (item.findtext("link") or "").strip()
                date = (item.findtext("pubDate") or "").strip()
                rows.append({"ticker": ticker, "company": company,
                             "title": title, "published_at": date,
                             "url": link, "verification": "NEWS_DISCOVERY_REVIEW_ONLY",
                             "source_feed": url})
        except Exception as exc:
            states["SOURCE_BLOCKED_" + failure_label(exc)] += 1
        time.sleep(0.2)
    path = out / "issuer_news_discovery.csv"
    write_rows(path, rows, ["ticker", "company", "title", "published_at",
                            "url", "verification", "source_feed"])
    return {"events_due": len(by_ticker),
            "feeds_checked": states["FEED_FETCHED"],
            "issuer_news_candidates": len(rows),
            "issuer_feeds_status": dict(states),
            "issuer_output": str(path),
            "issuer_press_releases_verified": 0}


def recheck(source, data_dir, out):
    """Use existing direct-source event recheck with isolated checkout outputs."""
    events = candidates(data_dir)
    args = [sys.executable, str(ROOT / "scripts/recheck_events.py"),
            "--all", "--categories", ",".join(CATS[source])]
    try:
        result = subprocess.run(args, cwd=ROOT, timeout=3600, check=False)
        exitcode = result.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("Recheck exited without completion: " + type(exc).__name__, file=sys.stderr)
        exitcode = 1
    rows = read_rows(data_dir / "recheck_status.csv")
    keys = {x["event_key"] for x in events}
    scope = [r for r in rows if r.get("event_key") in keys and
             r.get("requested_scope") == "ALL"]
    counts = Counter()
    issues = Counter()
    true_failures = Counter()
    examples = []
    for row in scope:
        for cat in STATUS_MAP[source]:
            status = (row.get(cat + "_status") or "NOT_CHECKED").strip().upper()
            counts[status] += 1
            failed = any(flag in status for flag in ("ERROR", "BLOCKED", "UNAVAILABLE"))
            unresolved = failed or any(flag in status for flag in (
                "REVIEW", "NO_SOURCE", "NO_CIK", "NOT_CHECKED", "NO_VERIFIED_SOURCE",
                "NON_FDA_SOURCE", "DATE_UNVERIFIED"))
            if unresolved:
                issues[cat + ":" + status] += 1
                if len(examples) < 12:
                    examples.append({
                        "ticker": row.get("ticker", ""),
                        "event_key": row.get("event_key", ""),
                        "category": cat,
                        "status": status,
                        "note": (row.get(cat + "_note") or "")[:160],
                    })
            if failed:
                true_failures[cat + ":" + status] += 1
    outfile = out / (source.lower() + "_event_rechecks.csv")
    write_rows(outfile, scope, list(scope[0]) if scope else [
        "event_key", "run_status", "requested_scope"])
    return {"events_due": len(keys), "events_checked": len(scope),
            "source_observations": len(scope) * len(STATUS_MAP[source]),
            "source_status_counts": dict(counts),
            "source_issue_count": sum(issues.values()),
            "source_technical_failure_count": sum(true_failures.values()),
            "source_review_only_count": sum(issues.values()) - sum(true_failures.values()),
            "source_issue_breakdown": dict(issues),
            "source_technical_failure_breakdown": dict(true_failures),
            "source_issue_examples": examples,
            "recheck_exit_code": exitcode, "recheck_output": str(outfile)}


def coverage(out):
    reports = {}
    for name in ("FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER"):
        path = out / (name.lower() + "_scan_report.json")
        try:
            reports[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            reports[name] = {"status": "NOT_RUN_OR_MISSING"}
    statuses = {name: r.get("status", "UNKNOWN") for name, r in reports.items()}
    missing = [name for name, status in statuses.items() if status != "COMPLETE"]
    return {"source_statuses": statuses,
            "missing_required_source_families": missing,
            "sources_passed": sum(x == "COMPLETE" for x in statuses.values()),
            "sources_due": len(statuses),
            "note": "Clinical collection has a separate nightly workflow. "
                    "Issuer RSS is discovery only; verified IR releases, full "
                    "SEC closing-exhibit evidence, FDA action adjudication, "
                    "cash runway, short/borrow/IV, and dashboard ingestion "
                    "remain separately auditable."}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True, choices=[
        "FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER", "AUDIT"])
    p.add_argument("--data-dir", type=Path, default=DATA)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--artifacts-dir", type=Path, default=OUT)
    args = p.parse_args(argv)
    args.artifacts_dir.mkdir(parents=True, exist_ok=True)
    first = now()
    problem = ""
    evidence = {}
    try:
        if args.source == "AUDIT":
            evidence = coverage(args.artifacts_dir)
        elif args.source == "ISSUER":
            evidence = issuer_discovery(args.data_dir, args.artifacts_dir)
        else:
            evidence = recheck(args.source, args.data_dir, args.artifacts_dir)
            if args.source == "SEC":
                from_env = os.environ.get("SEC_USER_AGENT", "").strip()
                if not re.fullmatch(r".{3,120}\s+[^\s@]+@[^\s@]+\.[^\s@]+", from_env):
                    evidence["sec_registry_reason"] = "No valid identifying SEC_USER_AGENT"
                else:
                    evidence.update(sec_registry(args.data_dir, args.artifacts_dir, from_env))
    except Exception as exc:
        problem = type(exc).__name__
        print("Source scan failed: " + problem, file=sys.stderr)

    if args.source == "AUDIT":
        # This audit can only certify completeness with independently checked
        # primary evidence and cross-system reconciliation, which is not present.
        status = "PARTIAL" if not problem else "FAILED"
    elif problem or (args.source in CATS and evidence.get("recheck_exit_code", 1) != 0):
        status = "FAILED"
    else:
        status = "PARTIAL"  # Coverage gaps are explicit, never masked.
    counts = [k + ": " + str(v) for k, v in evidence.items()
              if isinstance(v, int) and not isinstance(v, bool)]
    report = {
        "scan": args.source, "started_at": first, "finished_at": now(),
        "status": status, "source": args.source,
        "scope": "PDUFA event-specific live sources; SEC also inventories company registry",
        "full_coverage_verified": False,
        "errors_count": int(bool(problem)) + evidence.get("source_technical_failure_count", 0),
        "source_review_count": evidence.get("source_review_only_count", 0),
        "errors": [problem] if problem else [],
        "missing_required_source_families": (
            evidence.get("missing_required_source_families", FULL_SOURCE_FAMILIES)),
        "verification_limits": "Source requests and links do NOT certify second financing closure, CRLs, Phase 3 success, or trade eligibility.",
        "source_summary": "; ".join(counts),
        **evidence,
    }
    write_json(args.report, report)
    print(json.dumps(report, indent=2))
    return 0 if status == "PARTIAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
