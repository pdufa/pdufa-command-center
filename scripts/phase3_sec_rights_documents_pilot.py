#!/usr/bin/env python3
"""Research-only retrieval of exact SEC documents from a verified filing-leads report.

SEC index metadata points to documents; retrieved text and rights keywords do
NOT verify a particular trial's drug, indication, geography or legal rights.
A blocked source is UNAVAILABLE, never negative evidence about rights.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.phase3_sec_rights_discovery import validate_casebook, FORMS_CURRENT, FORMS_PERIODIC, ACCESSION, DOCUMENT, SHA
from scripts.source_verification import Verifier

EXPECTED_ISSUERS = 130
EXPECTED_TRIALS = 741
ALLOWED_INDEX_STATES = {
    "FILING_METADATA_LEADS", "NO_RECENT_FILING_METADATA_LEADS",
    "SEC_SOURCE_UNAVAILABLE", "SEC_SOURCE_INVALID",
}
USER_AGENT = re.compile(r"^.{3,120}\s+[^\s@]+@[^\s@]+\.[^\s@]+$")
CANDIDATE_TERMS = re.compile(
    r"(?i)\b(?:licens(?:e|ed|ing|or|ee)|collaboration|commercializ(?:ation|e)|"
    r"development rights|intellectual property|exclusive rights|territorial rights)\b"
)
DENIAL = re.compile(r"(?i)request rate threshold exceeded|access denied|your request has been denied")
# Document-text locators are lexical review leads, never ownership or rights findings.
REVIEW_TOPICS = (
    ("LICENSE_OR_EXCLUSIVITY", re.compile(
        r"(?i)\b(?:licens(?:e|es|ed|ing|or|ee)|in-licens(?:e|ing)|exclusive rights)\b")),
    ("COLLABORATION", re.compile(r"(?i)\b(?:collaboration|co-development|co-commercialization)\b")),
    ("US_TERRITORY", re.compile(r"(?i)\b(?:United States|U\.S\.|North America|worldwide rights)\b")),
    ("RIGHTS_TRANSFER_OR_TERMINATION", re.compile(
        r"(?i)\b(?:termination of (?:the )?agreement|terminated (?:the )?license|"
        r"assigned (?:the )?rights|transferred (?:the )?rights)\b")),
)
MAX_REVIEW_LOCATORS = 6
MAX_REVIEW_EXCERPT_CHARS = 150


def rights_review_locators(plain):
    """Bounded, source-offset lexical hints. A match is NEVER a legal conclusion."""
    if not isinstance(plain, str) or len(plain) > 8_000_000:
        raise ValueError("Invalid normalized SEC text for review")
    hits = []
    for topic, pattern in REVIEW_TOPICS:
        matches = 0
        for match in pattern.finditer(plain):
            begin = max(0, match.start() - 65)
            end = min(len(plain), match.end() + 65)
            hits.append({
                "topic": topic, "matched_term": match.group()[:65],
                "normalized_text_offset": match.start(),
                "context_excerpt": plain[begin:end][:MAX_REVIEW_EXCERPT_CHARS],
                "status": "LEXICAL_REVIEW_LEAD_NOT_LEGAL_RIGHTS_PROOF",
            })
            matches += 1
            if matches == 2:
                break
    hits.sort(key=lambda item: (item["normalized_text_offset"], item["topic"]))
    return hits[:MAX_REVIEW_LOCATORS]


def validate_leads(casebook, leads):
    """Require exact 741-to-130 alignment before attempting any SEC document."""
    issuers = validate_casebook(casebook)
    issuer_rows, trial_rows = leads.get("issuers"), leads.get("trials")
    if (leads.get("report_type") != "MAIN_PHASE3_SEC_RIGHTS_FILING_LEADS_RESEARCH_ONLY"
        or leads.get("total_issuers") != EXPECTED_ISSUERS
        or leads.get("total_trials") != EXPECTED_TRIALS
        or leads.get("verified_current_commercial_rights") != 0
        or leads.get("qualified_pipeline_total") is not None
        or not isinstance(issuer_rows, list) or len(issuer_rows) != EXPECTED_ISSUERS
        or not isinstance(trial_rows, list) or len(trial_rows) != EXPECTED_TRIALS):
        raise ValueError("Only complete research-only official SEC filing leads accepted")
    checked_as_of = leads.get("as_of")
    try:
        as_of = date.fromisoformat(checked_as_of)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid SEC source evidence date") from exc
    if as_of > datetime.now(timezone.utc).date():
        raise ValueError("Future-dated SEC lead report")
    index = {}
    for row in issuer_rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed SEC issuer filing leads")
        ticker, cik, state = row.get("ticker"), row.get("cik"), row.get("retrieval_status")
        if (ticker not in issuers or ticker in index or not isinstance(cik, str)
            or cik != issuers[ticker]["cik"]
            or row.get("sec_submissions_url") != f"https://data.sec.gov/submissions/CIK{cik}.json"
            or row.get("linked_trial_count") != len(issuers[ticker]["nct_ids"])
            or state not in ALLOWED_INDEX_STATES or row.get("rights_verified") is not False):
            raise ValueError("SEC filing lead issuer/CIK or rights mismatch")
        candidates, digest = row.get("candidate_filings"), row.get("source_sha256")
        if not isinstance(candidates, list) or len(candidates) > 7:
            raise ValueError("SEC filing candidates missing or unbounded")
        if state in {"FILING_METADATA_LEADS", "NO_RECENT_FILING_METADATA_LEADS"}:
            if not isinstance(digest, str) or not SHA.fullmatch(digest):
                raise ValueError("Official SEC index lacks original response SHA")
            if (state == "FILING_METADATA_LEADS") != bool(candidates):
                raise ValueError("Official filing metadata status/count mismatch")
        elif candidates or digest is not None:
            raise ValueError("Failed SEC source cannot contribute document leads")
        seen_accessions = set()
        for filing in candidates:
            if not isinstance(filing, dict):
                raise ValueError("Malformed candidate SEC filing")
            acc, form, doc_url = filing.get("accession_number"), filing.get("form"), filing.get("primary_document_url")
            if (filing.get("source_type") != "SEC_FILING_METADATA_LINK_ONLY"
                or filing.get("rights_verified") is not False
                or form not in FORMS_CURRENT | FORMS_PERIODIC
                or not isinstance(acc, str) or not ACCESSION.fullmatch(acc)
                or acc in seen_accessions
                or not isinstance(doc_url, str)):
                raise ValueError("Invalid SEC filing accession, form or research-only scope")
            seen_accessions.add(acc)
            prefix = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/"
            if not doc_url.startswith(prefix) or not DOCUMENT.fullmatch(doc_url[len(prefix):]):
                raise ValueError("Document URL does not belong to exact issuer SEC accession")
            try:
                filed = date.fromisoformat(filing["filed_date"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("Invalid official filing date") from exc
            if filed > as_of:
                raise ValueError("Future filing cannot be selected for review")
        index[ticker] = row
    if set(index) != set(issuers):
        raise ValueError("Issuer research scope is not complete")
    studies = {}
    for row in trial_rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed SEC lead trial association")
        nct = row.get("nct_id")
        if nct in studies or not isinstance(nct, str):
            raise ValueError("Duplicate or malformed SEC lead NCT")
        studies[nct] = row
    original = {r["nct_id"]: r for r in casebook["items"]}
    if set(studies) != set(original):
        raise ValueError("SEC lead report lost Phase 3 trial identity")
    for nct, study in studies.items():
        source = original[nct]
        ref = index[source["ticker"]]
        if (study.get("ticker") != source["ticker"]
            or study.get("saved_sec_cik") != source["saved_sec_cik"]
            or study.get("issuer_retrieval_status") != ref["retrieval_status"]
            or study.get("issuer_candidate_filing_count") != len(ref["candidate_filings"])
            or study.get("development_rights_verified") is not False
            or study.get("qualified_pipeline") is not None):
            raise ValueError("SEC filing metadata cannot be attributed to another trial")
    return issuers, index


def choose_documents(filings):
    """At most one current and one periodic report per issuer."""
    current = next((f for f in filings if f["form"] in FORMS_CURRENT), None)
    periodic = next((f for f in filings if f["form"] in FORMS_PERIODIC), None)
    return [f for f in (current, periodic) if f is not None]


def read_text(raw):
    if not isinstance(raw, bytes) or not raw.strip() or len(raw) > 8_000_000:
        raise ValueError("Missing or oversized SEC original document")
    plain = html.unescape(raw.decode("utf-8", "replace"))
    if DENIAL.search(plain[:6000]):
        raise ValueError("SEC denial/error page is not original filing evidence")
    # We only retain lexical counts as leads; never infer live rights from text.
    plain = re.sub(r"(?is)<script\b.*?</script>|<style\b.*?</style>", " ", plain)
    plain = re.sub(r"(?s)<[^>]*>", " ", plain)
    return re.sub(r"\s+", " ", plain)


def build_report(casebook, leads, fetch=None, max_issuers=10, agent=None):
    if type(max_issuers) is not int or not 1 <= max_issuers <= EXPECTED_ISSUERS:
        raise ValueError("Pilot max issuers must be 1..130")
    issuers, indexed = validate_leads(casebook, leads)
    if fetch is None:
        fetch = Verifier([]).fetch
        agent = os.environ.get("SEC_USER_AGENT", "") if agent is None else agent
        configured = isinstance(agent, str) and bool(USER_AGENT.fullmatch(agent))
    else:
        configured = True  # A controlled test or externally validated fetcher.
    ready = sorted(
        [ticker for ticker, x in indexed.items() if x["retrieval_status"] == "FILING_METADATA_LEADS"],
        key=lambda ticker: ticker
    )
    selected = set(ready[:max_issuers])
    rows = []
    for issuer in sorted(issuers.values(), key=lambda x: x["ticker"]):
        ticker, cik = issuer["ticker"], issuer["cik"]
        row = indexed[ticker]
        record = {
            "ticker": ticker, "cik": cik, "linked_trial_count": len(issuer["nct_ids"]),
            "metadata_status": row["retrieval_status"],
            "original_sec_index_sha256": row["source_sha256"],
            "review_status": ("NOT_SCANNED_METADATA_UNAVAILABLE"
                              if row["retrieval_status"] != "FILING_METADATA_LEADS"
                              else "NOT_SELECTED_THIS_PILOT"),
            "documents": [], "independently_verified_rights": False,
        }
        if ticker in selected:
            record["review_status"] = "SCANNED"
            for filing in choose_documents(row["candidate_filings"]):
                item = {
                    "sec_form": filing["form"], "filed_date": filing["filed_date"],
                    "sec_primary_document_url": filing["primary_document_url"],
                    "retrieval_status": "SOURCE_UNAVAILABLE",
                    "source_sha256": None, "rights_language_locator_count": None,
                    "rights_language_review_locators": [],
                    "verified_trial_development_rights": False,
                }
                if not configured:
                    item["retrieval_status"] = "IDENTIFYING_AGENT_REQUIRED"
                else:
                    try:
                        raw = fetch(item["sec_primary_document_url"])
                        text = read_text(raw)
                        item["source_sha256"] = hashlib.sha256(raw).hexdigest()
                        item["rights_language_locator_count"] = min(len(CANDIDATE_TERMS.findall(text)), 10000)
                        item["rights_language_review_locators"] = rights_review_locators(text)
                        item["retrieval_status"] = "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY"
                    except Exception as exc:
                        item["source_error_type"] = type(exc).__name__
                record["documents"].append(item)
            states = {d["retrieval_status"] for d in record["documents"]}
            if states == {"IDENTIFYING_AGENT_REQUIRED"}:
                record["review_status"] = "NOT_REQUESTED_IDENTIFYING_AGENT_REQUIRED"
            elif "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY" in states:
                record["review_status"] = "SOURCE_TEXT_AVAILABLE_REVIEW_REQUIRED"
            else:
                record["review_status"] = "DOCUMENT_REQUESTS_FAILED_OR_BLOCKED"
        rows.append(record)
    all_documents = [doc for r in rows for doc in r["documents"]]
    outcomes = Counter(doc["retrieval_status"] for doc in all_documents)
    return {
        "report_type": "MAIN_PHASE3_SEC_PRIMARY_RIGHTS_DOCUMENT_PILOT_RESEARCH_ONLY",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_issuers": EXPECTED_ISSUERS, "total_trials": EXPECTED_TRIALS,
        "issuers_with_official_filing_leads": len(ready),
        "pilot_issuer_limit": max_issuers, "issuers_selected": len(selected),
        "issuers_not_selected": EXPECTED_ISSUERS - len(selected),
        "document_status_counts": dict(outcomes),
        "documents_selected_for_retrieval": len(all_documents),
        "documents_not_attempted_missing_agent": outcomes["IDENTIFYING_AGENT_REQUIRED"],
        "documents_attempted": (outcomes["PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY"]
                                + outcomes["SOURCE_UNAVAILABLE"]),
        "documents_retrieved": outcomes["PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY"],
        "documents_access_failed_or_blocked": outcomes["SOURCE_UNAVAILABLE"],
        "documents_with_bounded_review_locators": sum(
            bool(d["rights_language_review_locators"]) for d in all_documents),
        "documents_with_rights_language_locators": sum(
            d["rights_language_locator_count"] is not None
            and d["rights_language_locator_count"] > 0 for d in all_documents),
        "independently_verified_current_rights": 0,
        "independently_verified_rights_denominator": EXPECTED_TRIALS,
        "qualified_pipeline_total": None,
        "issuers": rows,
        "limitations": (
            "Official filing metadata and downloaded SEC documents are review leads only. "
            "No specific drug/indication, effective license terms, U.S. territory, "
            "current development rights or FDA PDUFA independently established. "
            "SEC access failures do not prove absence of rights. No Pipeline/GEM promotion."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("casebook", type=Path)
    parser.add_argument("sec_filing_leads", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-issuers", type=int, default=10)
    args = parser.parse_args()
    casebook = json.loads(args.casebook.read_text(encoding="utf-8"))
    leads = json.loads(args.sec_filing_leads.read_text(encoding="utf-8"))
    result = build_report(casebook, leads, max_issuers=args.max_issuers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"SEC primary-document pilot: {result['issuers_selected']}/{result['total_issuers']} "
          f"issuers selected; {result['documents_retrieved']} SEC documents fetched; "
          f"{result['documents_attempted']}/{result['documents_selected_for_retrieval']} attempts; "
          f"{result['documents_retrieved']} fetched; "
          f"{result['documents_not_attempted_missing_agent']} not attempted (missing identifying agent); "
          f"{result['documents_access_failed_or_blocked']} failed/blocked; "
          f"rights independently verified 0/{result['total_trials']}")
    if result["document_status_counts"].get("IDENTIFYING_AGENT_REQUIRED"):
        print("SEC_USER_AGENT identifying contact not configured: no SEC document requests were made.")


if __name__ == "__main__":
    main()
