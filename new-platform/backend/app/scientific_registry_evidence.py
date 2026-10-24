"""Read-only ClinicalTrials.gov evidence extraction.

Extract descriptive trial metadata, never transform it into a scientific score.
An NCT record alone does not verify efficacy, safety, or regulatory conclusions.
"""
from __future__ import annotations
from typing import Any, Mapping
import re

NCT_PATTERN = re.compile(r"^NCT[0-9]{8}$")


def extract_trial_evidence(nct_id: str, record: Mapping[str, Any]) -> dict:
    if not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Valid exact NCT identity required")
    protocol = record.get("protocolSection", {})
    if not isinstance(protocol, dict):
        protocol = {}
    identification = protocol.get("identificationModule", {}) or {}
    recorded_id = identification.get("nctId")
    if recorded_id != nct_id:
        raise ValueError("Source NCT identity mismatch")
    design = protocol.get("designModule", {}) or {}
    outcomes = protocol.get("outcomesModule", {}) or {}
    status = protocol.get("statusModule", {}) or {}
    source_url = f"https://clinicaltrials.gov/study/{nct_id}"
    return {
        "nctId": nct_id,
        "sourceUrl": source_url,
        "sourceType": "clinicaltrials_gov_record",
        "verificationStatus": "source_record_only",
        "metadata": {
            "allocation": (design.get("designInfo") or {}).get("allocation"),
            "interventionModel": (design.get("designInfo") or {}).get("interventionModel"),
            "masking": ((design.get("designInfo") or {}).get("maskingInfo") or {}).get("masking"),
            "enrollment": (design.get("enrollmentInfo") or {}).get("count"),
            "primaryOutcomes": outcomes.get("primaryOutcomes") or [],
            "overallStatus": status.get("overallStatus"),
        },
        "scoringEvidence": {},
        "note": "Descriptive registry data only. No domain score without independently verified quantitative evidence.",
    }
