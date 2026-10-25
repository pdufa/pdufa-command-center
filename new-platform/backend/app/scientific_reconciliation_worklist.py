"""Conservative, source-attributed independent review worksheet.

This is a bounded, READ-ONLY worklist of concrete reconciliation questions,
not a scored scientific conclusion. No record is marked scientifically verified
and no automatic PDUFA, efficacy, or safety determination is made.
"""
from __future__ import annotations

from copy import deepcopy

from .scientific_investigation_20 import NCT_PATTERN
from .scientific_readiness_grades import EXTERNAL_GATES

REGISTRY = "https://clinicaltrials.gov/study/NCT02142738"
PROTOCOL_SAP = "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf"
GERMAN_REGULATOR_CSR = "https://portal.dimdi.de/data/ctr/O-2145_01-2-0-CE336C-20220110151635.pdf"
FDA_2016_APPROVAL = (
    "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/"
    "2016/125514Orig1s008,125514Orig1s012ltr.pdf"
)
ORIGINAL_TRIAL = "https://pubmed.ncbi.nlm.nih.gov/27718847/"
FOLLOWUP_5YEAR = "https://pubmed.ncbi.nlm.nih.gov/33872070/"
QUALITY_OF_LIFE = "https://pubmed.ncbi.nlm.nih.gov/29129441/"
NCI_SAFETY = "https://www.cancer.gov/types/lung/research/pembrolizumab-nsclc-keynote-024"

_PILOT_CHECKS = (
    {
        "id": "protocol_amendment_chronology",
        "gateId": "protocol_sap",
        "title": "Reconcile protocol/SAP version and statistical lock",
        "priority": "critical",
        "observedDiscrepancy": (
            "The ClinicalTrials.gov-hosted protocol/SAP was posted in 2017, "
            "after the original interim analysis and 2016 FDA action."
        ),
        "question": (
            "Which protocol version, endpoint hierarchy, alpha spending and "
            "censoring rules were prospectively locked for the May 2016 cutoff?"
        ),
        "nextAction": (
            "Inspect dated amendment history, version signatures, and the "
            "prospective SAP; compare primary and interim endpoint definitions."
        ),
        "sourceUrls": [REGISTRY, PROTOCOL_SAP, GERMAN_REGULATOR_CSR, ORIGINAL_TRIAL],
    },
    {
        "id": "baseline_population_indication",
        "gateId": "published_results",
        "title": "Match original randomized population to the FDA indication",
        "priority": "high",
        "observedDiscrepancy": None,
        "question": (
            "Do PD-L1 TPS >=50%, prior therapy restrictions and EGFR/ALK "
            "exclusions match the original analysis set and the S-12 label?"
        ),
        "nextAction": (
            "Compare the trial enrollment and analysis populations with "
            "FDA first-line indication wording without merging other NSCLC uses."
        ),
        "sourceUrls": [REGISTRY, ORIGINAL_TRIAL, FDA_2016_APPROVAL],
    },
    {
        "id": "pfs_initial_vs_followup",
        "gateId": "published_results",
        "title": "Keep original PFS and later OS analyses separate",
        "priority": "critical",
        "observedDiscrepancy": (
            "The original 2016 primary PFS analysis and 2021 five-year OS "
            "update use different follow-up windows, outcomes, and cutoffs."
        ),
        "question": (
            "Which reported estimates and CIs correspond to the prospectively "
            "declared primary endpoint, which to interim OS, and which to updated OS?"
        ),
        "nextAction": (
            "Build an analysis-level table by endpoint, cutoff, population, "
            "statistical method, estimate, CI, p-value, and multiplicity boundary."
        ),
        "sourceUrls": [ORIGINAL_TRIAL, FOLLOWUP_5YEAR, PROTOCOL_SAP, GERMAN_REGULATOR_CSR],
    },
    {
        "id": "crossover_adjustment",
        "gateId": "published_results",
        "title": "Evaluate crossover effects on long-term survival",
        "priority": "high",
        "observedDiscrepancy": (
            "Long-term follow-up reports substantial subsequent immunotherapy "
            "among chemotherapy-assigned participants."
        ),
        "question": (
            "How does crossover influence intention-to-treat OS and any "
            "hypothetical crossover-adjusted estimands?"
        ),
        "nextAction": (
            "Record crossover rules and proportions, treatment switching "
            "assumptions and prespecified versus exploratory analyses."
        ),
        "sourceUrls": [ORIGINAL_TRIAL, FOLLOWUP_5YEAR, PROTOCOL_SAP],
    },
    {
        "id": "safety_endpoint_taxonomy",
        "gateId": "published_results",
        "title": "Avoid combining non-comparable adverse-event categories",
        "priority": "critical",
        "observedDiscrepancy": (
            "Treatment-related grade 3–5 events and immune-mediated events "
            "are distinct adverse-event classes with different numerators."
        ),
        "question": (
            "Do event attribution, grades, risk denominators and duration "
            "of exposure match across registry, publication and NCI summary?"
        ),
        "nextAction": (
            "Separate all-cause AEs, treatment-related AEs, immune-mediated "
            "AEs, serious AEs, exposure and grade-specific denominators."
        ),
        "sourceUrls": [REGISTRY, ORIGINAL_TRIAL, NCI_SAFETY],
    },
    {
        "id": "exploratory_qol_multiplicity",
        "gateId": "published_results",
        "title": "Distinguish exploratory quality-of-life p-values",
        "priority": "medium",
        "observedDiscrepancy": None,
        "question": (
            "Were patient-reported outcome comparisons multiplicity controlled "
            "or nominal, and how was missing questionnaire data handled?"
        ),
        "nextAction": (
            "Label all exploratory estimates and missingness/selection bias "
            "separately from the prespecified primary clinical endpoint."
        ),
        "sourceUrls": [QUALITY_OF_LIFE, PROTOCOL_SAP],
    },
    {
        "id": "2015_vs_2016_fda_actions",
        "gateId": "official_regulatory",
        "title": "Do not confuse 2015 and 2016 FDA NSCLC actions",
        "priority": "critical",
        "observedDiscrepancy": (
            "The FDA letter covers both S-8 modifications of a previously "
            "treated indication and S-12 first-line high-PD-L1 expansion."
        ),
        "question": (
            "Was the relevant first-line PD-L1-high indication approved "
            "under S-12 on October 24, 2016, versus the earlier treated setting?"
        ),
        "nextAction": (
            "Audit the FDA letter, label language, BLA/supplement numbers and "
            "historical decision date separately from future PDUFA events."
        ),
        "sourceUrls": [FDA_2016_APPROVAL, REGISTRY],
    },
    {
        "id": "independent_corroboration",
        "gateId": "independent_replication",
        "title": "Separate external corroboration from independent replication",
        "priority": "high",
        "observedDiscrepancy": None,
        "question": (
            "Which sources independently replicate an effect in a distinct "
            "cohort, as opposed to summarizing the same KEYNOTE-024 data?"
        ),
        "nextAction": (
            "Seek independent trials, benchmark comparator evidence and "
            "contradictory findings; mark institutional summaries as context."
        ),
        "sourceUrls": [ORIGINAL_TRIAL, NCI_SAFETY],
    },
)


def reconciliation_worklist(nct_id: str) -> dict:
    """Never marks any external evidence gate verified."""
    if not isinstance(nct_id, str) or not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    if nct_id == "NCT02142738":
        checks = deepcopy(list(_PILOT_CHECKS))
    else:
        checks = [
            {
                "id": "external_" + gate_id,
                "gateId": gate_id,
                "title": label,
                "priority": "high",
                "observedDiscrepancy": None,
                "question": "What independent evidence establishes this requirement?",
                "nextAction": action,
                "sourceUrls": [],
            }
            for gate_id, label, action in EXTERNAL_GATES
        ]
    for item in checks:
        item["status"] = "open_unadjudicated"
        item["independentlyVerified"] = False
        item["scientificScore"] = None
    return {
        "nctId": nct_id,
        "kind": "source_reconciliation_worklist",
        "scope": "historical_pilot" if nct_id == "NCT02142738" else "unreviewed_trial",
        "checks": checks,
        "totalChecks": len(checks),
        "unresolvedChecks": len(checks),
        "verifiedChecks": 0,
        "readinessMayBePromoted": False,
        "approvalProbability": None,
        "caution": (
            "Questions and potential conflicts are source-attributed prompts. "
            "They are not adjudicated findings, trial failure grades, "
            "or a prospective FDA approval prediction."
        ),
    }
