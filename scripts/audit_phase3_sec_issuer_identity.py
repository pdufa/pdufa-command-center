#!/usr/bin/env python3
"""Independent read-only SEC ticker-to-CIK research audit for 130 census issuers.

The 741-trial Phase 3 historical research census is NOT a qualified Pipeline.
This cross-check ONLY verifies whether the saved ticker -> CIK pointers agree
with the current public SEC ticker directory. It does not certify ownership
of any trial or development rights, an active program, current market cap,
a U.S. FDA application/PDUFA date, or scientific approval probability.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
COMPANIES_PATH = ROOT / "new-platform/frontend/public/phase3-census-sources-2026-10-26.json"
TRIALS_PATH = ROOT / "new-platform/frontend/public/phase3-census-2026-10-26.csv"
COMPANY_REGISTRY_PATH = ROOT / "data/company_registry.csv"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
MAX_SOURCE_BYTES = 3_000_000
CENSUS_COUNT = 741
CENSUS_ISSUERS = 130

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("SEC ticker directory redirected from fixed source URL")


def saved_issuers() -> list[dict[str, str]]:
    """Validate each saved ticker/CIK against its original local issuer record."""
    raw = json.loads(COMPANIES_PATH.read_text("utf-8"))
    rows = list(csv.DictReader(io.StringIO(TRIALS_PATH.read_text("utf-8-sig"))))
    companies = list(csv.DictReader(io.StringIO(COMPANY_REGISTRY_PATH.read_text("utf-8-sig"))))
    if (not isinstance(raw, dict) or raw.get("scope") != "RESEARCH_POINTERS_ONLY"
        or raw.get("schemaVersion") != 1 or raw.get("trialCount") != CENSUS_COUNT
        or raw.get("companyCount") != CENSUS_ISSUERS
        or not isinstance(raw.get("companies"), list) or len(raw["companies"]) != CENSUS_ISSUERS
        or len(rows) != CENSUS_COUNT or len({r["nct_id"] for r in rows}) != CENSUS_COUNT):
        raise ValueError("Saved Phase 3 original census/issuer scope cannot be reconciled")
    by_ticker: dict[str, dict[str, str]] = {}
    for row in companies:
        ticker = row.get("ticker")
        if ticker in by_ticker:
            raise ValueError("Duplicated original company-registry ticker")
        by_ticker[ticker] = row
    expected_tickers = {r["ticker"] for r in rows}
    if len(expected_tickers) != CENSUS_ISSUERS:
        raise ValueError("Original Phase 3 census ticker count changed")
    mapping = []
    seen = set()
    all_ncts = set()
    for issuer in raw["companies"]:
        if not isinstance(issuer, dict):
            raise ValueError("Malformed saved issuer source")
        ticker, cik = issuer.get("ticker"), issuer.get("cik")
        if (not isinstance(ticker, str) or not re.fullmatch(r"[A-Z]{1,7}(?:[.-][A-Z]{1,3})?", ticker)
            or ticker not in expected_tickers or ticker in seen
            or not isinstance(cik, str) or not re.fullmatch(r"\d{10}", cik)
            or cik == "0000000000" or ticker not in by_ticker
            or by_ticker[ticker].get("cik10") != cik
            or by_ticker[ticker].get("status") != "OK"
            or issuer.get("secSubmissionsUrl") != f"https://data.sec.gov/submissions/CIK{cik}.json"
            or issuer.get("secFilingsUrl") != f"https://www.sec.gov/edgar/browse/?CIK={cik}&owner=exclude"
            or not isinstance(issuer.get("nctIds"), list)):
            raise ValueError("Saved Phase 3 CIK/ticker identity is inconsistent")
        for nct in issuer["nctIds"]:
            if (not isinstance(nct, str) or not re.fullmatch(r"NCT\d{8}", nct)
                or nct in all_ncts
                or not any(r["nct_id"] == nct and r["ticker"] == ticker for r in rows)):
                raise ValueError("Saved issuer-to-trial association is not exact")
            all_ncts.add(nct)
        seen.add(ticker)
        mapping.append({"ticker": ticker, "cik": cik, "saved_company": issuer.get("company", "")})
    if seen != expected_tickers or len(all_ncts) != CENSUS_COUNT:
        raise ValueError("Saved Phase 3 issuer coverage is incomplete")
    return sorted(mapping, key=lambda x: x["ticker"])


def parse_sec_directory(source: bytes) -> dict[str, list[dict[str, str]]]:
    if not source or len(source) > MAX_SOURCE_BYTES:
        raise ValueError("SEC issuer directory exceeds bounded source size")
    try:
        payload = json.loads(source)
    except (ValueError, UnicodeError) as error:
        raise ValueError("SEC directory is not valid JSON") from error
    if not isinstance(payload, dict) or len(payload) < 100:
        raise ValueError("SEC ticker directory format or completeness invalid")
    result: dict[str, list[dict[str, str]]] = {}
    for entry in payload.values():
        if not isinstance(entry, dict):
            raise ValueError("Invalid SEC ticker directory row")
        ticker = entry.get("ticker")
        cik = entry.get("cik_str")
        title = entry.get("title")
        if (not isinstance(ticker, str) or not 1 <= len(ticker) <= 20
            or not isinstance(cik, int) or isinstance(cik, bool) or not 0 < cik < 10_000_000_000
            or not isinstance(title, str) or not title or len(title) > 300):
            raise ValueError("Malformed ticker/CIK in SEC official source")
        result.setdefault(ticker.upper(), []).append({
            "sec_cik": f"{cik:010d}", "sec_title": title[:300],
        })
    return result


def audit_130(saved: list[dict[str, str]], sec: dict[str, list[dict[str, str]]],
              source_hash: str, fetched_at: str) -> dict[str, object]:
    if (len(saved) != CENSUS_ISSUERS or len({x["ticker"] for x in saved}) != CENSUS_ISSUERS
        or not re.fullmatch(r"[a-f0-9]{64}", source_hash)
        or not fetched_at):
        raise ValueError("Original issuer audit identity/count invalid")
    audited = []
    for issuer in saved:
        candidates = sec.get(issuer["ticker"], [])
        if not candidates:
            disposition = "TICKER_NOT_FOUND_IN_SEC_DIRECTORY"
        elif len(candidates) != 1:
            disposition = "AMBIGUOUS_OFFICIAL_TICKER_MAPPING"
        elif candidates[0]["sec_cik"] != issuer["cik"]:
            disposition = "SAVED_CIK_DIFFERS_FROM_SEC"
        else:
            disposition = "SAVED_CIK_MATCHES_OFFICIAL_SEC_TICKER"
        audited.append({
            "ticker": issuer["ticker"],
            "saved_cik": issuer["cik"],
            "sec_ciks": [x["sec_cik"] for x in candidates],
            "sec_names": [x["sec_title"] for x in candidates],
            "identity_disposition": disposition,
            "development_rights_verified": False,
            "drug_indication_verified": False,
            "verified_us_fda_pdufa": False,
            "qualified_pipeline": None,
            "approval_probability": None,
        })
    verified = sum(r["identity_disposition"] == "SAVED_CIK_MATCHES_OFFICIAL_SEC_TICKER"
                   for r in audited)
    return {
        "report_type": "SEC_ORIGINAL_TICKER_CIK_RESEARCH_ONLY",
        "official_source_url": SEC_TICKERS_URL,
        "official_source_sha256": source_hash,
        "checked_at_utc": fetched_at,
        "dated_census_trials": CENSUS_COUNT,
        "requested_census_issuers": CENSUS_ISSUERS,
        "issuer_ticker_cik_matches": verified,
        "issuer_mapping_unresolved": CENSUS_ISSUERS - verified,
        "all_sec_ticker_cik_mappings_matched": verified == CENSUS_ISSUERS,
        "issuer_audit_rows": audited,
        "qualified_pipeline_total": None,
        "verified_us_fda_pdufa_total": None,
        "validated_approval_probabilities": None,
        "limits": "A matching SEC ticker/CIK identifies a public issuer, NOT sponsor IP rights, listing/current cap, live development, FDA application or PDUFA.",
    }


def run(output: Path) -> int:
    saved = saved_issuers()
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(SEC_TICKERS_URL, method="GET",
        headers={"Accept": "application/json",
                 "User-Agent": "PDUFA-Command-Center-ReadOnly-Research/1.0"})
    with opener.open(request, timeout=20) as response:
        if (response.status != 200 or response.geturl() != SEC_TICKERS_URL
            or "application/json" not in response.headers.get("content-type", "").lower()):
            raise ValueError("SEC original ticker directory not accessible at exact source")
        raw = response.read(MAX_SOURCE_BYTES+1)
    sec = parse_sec_directory(raw)
    report = audit_130(saved, sec, hashlib.sha256(raw).hexdigest(),
                       datetime.now(timezone.utc).isoformat())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print(f"SEC original ticker/CIK match: {report['issuer_ticker_cik_matches']}/130; "
          f"{report['issuer_mapping_unresolved']} unresolved official source mappings.")
    for issuer in report["issuer_audit_rows"]:
        if issuer["identity_disposition"] != "SAVED_CIK_MATCHES_OFFICIAL_SEC_TICKER":
            print(f"NEEDS_REVIEW: {issuer['ticker']} {issuer['identity_disposition']}")
    print("No SEC company match certifies current drug rights, listing/cap, FDA PDUFA or Pipeline qualification.")
    return 0  # Source fetched/parsed successfully. Match coverage is recorded, not invented.


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: audit_phase3_sec_issuer_identity.py <report-path>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run(Path(sys.argv[1])))
