"""Server-maintained PEAK research register, separate from SCIENCE signoff.

No caller claims, DB/network activity, scores, labels, model fit or certification.
Unknown original publication dates/hashes remain unknown. The examples are
selected context and cannot become a point-in-time training cohort.
"""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

KEY = "APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130"
REGISTER = Path(__file__).with_name("peak_research_register.json")


@lru_cache(maxsize=1)
def _load():
    raw = REGISTER.read_bytes()
    if len(raw) > 200_000:
        raise ValueError("PEAK research register exceeds size budget")
    return json.loads(raw)


def research_register(*, exact_key: str, as_of: str, register=None):
    from .science_40_dossier import _catalog, _date, _valid_https
    cutoff = _date(as_of)
    if cutoff is None:
        raise ValueError("Valid research cutoff required")
    if exact_key != KEY:
        return None
    r = deepcopy(_load() if register is None else register)
    if (not isinstance(r, dict) or r.get("schemaVersion") != "peak-research-register-v1"
            or r.get("exactKey") != exact_key or r.get("nctId") != "NCT05208047"
            or r.get("status") != "UNADJUDICATED_RESEARCH_ONLY"
            or r.get("modelValidated") is not False or r.get("tradeAuthorized") is not False
            or r.get("approvalProbability") is not None or r.get("originalBytesRetained") is not False
            or _date(r.get("indexedOn")) is None):
        raise ValueError("Invalid source-bound PEAK research register")
    if _date(r["indexedOn"]) > cutoff:
        return None
    sources = r.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 30:
        raise ValueError("Bounded research sources required")
    ids = set()
    for source in sources:
        if (not isinstance(source, dict) or not isinstance(source.get("id"), str)
                or source["id"] in ids or not _valid_https(source.get("url"))
                or source.get("originalDocumentSha256") is not None
                or source.get("originalBytesRetained") is not False
                or source.get("independentlyReviewed") is not False
                or _date(source.get("observedOn")) is None
                or _date(source["observedOn"]) > cutoff
                or source.get("publishedAt") is not None and (
                    _date(source["publishedAt"]) is None
                    or _date(source["publishedAt"]) > _date(source["observedOn"]))):
            raise ValueError("Invalid or post-cutoff research source")
        ids.add(source["id"])
    documents = r.get("requiredDocuments")
    if not isinstance(documents, list) or len(documents) != 12:
        raise ValueError("Research document inventory inconsistent")
    doc_ids = set()
    for d in documents:
        if (not isinstance(d, dict) or not isinstance(d.get("id"), str)
                or d["id"] in doc_ids or d.get("status") not in {"MISSING", "UNVERIFIED"}
                or not isinstance(d.get("name"), str) or not d["name"].strip()):
            raise ValueError("Invalid missing-document inventory")
        doc_ids.add(d["id"])
    catalog = _catalog()
    rows = r.get("questions")
    if not isinstance(rows, list) or len(rows) != 40:
        raise ValueError("Exactly 40 question research records required")
    for q, expected in zip(rows, catalog):
        if (not isinstance(q, dict) or q.get("id") != expected["id"]
                or q.get("exactKey") != exact_key or q.get("nctId") != r["nctId"]
                or q.get("independentReviewRequired") is not True
                or q.get("independentlyReviewed") is not False
                or q.get("reviewedDepthLevels") != []
                or q.get("reviewStatus") not in {"MISSING", "UNADJUDICATED_RESEARCH"}
                or not isinstance(q.get("sourceIds"), list) or any(s not in ids for s in q["sourceIds"])
                or not isinstance(q.get("missingDocumentIds"), list)
                or not q["missingDocumentIds"] or any(d not in doc_ids for d in q["missingDocumentIds"])
                or not isinstance(q.get("researchObservation"), str) or not q["researchObservation"].strip()
                or not isinstance(q.get("uncertainties"), list) or not q["uncertainties"]
                or any(not isinstance(x, str) or not x.strip() for x in q["uncertainties"])):
            raise ValueError("Question research identity, source or review status inconsistent")
        q.update(question=expected["question"], layer=expected["layer"], layerName=expected["layerName"])
    contexts = r.get("historicalContexts")
    if not isinstance(contexts, list) or len(contexts) > 20:
        raise ValueError("Bounded historical context required")
    for c in contexts:
        if (not isinstance(c, dict) or c.get("independentlyAdjudicated") is not False
                or c.get("modelEligible") is not False or c.get("reviewCycle") is not None
                or not isinstance(c.get("sourceIds"), list) or not c["sourceIds"]
                or any(s not in ids for s in c["sourceIds"])
                or c.get("actionDate") is not None and (
                    _date(c["actionDate"]) is None or _date(c["actionDate"]) >= cutoff)):
            raise ValueError("Historical context cannot be promoted or leak future actions")
    depth = r.get("depthFramework")
    if (not isinstance(depth, dict) or depth.get("requiredLevels") != list(range(1, 21))
            or depth.get("independentlyReviewedLevels") != []):
        raise ValueError("Existing 20-level review boundary must remain explicit")
    timeline = r.get("timeline")
    if (not isinstance(timeline, list) or len(timeline) > 20
            or any(not isinstance(t, dict) or _date(t.get("date")) is None
                   or t.get("sourceId") not in ids or not isinstance(t.get("basis"), str)
                   for t in timeline)):
        raise ValueError("Timeline dates and source identity must reconcile")
    discrepancies = r.get("evidenceDiscrepancies")
    if (not isinstance(discrepancies, list) or len(discrepancies) > 20
            or any(not isinstance(d, dict) or not isinstance(d.get("observation"), str)
                   or d.get("status") not in {"CONTEXT_RECONCILIATION_REQUIRED",
                        "SOURCE_EXPLANATION_AVAILABLE_NOT_INDEPENDENTLY_ADJUDICATED"}
                   or not isinstance(d.get("sourceIds"), list)
                   or any(s not in ids for s in d["sourceIds"]) for d in discrepancies)):
        raise ValueError("Discrepancy observations must retain source and review scope")
    r["summary"] = {
        "questionRecords": len(rows),
        "questionsWithSourceObservations": sum(bool(q["sourceIds"]) for q in rows),
        "missingRequiredDocumentFamilies": len(documents),
        "historicalSourceContexts": len(contexts),
        "independentlyAdjudicatedHistoricalCycles": 0,
        "originalSourceBytesRetained": 0,
        "independentlyCertifiedAssessments": 0,
        "pointInTimeTrainingEligible": False,
    }
    return r


def outcome_readiness(science40: dict, register: dict | None) -> dict:
    """Do not turn completeness, source assertions or examples into probability."""
    return {
        "schemaVersion": "phase3-outcome-readiness-v1", "exactKey": science40["exactKey"],
        "asOf": science40["asOf"], "researchReadinessGrade": science40["readinessGrade"],
        "decisionReadinessGrade": "ABSTAIN", "decision": "ABSTAIN",
        "scientificEvidence": {
            "independentlyCertified": science40["independentlyReviewedAssessments"],
            "required": 40, "sourceLeads": science40["sourceLeadsDiscovered"],
            "requiredDepthLevels": 20, "reviewedDepthLevels": science40["reviewedDepthLevels"],
        },
        "historicalComparison": {
            "selectedSourceContexts": register["summary"]["historicalSourceContexts"] if register else 0,
            "independentlyAdjudicatedCycles": 0, "representativeCohortVerified": False,
            "predecisionSnapshotsVerified": False,
        },
        "regulatoryUncertainty": {
            "originalCurrentFdaCorrespondenceExamined": False,
            "manufacturingAndInspectionReviewComplete": False,
        },
        "predictionValidation": {"status": "NOT_VALIDATED", "outOfSampleAccuracy": None,
                                 "calibration": None, "independentValidationAvailable": False},
        "approvalProbability": None, "nonapprovalProbability": None, "confidence": None,
        "modelValidated": False, "tradeAuthorized": False,
        "blockers": ["Independent scientific review and required primary documents are incomplete.",
                     "Selected historical action claims are not adjudicated cycle labels or a representative validation cohort.",
                     "No independently validated, calibrated FDA prediction method is available."],
    }
