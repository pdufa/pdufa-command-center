"""Research-only preliminary candidate scope gate; never issues an FDA outcome.

The $300M–$10B market-cap requirement is necessary, not sufficient.
No live prices, regulatory evidence, or production restriction settings are read.
"""
from decimal import Decimal, InvalidOperation

MIN_MARKET_CAP_USD = Decimal("300000000")
MAX_MARKET_CAP_USD = Decimal("10000000000")


def preliminary_candidate_scope(candidate):
    """Return a transparent eligibility triage, not a PASS/CRL/EXTENSION forecast.

    Caller must supply a current, documented market-cap observation and the
    established pipeline membership. Unknown values fail closed. A caller's
    assertion of membership is not independent verification.
    """
    blockers = []
    if not isinstance(candidate, dict):
        return {"scope": "UNKNOWN", "blockers": ["INVALID_CANDIDATE"],
                "prediction": None, "prediction_status": "ABSTAIN"}
    if candidate.get("publicly_traded") is not True:
        blockers.append("PUBLIC_LISTING_NOT_ESTABLISHED")
    cap = candidate.get("market_cap_usd")
    try:
        if isinstance(cap, bool) or not isinstance(cap, (int, str, Decimal)):
            raise InvalidOperation
        value = Decimal(str(cap))
        if not value.is_finite() or not MIN_MARKET_CAP_USD <= value <= MAX_MARKET_CAP_USD:
            blockers.append("MARKET_CAP_OUTSIDE_APPROVED_RANGE_OR_UNKNOWN")
    except (InvalidOperation, ValueError):
        blockers.append("MARKET_CAP_OUTSIDE_APPROVED_RANGE_OR_UNKNOWN")
    if candidate.get("pipeline_member") is not True:
        blockers.append("PIPELINE_RESTRICTIONS_NOT_CONFIRMED")
    if candidate.get("fda_pdufa_target_confirmed") is not True:
        blockers.append("PDUFA_TARGET_NOT_CONFIRMED")
    return {"scope": "CANDIDATE_FOR_EVIDENCE_REVIEW" if not blockers else "BLOCKED",
            "blockers": blockers, "prediction": None,
            "prediction_status": "ABSTAIN",
            "note": "Scope is not a prediction; requires point-in-time evidence and scientific assessment."}
