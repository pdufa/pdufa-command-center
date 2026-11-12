# Research-only engineering intake. Does NOT certify this scientific level.
from __future__ import annotations
import re
LEVEL = 7
LEVEL_NAME = 'Predictive Modeling and Uncertainty'
REQUIRED_FIELDS = ('model_validation', 'uncertainty_methods', 'calibration_evidence')
REVIEW_QUESTIONS = ('What are the key performance indicators (KPIs) used to evaluate the predictive accuracy of the model?', "How do uncertainty methods such as bootstrapping and cross-validation contribute to the model's reliability?", "What is the calibration evidence provided to assess the model's ability to predict the true outcomes?", 'How do the results of the model validation process compare to the expected performance based on the calibration evidence?')
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
