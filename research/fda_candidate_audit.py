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
    seen_cycles = {}
    eligible_cycles = set()
    for record in records:
        total += 1
        decision = assess_label_eligibility(record)
        # Duplicate review cycles cannot become independent research examples.
        application = record.get("application_id")
        cycle = record.get("review_cycle_id")
        cycle_key = (application, cycle) if isinstance(application, str) and isinstance(cycle, str) else None
        if cycle_key and all(cycle_key):
            if cycle_key in seen_cycles:
                reasons["duplicate_review_cycle"] += 1
                if cycle_key in eligible_cycles:
                    eligible_cycles.remove(cycle_key)
                    eligible -= 1
                    outcomes["approval" if seen_cycles[cycle_key] == 1 else "crl"] -= 1
                    reasons["duplicate_review_cycle_previous_occurrence"] += 1
                continue
            seen_cycles[cycle_key] = decision["label"]
            if decision["status"] == "ELIGIBLE_FOR_FURTHER_REVIEW":
                eligible_cycles.add(cycle_key)
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
