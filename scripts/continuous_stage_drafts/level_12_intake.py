# Research-only engineering intake. Does NOT certify this scientific level.
from __future__ import annotations
import re
LEVEL = 12
LEVEL_NAME = 'Multi-Model Scientific Adjudication'
REQUIRED_FIELDS = ('independent_model_outputs', 'model_disagreements', 'adjudication_protocol')
REVIEW_QUESTIONS = ('What are the key steps in the multi-model scientific adjudication process?', 'How do independent model outputs contribute to the adjudication process?', 'What are the potential challenges in the multi-model scientific adjudication process?', 'What are the key factors that influence the adjudication outcome?')
NCT = re.compile(r"NCT[0-9]{8}\Z")

def assess(record: dict) -> dict:
    if not isinstance(record, dict):
        raise ValueError("Expected one research intake record")
    nct = record.get("nct")
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Exact NCT identifier required")
    observed = record.get("evidence_fields", {})
    if not isinstance(observed, dict):
        raise ValueError("Evidence fields must be keyed source observations")
    # Only identify documentary gaps; absence is not negative trial evidence.
    missing = [key for key in REQUIRED_FIELDS if not isinstance(observed.get(key), str)
               or not observed[key].strip()]
    return {"nct": nct, "level": LEVEL, "status": "RESEARCH_INTAKE_REVIEW_REQUIRED",
            "missing_source_fields": missing, "questions": list(REVIEW_QUESTIONS),
            "source_facts_independently_verified": False,
            "scientific_stage_complete": False, "fda_prediction": None,
            "approval_probability": None, "clinical_score": None}
