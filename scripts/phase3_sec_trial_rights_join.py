#!/usr/bin/env python3
"""Join exact per-NCT ClinicalTrials.gov program leads with SEC document review status.

This is a RESEARCH QUEUE, not evidence of legal ownership or FDA qualification.
Issuer-level filings must never become an NCT-specific rights PASS by association.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.phase3_sec_rights_documents_pilot import validate_leads
from scripts.phase3_sec_rights_discovery import SHA

TOTAL = 741
ISSUERS = 130
NCT = re.compile(r"^NCT[0-9]{8}$")
DOCUMENT_STATES = {
    "SOURCE_UNAVAILABLE", "IDENTIFYING_AGENT_REQUIRED",
    "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY",
}


def build_join(program, casebook, leads, pilot):
    issuers, indexed_leads = validate_leads(casebook, leads)
    records = program.get("items")
    if (program.get("report_type") != "MAIN_PHASE3_ORIGINAL_DRUG_INDICATION_TERMS_RESEARCH_ONLY"
        or program.get("total_trials") != TOTAL
        or program.get("total_saved_issuer_pointers") != ISSUERS
        or program.get("independently_verified_program_identities") != 0
        or program.get("independently_verified_commercial_rights") != 0
        or program.get("qualified_pipeline_total") is not None
        or not isinstance(records, list) or len(records) != TOTAL):
        raise ValueError("Complete research-only drug/indication source context required")
    program_by_nct = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Malformed program record")
        nct = record.get("nct_id")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in program_by_nct:
            raise ValueError("Duplicate, missing or malformed trial identity")
        program_by_nct[nct] = record
    casebook_by_nct = {x["nct_id"]: x for x in casebook["items"]}
    if set(program_by_nct) != set(casebook_by_nct):
        raise ValueError("Program and SEC rights casebook have different NCT scope")
    pilot_rows = pilot.get("issuers")
    if (pilot.get("report_type") != "MAIN_PHASE3_SEC_PRIMARY_RIGHTS_DOCUMENT_PILOT_RESEARCH_ONLY"
        or pilot.get("total_issuers") != ISSUERS or pilot.get("total_trials") != TOTAL
        or pilot.get("independently_verified_current_rights") != 0
        or pilot.get("qualified_pipeline_total") is not None
        or not isinstance(pilot_rows, list) or len(pilot_rows) != ISSUERS):
        raise ValueError("Incomplete or qualifying SEC primary-document pilot")
    document_issuers = {}
    trial_lexical_sources = {}
    for issuer in pilot_rows:
        if not isinstance(issuer, dict):
            raise ValueError("Invalid pilot issuer")
        ticker = issuer.get("ticker")
        if (ticker not in issuers or ticker in document_issuers
            or issuer.get("cik") != issuers[ticker]["cik"]
            or issuer.get("original_sec_index_sha256") != indexed_leads[ticker]["source_sha256"]
            or issuer.get("independently_verified_rights") is not False):
            raise ValueError("Pilot issuer CIK, index hash or rights scope mismatched")
        documents = issuer.get("documents")
        if not isinstance(documents, list) or len(documents) > 2:
            raise ValueError("Unbounded or malformed primary documents")
        allowable = {x["primary_document_url"] for x in indexed_leads[ticker]["candidate_filings"]}
        seen = set()
        verified_documents = []
        for doc in documents:
            if not isinstance(doc, dict):
                raise ValueError("Malformed pilot SEC document")
            url, state, digest = (doc.get("sec_primary_document_url"),
                                  doc.get("retrieval_status"), doc.get("source_sha256"))
            if (url not in allowable or url in seen or state not in DOCUMENT_STATES
                or doc.get("verified_trial_development_rights") is not False):
                raise ValueError("Invalid document association or rights status")
            seen.add(url)
            if state == "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY":
                if not isinstance(digest, str) or not SHA.fullmatch(digest):
                    raise ValueError("SEC document missing source bytes digest")
                verified_documents.append({"url": url, "sha256": digest,
                                           "scope": "ISSUER_DOCUMENT_ONLY_NOT_TRIAL_RIGHTS"})
            elif digest is not None:
                raise ValueError("Failed SEC document cannot claim a source hash")
            mentions = doc.get("trial_registered_term_lexical_mentions", [])
            if not isinstance(mentions, list) or len(mentions) > 120:
                raise ValueError("Malformed/oversized exact trial term source leads")
            if state != "PRIMARY_DOCUMENT_FETCHED_RESEARCH_ONLY" and mentions:
                raise ValueError("Unavailable document cannot provide text matches")
            seen_terms = set()
            for mention in mentions:
                if not isinstance(mention, dict):
                    raise ValueError("Malformed trial-specific source locator")
                nct, kind, name = (mention.get("nct_id"), mention.get("term_kind"),
                                   mention.get("registered_term"))
                if (nct not in issuers[ticker]["nct_ids"] or nct not in program_by_nct
                    or kind not in ("REGISTERED_DRUG_OR_BIOLOGIC", "REGISTERED_CONDITION")
                    or not isinstance(name, str) or not 4 <= len(name) <= 400
                    or (nct, kind, name) in seen_terms
                    or mention.get("status") !=
                        "EXACT_LEXICAL_MENTION_RESEARCH_ONLY_NO_RIGHTS_VERIFIED"
                    or type(mention.get("normalized_text_offset")) is not int
                    or not 0 <= mention["normalized_text_offset"] <= 8_000_000
                    or not isinstance(mention.get("context_excerpt"), str)
                    or len(mention["context_excerpt"]) > 160):
                    raise ValueError("Forged, duplicate or cross-issuer exact text locator")
                entry = program_by_nct[nct]
                allowed = (entry.get("provisional_drug_or_biologic_names") if
                           kind == "REGISTERED_DRUG_OR_BIOLOGIC" else
                           entry.get("registry_conditions"))
                if not isinstance(allowed, list) or name not in allowed:
                    raise ValueError("SEC text lead does not match original NCT registered term")
                seen_terms.add((nct, kind, name))
                trial_lexical_sources.setdefault(nct, []).append({
                    "term_kind": kind, "registered_term": name,
                    "source_url": url, "source_sha256": digest,
                    "normalized_text_offset": mention["normalized_text_offset"],
                    "context_excerpt": mention["context_excerpt"],
                    "review_status": "LEXICAL_ONLY_NOT_VERIFIED_LEGAL_RIGHTS",
                })
        document_issuers[ticker] = verified_documents
    if set(document_issuers) != set(issuers):
        raise ValueError("Pilot SEC issuer scope incomplete")
    rows = []
    for nct in sorted(program_by_nct):
        item, source = program_by_nct[nct], casebook_by_nct[nct]
        ticker = source["ticker"]
        if (item.get("ticker") != ticker
            or item.get("original_registry_source_url") != source["original_registry_api_url"]
            or item.get("original_registry_source_sha256") != source["original_registry_sha256"]
            or item.get("drug_indication_qualified") is not False
            or item.get("commercial_rights_verified") is not False
            or item.get("qualified_pipeline") is not None
            or item.get("identity_review_status") != "REGISTRY_TERMS_REQUIRE_INDEPENDENT_REVIEW"
            or not isinstance(item.get("registry_conditions"), list)
            or not isinstance(item.get("registry_interventions"), list)
            or not isinstance(item.get("provisional_drug_or_biologic_names"), list)):
            raise ValueError("Drug/indication context has mismatched provenance or unsafe rights status")
        names = {v.get("name") for v in item["registry_interventions"] if isinstance(v, dict)}
        if not all(isinstance(v, str) and v in names for v in item["provisional_drug_or_biologic_names"]):
            raise ValueError("Provisional drug names are not from original NCT interventions")
        lead = indexed_leads[ticker]
        rows.append({
            "nct_id": nct, "ticker": ticker, "saved_sec_cik": source["saved_sec_cik"],
            "original_registry_url": item["original_registry_source_url"],
            "original_registry_sha256": item["original_registry_source_sha256"],
            "original_registry_study_title": item["original_registry_study_title"],
            "registered_conditions": item["registry_conditions"],
            "registered_interventions": item["registry_interventions"],
            "provisional_drug_or_biologic_names": item["provisional_drug_or_biologic_names"],
            "conditions_field_status": item["conditions_field_status"],
            "interventions_field_status": item["interventions_field_status"],
            "issuer_sec_filing_leads": len(lead["candidate_filings"]),
            "issuer_sec_retrieval_status": lead["retrieval_status"],
            "issuer_sec_primary_documents_retrieved": len(document_issuers[ticker]),
            "issuer_primary_document_sources": document_issuers[ticker],
            "exact_registry_term_sec_text_leads": trial_lexical_sources.get(nct, []),
            "trial_drug_sec_document_match": "NOT_REVIEWED",
            "trial_indication_sec_document_match": "NOT_REVIEWED",
            "current_us_territorial_rights": "NOT_VERIFIED",
            "legal_effective_or_termination_dates": "NOT_VERIFIED",
            "current_rights_verified": False,
            "review_status": "TRIAL_SPECIFIC_RIGHTS_EVIDENCE_REQUIRED",
            "qualified_pipeline": None,
        })
    return {
        "report_type": "MAIN_PHASE3_TRIAL_DRUG_SEC_RIGHTS_JOIN_RESEARCH_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_trials": TOTAL, "total_issuers": ISSUERS,
        "trials_with_registry_provisional_drugs": sum(bool(x["provisional_drug_or_biologic_names"]) for x in rows),
        "trials_with_registered_conditions": sum(bool(x["registered_conditions"]) for x in rows),
        "trials_with_issuer_filing_leads": sum(x["issuer_sec_filing_leads"] > 0 for x in rows),
        "trials_with_issuer_primary_document_sources": sum(x["issuer_sec_primary_documents_retrieved"] > 0 for x in rows),
        "trials_with_exact_registered_term_sec_lexical_leads": sum(bool(x["exact_registry_term_sec_text_leads"]) for x in rows),
        "trials_requiring_rights_verification": TOTAL,
        "verified_current_commercial_rights": 0,
        "qualified_pipeline_total": None,
        "items": rows,
        "limitations": (
            "Registered drugs and conditions are unadjudicated labels. SEC issuer filings "
            "are company-level leads, not proof for the trial's drug/indication, license, "
            "US territory, effective dates or FDA application. Unavailable documents are "
            "not negative evidence. No automatic Pipeline/GEM JR/GEM/FS/FA changes."
        ),
    }


def main():
    if len(sys.argv) != 6:
        sys.exit("Usage: phase3_sec_trial_rights_join.py <program.json> <casebook.json> <filings.json> <pilot.json> <output.json>")
    data = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:5]]
    report = build_join(*data)
    destination = Path(sys.argv[5])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Rights join: {report['total_trials']}/741 trials, {report['total_issuers']}/130 issuers; "
          f"registered drugs {report['trials_with_registry_provisional_drugs']}/741; "
          f"issuer documents fetched for {report['trials_with_issuer_primary_document_sources']}/741; "
          f"verified rights {report['verified_current_commercial_rights']}/741")


if __name__ == "__main__":
    main()
