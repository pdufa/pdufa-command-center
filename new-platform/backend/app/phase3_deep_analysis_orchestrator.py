"""Fail-closed orchestration for post-Phase-3, post-PDUFA-date investigations.

Discovery remains independent of this deep-analysis entrypoint. No scanner or
production job is wired to this module until integration and validation.
"""
from __future__ import annotations
from .phase3_pdufa_eligibility import phase3_pdufa_eligibility
from .science_independent_investigation import scientific_investigation
from .science_40_dossier import evaluate_science_40
from .peak_research import research_register, outcome_readiness

def prepare_deep_analysis(*, exact_key: str, phase3_results: dict,
                          pdufa_assignment: dict, scientific_evidence: dict,
                          as_of: str) -> dict:
    """Check gate BEFORE reading/scoring evidence; never emit an approval estimate."""
    gate = phase3_pdufa_eligibility(
        exact_key=exact_key, phase3_results=phase3_results,
        pdufa_assignment=pdufa_assignment, as_of=as_of)
    if not gate["deepAnalysisEligible"]:
        return {
            "exactKey": exact_key, "asOf": as_of,
            "status": "BLOCKED", "gate": gate,
            "science": None, "science40": None, "outcome": None, "main": None,
            "approvalProbability": None, "tradeAuthorized": False,
        }
    science = scientific_investigation(
        exact_key=exact_key, evidence=scientific_evidence, as_of=as_of)
    # Independent 40-question contract runs alongside the established legacy
    # investigation; neither can infer evidence from a publication-date gate.
    science40 = evaluate_science_40(
        exact_key=exact_key, evidence=scientific_evidence, as_of=as_of)
    register = research_register(exact_key=exact_key, as_of=as_of)
    outcome = outcome_readiness(science40, register)
    main = {"exactKey": exact_key, "asOf": as_of,
            "researchReadinessGrade": science40["readinessGrade"],
            "decisionReadinessGrade": "ABSTAIN", "prediction": "INSUFFICIENT_EVIDENCE",
            "approvalProbability": None, "confidence": None, "modelValidated": False,
            "tradeAuthorized": False, "researchRegister": register}
    return {
        "exactKey": exact_key, "asOf": as_of,
        "status": "RESEARCH_IN_PROGRESS", "gate": gate,
        "science": science, "science40": science40, "outcome": outcome, "main": main,
        "approvalProbability": None, "tradeAuthorized": False,
    }
