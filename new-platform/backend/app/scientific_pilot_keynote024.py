"""Evidence-linked, conservative pilot manifest for a completed Phase 3 study.

This is a curated starting-point for human review, not a scientific score.
No network or database operations occur when importing this module.
"""
from __future__ import annotations

from copy import deepcopy

PILOT_NCT_ID = "NCT02142738"

_PILOT = {
    "pilot_version": "keynote024-phase3-v1",
    "nct_id": PILOT_NCT_ID,
    "trial_name": "KEYNOTE-024",
    "phase": "PHASE3",
    "program": "Pembrolizumab versus platinum-based chemotherapy",
    "condition": "Previously untreated metastatic non-small-cell lung cancer with PD-L1 high expression",
    "registry": "https://clinicaltrials.gov/study/NCT02142738",
    "registry_source_status": "registry_reported",
    "study_status": "COMPLETED",
    "enrollment": 305,
    "design": "Randomized, open-label, comparator-controlled Phase III",
    "primary_hypothesis": "Progression-free survival improvement",
    "source_references": [
        {
            "source_kind": "clinicaltrials",
            "source_id": PILOT_NCT_ID,
            "source_url": "https://clinicaltrials.gov/study/NCT02142738",
            "relationship": "exact_registry_record",
            "review_status": "registry_identity_confirmed",
        },
        {
            "source_kind": "pubmed",
            "source_id": "27718847",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/27718847/",
            "relationship": "publication_listed_in_registry_study_results",
            "review_status": "bibliographic_link_confirmed",
            "note": "Original KEYNOTE-024 efficacy publication; full statistical extraction pending.",
        },
        {
            "source_kind": "pubmed",
            "source_id": "29129441",
            "source_url": "https://pubmed.ncbi.nlm.nih.gov/29129441/",
            "relationship": "publication_listed_in_registry_pubmed_section",
            "review_status": "bibliographic_link_confirmed",
            "note": "Health-related quality-of-life results; independent appraisal pending.",
        },
    ],
    "domains": {
        "disease_biology": {"status": "pending_review"},
        "mechanism_of_action": {"status": "pending_review"},
        "preclinical_evidence": {"status": "pending_review"},
        "clinical_design": {"status": "registry_metadata_available"},
        "clinical_results": {"status": "publications_identified_unadjudicated"},
        "competitive_landscape": {"status": "pending_review"},
        "regulatory_analysis": {"status": "pending_review"},
        "advanced_inference": {"status": "pending_review"},
    },
    "required_next_checks": [
        "Read original trial publication and extract effect size, confidence intervals and endpoint definitions.",
        "Check prespecified statistical analysis plan, amendments, and multiplicity controls.",
        "Compare registry adverse-event tables with peer-reviewed adverse-event reporting.",
        "Check baseline subgroup balance, crossover and generalizability.",
        "Confirm FDA label/application history separately; do not infer from publication.",
        "Document uncertainties and contradictory evidence before scoring.",
    ],
    "assessment_status": "pilot_evidence_inventory_only",
    "overall_score": None,
    "fda_approval_probability": None,
    "live_system_writes": False,
}


def keynote024_pilot_manifest() -> dict:
    """Return an isolated copy of the reference manifest."""
    return deepcopy(_PILOT)
