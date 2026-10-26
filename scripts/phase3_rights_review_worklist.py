#!/usr/bin/env python3
"""Build a research-only per-NCT commercial-rights review worklist.

A verified registry record, ticker CIK match, SEC filing index, or lexical
document match does NOT prove a product's current U.S. commercial rights.
This tool reconciles all existing sources, prioritizes manual work, and
does not change Pipeline/GEM eligibility or FS/FA presets.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.phase3_sec_rights_documents_pilot import validate_leads
from scripts.phase3_qualification_ledger import GATES

TOTAL = 741
ISSUERS = 130
NCT = re.compile(r"^NCT[0-9]{8}$")
SHA = re.compile(r"^[a-fA-F0-9]{64}$")
SOURCE = "https://clinicaltrials.gov/api/v2/studies/"
ACTIVE_REGISTRY_STATUSES = {
    "RECRUITING", "ACTIVE_NOT_RECRUITING",
    "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING",
}
HISTORICAL_REGISTRY_STATUSES = {
    "COMPLETED", "TERMINATED", "WITHDRAWN",
}
REQUIRED_REVIEW = (
    "VERIFY_CURRENT_ISSUER_AND_LEGAL_ENTITY_CHAIN",
    "MATCH_ACTUAL_DRUG_AND_INDICATION_TO_PRIMARY_DISCLOSURE",
    "VERIFY_CURRENT_US_TERRITORIAL_DEVELOPMENT_OR_COMMERCIAL_RIGHTS",
    "VERIFY_EFFECTIVE_EXPIRATION_TERMINATION_AND_TRANSFER_DATES",
    "REVIEW_EXCLUSIVITY_SUBLICENSE_AND_COUNTERPARTY_LIMITATIONS",
    "INDEPENDENTLY_REVIEW_AND_DATE_ORIGINAL_SOURCE_DOCUMENT",
)


def indexed_rows(rows, label):
    if not isinstance(rows, list) or len(rows) != TOTAL:
        raise ValueError(f"Expected 741 complete {label} rows")
    result = {}
    for record in rows:
        if not isinstance(record, dict):
            raise ValueError(f"Malformed {label} record")
        nct = record.get("nct_id")
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in result:
            raise ValueError(f"Duplicate/malformed {label} NCT identity")
        result[nct] = record
    return result


def registry_priority(source):
    status = source.get("current_registry_status")
    if not isinstance(status, str) or not status.strip() or len(status) > 80:
        raise ValueError("Exact registry record lacks bounded study status")
    phase3 = source.get("phase3_in_current_registry")
    if type(phase3) is not bool:
        raise ValueError("Exact registry Phase 3 flag is not boolean")
    if source.get("status_matches_dated_census") not in (True, False):
        raise ValueError("Exact registry status comparison is invalid")
    if status in ACTIVE_REGISTRY_STATUSES and phase3 and source["status_matches_dated_census"]:
        return "P1_CURRENTLY_ACTIVE_REGISTRY_ONLY", 0
    if status in HISTORICAL_REGISTRY_STATUSES and source["status_matches_dated_census"]:
        return "P3_HISTORICAL_OR_ENDED_REGISTRY_ONLY", 2
    return "P2_REGISTRY_STATUS_OR_PHASE_REVIEW", 1


def build_worklist(registry, ledger, casebook, leads, trial_join):
    issuer_index, sec_by_ticker = validate_leads(casebook, leads)
    if (registry.get("census_total") != TOTAL
        or registry.get("source_identity_verified") != TOTAL
        or registry.get("source_errors") != []
        or registry.get("qualified_pipeline_total") is not None
        or ledger.get("report_type") != "MAIN_PHASE3_QUALIFICATION_EVIDENCE_LEDGER_RESEARCH_ONLY"
        or ledger.get("total") != TOTAL
        or ledger.get("qualified_pipeline_total") is not None
        or trial_join.get("report_type") != "MAIN_PHASE3_TRIAL_DRUG_SEC_RIGHTS_JOIN_RESEARCH_ONLY"
        or trial_join.get("total_trials") != TOTAL
        or trial_join.get("total_issuers") != ISSUERS
        or trial_join.get("verified_current_commercial_rights") != 0
        or trial_join.get("qualified_pipeline_total") is not None):
        raise ValueError("Inputs must be complete unqualified original research")
    originals = indexed_rows(registry.get("original_source_records"), "registry")
    gates = indexed_rows(ledger.get("records"), "qualification ledger")
    joined = indexed_rows(trial_join.get("items"), "trial-to-SEC join")
    cases = indexed_rows(casebook.get("items"), "rights casebook")
    if not set(originals) == set(gates) == set(joined) == set(cases):
        raise ValueError("Exact registry and SEC research NCT sets differ")
    studies = []
    for nct in originals:
        source, gate_row, joined_row, case = (originals[nct], gates[nct],
                                             joined[nct], cases[nct])
        ticker, company, cik = (gate_row.get("ticker"), gate_row.get("company"),
                                case.get("saved_sec_cik"))
        if (not isinstance(ticker, str) or ticker not in issuer_index
            or ticker != joined_row.get("ticker") or ticker != case.get("ticker")
            or company != case.get("saved_census_company")
            or source.get("census_ticker") != ticker
            or source.get("census_company") != company
            or source.get("source") != SOURCE + nct
            or joined_row.get("original_registry_url") != SOURCE + nct
            or gate_row.get("source_url") != f"https://clinicaltrials.gov/study/{nct}"
            or case.get("original_registry_api_url") != SOURCE + nct
            or not isinstance(source.get("source_sha256"), str)
            or not SHA.fullmatch(source["source_sha256"])
            or not (source["source_sha256"] == gate_row.get("source_sha256")
                    == case.get("original_registry_sha256")
                    == joined_row.get("original_registry_sha256"))
            or cik != issuer_index[ticker]["cik"]
            or cik != joined_row.get("saved_sec_cik")
            or case.get("rights_verification_status") != "NOT_ESTABLISHED"
            or joined_row.get("current_rights_verified") is not False
            or joined_row.get("qualified_pipeline") is not None
            or gate_row.get("qualified_pipeline") is not None):
            raise ValueError(f"{nct}: source / issuer association or rights boundary violated")
        recorded_gates = gate_row.get("gates")
        if (not isinstance(recorded_gates, dict)
            or set(recorded_gates) != set(GATES)
            or recorded_gates["registry_identity"] != "PASS"
            or recorded_gates["current_commercial_rights"] != "REVIEW"
            or gate_row.get("qualification_status") != "REVIEW"):
            raise ValueError(f"{nct}: no gate/rights promotion is permitted")
        provisional_drugs = joined_row.get("provisional_drug_or_biologic_names")
        conditions = joined_row.get("registered_conditions")
        if (not isinstance(provisional_drugs, list)
            or not all(isinstance(x, str) and x.strip() for x in provisional_drugs)
            or not isinstance(conditions, list)
            or not all(isinstance(x, str) and x.strip() for x in conditions)):
            raise ValueError(f"{nct}: missing original trial program context")
        sec = sec_by_ticker[ticker]
        filing_refs = sec["candidate_filings"]
        if joined_row.get("issuer_sec_filing_leads") != len(filing_refs):
            raise ValueError(f"{nct}: issuer filing lead count mismatch")
        permitted_documents = {f["primary_document_url"] for f in filing_refs}
        fetched = joined_row.get("issuer_primary_document_sources")
        matches = joined_row.get("exact_registry_term_sec_text_leads")
        if not isinstance(fetched, list) or not isinstance(matches, list):
            raise ValueError(f"{nct}: original SEC document lead records missing")
        fetched_urls = set()
        for doc in fetched:
            if (not isinstance(doc, dict)
                or doc.get("url") not in permitted_documents
                or doc["url"] in fetched_urls
                or not isinstance(doc.get("sha256"), str)
                or not SHA.fullmatch(doc["sha256"])
                or doc.get("scope") != "ISSUER_DOCUMENT_ONLY_NOT_TRIAL_RIGHTS"):
                raise ValueError(f"{nct}: SEC fetched document is ungrounded")
            fetched_urls.add(doc["url"])
        if joined_row.get("issuer_sec_primary_documents_retrieved") != len(fetched_urls):
            raise ValueError(f"{nct}: inconsistent source document count")
        for match in matches:
            if (not isinstance(match, dict) or match.get("source_url") not in fetched_urls
                or match.get("review_status") != "LEXICAL_ONLY_NOT_VERIFIED_LEGAL_RIGHTS"
                or match.get("registered_term") not in provisional_drugs + conditions
                or not isinstance(match.get("source_sha256"), str)
                or not SHA.fullmatch(match["source_sha256"])
                or not any(doc["url"] == match["source_url"]
                           and doc["sha256"] == match["source_sha256"]
                           for doc in fetched)):
                raise ValueError(f"{nct}: invalid trial-level lexical document evidence")
        priority, order = registry_priority(source)
        if matches:
            source_stage = "SOURCE_TEXT_TERM_LEADS_FOR_MANUAL_CHECK"
        elif fetched:
            source_stage = "SOURCE_TEXT_AVAILABLE_NO_EXACT_TERM_LEAD"
        elif sec["retrieval_status"] == "FILING_METADATA_LEADS":
            source_stage = "SEC_PRIMARY_DOCUMENT_NOT_YET_AVAILABLE"
        else:
            source_stage = "SEC_FILING_METADATA_UNAVAILABLE_OR_NO_LEADS"
        studies.append({
            "nct_id": nct, "ticker": ticker, "census_company": company,
            "issuer_sec_cik": cik, "registry_status": source["current_registry_status"],
            "registry_phase3_current": source["phase3_in_current_registry"],
            "registry_source_url": SOURCE + nct,
            "registry_source_sha256": source["source_sha256"],
            "source_fetched_at_utc": source.get("fetched_at_utc"),
            "registered_provisional_drugs": provisional_drugs,
            "registered_conditions": conditions,
            "sec_issuer_submissions_url": sec["sec_submissions_url"],
            "sec_issuer_filing_candidates": [
                {"form": x["form"], "filed_date": x["filed_date"],
                 "url": x["primary_document_url"]}
                for x in filing_refs
            ],
            "sec_source_documents_fetched": fetched,
            "exact_lexical_term_source_leads": matches,
            "research_priority": priority,
            "source_review_stage": source_stage,
            "rights_review_checklist": {item: "NOT_VERIFIED" for item in REQUIRED_REVIEW},
            "commercial_rights_verified": False,
            "qualified_pipeline": None,
            "note": ("Filing candidates, sponsor names, and lexical drug mentions "
                     "are research leads only; no independent rights adjudication."),
            "_sort_order": order,
        })
    studies.sort(key=lambda r: (r["_sort_order"],
                                -bool(r["exact_lexical_term_source_leads"]),
                                -bool(r["sec_source_documents_fetched"]),
                                r["ticker"], r["nct_id"]))
    for rank, row in enumerate(studies, start=1):
        del row["_sort_order"]
        row["research_review_queue_position"] = rank
    priority_counts = Counter(r["research_priority"] for r in studies)
    stage_counts = Counter(r["source_review_stage"] for r in studies)
    return {
        "report_type": "MAIN_PHASE3_COMMERCIAL_RIGHTS_REVIEW_WORKLIST_RESEARCH_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_trials": TOTAL, "total_issuer_research_pointers": ISSUERS,
        "priority_counts": dict(priority_counts),
        "source_review_stage_counts": dict(stage_counts),
        "trials_with_any_original_provisional_drug": sum(
            bool(r["registered_provisional_drugs"]) for r in studies),
        "trials_with_issuer_primary_document_text": sum(
            bool(r["sec_source_documents_fetched"]) for r in studies),
        "trials_with_trial_exact_term_lexical_lead": sum(
            bool(r["exact_lexical_term_source_leads"]) for r in studies),
        "rights_checks_required_per_trial": len(REQUIRED_REVIEW),
        "independently_verified_current_rights": 0,
        "qualified_pipeline_total": None,
        "items": studies,
        "limitations": (
            "Research priority is NOT scientific or trading rank. Registry status "
            "does not independently prove active development. Filing metadata and "
            "text leads do not establish rights, territory, time validity or FDA "
            "PDUFA. Missing documents do not prove no rights. No Pipeline/GEM/FS/FA "
            "promotion or automatic qualification."
        ),
    }


def main():
    if len(sys.argv) != 7:
        sys.exit("Usage: phase3_rights_review_worklist.py <registry> <ledger> <casebook> <sec-leads> <trial-join> <output>")
    inputs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:6]]
    report = build_worklist(*inputs)
    output = Path(sys.argv[6])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Commercial-rights review worklist: {report['total_trials']}/741 trial identities; "
        f"{report['total_issuer_research_pointers']}/130 SEC issuer pointers; "
        f"{report['trials_with_issuer_primary_document_text']}/741 with fetched issuer documents; "
        f"verified current rights {report['independently_verified_current_rights']}/741; "
        "Pipeline qualified UNKNOWN"
    )


if __name__ == "__main__":
    main()
