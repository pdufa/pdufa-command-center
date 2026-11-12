# Research-only engineering intake. Does NOT certify this scientific level.
from __future__ import annotations
import re
LEVEL = 13
LEVEL_NAME = 'Quantitative Pharmacology'
REQUIRED_FIELDS = ('pharmacokinetics', 'pharmacodynamics', 'exposure_response')
REVIEW_QUESTIONS = ('What are the key pharmacokinetic parameters measured in pharmacokinetic studies?', 'What are the key pharmacodynamic parameters measured in pharmacodynamic studies?', 'What is the exposure-response relationship in pharmacokinetic studies?', 'What is the exposure-response relationship in pharmacodynamic studies?')
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
