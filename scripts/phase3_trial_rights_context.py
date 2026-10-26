#!/usr/bin/env python3
"""Join exact ClinicalTrials.gov intervention/condition context to SEC rights leads.

Each trial has its own registered intervention and condition context.
Issuer-level SEC filings remain general document leads, never study-level proof.
"""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.phase3_registry_context import validate_registry_context
from scripts.phase3_sec_rights_documents_pilot import validate_leads
from scripts.phase3_sec_rights_discovery import SHA

TRIALS = 741
ISSUERS = 130
DOCUMENT_STATES = {
    "SOURCE_UNAVAILABLE", "IDENTIFYING_AGENT_REQUIRED",
    "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY",
}


def build_review(registry, casebook, filing_leads, document_pilot):
    issuers, indexed_leads = validate_leads(casebook, filing_leads)
    records = registry.get("original_source_records")
    if (registry.get("census_total") != TRIALS
        or registry.get("source_identity_verified") != TRIALS
        or registry.get("source_errors") != []
        or registry.get("qualified_pipeline_total") is not None
        or not isinstance(records, list) or len(records) != TRIALS):
        raise ValueError("Complete verified ClinicalTrials.gov source report required")
    source_by_nct = {}
    for row in records:
        if not isinstance(row, dict) or row.get("nct_id") in source_by_nct:
            raise ValueError("Malformed/duplicate registry NCT")
        source_by_nct[row["nct_id"]] = row
    original = {r["nct_id"]: r for r in casebook["items"]}
    if set(source_by_nct) != set(original):
        raise ValueError("Registry records and rights casebook differ")

    pilot_issuers = document_pilot.get("issuers")
    if (document_pilot.get("report_type") != "MAIN_PHASE3_SEC_PRIMARY_RIGHTS_DOCUMENT_PILOT_RESEARCH_ONLY"
        or document_pilot.get("total_trials") != TRIALS
        or document_pilot.get("total_issuers") != ISSUERS
        or document_pilot.get("independently_verified_current_rights") != 0
        or document_pilot.get("qualified_pipeline_total") is not None
        or not isinstance(pilot_issuers, list) or len(pilot_issuers) != ISSUERS):
        raise ValueError("Invalid document pilot evidence scope")
    pilot_by_ticker = {}
    for item in pilot_issuers:
        if not isinstance(item, dict):
            raise ValueError("Invalid pilot issuer")
        ticker = item.get("ticker")
        if ticker not in issuers or ticker in pilot_by_ticker or item.get("cik") != issuers[ticker]["cik"]:
            raise ValueError("Pilot SEC issuer scope changed")
        if item.get("independently_verified_rights") is not False:
            raise ValueError("Pilot cannot assert commercial rights")
        if item.get("original_sec_index_sha256") != indexed_leads[ticker].get("source_sha256"):
            raise ValueError("Pilot SEC metadata hash mismatched")
        documents = item.get("documents")
        if not isinstance(documents, list) or len(documents) > 2:
            raise ValueError("Malformed or unbounded pilot document set")
        possible = {x["primary_document_url"] for x in indexed_leads[ticker]["candidate_filings"]}
        observed_urls = set()
        for doc in documents:
            url = doc.get("sec_primary_document_url")
            state, digest = doc.get("retrieval_status"), doc.get("source_sha256")
            if (url not in possible or url in observed_urls or state not in DOCUMENT_STATES
                or doc.get("verified_trial_development_rights") is not False):
                raise ValueError("Pilot document URL/status crosses rights boundary")
            observed_urls.add(url)
            if state == "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY":
                if not isinstance(digest, str) or not SHA.fullmatch(digest):
                    raise ValueError("Fetched SEC primary document lacks valid digest")
            elif digest is not None:
                raise ValueError("Unavailable document cannot have verified byte hash")
        pilot_by_ticker[ticker] = item
    if set(pilot_by_ticker) != set(issuers):
        raise ValueError("Document pilot did not account for 130 issuers")

    rows = []
    for record in casebook["items"]:
        nct, ticker = record["nct_id"], record["ticker"]
        source = source_by_nct[nct]
        if (source.get("source") != record["original_registry_api_url"]
            or source.get("source_sha256") != record["original_registry_sha256"]
            or source.get("census_ticker") != ticker
            or source.get("census_company") != record.get("saved_census_company")
            or source.get("verified_current_commercial_development_rights") is not False
            or source.get("qualified_pipeline") is not None):
            raise ValueError("Registry intervention context is not linked to exact NCT")
        context = validate_registry_context(source)
        lead = indexed_leads[ticker]
        pilot = pilot_by_ticker[ticker]
        fetched_documents = [
            {
                "sec_primary_document_url": d["sec_primary_document_url"],
                "source_sha256": d["source_sha256"],
                "retrieval_status": d["retrieval_status"],
            }
            for d in pilot["documents"] if d["retrieval_status"] == "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY"
        ]
        rows.append({
            "nct_id": nct, "ticker": ticker, "saved_sec_cik": record["saved_sec_cik"],
            "registry_source_url": record["original_registry_api_url"],
            "registry_source_sha256": record["original_registry_sha256"],
            "registered_interventions": context["registered_interventions"],
            "registered_conditions": context["registered_conditions"],
            "registry_context_status": context["registered_context_status"],
            "issuer_filing_metadata_status": lead["retrieval_status"],
            "issuer_filing_lead_count": len(lead["candidate_filings"]),
            "issuer_primary_documents_fetched": len(fetched_documents),
            "issuer_primary_document_sources": fetched_documents,
            "trial_specific_sec_drug_match": "NOT_REVIEWED",
            "trial_specific_sec_indication_match": "NOT_REVIEWED",
            "territorial_development_rights": "NOT_VERIFIED",
            "license_effective_termination_dates": "NOT_VERIFIED",
            "independently_verified_current_rights": False,
            "review_status": "NEEDS_TRIAL_SPECIFIC_DOCUMENT_REVIEW",
            "qualified_pipeline": None,
        })
    return {
        "report_type": "MAIN_PHASE3_REGISTRY_DRUG_INDICATION_SEC_RIGHTS_REVIEW_RESEARCH_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_trials": TRIALS, "total_issuer_pointers": ISSUERS,
        "interventions_reported_trials": sum(bool(r["registered_interventions"]) for r in rows),
        "conditions_reported_trials": sum(bool(r["registered_conditions"]) for r in rows),
        "both_interventions_conditions_reported_trials": sum(
            bool(r["registered_interventions"]) and bool(r["registered_conditions"]) for r in rows),
        "trials_with_issuer_metadata_filing_leads": sum(r["issuer_filing_lead_count"] > 0 for r in rows),
        "trials_with_retrieved_issuer_primary_documents": sum(r["issuer_primary_documents_fetched"] > 0 for r in rows),
        "independently_verified_current_rights": 0,
        "rights_needing_independent_document_review": TRIALS,
        "qualified_pipeline_total": None,
        "items": rows,
        "limitations": (
            "Registered interventions/conditions are not verified drug identities or indications. "
            "Issuer SEC filing leads and fetched documents do not establish that any exact study's "
            "drug, indication, US territory, licensing chain, legal rights, or PDUFA is verified. "
            "No evidence of absence and no automatic Pipeline/GEM/FS/FA promotion."
        ),
    }


def main():
    if len(sys.argv) != 6:
        sys.exit("Usage: phase3_trial_rights_context.py <registry> <casebook> <leads> <documents-pilot> <output>")
    sources = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:5]]
    result = build_review(*sources)
    path = Path(sys.argv[5])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Trial-specific context: {result['total_trials']}/741 exact trial identities; "
        f"interventions present {result['interventions_reported_trials']}/741; "
        f"conditions present {result['conditions_reported_trials']}/741; "
        f"issuer primary-document pointers fetched for {result['trials_with_retrieved_issuer_primary_documents']}/741; "
        f"commercial rights VERIFIED 0/741"
    )


if __name__ == "__main__":
    main()
