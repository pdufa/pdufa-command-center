"""Refresh SEC evidence for PUBLIC/IR-confirmed financing research leads.

These results NEVER alter the two-distinct-post-Phase-3-financings entry gate,
source verification statuses, company identities, or existing candidate data.
A search-engine result is discovery. Research leads remain visible on SEC failure.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

FIELDS = (
    "event_key", "ticker", "company_ir_status", "ir_close_date",
    "transaction_type", "company_ir_url", "sec_recheck_status",
    "sec_url", "sec_sha256", "checked_at_utc", "reason",
    "gem_entry_authorized",
)
FORMS = {"8-K", "8-K/A", "6-K", "10-Q", "10-K"}
MAX_FILINGS = 4
MAX_DOCUMENTS = 5


def safe_document(name):
    return (isinstance(name, str) and
            bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", name)) and
            name.lower().endswith((".htm", ".html", ".txt")))


def _filings(verifier, event, close):
    """Use *fresh* SEC submissions, validated by issuer CIK and ticker."""
    _, _, recent = verifier.submissions(event)
    cutoff = min(close + timedelta(days=90), verifier.as_of)
    matched = []
    for form, filed, accession, primary in zip(
        recent["form"], recent["filingDate"],
        recent["accessionNumber"], recent["primaryDocument"]
    ):
        if form not in FORMS or not safe_document(primary):
            continue
        try:
            day = date.fromisoformat(filed)
        except (ValueError, TypeError):
            continue
        if close <= day <= cutoff:
            matched.append((day, accession, primary))
    return sorted(matched, key=lambda r: (r[0], r[1]))[:MAX_FILINGS]


def _sec_documents(verifier, cik, accession, primary):
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
        return []
    if accession[:10] != cik or not safe_document(primary):
        return []
    base = ("https://www.sec.gov/Archives/edgar/data/" +
            str(int(cik)) + "/" + accession.replace("-", "") + "/")
    # Only an actual SEC index supplies source document names; never assume
    # an issuer website article is part of an SEC archive.
    index = json.loads(verifier.body(base + "index.json"))
    names = []
    for doc in index.get("directory", {}).get("item", []):
        name = doc.get("name", "")
        if safe_document(name) and re.search(
            r"(?i)(?:ex[-_]?99|exhibit[-_]?99)", name
        ):
            names.append(name)
    return [base + name for name in list(dict.fromkeys(names[:MAX_DOCUMENTS-1] + [primary]))]


def _result(lead, status, reason, sec=None):
    sec = sec or {}
    return {
        "event_key": lead["event_key"],
        "ticker": lead["ticker"],
        "company_ir_status": "CONFIRMED_PUBLIC_SOURCE_LEAD",
        "ir_close_date": lead["public_close_date"],
        "transaction_type": lead["transaction_type"],
        "company_ir_url": lead["company_ir_url"],
        "sec_recheck_status": status,
        "sec_url": sec.get("source_url", ""),
        "sec_sha256": sec.get("source_sha256", ""),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "reason": reason[:450],
        "gem_entry_authorized": "NO",
    }


def recheck_leads(verifier, events, targets_path, output_path):
    """Always refetch SEC submission/index/docs; no prior VERIFIED label is reused.

    One row per exact event and *possible* closing; unique SEC transaction
    evidence may verify a single closing, never that it was a separate second
    post-readout financing. Any missing/blocked source stays a review.
    """
    with Path(targets_path).open(newline="", encoding="utf-8-sig") as handle:
        leads = list(csv.DictReader(handle))
    event_map = {str(e.get("event_key", "")): e for e in events}
    results = []
    for lead in leads:
        key = lead.get("event_key", "")
        event = event_map.get(key)
        close_raw = lead.get("public_close_date", "")
        try:
            close = date.fromisoformat(close_raw)
        except (TypeError, ValueError):
            results.append(_result(lead, "REVIEW_BAD_DATE",
                                   "Research closing date is invalid"))
            continue
        if (event is None or event.get("ticker") != lead.get("ticker") or
                close > verifier.as_of):
            results.append(_result(lead, "REVIEW_IDENTITY_OR_DATE",
                                   "Candidate identity missing/mismatched or closing in future"))
            continue
        if not lead.get("company_ir_url", "").startswith("https://"):
            results.append(_result(lead, "REVIEW_NO_PRIMARY_IR_LINK",
                                   "Exact public-source transaction link not supplied"))
            continue
        cik = verifier.cik(event)
        if not cik:
            results.append(_result(lead, "REVIEW_MISSING_COMPANY_CIK",
                                   "Exact issuer CIK unavailable"))
            continue
        found = None
        failures = []
        document_count = 0
        try:
            filings = _filings(verifier, event, close)
        except Exception as exc:
            results.append(_result(lead, "SEC_SOURCE_UNAVAILABLE",
                                   "SEC submissions could not be refreshed: " +
                                   type(exc).__name__))
            continue
        for filed, accession, primary in filings:
            try:
                urls = _sec_documents(verifier, cik, accession, primary)
            except Exception as exc:
                failures.append(type(exc).__name__)
                continue
            for url in urls:
                if document_count >= MAX_FILINGS * MAX_DOCUMENTS:
                    break
                document_count += 1
                # The existing conservative verifier requires this exact
                # company CIK, actual dated funding clause, and SEC body hash.
                probe = dict(event)
                probe.update({
                    "financing_evidence_url": url,
                    "financing_close_date": close.isoformat(),
                    "_financing_review": {},
                })
                row = verifier.financing(probe)
                if row["verification_status"] == "VERIFIED" and row.get("source_sha256"):
                    found = row
                    break
                if row["verification_status"] == "TECHNICAL_FAILURE":
                    failures.append(str(row.get("reason", "SEC unavailable"))[:60])
            if found:
                break
        if found:
            results.append(_result(lead, "SEC_TRANSACTION_VERIFIED",
                                   "SEC independently confirms this specific dated transaction ONLY; " +
                                   "separate post-Phase-3 first/second financing sequence NOT verified",
                                   found))
        elif failures:
            results.append(_result(lead, "SEC_SOURCE_PARTIAL_REVIEW",
                                   "SEC lookup incomplete or blocked; provisional IR lead retained: " +
                                   ", ".join(failures[:3])))
        else:
            results.append(_result(lead, "SEC_DOCUMENT_NOT_CONFIRMED",
                                   "No exact dated completed funding clause verified in bounded " +
                                   "same-issuer SEC filings; provisional IR lead retained"))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(output_path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    return results
