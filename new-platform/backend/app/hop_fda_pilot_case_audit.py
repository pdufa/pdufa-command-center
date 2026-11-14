"""Read-only audit of one *research-stage* original FDA action-letter dossier.

This validates the structural and temporal claims of a documented pilot. It
does not authenticate the original PDF bytes, independently adjudicate FDA
regulatory outcomes, build a representative denominator, or train a model.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

PILOT_STATUS = "PRIMARY_DOCUMENT_PILOT_RESEARCH_NOT_INDEPENDENT_ADJUDICATION"
_REQUIRED_SUPPLEMENTS = {"S-8", "S-12"}
_REQUIRED_FALSE = (
    "reviewer_one_identity_verified",
    "reviewer_two_identity_verified",
    "independent_document_page_adjudication_complete",
    "exact_application_supplement_action_adjudicated",
    "source_original_pdf_digest_verified",
    "complete_fda_approval_and_nonapproval_cohort_verified",
    "model_calibration_validated",
    "trading_signal_allowed",
)
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_REFERENCE = re.compile(r"[1-9][0-9]{4,9}\Z")


def _valid_date(value: object) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("Expected canonical calendar date")
    return date.fromisoformat(value)


def _url(url: object, host: str, prefix: str) -> bool:
    if not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        return (parsed.scheme == "https" and parsed.hostname == host
                and parsed.path.startswith(prefix) and bool(parsed.path.strip("/"))
                and parsed.username is None and parsed.password is None
                and parsed.port is None and not parsed.query and not parsed.fragment)
    except (TypeError, ValueError):
        return False


def load_pilot_dossier(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Pilot source dossier must be a JSON object")
    return data


def audit_pilot_dossier(dossier: dict) -> dict:
    if (not isinstance(dossier, dict) or dossier.get("schema_version") != 1
            or dossier.get("status") != PILOT_STATUS
            or dossier.get("case_key") != "HOP_RESEARCH_BLA125514_S12_KEYNOTE024_20161024"):
        raise ValueError("Unknown/unreviewed pilot case contract")
    doc = dossier.get("document")
    if (not isinstance(doc, dict)
            or doc.get("agency") != "FDA"
            or doc.get("primary_application") != "BLA125514"
            or doc.get("reference_id") != "4003165"
            or doc.get("source_pdf_sha256") is not None
            or doc.get("primary_document_page_count") != 6
            or doc.get("inspected_page_numbers_1_based") != [1, 3, 6]
            or doc.get("actual_public_web_release_date") is not None
            or doc.get("pdufa_target_date") is not None
            or doc.get("independent_reviewer_attestation") is not None
            or doc.get("signed_source_date_not_pdufa_target") is not True
            or not _url(doc.get("official_fda_approval_letter_url"),
                        "www.accessdata.fda.gov", "/drugsatfda_docs/appletter/2016/")):
        raise ValueError("FDA original letter identity or verification limitations modified")
    if ("/125514Orig1s008,125514Orig1s012ltr.pdf"
            not in doc["official_fda_approval_letter_url"]):
        raise ValueError("Source URL is not the original combined S-8/S-12 letter")
    decision = _valid_date(doc.get("electronic_signature_date"))
    if decision != date(2016, 10, 24):
        raise ValueError("Unexpected original FDA letter signature date")

    supplements = dossier.get("supplements")
    if (not isinstance(supplements, list) or len(supplements) != 2
            or {s.get("supplement") for s in supplements if isinstance(s, dict)}
               != _REQUIRED_SUPPLEMENTS):
        raise ValueError("Original FDA letter must preserve two distinct supplements")
    keyed = {}
    for row in supplements:
        if (not isinstance(row, dict) or row.get("application_id") != "BLA125514"
                or row.get("source_claim_action") != "APPROVED"
                or _valid_date(row.get("source_claim_action_date")) != decision
                or row.get("same_letter_document") is not True
                or row.get("independently_adjudicated") is not False):
            raise ValueError("A supplement claim was promoted or altered")
        keyed[row["supplement"]] = row
    if (keyed["S-8"].get("key_trial") != "KEYNOTE-010"
            or keyed["S-12"].get("key_trial") != "KEYNOTE-024"
            or keyed["S-12"].get("nct_id") != "NCT02142738"):
        raise ValueError("Distinct supplement-trial mapping was altered")

    trial = dossier.get("trial_predecision_publication_candidate")
    if (not isinstance(trial, dict) or trial.get("nct_id") != "NCT02142738"
            or trial.get("trial") != "KEYNOTE-024"
            or trial.get("peer_review_article_doi") != "10.1056/NEJMoa1606774"
            or not _url(trial.get("pubmed_url"), "pubmed.ncbi.nlm.nih.gov",
                        "/27718847/")
            or trial.get("first_public_snapshot_independently_archived") is not False
            or trial.get("point_in_time_feature_set_complete") is not False
            or trial.get("after_decision_issue_date_must_not_be_used_as_predecision_publication_date") is not True):
        raise ValueError("Trial publication attribution or predecision controls changed")
    first_public = _valid_date(trial.get("ahead_of_print_date"))
    issue = _valid_date(trial.get("issue_date"))
    if not (first_public == date(2016, 10, 8) < decision
            < issue == date(2016, 11, 10)):
        raise ValueError("Historical source temporal ordering is unsafe")

    provenance = dossier.get("additional_provenance")
    if (not isinstance(provenance, dict)
            or set(provenance) != {
                "postmarketing_commitment_keynote024_on_original_letter_page_3",
                "keynote042_is_separate_trial_not_s12_training_evidence",
                "simultaneous_supplement_actions_must_not_be_collapsed_into_one_original_bla_decision",
                "all_secondary_postdecision_reviews_excluded_from_predecision_features",
            } or any(value is not True for value in provenance.values())):
        raise ValueError("Exact-trial attribution or leakage guard missing")

    gates = dossier.get("review_and_model_gates")
    if (not isinstance(gates, dict)
            or any(gates.get(k) is not False for k in _REQUIRED_FALSE)
            or any(type(gates.get(k)) is not int or gates[k] != 0
                   for k in ("model_eligible_records",
                             "independently_verified_review_cycle_outcomes"))
            or gates.get("approval_rate") is not None
            or gates.get("predicted_probability") is not None):
        raise ValueError("Pilot case cannot self-certify model or evidence readiness")
    return {
        "status": "DIRECT_FDA_PRIMARY_RESEARCH_ONLY_REVIEW_REQUIRED",
        "original_fda_pdf_references": 1,
        "distinct_supplement_claims_in_same_letter": 2,
        "separately_attributed_supplements": ["S-8", "S-12"],
        "keynote024_predecision_publication_candidate": True,
        "journal_issue_after_fda_action": True,
        "original_fda_pdf_bytes_verified": False,
        "independent_human_review_complete": False,
        "independently_verified_fda_outcome_labels": 0,
        "complete_approval_nonapproval_denominator_verified": False,
        "model_eligible_records": 0,
        "probability": None,
        "approval_rate": None,
        "readiness": "REVIEW_REQUIRED",
        "note": "Direct original-letter observations are research leads, not a cleared FDA outcome cohort.",
    }
