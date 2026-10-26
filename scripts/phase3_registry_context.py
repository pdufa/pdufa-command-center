#!/usr/bin/env python3
"""Bounded, research-only drug/intervention and condition context from exact CT.gov source.

Registered interventions are NOT verified unique assets. Registered conditions
are NOT verified target indications, FDA labels or commercial rights.
"""
import re

MAX_REPORTED_ITEMS = 500
MAX_NAME_CHARS = 1000
TYPES = {"DRUG", "BIOLOGICAL", "DEVICE", "PROCEDURE", "RADIATION",
         "BEHAVIORAL", "DIETARY_SUPPLEMENT", "COMBINATION_PRODUCT",
         "DIAGNOSTIC_TEST", "GENETIC", "OTHER"}


def extract_registry_context(protocol):
    if not isinstance(protocol, dict):
        raise ValueError("Registry protocol context must be an object")
    arms = protocol.get("armsInterventionsModule") or {}
    conditions_module = protocol.get("conditionsModule") or {}
    if not isinstance(arms, dict) or not isinstance(conditions_module, dict):
        raise ValueError("Malformed ClinicalTrials.gov context module")
    raw_interventions = arms.get("interventions") or []
    raw_conditions = conditions_module.get("conditions") or []
    if (not isinstance(raw_interventions, list) or not isinstance(raw_conditions, list)
        or len(raw_interventions) > MAX_REPORTED_ITEMS or len(raw_conditions) > MAX_REPORTED_ITEMS):
        raise ValueError("Unbounded or malformed intervention/condition list")
    interventions = []
    for item in raw_interventions:
        if not isinstance(item, dict):
            raise ValueError("Malformed registered intervention")
        name, kind = item.get("name"), item.get("type")
        if (not isinstance(name, str) or not name.strip() or len(name) > MAX_NAME_CHARS
            or not isinstance(kind, str) or kind not in TYPES):
            raise ValueError("Registered intervention name/type invalid")
        interventions.append({"name": name.strip(), "type": kind})
    conditions = []
    for name in raw_conditions:
        if not isinstance(name, str) or not name.strip() or len(name) > MAX_NAME_CHARS:
            raise ValueError("Registered condition name invalid")
        conditions.append(name.strip())
    return {
        "registered_interventions": interventions,
        "registered_conditions": conditions,
        "registered_context_status": ("AVAILABLE" if interventions and conditions
                                     else "PARTIAL_OR_NOT_REPORTED"),
    }


def validate_registry_context(row):
    """Apply same bounds to stored source records before joining to issuer evidence."""
    if not isinstance(row, dict):
        raise ValueError("Invalid registry record")
    interventions = row.get("registered_interventions")
    conditions = row.get("registered_conditions")
    if not isinstance(interventions, list) or not isinstance(conditions, list):
        raise ValueError("Original registry drug/condition context was not extracted")
    reconstructed = extract_registry_context({
        "armsInterventionsModule": {"interventions": interventions},
        "conditionsModule": {"conditions": conditions},
    })
    if reconstructed["registered_context_status"] != row.get("registered_context_status"):
        raise ValueError("Registry context status is inconsistent with original source")
    return reconstructed
