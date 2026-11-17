"""Source discovery avenues, not source discovery results.

All links are fixed public authorities or exact-NCT queries. No lookup is
executed, source is NOT verified, and a failed search is NOT a negative result.
The FDA avenue never maps an NCT to an application or makes a filing claim.
"""
from __future__ import annotations

import re

VERSION = "scientific-research-avenues-v1"
_NCT = re.compile(r"NCT[0-9]{8}")

# Classifications are intentionally not score weights or evidence-quality grades.
_ROUTES = {
    9: ("REGISTRY_AND_CLINICAL_PUBLICATIONS", "Compare source-dated efficacy, harms, populations and exposure before clinical synthesis."),
    10: ("DISEASE_GUIDELINES_AND_COMPARATOR", "Find dated clinical guidelines for exact disease subtype, care setting and jurisdiction; NCT alone does not identify the appropriate guideline."),
    11: ("EPIDEMIOLOGY_AND_TREATMENT_ALTERNATIVES", "Verify representative denominator, geography and treatment alternatives; a study enrollment count is not disease prevalence."),
    12: ("INDEPENDENT_STUDY_AND_LITERATURE_SEARCH", "Identify other exact NCTs and overlapping cohorts; separate NCT identifiers do not establish independent replication."),
    13: ("OFFICIAL_FDA_APPLICATION_FILE", "Requires exact NDA/BLA/ANDA application, review cycle and indication before filing attribution."),
    14: ("OFFICIAL_FDA_DESIGNATION_AND_PATHWAY", "Original designation document and indication match required; designation does not establish filing or approval."),
    15: ("OFFICIAL_FDA_REVIEW_PRECEDENT", "Use a different FDA application and pre-cutoff action; target outcome must remain hidden from prospective analysis."),
    16: ("OFFICIAL_FDA_MANUFACTURING_AND_INSPECTIONS", "Only attributable public records are reviewable; missing/nonpublic inspection reports are UNKNOWN."),
    17: ("SPONSOR_VERSIONED_DISCLOSURE", "Find original timestamped sponsor/SEC versions tied to exact study, not ticker-only inference."),
    18: ("INDEPENDENT_CLINICAL_CHALLENGE", "Locate alternate explanations and independent critiques; sources cannot replace owner adjudication."),
    19: ("INTERNAL_IMMUTABLE_FORECAST_ARTIFACTS", "Owner-controlled source/model freeze, hashes and outcome-isolation audit; public web search cannot prove prospective blindness."),
    20: ("OFFICIAL_FDA_GOAL_AND_ACTION_HISTORY", "Exact application/review-cycle original and revised goals plus official action records; never feed the final decision into a prior forecast."),
}
assert tuple(_ROUTES) == tuple(range(9, 21))

def candidate_research_avenues(trial_id):
    """Generate bounded unexecuted leads for one exact trial, never evidence."""
    if not isinstance(trial_id, str) or _NCT.fullmatch(trial_id) is None:
        return {}
    registry = "https://clinicaltrials.gov/study/" + trial_id
    literature = "https://pubmed.ncbi.nlm.nih.gov/?term=" + trial_id
    fda = "https://www.fda.gov/drugsatfda"
    sec = "https://www.sec.gov/edgar/search/"
    output = {}
    for number, (category, instruction) in _ROUTES.items():
        if number in {9, 10, 11, 12, 18}:
            leads = [
                {"name": "ClinicalTrials.gov exact study", "url": registry},
                {"name": "PubMed exact NCT search", "url": literature},
            ]
            gate = ("Exact trial registry review; supplemental papers and guidelines "
                    "need independent dated source verification.")
        elif number in {13, 14, 15, 16, 20}:
            leads = [{"name": "FDA Drugs@FDA search", "url": fda}]
            gate = ("Exact application type, number, indication and review cycle required. "
                    "NCT-only lookup cannot establish that linkage.")
        elif number == 17:
            leads = [{"name": "SEC EDGAR search", "url": sec},
                     {"name": "ClinicalTrials.gov exact study", "url": registry}]
            gate = ("Identify sponsor and filing entity from dated primary records. "
                    "A company/ticker match cannot verify the exact trial disclosure.")
        else:
            leads = []
            gate = "Requires owner-controlled immutable records unavailable from open public discovery."
        output[str(number)] = {
            "level": number,
            "status": "UNSEARCHED_CANDIDATE_LEADS",
            "sourceClass": category,
            "instruction": instruction,
            "sourceLeads": leads,
            "identityGate": gate,
            "reviewResult": None,
            "fdaPrediction": "ABSTAIN",
        }
    return output
