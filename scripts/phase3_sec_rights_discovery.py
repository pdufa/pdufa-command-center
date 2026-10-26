#!/usr/bin/env python3
"""SEC primary-filing discovery pilot for Phase 3 commercial-rights research.

Official issuer submissions and actual SEC primary documents are fetched where
accessible; issuer identity, filing metadata and body digests are recorded.
Keyword hits are LOCATORS ONLY, never independent rights verification.
Nothing changes Pipeline/GEM gates, source ledgers or trading eligibility.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone, timedelta
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.source_verification import Verifier

EXPECTED_TRIALS = 741
EXPECTED_ISSUERS = 130
FORMS_CURRENT = {"8-K", "8-K/A", "6-K"}
FORMS_PERIODIC = {"10-K", "10-K/A", "10-Q", "20-F", "20-F/A", "40-F"}
FORMS = FORMS_CURRENT | FORMS_PERIODIC
ACCESSION = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
DOCUMENT = re.compile(r"^[A-Za-z0-9_.-]{1,120}\.(?:htm|html|txt)$", re.I)
USER_AGENT = re.compile(r"^.{3,120}\s+[^\s@]+@[^\s@]+\.[^\s@]+$")
RIGHTS_LOCATORS = re.compile(
    rb"(?i)\b(?:licens(?:e|ed|ing|or|ee)|collaboration|commercializ(?:ation|e)|"
    rb"development rights|intellectual property|exclusive rights|territorial rights)\b"
)
DENIAL = re.compile(rb"(?i)request rate threshold exceeded|access denied|automated tool|your request has been denied")


def bounded_bytes(value):
    if not isinstance(value, bytes) or not value.strip() or len(value) > 8_000_000:
        raise ValueError("Empty or oversized original SEC response")
    if DENIAL.search(value[:6000]):
        raise ValueError("SEC access-denial document is not a primary filing")
    return value


def case_issuers(casebook):
    rows = casebook.get("items")
    if (casebook.get("report_type") != "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY"
        or casebook.get("total_trials") != EXPECTED_TRIALS
        or casebook.get("saved_issuer_pointers") != EXPECTED_ISSUERS
        or casebook.get("rights_verified_trials") != 0
        or casebook.get("rights_unverified_trials") != EXPECTED_TRIALS
        or casebook.get("qualified_pipeline_total") is not None
        or not isinstance(rows, list) or len(rows) != EXPECTED_TRIALS):
        raise ValueError("Incomplete or non-research-only Phase 3 rights casebook")
    by_ticker = {}
    seen_nct = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed casebook study")
        nct, ticker, cik = row.get("nct_id"), row.get("ticker"), row.get("saved_sec_cik")
        if (not isinstance(nct, str) or not re.fullmatch(r"NCT[0-9]{8}", nct)
            or nct in seen_nct or not isinstance(ticker, str) or not ticker
            or not isinstance(cik, str) or not re.fullmatch(r"[0-9]{10}", cik)
            or cik == "0000000000"
            or row.get("saved_sec_submissions_url") != f"https://data.sec.gov/submissions/CIK{cik}.json"
            or row.get("rights_verification_status") != "NOT_ESTABLISHED"
            or row.get("independent_rights_source_url") is not None
            or row.get("qualified_pipeline") is not None):
            raise ValueError("Invalid rights identity or claim in casebook")
        seen_nct.add(nct)
        entry = by_ticker.setdefault(ticker, {"ticker": ticker, "cik": cik, "nct_ids": []})
        if entry["cik"] != cik:
            raise ValueError("Conflicting issuer CIK for same ticker")
        entry["nct_ids"].append(nct)
    if len(by_ticker) != EXPECTED_ISSUERS or len({e["cik"] for e in by_ticker.values()}) != EXPECTED_ISSUERS:
        raise ValueError("Expected 130 uniquely identified saved SEC issuers")
    return sorted(by_ticker.values(), key=lambda row: row["ticker"])


def recent_primary_filings(raw, cik, ticker, as_of):
    source = json.loads(bounded_bytes(raw))
    if not isinstance(source, dict):
        raise ValueError("Invalid official SEC submissions schema")
    official_cik = source.get("cik")
    if (isinstance(official_cik, bool) or not isinstance(official_cik, (int, str))
        or not str(official_cik).isdigit() or int(official_cik) != int(cik)):
        raise ValueError("Official SEC submissions CIK mismatch")
    tickers = source.get("tickers")
    if not isinstance(tickers, list) or ticker.upper() not in {
        t.upper() for t in tickers if isinstance(t, str)
    }:
        raise ValueError("Saved ticker not present in official SEC issuer record")
    recent = source.get("filings", {}).get("recent", {})
    if not isinstance(recent, dict):
        raise ValueError("Malformed SEC recent filings metadata")
    keys = ("form", "filingDate", "accessionNumber", "primaryDocument")
    arrays = [recent.get(key) for key in keys]
    if (not all(isinstance(x, list) for x in arrays)
        or not 0 < len(arrays[0]) <= 10000
        or len({len(x) for x in arrays}) != 1):
        raise ValueError("Misaligned or empty SEC filings arrays")
    cutoff = as_of - timedelta(days=730)
    selected = {"CURRENT": [], "PERIODIC": []}
    for form, filed, accession, primary in zip(*arrays):
        if (form not in FORMS or not isinstance(filed, str)
            or not isinstance(accession, str) or not ACCESSION.fullmatch(accession)
            or not isinstance(primary, str) or not DOCUMENT.fullmatch(primary)):
            continue
        try:
            filed_day = date.fromisoformat(filed)
        except ValueError:
            continue
        if not cutoff <= filed_day <= as_of:
            continue
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
               f"{accession.replace('-', '')}/{primary}")
        group = "CURRENT" if form in FORMS_CURRENT else "PERIODIC"
        selected[group].append({
            "form": form, "filed_at": filed, "accession_number": accession,
            "primary_document_url": url,
        })
    for key in selected:
        selected[key].sort(key=lambda f: (f["filed_at"], f["accession_number"]), reverse=True)
    # Balance current and annual/quarterly disclosures; never mistake an index
    # entry for a fetched original legal document.
    return selected["CURRENT"][:1] + selected["PERIODIC"][:1]


def discover(casebook, fetch=None, max_issuers=10, as_of=None, agent=None):
    if type(max_issuers) is not int or not 1 <= max_issuers <= EXPECTED_ISSUERS:
        raise ValueError("Pilot issuer count must be between 1 and 130")
    issuers = case_issuers(casebook)
    as_of = as_of or datetime.now(timezone.utc).date()
    if not isinstance(as_of, date):
        raise ValueError("Invalid research as-of date")
    when = datetime.now(timezone.utc).isoformat()
    # Use the existing hardened SEC fetcher, including HTTPS host protections,
    # timeouts, bounded responses, SEC 403 circuit breaker and respectful pacing.
    if fetch is None:
        fetch = Verifier([]).fetch
        agent = os.environ.get("SEC_USER_AGENT", "") if agent is None else agent
        # No fabricated researcher contact. No network request without an
        # identifying agent; the workflow still inventories the blocked scope.
        configured = isinstance(agent, str) and bool(USER_AGENT.fullmatch(agent))
    else:
        configured = True  # dependency-injected test or approved caller fetcher
    output = []
    for index, issuer in enumerate(issuers):
        ticker, cik = issuer["ticker"], issuer["cik"]
        entry = {
            "ticker": ticker, "cik": cik, "study_count": len(issuer["nct_ids"]),
            "nct_ids": sorted(issuer["nct_ids"]),
            "official_submissions_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
            "submissions_status": "NOT_SCANNED",
            "official_submissions_sha256": None,
            "recent_filing_candidates": [],
            "document_fetches": [],
            "rights_verified": False,
        }
        if index >= max_issuers:
            output.append(entry)
            continue
        if not configured:
            entry["submissions_status"] = "IDENTIFYING_AGENT_REQUIRED"
            output.append(entry)
            continue
        try:
            body = bounded_bytes(fetch(entry["official_submissions_url"]))
            filings = recent_primary_filings(body, cik, ticker, as_of)
            entry["official_submissions_sha256"] = hashlib.sha256(body).hexdigest()
            entry["submissions_status"] = "INDEX_VALIDATED"
            entry["recent_filing_candidates"] = filings
        except (ValueError, TypeError, KeyError, UnicodeError) as exc:
            entry["submissions_status"] = "INVALID_OR_MISMATCHED_OFFICIAL_SOURCE"
            entry["source_error_type"] = type(exc).__name__
            output.append(entry)
            continue
        except Exception as exc:
            entry["submissions_status"] = "SOURCE_UNAVAILABLE"
            entry["source_error_type"] = type(exc).__name__
            output.append(entry)
            continue
        for filing in filings:
            doc = {
                "form": filing["form"], "filed_at": filing["filed_at"],
                "url": filing["primary_document_url"],
                "retrieval_status": "SOURCE_UNAVAILABLE",
                "sha256": None, "rights_language_locator_present": None,
                "commercial_rights_verified": False,
            }
            try:
                body = bounded_bytes(fetch(doc["url"]))
                doc["sha256"] = hashlib.sha256(body).hexdigest()
                # A lexical hint is neither a program match nor a legal conclusion.
                doc["rights_language_locator_present"] = bool(RIGHTS_LOCATORS.search(
                    html.unescape(body.decode("utf-8", "replace")).encode("utf-8")))
                doc["retrieval_status"] = "FETCHED_RESEARCH_ONLY"
            except Exception as exc:
                doc["source_error_type"] = type(exc).__name__
            entry["document_fetches"].append(doc)
        output.append(entry)
    counts = Counter(row["submissions_status"] for row in output)
    documents = [doc for row in output for doc in row["document_fetches"]]
    return {
        "report_type": "MAIN_PHASE3_SEC_RIGHTS_DISCOVERY_PILOT_RESEARCH_ONLY",
        "checked_at_utc": when, "as_of_date": as_of.isoformat(),
        "total_issuers": EXPECTED_ISSUERS, "total_trials": EXPECTED_TRIALS,
        "pilot_issuers_requested": max_issuers, "issuer_status_counts": dict(counts),
        "official_indices_validated": counts["INDEX_VALIDATED"],
        "documents_fetched": sum(d["retrieval_status"] == "FETCHED_RESEARCH_ONLY" for d in documents),
        "document_rights_language_leads": sum(d["rights_language_locator_present"] is True for d in documents),
        "documents_unavailable": sum(d["retrieval_status"] != "FETCHED_RESEARCH_ONLY" for d in documents),
        "independently_verified_current_rights": 0,
        "independently_verified_rights_denominator": EXPECTED_TRIALS,
        "qualified_pipeline_total": None, "issuer_rows": output,
        "limitations": (
            "A retrieved SEC filing, keyword occurrence or matched SEC ticker/CIK is "
            "not proof of current trial-specific U.S. development rights. "
            "No legal-document verification, gate PASS, Pipeline/GEM promotion or trading permission."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("casebook", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-issuers", type=int, default=10)
    args = parser.parse_args()
    result = discover(json.loads(args.casebook.read_text(encoding="utf-8")),
                      max_issuers=args.max_issuers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"SEC rights pilot: {result['official_indices_validated']}/{args.max_issuers} "
          f"official issuer indices; {result['documents_fetched']} primary documents fetched; "
          f"{result['document_rights_language_leads']} research-only rights-language leads; "
          f"current rights independently verified 0/741")
    if result["issuer_status_counts"].get("IDENTIFYING_AGENT_REQUIRED"):
        print("SEC_USER_AGENT (identifying organization/contact email) not configured: "
              "pilot requests were not made; no missing evidence inferred.")


if __name__ == "__main__":
    main()
