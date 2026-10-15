#!/usr/bin/env python3
"""Discovery-only SEC filing sweep for unresolved company financing claims.

This is NOT a closing-verification override. Google queries, SEC filing indexes,
registration statements, and issuer press releases are ways to LOCATE evidence.
Only a fresh company-CIK-matched SEC document with a dated funded closing that
passes the existing Verifier.financing() may be tagged VERIFIED_TRANSACTION_ONLY.
Even that result never proves a distinct second post-Phase-3 financing or grants
GEM trading permission. A missing filing NEVER means no financing occurred.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote

from scripts.source_verification import Verifier, dates, read_rows, sec_url_matches
from scripts.provisional_financing_sec_recheck import safe_document

FORMS = {"8-K", "8-K/A", "6-K", "10-Q", "10-K", "20-F", "PRE 14A", "DEF 14A"}
MIN_FILED = date(2025, 1, 1)
MAX_FILINGS_PER_ISSUER = 16
MAX_EXHIBITS_PER_8K = 2
MAX_CLOSING_CANDIDATES_PER_DOCUMENT = 5
FIELDS = ("event_key", "ticker", "issuer_cik", "discovery_status",
          "sec_form", "filed_at", "candidate_close_date", "sec_url",
          "sec_sha256", "evidence_excerpt", "reason",
          "google_sec_query_url", "checked_at_utc",
          "second_post_phase3_verified", "trade_entry_authorized")
FINANCE = re.compile(
    r"(?i)\b(?:underwritten|registered\s+direct|private\s+placement|"
    r"public\s+offering|offering|financing|convertible\s+(?:senior\s+)?notes|"
    r"securities\s+purchase|initial\s+public\s+offering|IPO)\b"
)
COMPLETED = re.compile(
    r"(?i)\b(?:closed|completed|consummated|purchased|issued|received|sold)\b"
)
EXPECTED = re.compile(
    r"(?i)\b(?:expects?\s+to|expected\s+to|anticipated\s+to|"
    r"will\s+close|subject\s+to\s+(?:customary|closing)|"
    r"plans?\s+to|may\s+close)\b"
)
MONTH_DAY = re.compile(
    r"(?i)\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2},?\s+20\d{2}\b|"
    r"\b20\d{2}-\d{2}-\d{2}\b"
)
CLOSE_CONTEXT = re.compile(
    r"(?i)\b(?:closed|completed|consummated)\b.{0,115}"
    r"\b(?:offering|financing|placement|shares|notes|IPO)\b|"
    r"\b(?:offering|financing|placement|IPO)\b.{0,95}"
    r"\b(?:closed|completed|consummated)\b"
)


def google_link(company, cik):
    # Navigation/discovery only; never make an automated Google request.
    query = f'site:sec.gov/Archives/edgar/data/{int(cik)}/ "{company}" offering closed 8-K 10-Q'
    return "https://www.google.com/search?q=" + quote(query, safe="")


def row(event, cik, status, reason, **extra):
    output = {key: "" for key in FIELDS}
    output.update({
        "event_key": event["event_key"], "ticker": event["ticker"],
        "issuer_cik": cik, "discovery_status": status,
        "reason": str(reason)[:450],
        "google_sec_query_url": google_link(
            event.get("company", event["ticker"]), cik
        ) if cik.isdigit() and int(cik) else "",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "second_post_phase3_verified": "NO",
        "trade_entry_authorized": "NO",
    })
    output.update(extra)
    return output


def recent_documents(verifier, event):
    """Bounded SEC submissions for one verified issuer, not arbitrary search hits."""
    _, _, recent = verifier.submissions(event)
    grouped = {"CURRENT": [], "PERIODIC": [], "PROXY": []}
    for form, filed, acc, primary in zip(
        recent["form"], recent["filingDate"],
        recent["accessionNumber"], recent["primaryDocument"]
    ):
        if form not in FORMS or not safe_document(primary):
            continue
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(acc)):
            continue
        try:
            day = date.fromisoformat(filed)
        except (TypeError, ValueError):
            continue
        if not MIN_FILED <= day <= verifier.as_of:
            continue
        group = ("CURRENT" if form in {"8-K", "8-K/A", "6-K"}
                 else "PERIODIC" if form in {"10-Q", "10-K", "20-F"}
                 else "PROXY")
        grouped[group].append((day, form, acc, primary))
    for group in grouped.values():
        group.sort(reverse=True)
    # Each SEC family matters. An issuer with dozens of current reports must
    # not crowd out its 10-Q/10-K subsequent-events financing disclosure.
    selected = (grouped["CURRENT"][:9] + grouped["PERIODIC"][:5]
                + grouped["PROXY"][:2])
    selected.sort(reverse=True)
    return selected[:MAX_FILINGS_PER_ISSUER]


def indexed_documents(verifier, cik, form, acc, primary):
    base = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            + acc.replace("-", "") + "/")
    names = [primary]
    # SEC exhibits can provide post-closing statements omitted from the 8-K.
    # Never invent an exhibit name or accept a Google redirect as an SEC index.
    if form in {"8-K", "8-K/A", "6-K"}:
        try:
            index = json.loads(verifier.body(base + "index.json"))
            items = index.get("directory", {}).get("item", [])
            exhibit_names = [
                item["name"] for item in items if isinstance(item, dict)
                and safe_document(item.get("name"))
                and re.search(r"(?i)(?:ex|exhibit)[._-]?(?:99|10|4)[._-]?",
                              item["name"])
            ]
            names += exhibit_names[:MAX_EXHIBITS_PER_8K]
        except Exception:
            # Preserve ability to fetch primary filing if index is unavailable.
            pass
    return list(dict.fromkeys(base + name for name in names))


def candidate_clauses(plain, as_of):
    """Surface plausible nearby closing dates; NEVER assert a transaction."""
    clauses = []
    seen = set()
    for close in CLOSE_CONTEXT.finditer(plain):
        left = max(0, close.start() - 210)
        right = min(len(plain), close.end() + 260)
        segment = plain[left:right]
        if not (FINANCE.search(segment) and COMPLETED.search(segment)):
            continue
        # A prospective statement can appear in a closing paragraph; only
        # the strict verifier decides whether it is real completion evidence.
        dates_near = set()
        for m in MONTH_DAY.finditer(segment):
            for d in dates(m.group()):
                try:
                    if date.fromisoformat(d) <= as_of:
                        dates_near.add(d)
                except ValueError:
                    pass
        if len(dates_near) != 1:
            continue
        day = next(iter(dates_near))
        key = (day, re.sub(r"\s+", " ", segment[:100]).strip())
        if key in seen:
            continue
        seen.add(key)
        clauses.append((day, re.sub(r"\s+", " ", segment).strip()[:700]))
        if len(clauses) >= MAX_CLOSING_CANDIDATES_PER_DOCUMENT:
            break
    return clauses


def discover(verifier, queue, events, max_issuers=None, sleep=time.sleep):
    """Fresh, bounded evidence discovery; repeat event identities without mixing."""
    event_map = {x["event_key"]: x for x in events}
    by_ticker = {}
    for old in queue:
        if old.get("category") != "SEC" or old.get("claim") != "FINANCING_CLOSURE":
            continue
        event = event_map.get(old["event_key"])
        if not event or event.get("ticker") != old.get("ticker"):
            raise ValueError("Unresolved SEC event identity is missing or mismatched")
        by_ticker.setdefault(event["ticker"], []).append(event)
    results = []
    for i, ticker in enumerate(sorted(by_ticker)):
        if max_issuers is not None and i >= max_issuers:
            break
        issuer_events = by_ticker[ticker]
        event = issuer_events[0]
        cik = verifier.cik(event)
        if not cik:
            results.extend(row(e, "", "MISSING_ISSUER_CIK",
                               "Current registry lacks matching CIK") for e in issuer_events)
            continue
        try:
            filings = recent_documents(verifier, event)
        except Exception as exc:
            results.extend(row(e, cik, "SEC_SOURCE_UNAVAILABLE",
                               "Issuer-matched SEC filings could not be fetched: " +
                               type(exc).__name__) for e in issuer_events)
            continue
        leads, failures = [], 0
        for filed, form, acc, primary in filings:
            urls = indexed_documents(verifier, cik, form, acc, primary)
            for url in urls:
                if not sec_url_matches(url, cik):
                    continue
                try:
                    sleep(0.16)  # SEC fair access, roughly <= 6 req/sec.
                    _, plain = verifier.document(url)
                except Exception:
                    failures += 1
                    continue
                for day, snippet in candidate_clauses(plain, verifier.as_of):
                    # Reuse original strict SEC verifier: date, actual funded
                    # deal, document hash and issuer identity all required.
                    probe = {**event, "financing_evidence_url": url,
                             "financing_close_date": day,
                             "_financing_review": {},
                             "_recheck_exact_sec_url": True}
                    decision = verifier.financing(probe)
                    verified = (
                        decision.get("verification_status") == "VERIFIED"
                        and bool(re.fullmatch(r"[a-f0-9]{64}",
                                              decision.get("source_sha256", "")))
                        and decision.get("source_url") == url
                    )
                    leads.append({
                        "discovery_status": ("VERIFIED_TRANSACTION_ONLY" if verified
                                             else "POTENTIAL_CLOSING_REVIEW"),
                        "sec_form": form, "filed_at": filed.isoformat(),
                        "candidate_close_date": day, "sec_url": url,
                        "sec_sha256": decision.get("source_sha256", ""),
                        "evidence_excerpt": (decision.get("evidence") or snippet)[:700],
                        "reason": (decision.get("reason") or
                                   "Date and financing keywords discovered; strict verifier did not pass"),
                    })
        # Replicate company financing research under each exact trial identity.
        # It does not imply the financing occurred after THAT program's Phase 3.
        if leads:
            leads.sort(key=lambda x: (x["discovery_status"] != "VERIFIED_TRANSACTION_ONLY",
                                      x["candidate_close_date"], x["sec_url"]),
                       reverse=False)
            for e in issuer_events:
                results.extend(row(e, cik, x["discovery_status"],
                                   x.pop("reason"), **x) for x in [dict(y) for y in leads[:14]])
        else:
            outcome = ("SEC_SOURCE_PARTIAL" if failures
                       else "NO_MATCHING_DOCUMENT_IN_BOUNDED_SEARCH")
            results.extend(row(e, cik, outcome,
                               f"No dated funded close independently matched; "
                               f"{len(filings)} filings considered, {failures} document failures. "
                               "This is NOT proof that no financing happened.")
                           for e in issuer_events)
    return results


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--output", type=Path,
                   default=Path("reports/missing_sources/sec_unresolved_discovery.csv"))
    p.add_argument("--max-issuers", type=int, default=None,
                   help="Optional bounded test/smoke scope. Omit for all unresolved issuers.")
    args = p.parse_args(argv)
    if args.max_issuers is not None and not 1 <= args.max_issuers <= 100:
        p.error("max-issuers must be between 1 and 100")
    folder = args.data_dir
    report = json.loads((folder / "pdufa_source_report.json").read_text())
    queue = read_rows(folder / "pdufa_source_review_queue.csv")
    if (report.get("required_findings_unresolved") != len(queue) or
            report.get("execution_status") != "COMPLETE"):
        raise SystemExit("Refuse stale or incomplete SEC review queue")
    events = read_rows(folder / "pdufa_candidates.csv")
    companies = read_rows(folder / "company_registry.csv")
    verifier = Verifier(companies)
    rows = discover(verifier, queue, events, max_issuers=args.max_issuers)
    if not rows:
        raise SystemExit("No unresolved SEC candidates; no empty report published")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(x["discovery_status"] for x in rows)
    summary = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
               "source_report_run_id": report.get("latest_run_id", ""),
               "unresolved_sec_events_in_queue": sum(
                   q["category"] == "SEC" for q in queue),
               "output_research_rows": len(rows),
               "distinct_issuers": len({r["ticker"] for r in rows}),
               "status_counts": dict(counts),
               "second_post_phase3_verified": 0,
               "trade_entry_authorized": 0,
               "canonical_ledger_modified": False,
               "output": str(args.output)}
    print(json.dumps(summary, sort_keys=True))
    return rows


if __name__ == "__main__":
    main()
