"""OUTCOME research status from SCIENCE provenance, with mandatory abstention.

Not a production decision model or validated prediction probability.
"""
from collections.abc import Mapping
from datetime import date

from research.fda_science_provenance_gate import bind_science_research_gate


TARGET_CLASSES = ("PASS", "CRL", "EXTENSION")
CLASS_DEFINITIONS = {
    "PASS": "FDA approval for the exact application and review cycle at the prespecified review horizon.",
    "CRL": "An authenticated complete response letter for that review cycle; other unresolved or withdrawn actions are not CRLs.",
    "EXTENSION": "A documented formal FDA revision of the prespecified review target, distinct from a missed date, delay or later approval/CRL.",
}


def build_unvalidated_decision_contract(*, blockers=(), as_of=None):
    """Describe the three-outcome research target without inventing a forecast.

    A formal extension and an eventual approval can both occur in one application
    history. They become mutually exclusive forecasting classes only after the
    target horizon/event policy is prespecified. This adapter defines neither a
    calibrated model nor a shortcut from a known historical action to a forecast.
    """
    if (not isinstance(blockers, (list, tuple))
            or any(not isinstance(item, str) or not item.strip() for item in blockers)):
        raise ValueError("explicit research blocker strings required")
    if as_of is not None and type(as_of) is not date:
        raise ValueError("explicit research snapshot date required")
    return {
        "schema_version": "fda-three-outcome-research-contract-v1",
        "research_only": True,
        "target_classes": list(TARGET_CLASSES),
        "class_definitions": dict(CLASS_DEFINITIONS),
        "target_definition_status": "PRESPECIFIED_REVIEW_HORIZON_REQUIRED",
        "extension_is_binary_nonapproval": False,
        "predicted_decision": "ABSTAIN",
        "abstention_reason": "INSUFFICIENT_INDEPENDENTLY_VERIFIED_EVIDENCE_AND_MODEL_VALIDATION",
        "probabilities": {name: None for name in TARGET_CLASSES},
        "science_readiness_grade": "NOT_READY",
        "prediction_confidence_grade": "NOT_ESTABLISHED",
        "reluctance_grade": "INSUFFICIENT_VERIFIED_EVIDENCE",
        "evidence_completeness": "INCOMPLETE_NOT_QUANTIFIED",
        "source_verification_status": "NOT_INDEPENDENTLY_AUTHENTICATED",
        "historical_validation_status": "NOT_INDEPENDENTLY_VALIDATED",
        "uncertainty_range": None,
        "model_version": None,
        "prediction_version": None,
        "last_updated": None if as_of is None else as_of.isoformat(),
        "eligible_for_validated_accuracy": False,
        "trading_authorized": False,
        "blockers": sorted(set(blockers)),
    }


def validate_unvalidated_decision_contract(contract):
    """Reject promoted/malformed research payloads; no validation bypass exists."""
    if not isinstance(contract, Mapping):
        raise ValueError("unvalidated three-outcome research contract required")
    snapshot = contract.get("last_updated")
    parsed = None
    if snapshot is not None:
        if not isinstance(snapshot, str) or len(snapshot) != 10:
            raise ValueError("explicit research snapshot date required")
        try:
            parsed = date.fromisoformat(snapshot)
        except ValueError as exc:
            raise ValueError("explicit research snapshot date required") from exc
        if parsed.isoformat() != snapshot:
            raise ValueError("explicit research snapshot date required")
    expected = build_unvalidated_decision_contract(blockers=contract.get("blockers"), as_of=parsed)
    if set(contract) != set(expected):
        raise ValueError("unvalidated three-outcome contract fields cannot be added or omitted")
    # Compare types as well as values: Python bool/int equality must not accept a
    # numeric alias for an explicit false safety flag.
    for key, value in expected.items():
        if type(contract[key]) is not type(value) or contract[key] != value:
            raise ValueError("unvalidated three-outcome contract cannot promote predictions or evidence")
    return contract


def build_outcome_provenance_status(reconstruction, science_dossiers):
    science = bind_science_research_gate(reconstruction, science_dossiers)
    cases = []
    for row in science["cases"]:
        cases.append({
            "event_key": row["event_key"],
            "decision_contract": build_unvalidated_decision_contract(blockers=row["blockers"]),
            "science_provenance_blockers": row["blockers"],
            "outcome_decision": "ABSTAIN",
            "approval_probability": None,
            "pass_fail_grade": None,
            "ready_for_analysis_grade": "NOT_READY",
            "reluctant_grade": "INSUFFICIENT_VERIFIED_EVIDENCE",
            "eligible_for_validated_accuracy": False,
            "eligible_for_trading_recommendation": False,
        })
    return {"research_only": True, "trading_authorized": False,
            "validated_predictions": 0, "cases": cases}
