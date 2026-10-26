#!/usr/bin/env python3
"""Join original registry evidence, sponsor queue and saved SEC pointers.

Research pointers are NOT independent evidence of current commercial rights.
No live requests or qualification decisions. Fail closed on scope or identity drift.
"""
import json
import re
import sys
from pathlib import Path

EXPECTED_TRIALS = 741
EXPECTED_ISSUERS = 130
CIK = re.compile(r"^[0-9]{10}$")
SHA256 = re.compile(r"^[a-fA-F0-9]{64}$")


def index_exact(rows, label, field="nct_id"):
    if not isinstance(rows, list) or len(rows) != EXPECTED_TRIALS:
        raise ValueError(f"{label}: expected complete 741-record dataset")
    indexed = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{label}: malformed row")
        key = row.get(field)
        if not isinstance(key, str) or not re.fullmatch(r"NCT[0-9]{8}", key) or key in indexed:
            raise ValueError(f"{label}: missing, malformed or duplicated NCT")
        indexed[key] = row
    return indexed


def build_casebook(ledger, registry, sponsor_queue, rights_gaps):
    if (ledger.get("total") != EXPECTED_TRIALS
        or registry.get("census_total") != EXPECTED_TRIALS
        or registry.get("source_identity_verified") != EXPECTED_TRIALS
        or registry.get("source_errors") != []
        or sponsor_queue.get("total") != EXPECTED_TRIALS
        or sponsor_queue.get("review_required") != EXPECTED_TRIALS
        or rights_gaps.get("trial_count") != EXPECTED_TRIALS
        or rights_gaps.get("issuer_count") != EXPECTED_ISSUERS
        or rights_gaps.get("independently_verified_current_development_rights") != 0
        or rights_gaps.get("qualified_pipeline_count") is not None
        or ledger.get("qualified_pipeline_total") is not None
        or sponsor_queue.get("qualified_pipeline_total") is not None
        or registry.get("qualified_pipeline_total") is not None):
        raise ValueError("Fail-closed source, identity or research-only scope mismatch")
    base = index_exact(ledger.get("records"), "ledger")
    sources = index_exact(registry.get("original_source_records"), "registry")
    sponsors = index_exact(sponsor_queue.get("items"), "sponsor queue")
    gaps = index_exact(rights_gaps.get("trials"), "rights gaps")
    if not (set(base) == set(sources) == set(sponsors) == set(gaps)):
        raise ValueError("Four research source datasets disagree on NCT identities")
    rows = []
    issuer_ciks = {}
    comparisons = {"MATCH": 0, "MISMATCH_REVIEW": 0, "UNAVAILABLE": 0}
    for nct in sorted(base):
        record, source, sponsor, gap = base[nct], sources[nct], sponsors[nct], gaps[nct]
        ticker, company = record.get("ticker"), record.get("company")
        expected_registry_url = f"https://clinicaltrials.gov/api/v2/studies/{nct}"
        if (not isinstance(ticker, str) or not ticker or not isinstance(company, str) or not company
            or source.get("census_ticker") != ticker or source.get("census_company") != company
            or sponsor.get("ticker") != ticker or sponsor.get("census_company") != company
            or gap.get("ticker") != ticker
            or gap.get("registry_lead_sponsor_name") != company
            or gap.get("registry_record_url") != record.get("source_url")
            or source.get("source") != expected_registry_url
            or sponsor.get("original_registry_url") != expected_registry_url
            or record.get("source_sha256") != source.get("source_sha256")
            or sponsor.get("source_sha256") != source.get("source_sha256")
            or not isinstance(source.get("source_sha256"), str)
            or not SHA256.fullmatch(source["source_sha256"])
            or record.get("gates", {}).get("registry_identity") != "PASS"
            or record.get("gates", {}).get("current_commercial_rights") != "REVIEW"
            or record.get("qualified_pipeline") is not None
            or sponsor.get("review_gate") != "current_commercial_rights"
            or sponsor.get("review_status") != "REVIEW"
            or sponsor.get("commercial_rights_verified") is not False
            or gap.get("current_development_rights_status") != "RIGHTS_NOT_ESTABLISHED"
            or gap.get("current_rights_primary_source") is not None
            or gap.get("qualified_pipeline") is not None):
            raise ValueError(f"{nct}: research source association or qualification drift")
        cik = gap.get("issuer_cik")
        if not isinstance(cik, str) or not CIK.fullmatch(cik) or cik == "0000000000":
            raise ValueError(f"{nct}: invalid saved SEC CIK")
        sec_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        if gap.get("issuer_sec_submissions_url") != sec_url:
            raise ValueError(f"{nct}: SEC issuer research pointer mismatch")
        if ticker in issuer_ciks and issuer_ciks[ticker] != cik:
            raise ValueError(f"{nct}: conflicting SEC issuer identity")
        issuer_ciks[ticker] = cik
        current_sponsor = source.get("currently_registered_lead_sponsor")
        if sponsor.get("registered_lead_sponsor") != current_sponsor:
            raise ValueError(f"{nct}: sponsor source mismatch")
        if current_sponsor is None:
            comparison = "UNAVAILABLE"
        elif not isinstance(current_sponsor, str) or not current_sponsor.strip():
            raise ValueError(f"{nct}: invalid original sponsor name")
        elif current_sponsor.strip().casefold() == company.strip().casefold():
            comparison = "MATCH"
        else:
            comparison = "MISMATCH_REVIEW"
        comparisons[comparison] += 1
        rows.append({
            "nct_id": nct, "ticker": ticker, "saved_census_company": company,
            "current_registry_lead_sponsor": current_sponsor,
            "registry_sponsor_name_comparison": comparison,
            "original_registry_api_url": expected_registry_url,
            "original_registry_sha256": source["source_sha256"],
            "saved_sec_cik": cik, "saved_sec_submissions_url": sec_url,
            "rights_verification_status": "NOT_ESTABLISHED",
            "review_priority": "SPONSOR_MISMATCH_REVIEW" if comparison == "MISMATCH_REVIEW" else "RIGHTS_DOCUMENT_REQUIRED",
            "independent_rights_source_url": None,
            "required_document_checks": [
                "CURRENT_OWNERSHIP_OR_LICENSE_PRIMARY_SOURCE",
                "DRUG_AND_INDICATION_MATCH",
                "US_TERRITORY_AND_DEVELOPMENT_RIGHTS",
                "EFFECTIVE_AND_TERMINATION_DATES",
                "ISSUER_AND_LEGAL_ENTITY_CHAIN",
            ], "qualified_pipeline": None,
        })
    if len(issuer_ciks) != EXPECTED_ISSUERS:
        raise ValueError("Expected all 130 saved issuer pointers")
    return {
        "report_type": "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY",
        "total_trials": EXPECTED_TRIALS, "saved_issuer_pointers": len(issuer_ciks),
        "registry_sponsor_comparisons": comparisons,
        "rights_unverified_trials": EXPECTED_TRIALS, "rights_verified_trials": 0,
        "qualified_pipeline_total": None, "items": rows,
        "limitations": "Registry sponsorship and saved SEC CIK point to research sources only. No current rights have been independently verified; no Pipeline/GEM promotion.",
    }


def main():
    if len(sys.argv) != 6:
        sys.exit("Usage: phase3_rights_casebook.py <ledger> <registry> <sponsor_queue> <rights_gaps> <output>")
    inputs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:5]]
    result = build_casebook(*inputs)
    output = Path(sys.argv[5])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Rights casebook: {result['total_trials']}/741 original trials, "
          f"{result['saved_issuer_pointers']}/130 SEC issuer pointers; "
          f"{result['rights_unverified_trials']}/741 rights unverified")


if __name__ == "__main__":
    main()
