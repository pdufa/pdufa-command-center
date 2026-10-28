"""Research-only batch audit of FDA decision-label candidates.

Does not train a model or infer an approval denominator.
"""
from collections import Counter
from typing import Iterable, Mapping, Any
from research.fda_decision_label_gate import assess_label_eligibility


def audit_candidates(records: Iterable[Mapping[str, Any]]) -> dict:
    """Count eligibility and abstention reasons without fabricating labels.

    Each candidate is checked independently. The returned records intentionally
    exclude application identifiers, URLs and other source content.
    """
    total = 0
    eligible = 0
    reasons = Counter()
    outcomes = Counter()
    for record in records:
        total += 1
        decision = assess_label_eligibility(record)
        if decision["status"] == "ELIGIBLE_FOR_FURTHER_REVIEW":
            eligible += 1
            outcomes["approval" if decision["label"] == 1 else "crl"] += 1
        else:
            reasons.update(decision["reasons"])
    return {
        "total_candidates": total,
        "eligible_for_further_review": eligible,
        "abstained": total - eligible,
        "abstention_reasons": dict(sorted(reasons.items())),
        "eligible_action_counts": dict(sorted(outcomes.items())),
        "approval_rate": None,
        "validated_training_cohort": False,
        "research_only": True,
        "trading_authorized": False,
    }
