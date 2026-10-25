"""Evidence-safe crosswalk: 40 scientific questions linked to 20 investigation stages.

Twenty stages are chronological/methodological source-review subjects; the
separate eight-depth checklist contains 320 process tasks. The two frameworks
must not be mistaken for completed scientific evaluations or for each other.
This module does not persist data, change grades, promote a source, or trade.
"""
from __future__ import annotations

from collections.abc import Mapping

from .scientific_investigation_contract import LAYERS

# Every one of the 40 assessments maps to relevant stage numbers, not all 20
# indiscriminately. A mapping is a REVIEW PLAN, not evidentiary proof.
ASSESSMENT_STAGES: dict[str, tuple[int, ...]] = {
    "trial_design.randomization": (7, 11),
    "trial_design.comparator": (6, 7),
    "trial_design.blinding": (7, 11),
    "trial_design.sample_size_power": (5, 8, 11),
    "trial_design.protocol_endpoints": (1, 3, 9, 10, 11),
    "efficacy.primary_endpoint": (9, 12),
    "efficacy.effect_size": (12,),
    "efficacy.confidence_interval": (11, 12),
    "efficacy.multiplicity": (10, 11),
    "efficacy.clinical_meaning": (2, 5, 12, 20),
    "safety.serious_adverse_events": (13,),
    "safety.discontinuations": (13, 14),
    "safety.mortality": (12, 13, 20),
    "safety.exposure": (13, 14),
    "safety.benefit_risk": (13, 20),
    "biological_rationale.mechanism": (2, 16),
    "biological_rationale.target_validation": (16, 18),
    "biological_rationale.biomarker": (17,),
    "biological_rationale.translational_support": (16, 18),
    "biological_rationale.resistance": (16, 17),
    "statistical_integrity.missing_data": (14,),
    "statistical_integrity.interim_analysis": (4, 11),
    "statistical_integrity.subgroup_robustness": (15, 17),
    "statistical_integrity.sensitivity": (11, 14),
    "statistical_integrity.protocol_deviations": (1, 7, 14),
    "evidence_reproducibility.source_provenance": (1, 18),
    "evidence_reproducibility.independent_confirmation": (18,),
    "evidence_reproducibility.publication_consistency": (12, 18),
    "evidence_reproducibility.data_completeness": (14, 18),
    "evidence_reproducibility.auditability": (1, 11, 18),
    "regulatory.endpoint_acceptability": (9, 19),
    "regulatory.agency_interactions": (19,),
    "regulatory.precedent": (19,),
    "regulatory.submission_completeness": (4, 19),
    "regulatory.manufacturing_readiness": (19,),
    "timeline_and_uncertainty.trial_chronology": (4,),
    "timeline_and_uncertainty.readout_timing": (4, 12),
    "timeline_and_uncertainty.filing_timing": (4, 19),
    "timeline_and_uncertainty.conflicting_evidence": (18, 20),
    "timeline_and_uncertainty.remaining_unknowns": (20,),
}

_EXPECTED = {f"{layer}.{field}" for layer, fields in LAYERS.items() for field in fields}
assert set(ASSESSMENT_STAGES) == _EXPECTED
assert len(_EXPECTED) == 40
assert all(levels and len(set(levels)) == len(levels)
           and all(isinstance(level, int) and 1 <= level <= 20 for level in levels)
           for levels in ASSESSMENT_STAGES.values())
assert {level for levels in ASSESSMENT_STAGES.values() for level in levels} == set(range(1, 21))


def stage_crosswalk(investigation20: Mapping) -> dict:
    """Link documented registry field coverage to PENDING assessment work.

    The caller must first check exact NCT identity and archive SHA-256.
    Source presence at a stage never implies any linked assessment is verified.
    """
    if not isinstance(investigation20, Mapping):
        raise ValueError("Investigation20 payload unavailable")
    nct_id = investigation20.get("nctId")
    stages = investigation20.get("levels")
    if not isinstance(nct_id, str) or not nct_id.startswith("NCT") or len(nct_id) != 11:
        raise ValueError("Exact archived trial identity required")
    if not isinstance(stages, list) or len(stages) != 20:
        raise ValueError("All 20 investigation stages required")
    if [entry.get("level") for entry in stages] != list(range(1, 21)):
        raise ValueError("Investigation stages missing or out of order")
    if any(entry.get("scientificallyVerified") is not False
           or entry.get("score") is not None for entry in stages):
        raise ValueError("Scientific stages cannot be treated as independently verified")
    stage_rows = []
    for stage in stages:
        number = stage["level"]
        related = [key for key, links in ASSESSMENT_STAGES.items() if number in links]
        stage_rows.append({
            "level": number,
            "title": stage["title"],
            "registryFieldsPresent": stage["sourceEvidenceCount"],
            "registryFieldsInspected": stage["sourceFieldCount"],
            "registrySourceStatus": stage["status"],
            "assessmentIds": related,
            "linkedAssessments": len(related),
            "assessmentStatus": "independent_review_pending",
            "independentlyVerifiedAssessments": 0,
            "scientificScore": None,
        })
    return {
        "schemaVersion": "scientific-stage-assessment-crosswalk-v1",
        "nctId": nct_id,
        "stageCount": 20,
        "assessmentCount": 40,
        "assessmentStageLinks": sum(len(v) for v in ASSESSMENT_STAGES.values()),
        "stagesWithLinkedAssessments": sum(bool(row["assessmentIds"]) for row in stage_rows),
        "independentlyVerifiedAssessments": 0,
        "readinessConclusion": "NOT_READY",
        "approvalProbability": None,
        "assessments": [
            {
                "id": key,
                "relevantStages": list(levels),
                "independentReviewStatus": "pending",
                "verifiedEvidence": False,
                "scientificScore": None,
            }
            for key, levels in ASSESSMENT_STAGES.items()
        ],
        "stages": stage_rows,
        "note": (
            "Registry field presence, stage/assessment links, and the separate "
            "eight-depth review plan are workflows only. No independent medical "
            "source verification or regulatory conclusion has occurred."
        ),
    }
