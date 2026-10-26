"""Unscored 40-assessment × 20-depth scientific review plan for one exact trial.

Planning metadata only. Not a clinical finding, independent verification,
regulatory decision, grade, or PDUFA approval forecast. Does not change the
legacy 8-depth/320-task handoff or the GEM JR/GEM/WT FS/FA presets.
"""
from __future__ import annotations

import re

from .scientific_investigation_contract import LAYERS

_EXACT_NCT = re.compile(r"NCT[0-9]{8}\Z")

# The 20 requested depth methods are distinct from the 20 archived-registry
# source-coverage stages in scientific_investigation_20.py.
INVESTIGATION_DEPTHS = (
    ("document_reading", "Document Reading"),
    ("hypothesis_understanding", "Hypothesis Understanding"),
    ("biological_investigation", "Biological Investigation"),
    ("evidence_validation", "Evidence Validation"),
    ("critical_challenge", "Critical Challenge"),
    ("cross_disciplinary_integration", "Cross-Disciplinary Integration"),
    ("predictive_modeling", "Predictive Modeling"),
    ("scientific_synthesis", "Scientific Synthesis"),
    ("causal_inference", "Causal Inference"),
    ("systems_biology_modeling", "Systems Biology Modeling"),
    ("adversarial_review", "Adversarial Review"),
    ("multi_model_adjudication", "Multi-Model Adjudication"),
    ("quantitative_pharmacology", "Quantitative Pharmacology"),
    ("patient_heterogeneity", "Patient Heterogeneity"),
    ("bayesian_integration", "Bayesian Integration"),
    ("external_validity", "External Validity"),
    ("historical_failure_analysis", "Historical Failure Analysis"),
    ("regulatory_counterfactual", "Regulatory Counterfactual"),
    ("reproducibility_audit", "Reproducibility Audit"),
    ("red_team_adjudication", "Red-Team Adjudication"),
)


def build_investigation_800(nct_id: str) -> dict:
    """Create 800 *pending* task identities, with no evidence/grade promotion.

    Called only with an exact registry NCT ID, not an inferred ticker/company,
    PDUFA application identity or broad research cohort membership. It does
    not read a database or assert that this trial belongs to a named list.
    """
    if not isinstance(nct_id, str) or not _EXACT_NCT.fullmatch(nct_id):
        raise ValueError("Exact NCT ID required; ticker/application matching is prohibited")

    if len(LAYERS) != 8 or any(len(fields) != 5 for fields in LAYERS.values()):
        raise ValueError("Eight-layer/forty-assessment catalog drift")
    if len(INVESTIGATION_DEPTHS) != 20 or len(set(INVESTIGATION_DEPTHS)) != 20:
        raise ValueError("Twenty-depth investigation catalog drift")

    assessment_ids = [
        f"{layer}.{assessment}"
        for layer, fields in LAYERS.items()
        for assessment in fields
    ]
    if len(assessment_ids) != 40 or len(set(assessment_ids)) != 40:
        raise ValueError("Duplicate or missing scientific assessment")

    tasks = [
        {
            "taskId": f"{assessment_id}:depth{index:02d}",
            "assessmentId": assessment_id,
            "depthLevel": index,
            "depthId": depth_id,
            "reviewStatus": "pending_independent_review",
            "independentlyVerified": False,
            "reviewerA": "not_assigned",
            "reviewerB": "not_assigned",
            "scientificScore": None,
        }
        for assessment_id in assessment_ids
        for index, (depth_id, _) in enumerate(INVESTIGATION_DEPTHS, 1)
    ]
    if len(tasks) != 800 or len({task["taskId"] for task in tasks}) != 800:
        raise ValueError("Scientific review matrix must contain 800 unique tasks")

    return {
        "schemaVersion": "scientific-investigation-depth20-v1",
        "exactId": f"TRIAL|{nct_id}",
        "nctId": nct_id,
        "mode": "unverified_planning_inventory_only",
        "layers": len(LAYERS),
        "assessments": len(assessment_ids),
        "depthCount": len(INVESTIGATION_DEPTHS),
        "depths": [
            {"level": index, "id": depth_id, "name": label}
            for index, (depth_id, label) in enumerate(INVESTIGATION_DEPTHS, 1)
        ],
        "requiredTasks": len(tasks),
        "completedTasks": 0,
        "independentlyVerifiedTasks": 0,
        "tasks": tasks,
        "analysisReady": False,
        "readinessGrade": None,
        "reluctantGrade": None,
        "scientificConclusion": None,
        "approvalProbability": None,
        "note": (
            "Planned review slots are not completed investigations. Each item "
            "requires dated original documents, independently authenticated "
            "reviewers and adjudication; scores and forecasts are withheld."
        ),
    }
