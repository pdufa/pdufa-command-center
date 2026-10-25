"""Read-only, source-traceable eight-domain scientific trial dossier.

Registry protocol data are descriptive, not proof of clinical benefit, safety,
or regulatory success. This module never alters candidate rankings.
"""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any, Mapping

DOMAINS = (
    "disease_biology", "mechanism_of_action", "preclinical_evidence",
    "clinical_design", "clinical_results", "competitive_landscape",
    "regulatory_analysis", "advanced_inference",
)
MODEL_VERSION = "trial-science-dossier-v1"
_NCT = re.compile(r"NCT[0-9]{8}\Z")


def build_scientific_dossier(exact_id: str, nct_id: str, registry: Mapping[str, Any]) -> dict:
    """Collect traceable registry facts; never fabricate an analysis score."""
    if not isinstance(exact_id, str) or not exact_id.strip():
        raise ValueError("Exact program identity required")
    if not isinstance(nct_id, str) or not _NCT.fullmatch(nct_id):
        raise ValueError("Valid exact NCT ID required")
    if not isinstance(registry, Mapping):
        raise ValueError("Registry document must be an object")
    protocol = registry.get("protocolSection")
    if not isinstance(protocol, Mapping):
        raise ValueError("Registry protocol section missing")
    identity = protocol.get("identificationModule") or {}
    if not isinstance(identity, Mapping) or identity.get("nctId") != nct_id:
        raise ValueError("Registry and requested NCT identities differ")
    design = protocol.get("designModule") or {}
    outcomes = protocol.get("outcomesModule") or {}
    if not isinstance(design, Mapping) or not isinstance(outcomes, Mapping):
        raise ValueError("Invalid registry design or outcomes object")
    design_info = design.get("designInfo") or {}
    enrollment_info = design.get("enrollmentInfo") or {}
    if not isinstance(design_info, Mapping) or not isinstance(enrollment_info, Mapping):
        raise ValueError("Invalid registry design fields")
    masking_info = design_info.get("maskingInfo") or {}
    if not isinstance(masking_info, Mapping):
        raise ValueError("Invalid registry masking fields")
    raw_fields = {
        "allocation": design_info.get("allocation"),
        "intervention_model": design_info.get("interventionModel"),
        "masking": masking_info.get("masking"),
        "enrollment": enrollment_info.get("count"),
        "primary_outcomes": outcomes.get("primaryOutcomes"),
    }
    fields = {key: value for key, value in raw_fields.items()
              if value is not None and value != "" and value != []}
    url = f"https://clinicaltrials.gov/study/{nct_id}"
    locators = {
        "allocation": "protocolSection.designModule.designInfo.allocation",
        "intervention_model": "protocolSection.designModule.designInfo.interventionModel",
        "masking": "protocolSection.designModule.designInfo.maskingInfo.masking",
        "enrollment": "protocolSection.designModule.enrollmentInfo.count",
        "primary_outcomes": "protocolSection.outcomesModule.primaryOutcomes",
    }
    claims = [
        {
            "field": key, "reported_value": value, "source_url": url,
            "source_locator": locators[key],
            "verification_status": "source_record_only",
            "scientifically_verified": False,
        }
        for key, value in fields.items()
    ]
    domains = {
        domain: {
            "status": "source_record_only" if domain == "clinical_design" and claims
                      else "not_assessed",
            "claims": claims if domain == "clinical_design" else [],
            "score": None,
        }
        for domain in DOMAINS
    }
    canonical = json.dumps(registry, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False).encode("utf-8")
    return {
        "model_version": MODEL_VERSION,
        "exact_program_id": exact_id,
        "nct_id": nct_id,
        "source_url": url,
        "source_sha256": hashlib.sha256(canonical).hexdigest(),
        "domains": domains,
        "assessment_status": "incomplete",
        "overall_score": None,
        "fda_approval_probability": None,
        "read_only": True,
        "note": "Protocol metadata only; not a full scientific assessment or FDA approval forecast.",
    }
