#!/usr/bin/env python3
"""Read-only SEC filings discovery for the 741-study Phase 3 rights casebook.

SEC issuer filing metadata provides DOCUMENT LEADS, not proof of drug/territory
rights. Never read this as a qualification or FDA outcome. No database writes.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

EXPECTED_TRIALS = 741
EXPECTED_ISSUERS = 130
SEC_BASE = "https://data.sec.gov/submissions/CIK"
MAX_BYTES = 6_000_000
FORMS_CURRENT = {"8-K", "8-K/A", "6-K", "6-K/A"}
FORMS_PERIODIC = {"10-K", "10-K/A", "10-Q", "20-F", "20-F/A", "40-F", "40-F/A"}
ACCESSION = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
DOCUMENT = re.compile(r"^[A-Za-z0-9_.-]{1,120}\.(?:htm|html|txt)$", re.I)
NCT = re.compile(r"^NCT[0-9]{8}$")
CIK = re.compile(r"^[0-9]{10}$")
SHA = re.compile(r"^[a-fA-F0-9]{64}$")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise ValueError("SEC submissions request redirected from exact source")


def fetch_sec_submissions(cik):
    """Return SEC original JSON and byte hash; source failures stay unverified."""
    if not CIK.fullmatch(cik) or cik == "0000000000":
        raise ValueError("Invalid CIK")
    url = f"{SEC_BASE}{cik}.json"
    request = urllib.request.Request(url, headers={
        "User-Agent": "PDUFA-Command-Center-ReadOnly-Research/1.0",
        "Accept": "application/json",
    })
    opener = urllib.request.build_opener(NoRedirect())
    for attempt in range(3):
        try:
            with opener.open(request, timeout=16) as response:
                if (response.status != 200 or response.geturl() != url
                    or "json" not in response.headers.get("content-type", "").lower()):
                    raise ValueError("SEC returned unexpected status, URL or content type")
                body = response.read(MAX_BYTES + 1)
            if not body or len(body) > MAX_BYTES:
                raise ValueError("SEC submissions document exceeds bounds")
            return json.loads(body), hashlib.sha256(body).hexdigest()
        except urllib.error.HTTPError as exc:
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 2:
                raise
        time.sleep(min(2 ** attempt, 4))
    raise AssertionError("Unreachable SEC retrieval state")


def validate_casebook(casebook):
    rows = casebook.get("items")
    if (casebook.get("report_type") != "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY"
        or casebook.get("total_trials") != EXPECTED_TRIALS
        or casebook.get("saved_issuer_pointers") != EXPECTED_ISSUERS
        or casebook.get("rights_unverified_trials") != EXPECTED_TRIALS
        or casebook.get("rights_verified_trials") != 0
        or casebook.get("qualified_pipeline_total") is not None
        or not isinstance(rows, list) or len(rows) != EXPECTED_TRIALS):
        raise ValueError("Only complete research-only 741-trial casebook accepted")
    issuers = {}
    seen_nct = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed casebook study")
        nct, ticker, cik = row.get("nct_id"), row.get("ticker"), row.get("saved_sec_cik")
        if (not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in seen_nct
            or not isinstance(ticker, str) or not ticker
            or not isinstance(cik, str) or not CIK.fullmatch(cik) or cik == "0000000000"
            or row.get("saved_sec_submissions_url") != f"{SEC_BASE}{cik}.json"
            or row.get("original_registry_api_url") != f"https://clinicaltrials.gov/api/v2/studies/{nct}"
            or not isinstance(row.get("original_registry_sha256"), str)
            or not SHA.fullmatch(row["original_registry_sha256"])
            or row.get("rights_verification_status") != "NOT_ESTABLISHED"
            or row.get("independent_rights_source_url") is not None
            or row.get("qualified_pipeline") is not None):
            raise ValueError("Casebook identity or rights boundary violated")
        seen_nct.add(nct)
        if ticker in issuers and issuers[ticker]["cik"] != cik:
            raise ValueError("One ticker mapped to conflicting issuer CIKs")
        issuers.setdefault(ticker, {"ticker": ticker, "cik": cik, "nct_ids": []})["nct_ids"].append(nct)
    if len(issuers) != EXPECTED_ISSUERS or len({x["cik"] for x in issuers.values()}) != EXPECTED_ISSUERS:
        raise ValueError("Expected 130 unique SEC issuer research pointers")
    return issuers


def candidate_filings(payload, cik, as_of):
    """Exact issuer metadata, bounded filing links; no document contents read."""
    if not isinstance(payload, dict):
        raise ValueError("SEC response is not an object")
    try:
        actual = int(payload["cik"])
    except (TypeError, KeyError, ValueError) as exc:
        raise ValueError("Missing issuer CIK in SEC submissions") from exc
    if actual != int(cik):
        raise ValueError("SEC issuer CIK differs from saved research pointer")
    filings = payload.get("filings")
    if not isinstance(filings, dict):
        raise ValueError("SEC filing metadata missing")
    recent = filings.get("recent")
    if not isinstance(recent, dict):
        raise ValueError("SEC recent filing section missing")
    keys = ("form", "filingDate", "accessionNumber", "primaryDocument")
    vectors = [recent.get(key) for key in keys]
    if any(not isinstance(v, list) for v in vectors) or len({len(v) for v in vectors}) != 1:
        raise ValueError("SEC recent filing arrays are incomplete")
    if len(vectors[0]) > 30000:
        raise ValueError("Unbounded SEC filing array")
    candidates = {"CURRENT": [], "PERIODIC": []}
    for form, filed, accession, document in zip(*vectors):
        group = "CURRENT" if form in FORMS_CURRENT else "PERIODIC" if form in FORMS_PERIODIC else None
        if group is None or not isinstance(accession, str) or not ACCESSION.fullmatch(accession):
            continue
        if not isinstance(document, str) or not DOCUMENT.fullmatch(document):
            continue
        try:
            filed_day = date.fromisoformat(filed)
        except (ValueError, TypeError):
            continue
        if not (date(as_of.year - 3, 1, 1) <= filed_day <= as_of):
            continue
        url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
               f"{accession.replace('-', '')}/{document}")
        candidates[group].append({
            "form": form, "filed_date": filed_day.isoformat(),
            "accession_number": accession, "primary_document_url": url,
            "source_type": "SEC_FILING_METADATA_LINK_ONLY",
            "rights_verified": False,
        })
    for group in candidates:
        candidates[group].sort(key=lambda x: (x["filed_date"], x["accession_number"]), reverse=True)
    return candidates["CURRENT"][:4] + candidates["PERIODIC"][:3]


def build_report(casebook, fetcher=fetch_sec_submissions, as_of=None, sleep=time.sleep):
    issuers = validate_casebook(casebook)
    as_of = as_of or datetime.now(timezone.utc).date()
    if not isinstance(as_of, date) or not (2024 <= as_of.year <= 2100):
        raise ValueError("Invalid discovery date")
    rows = []
    for position, issuer in enumerate(sorted(issuers.values(), key=lambda x: x["ticker"])):
        if position:
            sleep(0.25)  # modest SEC request pace, never bulk high-concurrency
        cik, ticker = issuer["cik"], issuer["ticker"]
        result = {
            "ticker": ticker, "cik": cik, "linked_trial_count": len(issuer["nct_ids"]),
            "sec_submissions_url": f"{SEC_BASE}{cik}.json",
            "retrieval_status": "SEC_SOURCE_UNAVAILABLE",
            "source_sha256": None, "candidate_filings": [],
            "source_error_type": None, "rights_verified": False,
        }
        try:
            payload, digest = fetcher(cik)
            if not isinstance(digest, str) or not SHA.fullmatch(digest):
                raise ValueError("Original SEC response lacks valid SHA256")
            filing_leads = candidate_filings(payload, cik, as_of)
            result["source_sha256"] = digest
            result["candidate_filings"] = filing_leads
            result["retrieval_status"] = ("FILING_METADATA_LEADS" if filing_leads
                                          else "NO_RECENT_FILING_METADATA_LEADS")
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
            result["retrieval_status"] = "SEC_SOURCE_INVALID"
            result["source_error_type"] = type(exc).__name__
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            result["source_error_type"] = (f"HTTP_{exc.code}" if isinstance(exc, urllib.error.HTTPError)
                                           else type(exc).__name__)
        rows.append(result)
    by_ticker = {x["ticker"]: x for x in rows}
    trials = [{
        "nct_id": item["nct_id"], "ticker": item["ticker"],
        "saved_sec_cik": item["saved_sec_cik"],
        "issuer_retrieval_status": by_ticker[item["ticker"]]["retrieval_status"],
        "issuer_candidate_filing_count": len(by_ticker[item["ticker"]]["candidate_filings"]),
        "development_rights_verified": False,
        "qualified_pipeline": None,
    } for item in casebook["items"]]
    counts = Counter(x["retrieval_status"] for x in rows)
    return {
        "report_type": "MAIN_PHASE3_SEC_RIGHTS_FILING_LEADS_RESEARCH_ONLY",
        "as_of": as_of.isoformat(),
        "source_checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_issuers": EXPECTED_ISSUERS,
        "issuer_metadata_fetched": sum(x["source_sha256"] is not None for x in rows),
        "issuer_metadata_unavailable_or_invalid": sum(x["source_sha256"] is None for x in rows),
        "issuer_status_counts": dict(counts), "total_trials": EXPECTED_TRIALS,
        "trials_with_issuer_filing_leads": sum(t["issuer_candidate_filing_count"] > 0 for t in trials),
        "trials_without_issuer_filing_leads": sum(t["issuer_candidate_filing_count"] == 0 for t in trials),
        "verified_current_commercial_rights": 0,
        "qualified_pipeline_total": None,
        "issuers": rows, "trials": trials,
        "limitations": "SEC submission filing metadata only. No filing body, license, drug, indication, geography or dates of rights verified. Missing filings or SEC errors do not prove absence of rights. No Pipeline/GEM promotion.",
    }


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: phase3_sec_rights_discovery.py <rights-casebook.json> <report.json>")
    casebook = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = build_report(casebook)
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"SEC filing leads: {result['issuer_metadata_fetched']}/130 issuer submissions fetched; "
          f"{result['trials_with_issuer_filing_leads']}/741 trial pointers have filing leads; "
          f"{result['verified_current_commercial_rights']}/741 rights verified")


if __name__ == "__main__":
    main()
