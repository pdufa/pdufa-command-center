"""Source-bound SCIENCE research dossiers, never completed assessments.

Consumes the reconstruction auditor's classifications and the existing SCIENCE
catalog. A timely issuer disclosure supplies a research observation, not an
independent assessment, a frozen feature, or a completed investigation depth.
"""
from collections.abc import Mapping
from copy import deepcopy
from datetime import date

from research.science_investigation_depths import build_depth_framework
from research.science_investigation_extension import build_extended_investigation_framework

CANDIDATE = "PREDECISION_RESEARCH_CANDIDATE"


def _catalog_questions(catalog):
    if not isinstance(catalog, Mapping):
        raise ValueError("existing SCIENCE catalog required")
    questions = catalog.get("questions")
    if (catalog.get("schemaVersion") != "science-40-question-catalog-v1"
            or catalog.get("layerCount") != 8 or catalog.get("questionCount") != 40
            or catalog.get("maximumInvestigationDepth") != 20
            or not isinstance(questions, list) or len(questions) != 40):
        raise ValueError("existing SCIENCE 40/8/20 catalog contract required")
    for index, question in enumerate(questions):
        if (not isinstance(question, Mapping) or question.get("id") != f"S{index+1:02d}"
                or question.get("layer") != 1+index//5
                or any(not isinstance(question.get(field), str) or not question[field].strip()
                       for field in ("layerName", "question", "requiredEvidence"))):
            raise ValueError("SCIENCE question identity, evidence or layer contract changed")
    return questions


def _strict_date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("audited research cutoff and availability dates required")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("audited research cutoff and availability dates required") from exc
    if parsed.isoformat() != value:
        raise ValueError("audited research cutoff and availability dates required")
    return parsed


def _classified_sources(case, question_ids):
    cutoff = _strict_date(case.get("reconstruction_cutoff"))
    sources = case.get("source_classification")
    if not isinstance(sources, list):
        raise ValueError("audited source classifications required")
    seen = set()
    for source in sources:
        if (not isinstance(source, Mapping) or not isinstance(source.get("source_id"), str)
                or not source["source_id"].strip() or source["source_id"] in seen
                or not isinstance(source.get("source_url"), str)
                or not isinstance(source.get("finding"), str)
                or not isinstance(source.get("science_question_ids"), list)
                or any(not isinstance(q,str) or q not in question_ids for q in source["science_question_ids"])
                or len(set(source["science_question_ids"])) != len(source["science_question_ids"])):
            raise ValueError("unique, source-bound SCIENCE classifications required")
        seen.add(source["source_id"])
        if (source.get("independently_reviewed") is not False
                or source.get("eligible_for_frozen_prediction") is not False):
            raise ValueError("research adapter cannot accept independent certification or frozen features")
        status = source.get("classification")
        if status not in {CANDIDATE, "EXCLUDED_OUTCOME_ONLY", "EXCLUDED_AFTER_AUDIT_SNAPSHOT",
                          "EXCLUDED_AFTER_RECONSTRUCTION_CUTOFF", "QUARANTINED_UNKNOWN_AVAILABILITY",
                          "QUARANTINED_PRINTED_DATE_ONLY"}:
            raise ValueError("audited source classification required")
        if status == CANDIDATE:
            if source.get("source_role") != "PREDECISION_RESEARCH":
                raise ValueError("outcome evidence cannot enter scientific research observations")
            if (_strict_date(source.get("available_on")) > cutoff
                    or source.get("availability_basis") != "SEC_FILING_INDEX"
                    or not isinstance(source.get("availability_source_url"),str)
                    or not source["availability_source_url"].strip()):
                raise ValueError("research observation requires audited pre-cutoff availability")
    return sources


def build_scientific_dossier(case_report, catalog):
    """Build a read-only research matrix from an already audited case report.

    This intentionally has no promotion path: independently reviewed evidence
    belongs in the existing server-side SCIENCE adjudication register. Unknown
    evidence is never interpreted as an adverse finding or a favorable result.
    """
    questions = _catalog_questions(catalog)
    if not isinstance(case_report, Mapping) or not isinstance(case_report.get("event_key"), str):
        raise ValueError("exact audited case identity required")
    sources = _classified_sources(case_report, {q["id"] for q in questions})
    question_rows = []
    for question in questions:
        linked = [s for s in sources if question["id"] in s["science_question_ids"]]
        observations = [s for s in linked if s["classification"] == CANDIDATE]
        question_rows.append({
            "question_id": question["id"], "layer": question["layer"],
            "question": question["question"], "required_evidence": question["requiredEvidence"],
            "scientific_rationale": "Evaluate this question using " + question["requiredEvidence"] + "; source reports alone do not establish the finding.",
            "historical_prediction_cutoff": case_report.get("original_prediction_cutoff"),
            "research_cutoff": case_report["reconstruction_cutoff"],
            "supporting_findings": [], "contradictory_findings": [],
            "finding_classification_status": "INDEPENDENT_REVIEW_REQUIRED",
            "missing_information": [question["requiredEvidence"], "Independent supporting/opposing interpretation and source provenance"],
            "confidence_grade": "NOT_ESTABLISHED",
            "independent_verification_status": "NOT_INDEPENDENTLY_ASSESSED",
            "effect_on_proposed_fda_decision": "NO_CERTIFIED_EFFECT_ABSTAIN",
            "research_status": "RESEARCH_OBSERVATION_ONLY" if observations else "MISSING_PREDECISION_SOURCE",
            "observations": [{"source_id": s["source_id"], "source_url": s["source_url"],
                              "available_on": s["available_on"],
                              "availability_source_url": s["availability_source_url"],
                              "source_reported_finding": s["finding"],
                              "source_date_vs_original_cutoff": s.get("supplied_source_date_vs_original_cutoff"),
                              "independently_reviewed": False,
                              "eligible_for_frozen_prediction": False}
                             for s in observations],
            "excluded_or_quarantined_sources": [{"source_id": s["source_id"],
                "source_url": s["source_url"], "reason": s["classification"]}
                for s in linked if s["classification"] != CANDIDATE],
            "assessment_status": "NOT_INDEPENDENTLY_ASSESSED", "scientific_conclusion": None,
            "uncertainties": [
                "A source-reported finding is not an independently reproduced scientific assessment.",
                f"Complete and independently review {question['requiredEvidence']}.",
                "Bind original source bytes and public availability to the exact application, cycle and cutoff.",
            ],
            "independently_reviewed_depth_levels": [],
        })
    layers = []
    for layer in range(1, 9):
        rows = [row for row in question_rows if row["layer"] == layer]
        layers.append({
            "layer": layer, "layer_name": questions[(layer-1)*5]["layerName"],
            "questions": rows,
            "questions_with_research_observations": sum(bool(row["observations"]) for row in rows),
            "independently_completed_assessments": 0,
            "missing_predecision_source_question_ids": [row["question_id"] for row in rows if not row["observations"]],
            "required_document_families": sorted({row["required_evidence"] for row in rows}),
        })
    return {
        "schema_version": "fda-science-research-dossier-v1", "research_only": True,
        "event_key": case_report["event_key"], "application_id": case_report.get("application_id"),
        "reconstruction_cutoff": case_report.get("reconstruction_cutoff"),
        "original_prediction_cutoff": case_report.get("original_prediction_cutoff"),
        "scope": "RECONSTRUCTED_OBSERVATIONS_NOT_COMPLETED_SCIENTIFIC_ASSESSMENTS",
        "layers": layers,
        "depth_framework": build_depth_framework(catalog, sources,
            reconstruction_cutoff=case_report["reconstruction_cutoff"]),
        "extended_investigation_framework": build_extended_investigation_framework(
            catalog, sources, reconstruction_cutoff=case_report["reconstruction_cutoff"]),
        "historical_comparison": {
            "status": "UNADJUDICATED_RESEARCH_CONTEXT", "model_eligible_comparisons": 0,
            "contexts": deepcopy(case_report.get("related_precedents", [])),
            "required_matching_fields": ["application_id", "review_cycle", "indication", "mechanism",
                "population", "trial_design", "comparator", "endpoint", "regulatory_pathway",
                "manufacturing_context", "evidence_cutoff", "action_date", "program_family"],
            "requirements": ["Select comparator cases without using the candidate's later outcome.",
                "Account for indication, endpoint, treatment era and review-cycle differences.",
                "Verify complete sampling denominator and program-family independence before modeling."],
        },
        "counterevidence_review": {
            "status": "INDEPENDENT_ADVERSARIAL_REVIEW_REQUIRED",
            "supporting_context": deepcopy(case_report.get("supporting_factors", [])),
            "opposing_context": deepcopy(case_report.get("opposing_factors", [])),
            "context_scope": "UNADJUDICATED_CASE_NOTES_NOT_QUESTION_LEVEL_FINDINGS",
            "requirements": ["Review contrary efficacy, design, statistical, safety, regulatory and CMC evidence.",
                "A missing document is unknown; it does not support either regulatory outcome."],
        },
        "summary": {
            "required_assessments": 40, "required_layers": 8, "required_depth_levels": 20,
            "questions_with_research_observations": sum(bool(row["observations"]) for row in question_rows),
            "independently_completed_assessments": 0, "independently_completed_depth_levels": 0,
            "eligible_frozen_features": 0, "scientific_score": None,
            "approval_probability": None, "independent_scientific_conclusion": None,
        },
        "missing_documents": deepcopy(case_report.get("missing_documents", [])),
        "validation_blockers": deepcopy(case_report.get("blockers", [])),
        "trading_authorized": False,
    }
