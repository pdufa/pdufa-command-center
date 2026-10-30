"""Cross-check historical SCIENCE research dossiers against provenance safety gate.

This adapter never upgrades an unverified source or completes a scientific level.
"""
from research.fda_reconstruction_input_gate import build_reconstruction_input_gate


def bind_science_research_gate(reconstruction, science_dossiers):
    gate = build_reconstruction_input_gate(reconstruction)
    cases = {case["event_key"]: case for case in gate["cases"]}
    if len(cases) != len(gate["cases"]):
        raise ValueError("duplicate gate event")
    results = []
    seen = set()
    for dossier in science_dossiers:
        key = dossier.get("event_key")
        if key not in cases or key in seen:
            raise ValueError("unknown or duplicate SCIENCE dossier")
        seen.add(key)
        if dossier.get("research_only") is not True:
            raise ValueError("SCIENCE dossier must remain research only")
        if dossier.get("original_prediction_cutoff") is not None:
            raise ValueError("unauthenticated original prediction cutoff")
        results.append({
            "event_key": key,
            "science_dossier_schema": dossier.get("schema_version"),
            "research_only": True,
            "eligible_for_training": False,
            "eligible_for_validated_prediction": False,
            "independently_completed_assessments": 0,
            "blockers": cases[key]["blockers"],
        })
    if seen != set(cases):
        raise ValueError("missing SCIENCE dossiers")
    return {"research_only": True, "trading_authorized": False,
            "validated_science_dossiers": 0, "cases": results}
