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
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

if __package__ in ("", None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.source_verification import (
    VERSION, STATES, digest, read_rows as strict_rows, run_identity,
    scope_hash, summary as verification_summary, validate_submissions, verify_source,
)

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
        payload = response.read(3_000_001)
        if response.status != 200 or not payload.strip() or len(payload) > 3_000_000:
            raise ValueError("HTTP response is empty, oversized, or unsuccessful")
        return payload


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
                recent = validate_submissions(payload, cik, ticker)
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
    execution_id = str(uuid.uuid4())
    args = [sys.executable, str(ROOT / "scripts/recheck_events.py"),
            "--all", "--categories", ",".join(CATS[source]),
            "--data-dir", str(data_dir), "--run-id", execution_id]
    try:
        result = subprocess.run(args, cwd=ROOT, timeout=3600, check=False)
        exitcode = result.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("Recheck exited without completion: " + type(exc).__name__, file=sys.stderr)
        exitcode = 1
    rows = read_rows(data_dir / "recheck_status.csv")
    keys = {x["event_key"] for x in events}
    def fresh(row):
        try:
            stamp = datetime.fromisoformat(row.get("completed_at_utc", "").replace("Z", "+00:00"))
            return (row.get("execution_id") == execution_id and
                    row.get("run_status") in {"COMPLETED", "COMPLETED_WITH_ERRORS"} and
                    stamp <= datetime.now(timezone.utc))
        except (ValueError, TypeError):
            return False
    scope = [r for r in rows if r.get("event_key") in keys and
             r.get("requested_scope") == "ALL" and fresh(r)]
    # Duplicate/stale rows cannot inflate collection completion.
    scope = list({r["event_key"]: r for r in scope}.values())
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
            "collection_missing_event_keys": sorted(keys - {r["event_key"] for r in scope}),
            "collection_execution_id": execution_id,
            "recheck_exit_code": exitcode, "recheck_output": str(outfile)}


def coverage(out, data_dir=DATA):
    """Reconcile source evidence, never just trust a COMPLETE label."""
    reports = {}
    rows = []
    rejected = {}
    expected_scope = scope_hash(strict_rows(data_dir / "pdufa_candidates.csv"),
                                strict_rows(data_dir / "company_registry.csv"))
    for name in ("FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER"):
        path = out / (name.lower() + "_scan_report.json")
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(report, dict) or report.get("verification_version") != VERSION:
                raise ValueError("Missing verification attestation")
            if report.get("verification_run_id") != run_identity():
                raise ValueError("Manifest belongs to a different workflow run/attempt/commit")
            if report.get("verification_scope_sha256") != expected_scope:
                raise ValueError("Manifest does not match current event and company scope")
            ledger = out / (name.lower() + "_verification.csv")
            if report.get("verification_ledger") != ledger.name or digest(ledger.read_bytes()) != report.get("verification_ledger_sha256"):
                raise ValueError("Verification ledger is missing or its content hash disagrees")
            evidence = strict_rows(ledger)
            if not evidence or any(r.get("verification_status") not in STATES or r.get("category") != name for r in evidence):
                raise ValueError("Invalid or empty verification ledger")
            allowed_claims = {
                "FDA": {"PDUFA_TARGET", "FDA_DECISION"},
                "SEC": {"FILINGS_INVENTORY", "FINANCING_CLOSURE"},
                "FINANCIAL": {"CASH_FACT", "LIQUIDITY_FACT", "RUNWAY_ESTIMATE", "CASH_AND_RUNWAY"},
                "MARKET": {"PRICE_VOLUME", "SHORT_INTEREST", "OPTIONS_IV", "BORROW"},
                "ISSUER": {"PRIMARY_RELEASE"},
            }
            if any(r.get("claim") not in allowed_claims[name] for r in evidence):
                raise ValueError("Ledger contains claims outside source scope")
            for finding in evidence:
                supplemental = name == "MARKET" and finding["claim"] != "PRICE_VOLUME"
                if finding.get("verification_required") != ("NO" if supplemental else "YES"):
                    raise ValueError("Ledger changed the required/optional claim policy")
                if finding["verification_status"] == "UNAVAILABLE" and not supplemental:
                    raise ValueError("Required evidence cannot be dismissed as optional unavailable data")
                if finding["verification_status"] == "NOT_APPLICABLE" and (name, finding["claim"]) != ("FINANCIAL", "RUNWAY_ESTIMATE"):
                    raise ValueError("Not-applicable status is outside the cash-burn runway scope")
            started = datetime.fromisoformat(report["started_at"])
            finished = datetime.fromisoformat(report["finished_at"])
            age = (datetime.now(timezone.utc) - finished).total_seconds()
            if age < -60 or age > 30 * 3600 or started > finished:
                raise ValueError("Source manifest is stale or future-dated")
            if any(not started <= datetime.fromisoformat(r["checked_at"]) <= finished for r in evidence):
                raise ValueError("Evidence fetch timestamps are outside this source run")
            keys = [r["event_key"] + ":" + r["claim"] for r in evidence]
            if len(keys) != len(set(keys)):
                raise ValueError("Duplicate verification claims")
            events = {r["event_key"] for r in strict_rows(data_dir / "pdufa_candidates.csv")}
            expected_keys = set(events)
            if name == "SEC":
                expected_keys |= {"REGISTRY:" + r["ticker"] for r in strict_rows(data_dir / "company_registry.csv")}
            if {r["event_key"] for r in evidence} != expected_keys:
                raise ValueError("Verification ledger omits or adds event/company identities")
            for event in expected_keys:
                claims = {r["claim"] for r in evidence if r["event_key"] == event}
                required = ({"FILINGS_INVENTORY"} if event.startswith("REGISTRY:") else
                            {"FINANCING_CLOSURE"} if name == "SEC" else
                            {"PRICE_VOLUME", "SHORT_INTEREST", "OPTIONS_IV", "BORROW"} if name == "MARKET" else
                            {"PRIMARY_RELEASE"} if name == "ISSUER" else None)
                if required is not None and claims != required:
                    raise ValueError("Ledger omits a required claim for " + event)
                if name == "FDA" and len(claims) != 1:
                    raise ValueError("Regulatory claim scope is ambiguous")
                if name == "FINANCIAL" and claims not in ({"CASH_AND_RUNWAY"}, {"CASH_FACT", "RUNWAY_ESTIMATE"}, {"LIQUIDITY_FACT", "RUNWAY_ESTIMATE"}):
                    raise ValueError("Financial ledger omits cash/runway scope")
            if any(r["verification_status"] in {"VERIFIED", "NOT_APPLICABLE"} and (not r.get("source_url") or not re.fullmatch(r"[a-f0-9]{64}", r.get("source_sha256", ""))) for r in evidence):
                raise ValueError("Verified claim lacks primary/provider source content hash")
            totals = verification_summary(evidence)
            if any(report.get(k) != v for k, v in totals.items()):
                raise ValueError("Manifest counts disagree with verification ledger")
            complete = totals["required_findings_unresolved"] == 0
            if report.get("scope_coverage_verified") is not complete:
                raise ValueError("Manifest coverage assertion disagrees with evidence")
            if report.get("status") == "FAILED" or report.get("recheck_exit_code", 0) != 0:
                raise ValueError("Source collector or verifier failed")
            if report.get("collection_missing_event_keys"):
                complete = False
            reports[name] = {"status": ("COMPLETE WITH WARNINGS" if totals["optional_findings_unavailable"] else "COMPLETE") if complete else "PARTIAL"}
            rows.extend(evidence)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            reports[name] = {"status": "NOT_RUN_OR_MISSING"}
            rejected[name] = str(exc)[:180]
    statuses = {name: r.get("status", "UNKNOWN") for name, r in reports.items()}
    missing = [name for name, status in statuses.items() if status not in {"COMPLETE", "COMPLETE WITH WARNINGS"}]
    combined = out / "combined_verification.csv"
    from scripts.source_verification import FIELDS
    write_rows(combined, rows, FIELDS)
    write_rows(out / "verification_review_queue.csv",
               [r for r in rows if r["verification_required"] == "YES" and r["verification_status"] not in {"VERIFIED", "NOT_APPLICABLE"}], FIELDS)
    write_rows(out / "supplemental_data_gaps.csv",
               [r for r in rows if r["verification_required"] == "NO" and r["verification_status"] != "VERIFIED"], FIELDS)
    return {**verification_summary(rows), "verification_version": VERSION,
            "verification_run_id": run_identity(), "verification_scope_sha256": expected_scope,
            "scope_coverage_verified": not missing,
            "manifest_rejections": rejected,
            "combined_verification_ledger": combined.name,
            "combined_verification_ledger_sha256": digest(combined.read_bytes()),
            "source_statuses": statuses,
            "missing_required_source_families": missing,
            "sources_passed": sum(x in {"COMPLETE", "COMPLETE WITH WARNINGS"} for x in statuses.values()),
            "sources_due": len(statuses),
            "verification_issue_examples": [{k: r[k] for k in ("ticker", "category", "claim", "verification_status", "reason")}
                for r in rows if r["verification_required"] == "YES" and r["verification_status"] not in {"VERIFIED", "NOT_APPLICABLE"}][:12],
            "note": "Reconciles fresh source ledgers from this run. Clinical collection, "
                    "second-financing sequence adjudication and dashboard ingestion "
                    "have separate scopes; five-source completion is not a full trading baseline."}


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
            evidence = coverage(args.artifacts_dir, args.data_dir)
        elif args.source == "ISSUER":
            evidence = issuer_discovery(args.data_dir, args.artifacts_dir)
        else:
            evidence = recheck(args.source, args.data_dir, args.artifacts_dir)
            if args.source == "SEC":
                from_env = os.environ.get("SEC_USER_AGENT", "").strip()
                if not re.fullmatch(r".{3,120}\s+[^\s@]+@[^\s@]+\.[^\s@]+", from_env):
                    evidence["sec_registry_reason"] = "No valid identifying SEC_USER_AGENT"
                # The verifier now performs the full, identity-checked inventory.
                # Avoid fetching all 717 submissions twice in the same source job.
        if args.source != "AUDIT":
            evidence.update(verify_source(args.source, args.data_dir, args.artifacts_dir))
    except Exception as exc:
        problem = type(exc).__name__
        print("Source scan failed: " + problem, file=sys.stderr)

    if problem or (args.source in CATS and evidence.get("recheck_exit_code", 1) != 0):
        status = "FAILED"
    else:
        if evidence.get("scope_coverage_verified") and not evidence.get("collection_missing_event_keys"):
            status = "COMPLETE WITH WARNINGS" if evidence.get("optional_findings_unavailable") else "COMPLETE"
        else:
            status = "PARTIAL"
    counts = [k + ": " + str(v) for k, v in evidence.items()
              if isinstance(v, int) and not isinstance(v, bool)]
    report = {
        "scan": args.source, "started_at": first, "finished_at": now(),
        "status": status, "source": args.source,
        "scope": "PDUFA event-specific live sources; SEC also inventories company registry",
        "scan_kind": "VERIFIED_EXTENDED_SOURCE_CHECKS",
        "completion_scope": "This source's ledger claims; not the full clinical/trading baseline",
        "execution_status": "FAILED" if problem or evidence.get("recheck_exit_code", 0) else "COMPLETE",
        "full_coverage_verified": False,
        "errors_count": int(bool(problem)) + evidence.get("verification_technical_failure_count", 0),
        "source_review_count": evidence.get("findings_unresolved", 0) + evidence.get("findings_conflicted", 0),
        "errors": [problem] if problem else [],
        "missing_required_source_families": (
            evidence.get("missing_required_source_families", [args.source] if status == "PARTIAL" else [])),
        "verification_limits": "Verification is limited to each ledger claim. "
            "Cash runway is an estimate. A filing inventory is not a financing closing; "
            "a release is not an FDA decision. This does not certify Phase 3 success, "
            "second-financing sequence, full trading baseline or trade eligibility.",
        "source_summary": "; ".join(counts),
        **evidence,
    }
    write_json(args.report, report)
    print(json.dumps(report, indent=2))
    return 1 if status == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())


