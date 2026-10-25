"""Traceable published results for the KEYNOTE-024 historical Phase 3 pilot.

This is a fixed, read-only extraction from cited scientific publications.
Numbers are attributed to their own analyses; they are NOT recalculated
from patient-level data or eligible for automatic domain scoring.

References were checked against PubMed abstracts, a peer-reviewed
five-year update, NCI summary and an FDA-authored approval summary.
"""
from __future__ import annotations

from copy import deepcopy
from .scientific_pilot_keynote024 import keynote024_pilot_manifest

_SOURCE_URLS = {
    "initial": "https://pubmed.ncbi.nlm.nih.gov/27718847/",
    "five_year": "https://pubmed.ncbi.nlm.nih.gov/33872070/",
    "quality_of_life": "https://pubmed.ncbi.nlm.nih.gov/29129441/",
    "fda_summary": "https://academic.oup.com/oncolo/article/22/11/1392/6444702",
    "nci_safety": "https://www.cancer.gov/types/lung/research/pembrolizumab-nsclc-keynote-024",
}

_REPORTS = (
    {
        "analysis_id": "keynote024_initial_2016",
        "report_type": "original_randomized_trial_interim_analysis",
        "publication_date": "2016-10-08",
        "data_cutoff_date": "2016-05-09",
        "source_id": "27718847",
        "source_url": _SOURCE_URLS["initial"],
        "nct_id": "NCT02142738",
        "arm_counts_randomized": {"pembrolizumab": 154, "chemotherapy": 151},
        "primary_endpoint": "progression_free_survival",
        "endpoint_assessment": "blinded_independent_central_radiology",
        "effects": {
            "progression_free_survival": {
                "metric": "median_months",
                "pembrolizumab": 10.3,
                "chemotherapy": 6.0,
                "hazard_ratio": 0.50,
                "hazard_ratio_95pct_ci": [0.37, 0.68],
                "p_value": "<0.001",
                "analysis_role": "prespecified_primary",
                "result_status": "published_statistical_result",
            },
            "overall_survival": {
                "metric": "hazard_ratio",
                "hazard_ratio": 0.60,
                "hazard_ratio_95pct_ci": [0.41, 0.89],
                "p_value": "0.005",
                "survival_at_6_months_percent": {
                    "pembrolizumab": 80.2, "chemotherapy": 72.4,
                },
                "analysis_role": "secondary_interim",
                "result_status": "published_statistical_result",
            },
            "objective_response_rate": {
                "metric": "percent",
                "pembrolizumab": 44.8,
                "chemotherapy": 27.8,
                "analysis_role": "secondary",
                "result_status": "published_statistical_result",
            },
        },
        "safety": {
            "treatment_related_adverse_events_any_grade_percent": {
                "pembrolizumab": 73.4, "chemotherapy": 90.0,
            },
            "treatment_related_adverse_events_grade_3_to_5_percent": {
                "pembrolizumab": 26.6, "chemotherapy": 53.3,
            },
            "denominator_note": "Safety percentages are treatment-related AE frequencies reported by the original publication; not all-cause adverse events.",
        },
        "methodological_caveats": [
            "Open-label treatment assignment; PFS used blinded independent central assessment.",
            "Eligible patients had PD-L1 tumor proportion score >=50% and no sensitizing EGFR/ALK alterations.",
            "Chemotherapy-to-pembrolizumab crossover after disease progression permitted.",
            "Interim OS hazard ratio must not be paired with later final/long-term median OS as if one analysis.",
            "Sponsor funded the trial; independent critical appraisal and protocol/SAP review remain pending.",
        ],
        "source_evidence_status": "published_reported_not_independently_reanalyzed",
    },
    {
        "analysis_id": "keynote024_pros_2017",
        "report_type": "prespecified_exploratory_patient_reported_outcomes",
        "publication_date": "2017-11-09",
        "source_id": "29129441",
        "source_url": _SOURCE_URLS["quality_of_life"],
        "nct_id": "NCT02142738",
        "outcomes": {
            "quality_of_life_week15_change": {
                "pembrolizumab": 6.9,
                "chemotherapy": -0.9,
                "between_group_difference": 7.8,
                "difference_95pct_ci": [2.9, 12.8],
                "nominal_p_value": "0.0020",
                "measure": "EORTC QLQ-C30 global health status / quality-of-life",
                "analysis_role": "prespecified_exploratory",
            },
        },
        "methodological_caveats": [
            "Patient-reported outcome analysis is exploratory; P-values are nominal.",
            "Open-label design can introduce reporting bias in subjective endpoints.",
            "Quality-of-life change analysis excluded participants lacking sufficient completed instruments.",
        ],
        "source_evidence_status": "published_reported_not_independently_reanalyzed",
    },
    {
        "analysis_id": "keynote024_five_year_2021",
        "report_type": "long_term_followup",
        "publication_date": "2021-04-19",
        "data_cutoff_date": "2020-06-01",
        "source_id": "33872070",
        "source_url": _SOURCE_URLS["five_year"],
        "nct_id": "NCT02142738",
        "effects": {
            "overall_survival": {
                "metric": "median_months",
                "pembrolizumab": 26.3,
                "chemotherapy": 13.4,
                "hazard_ratio": 0.62,
                "hazard_ratio_95pct_ci": [0.48, 0.81],
                "five_year_kaplan_meier_survival_percent": {
                    "pembrolizumab": 31.9,
                    "chemotherapy": 16.3,
                },
                "analysis_role": "long_term_secondary_endpoint",
                "result_status": "published_statistical_result",
            },
        },
        "effective_crossover_percent_from_chemotherapy": 66.0,
        "effective_crossover_definition": "Subsequent anti-PD-1/PD-L1 therapy among chemotherapy-assigned patients.",
        "methodological_caveats": [
            "66% effective crossover complicates interpretation of the intention-to-treat OS contrast.",
            "Five-year survival percentages are Kaplan-Meier estimates, not uncensored raw proportions.",
            "Later follow-up estimate must not replace the original prespecified primary-endpoint analysis.",
        ],
        "source_evidence_status": "published_reported_not_independently_reanalyzed",
    },
)

_CORROBORATION = (
    {
        "source_url": _SOURCE_URLS["fda_summary"],
        "source_type": "fda_staff_authored_approval_summary",
        "supported_observation": "Original PFS HR 0.50 (95% CI 0.37–0.68), and interim OS HR 0.60 (95% CI 0.41–0.89); interim OS alpha threshold 0.0118.",
        "scope_note": "Regulatory history for an already-approved drug, not a prospective FDA-approval forecast.",
    },
    {
        "source_url": _SOURCE_URLS["nci_safety"],
        "source_type": "national_cancer_institute_scientific_summary",
        "supported_observation": "NCI reports immune-mediated adverse events of 29.2% versus 4.7%; this is a distinct safety category, not the total grade 3–5 TRAE frequency.",
        "scope_note": "Secondary institutional explanation; verify against original trial safety tables before merging safety categories.",
    },
)


def keynote024_published_results() -> dict:
    """Return independently scoped analysis snapshots, never a combined estimate."""
    pilot = keynote024_pilot_manifest()
    return deepcopy({
        "nct_id": pilot["nct_id"],
        "trial_name": pilot["trial_name"],
        "randomized_population": 305,
        "analysis_snapshots": list(_REPORTS),
        "corroborating_sources": list(_CORROBORATION),
        "scientific_review_status": "source_reported_requires_independent_appraisal",
        "unresolved_tasks": [
            "Verify full protocol and statistical-analysis plan against all interim boundaries.",
            "Compare registry adverse-event tables with peer-reviewed safety populations.",
            "Confirm source data and dates of subsequent regulatory submissions.",
            "Evaluate PD-L1 population selection, crossover, missingness and external validity.",
        ],
        "domain_scores": {name: None for name in pilot["domains"]},
        "overall_score": None,
        "fda_approval_probability": None,
        "read_only": True,
        "trading_actions_enabled": False,
    })
