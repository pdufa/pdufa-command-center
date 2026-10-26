#!/usr/bin/env python3
"""Research-only SEC primary-filing candidate index for all 741 original trial IDs.

Read-only SEC company submissions metadata is grouped by the 130 original issuer
CIKs. Recent annual/quarterly/current-report document URLs are *leads for
manual primary-document review*. Neither SEC identity nor the appearance of a
filing proves ownership, in-license, territorial rights, the linked trial drug,
FDA submission, or an actual PDUFA date. The output intentionally never
promotes a trial to qualified Pipeline.
"""
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
SOURCES = ROOT / "new-platform/frontend/public/phase3-census-sources-2026-10-26.json"
SEC_BASE = "https://data.sec.gov/submissions/"
SEC_FORMS = frozenset(("10-K", "10-K/A", "20-F", "20-F/A", "10-Q", "10-Q/A",
                       "8-K", "8-K/A", "6-K", "6-K/A", "S-1", "F-1"))
ANNUAL_FORMS = frozenset(("10-K", "10-K/A", "20-F", "20-F/A"))
MAX_BYTES = 7_000_000
MAX_RECENT_PER_ISSUER = 8
# Identifies the publicly accessible project for SEC fair-access requests;
# a deployed runner can override this with its own verified organization/contact.
DEFAULT_USER_AGENT = "PDUFACommandCenterResearch/1.0 (+https://github.com/pdufa/pdufa-command-center/issues)"


def load_originals():
    with TRIALS.open(encoding="utf-8-sig", newline="") as handle:
        trials = list(csv.DictReader(handle))
    research = json.loads(SOURCES.read_text(encoding="utf-8"))
    if (len(trials) != 741 or len({r["nct_id"] for r in trials}) != 741
        or len({r["ticker"] for r in trials}) != 130
        or research.get("scope") != "RESEARCH_POINTERS_ONLY"
        or research.get("trialCount") != 741
        or research.get("companyCount") != 130):
        raise ValueError("Original trial census or issuer research scope has changed")
    companies = research["companies"]
    if len(companies) != 130 or len({r["ticker"] for r in companies}) != 130:
        raise ValueError("130 unique issuer source pointers required")
    by_ticker = {r["ticker"]: r for r in companies}
    for r in trials:
        issuer = by_ticker.get(r["ticker"])
        if (issuer is None or r["nct_id"] not in issuer["nctIds"]
                or r["company"] not in issuer["leadSponsorNames"]
                or not re.fullmatch(r"\d{10}", issuer["cik"])):
            raise ValueError("Missing exact NCT, lead-sponsor or CIK source identity")
    return trials, companies


def sec_filing_url(cik, accession, filename):
    if (not re.fullmatch(r"\d{10}", cik)
            or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession)
            or not re.fullmatch(r"[A-Za-z0-9_.-]{1,200}", filename)
            or filename in (".", "..")):
        raise ValueError("Invalid or unsafe SEC filing reference")
    return ("https://www.sec.gov/Archives/edgar/data/"
            + str(int(cik)) + "/" + accession.replace("-", "") + "/"
            + urllib.parse.quote(filename))


def extract_filing_candidates(cik, payload):
    """Check CIK identity and align SEC filings.recent array rows by index."""
    if not isinstance(payload, dict) or str(payload.get("cik")) != str(int(cik)):
        raise ValueError("SEC returned mismatched issuer CIK")
    recent = payload.get("filings", {}).get("recent")
    if not isinstance(recent, dict):
        raise ValueError("SEC recent filings data missing")
    keys = ("form", "filingDate", "accessionNumber", "primaryDocument")
    arrays = [recent.get(k) for k in keys]
    if any(not isinstance(v, list) for v in arrays):
        raise ValueError("Malformed SEC recent-filing arrays")
    if len(set(map(len, arrays))) != 1:
        raise ValueError("SEC recent filings columns have differing lengths")
    candidates = []
    invalid_entries = 0
    for form, date, accession, primary in zip(*arrays):
        if form not in SEC_FORMS:
            continue
        if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            invalid_entries += 1
            continue
        try:
            url = sec_filing_url(cik, accession, primary)
        except (TypeError, ValueError):
            invalid_entries += 1
            continue
        candidates.append({"form": form, "filed_at": date,
                           "accession": accession, "primary_document_url": url,
                           "is_annual_report": form in ANNUAL_FORMS,
                           "rights_document_relevance": "NOT_YET_REVIEWED"})
    candidates.sort(key=lambda x: (x["filed_at"], x["accession"]), reverse=True)
    latest_annual = next((x for x in candidates if x["is_annual_report"]), None)
    selected = candidates[:MAX_RECENT_PER_ISSUER]
    if latest_annual is not None and latest_annual not in selected:
        selected = selected[:-1] + [latest_annual]
        selected.sort(key=lambda x: (x["filed_at"], x["accession"]), reverse=True)
    tickers = payload.get("tickers")
    listed = (c for c in tickers) if isinstance(tickers, list) else ()
    return {"sec_reported_tickers": sorted(set(str(t) for t in listed)),
            "relevant_form_entries": len(candidates),
            "invalid_form_entries": invalid_entries,
            "candidate_filings": selected,
            "latest_annual_report": latest_annual}


def fetch_sec_submissions(cik, sleep_fn=time.sleep):
    if not re.fullmatch(r"\d{10}", cik):
        raise ValueError("Invalid issuer CIK")
    url = SEC_BASE + "CIK" + cik + ".json"
    ua = os.environ.get("SEC_EDGAR_USER_AGENT") or DEFAULT_USER_AGENT
    if not ua.strip():
        raise ValueError("SEC User-Agent required")
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": ua, "Accept": "application/json",
            })
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status != 200:
                    raise ValueError("SEC request did not return HTTP 200")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("SEC submissions document exceeded capped bytes")
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 503) or attempt == 2:
                raise
            delay = min(2 * 2 ** attempt, 8)
            sleep_fn(delay)
    raise RuntimeError("Unreachable retry state")


def audit(fetcher=None, sleep_fn=time.sleep):
    if fetcher is None:
        fetcher = fetch_sec_submissions
    trials, companies = load_originals()
    issuers = []
    denied_streak = 0  # Stop repeated requests if SEC rejects runner with HTTP 403.
    blocked_after_403 = False
    actual_requests = 0
    for idx, issuer in enumerate(sorted(companies, key=lambda x: x["ticker"])):
        state = {"ticker": issuer["ticker"], "cik": issuer["cik"],
                 "sec_submissions_url": issuer["secSubmissionsUrl"],
                 "sec_browse_url": issuer["secFilingsUrl"],
                 "official_metadata_retrieved_at_utc": None,
                 "sec_source_status": "UNRESOLVED",
                 "sec_reported_tickers": [],
                 "ticker_present_in_sec_submissions": None,
                 "recent_relevant_filing_count": None,
                 "malformed_candidate_entries": None,
                 "candidate_filings": [], "latest_annual_report": None,
                 "error": None, "current_drug_development_rights_verified": False}
        try:
            if blocked_after_403:
                state["sec_source_status"] = "SEC_ACCESS_BLOCKED_403"
                state["error"] = "Skipped to honor SEC access restriction after three HTTP 403 responses"
                issuers.append(state)
                continue
            actual_requests += 1
            result = extract_filing_candidates(issuer["cik"], fetcher(issuer["cik"]))
            denied_streak = 0
            state["official_metadata_retrieved_at_utc"] = datetime.now(timezone.utc).isoformat()
            state["sec_source_status"] = (
                "SOURCE_DOCUMENT_CANDIDATES" if result["candidate_filings"]
                else "NO_RECENT_RELEVANT_FORMS")
            state["sec_reported_tickers"] = result["sec_reported_tickers"]
            state["ticker_present_in_sec_submissions"] = (
                issuer["ticker"] in result["sec_reported_tickers"])
            state["recent_relevant_filing_count"] = result["relevant_form_entries"]
            state["malformed_candidate_entries"] = result["invalid_form_entries"]
            state["candidate_filings"] = result["candidate_filings"]
            state["latest_annual_report"] = result["latest_annual_report"]
        except urllib.error.HTTPError as exc:
            state["error"] = type(exc).__name__ + ": " + str(exc)[:220]
            if exc.code == 403:
                denied_streak += 1
                if denied_streak >= 3:
                    blocked_after_403 = True
            else:
                denied_streak = 0
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError,
                urllib.error.URLError) as exc:
            state["error"] = type(exc).__name__ + ": " + str(exc)[:220]
            denied_streak = 0
        issuers.append(state)
        if idx < len(companies) - 1:
            sleep_fn(0.32)  # <= ~3.1 SEC requests/second, well below fair-access cap

    by_ticker = {issuer["ticker"]: issuer for issuer in issuers}
    trial_entries = []
    for row in sorted(trials, key=lambda x: x["nct_id"]):
        issuer = by_ticker[row["ticker"]]
        trial_entries.append({
            "nct_id": row["nct_id"], "ticker": row["ticker"],
            "registry_lead_sponsor_name": row["company"],
            "registry_url": row["source_url"], "issuer_cik": issuer["cik"],
            "issuer_sec_source_status": issuer["sec_source_status"],
            "issuer_primary_document_candidates": issuer["candidate_filings"],
            "trial_drug_matched_to_filing": False,
            "trial_indication_matched_to_filing": False,
            "current_rights_primary_source_verified": False,
            "current_rights_effective_date_verified": False,
            "fda_application_verified": False, "pdufa_date_verified": False,
            "qualified_pipeline": None,
            "review_state": "REQUIRES_TRIAL_SPECIFIC_PRIMARY_DOCUMENT_REVIEW",
        })
    fetched = sum(x["official_metadata_retrieved_at_utc"] is not None for x in issuers)
    found = sum(bool(x["candidate_filings"]) for x in issuers)
    covered = sum(bool(x["issuer_primary_document_candidates"]) for x in trial_entries)
    return {
        "scope": "SEC_PRIMARY_FILING_CANDIDATE_DISCOVERY_ONLY",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "historical_trial_count": 741, "historical_issuer_count": 130,
        "sec_metadata_retrieved": fetched,
        "sec_actual_requests_attempted": actual_requests,
        "sec_access_denied_circuit_breaker": blocked_after_403,
        "sec_metadata_unresolved": 130-fetched,
        "issuers_with_candidate_primary_filings": found,
        "trials_with_issuer_filing_candidate_pointers": covered,
        "current_rights_primary_documents_verified": 0,
        "fda_pdufa_verified": 0,
        "qualified_pipeline_count": None,
        "limitations": ("SEC submissions indexes are primary-source filing METADATA only. "
                        "Filing candidates are not evidence that trial-specific rights exist. "
                        "Issuer legal rights, asset/indication match, effective date, territorial "
                        "rights and subsequent transfers require human-reviewed primary documents."),
        "issuers": issuers, "trials": trial_entries,
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: audit_phase3_sec_rights_filing_candidates.py <output.json>")
    report = audit()
    path = Path(sys.argv[1])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("SEC official submissions metadata retrieved:", report["sec_metadata_retrieved"], "/130")
    print("SEC official submissions unresolved:", report["sec_metadata_unresolved"], "/130")
    print("SEC outgoing requests:", report["sec_actual_requests_attempted"], "/130")
    print("SEC access denied circuit breaker triggered:", report["sec_access_denied_circuit_breaker"])
    print("Issuers with candidate primary filing references:", report["issuers_with_candidate_primary_filings"], "/130")
    print("Trials with issuer filing pointers:", report["trials_with_issuer_filing_candidate_pointers"], "/741")
    print("Independently verified current rights: 0/741; FDA/PDUFA: 0/741; Pipeline: UNKNOWN.")
