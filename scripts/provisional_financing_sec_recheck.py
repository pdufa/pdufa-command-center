"""Refresh SEC evidence for PUBLIC/IR-confirmed financing research leads.

These results NEVER alter the two-distinct-post-Phase-3-financings entry gate,
source verification statuses, company identities, or existing candidate data.
A search-engine result is discovery. Research leads remain visible on SEC failure.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

FIELDS = (
    "event_key", "ticker", "company_ir_status", "ir_close_date",
    "transaction_type", "company_ir_url", "sec_recheck_status",
    "sec_url", "sec_sha256", "checked_at_utc", "reason",
    "gem_entry_authorized",
)
FORMS = {"8-K", "8-K/A", "6-K", "10-Q", "10-K"}
MAX_FILINGS = 16
MAX_DOCUMENTS = 8


def safe_document(name):
    return (isinstance(name, str) and
            bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", name)) and
            name.lower().endswith((".htm", ".html", ".txt")))


def _filings(verifier, event, close):
    """Find bounded, date-matched filings for the exact registered issuer.

    Look beyond the first eight filings: a later 8-K can disclose a closing
    that was announced only as an expected transaction in earlier filings.
    No filing date is itself treated as a closing date.
    """
    _, _, recent = verifier.submissions(event)
    cutoff = min(close + timedelta(days=180), verifier.as_of)
    matched = []
    for form, filed, accession, primary in zip(
        recent["form"], recent["filingDate"],
        recent["accessionNumber"], recent["primaryDocument"]
    ):
        if (form not in FORMS or not safe_document(primary)
                or not isinstance(accession, str)
                or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession)):
            continue
        try:
            day = date.fromisoformat(filed)
        except (ValueError, TypeError):
            continue
        if close <= day <= cutoff:
            # Prefer a current report over a periodic filing on the same date.
            priority = 0 if form in {"8-K", "8-K/A", "6-K"} else 1
            matched.append((day, priority, accession, primary))
    matched.sort(key=lambda r: (r[0], r[1], r[2]))
    return [(day, accession, primary)
            for day, _, accession, primary in matched[:MAX_FILINGS]]


def _sec_documents(verifier, cik, accession, primary):
    """Only indexed documents from the issuer's SEC archive; no guessed URLs.

    Include the filing itself and actual Exhibit 99 press releases, Exhibit
    10 agreements, Exhibit 4 securities instruments and Exhibit 2 agreements.
    These are search candidates, NEVER independent evidence of a closing.
    """
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(accession)):
        return []
    if not safe_document(primary) or not str(cik).isdigit() or not int(cik):
        return []
    # An accession prefix may belong to the filing agent rather than issuer.
    base = ("https://www.sec.gov/Archives/edgar/data/" +
            str(int(cik)) + "/" + accession.replace("-", "") + "/")
    index = json.loads(verifier.body(base + "index.json"))
    items = index.get("directory", {}).get("item", [])
    if not isinstance(items, list):
        raise ValueError("SEC index directory list is malformed")
    exhibits = []
    for doc in items:
        if not isinstance(doc, dict):
            continue
        name = doc.get("name", "")
        if safe_document(name) and re.search(
            r"(?i)(?:^|[^a-z0-9])(?:ex|exhibit)[-_.]?(?:99|10|4|2)(?=[^a-z0-9]|\d)",
            name,
        ):
            exhibits.append(name)
    # The listed primary document must always be reviewed, even if the index
    # is full of exhibits. Deduplicate without exceeding SEC request limits.
    names = list(dict.fromkeys([primary] + exhibits))[:MAX_DOCUMENTS]
    return [base + name for name in names]

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
                    "_recheck_exact_sec_url": True,
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

def main(argv=None):
    parser = argparse.ArgumentParser(description="Fresh SEC recheck of provisional financing leads")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--targets", type=Path, default=Path("data/finance_ir_sec_recheck_targets.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/missing_sources/sec_financing_ir_recheck.csv"))
    args = parser.parse_args(argv)
    from scripts.source_verification import Verifier, read_rows
    events = read_rows(args.data_dir / "pdufa_candidates.csv")
    registry = read_rows(args.data_dir / "company_registry.csv")
    if not events or not registry:
        raise SystemExit("Missing candidate or company registry: no SEC verification performed")
    # Every invocation uses a newly constructed verifier and fresh SEC submission
    # requests. Research leads never become proof just because they are in CSV.
    verifier = Verifier(registry)
    rows = recheck_leads(verifier, events, args.targets, args.output)
    if not rows:
        raise SystemExit("Empty SEC recheck queue; no confirmation audit published")
    totals = {}
    for row in rows:
        status = row["sec_recheck_status"]
        totals[status] = totals.get(status, 0) + 1
        if row["gem_entry_authorized"] != "NO":
            raise SystemExit("Unsafe SEC recheck output attempted entry authorization")
    print(json.dumps({"checked": len(rows), "status_counts": totals,
                      "trade_entry_authorized": 0, "output": str(args.output)},
                     sort_keys=True))
    return rows


if __name__ == "__main__":
    main()
