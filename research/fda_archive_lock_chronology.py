"""Research-only comparison of retrospective archive locks with FDA action dates.

A lock after an action is not prospective evidence, regardless of matching
legacy prediction probabilities. Never promote retrospective cases.
"""
from datetime import date, datetime, timezone


def audit_archive_lock_chronology(inventory, archive):
    groups = archive.get("prediction_archives", [])
    cases = []
    for case in inventory["cases"]:
        key = case["event_key"]
        action_day = date.fromisoformat(case["action_date"])
        matches = [group for group in groups if key in group.get("matched_priority_event_keys", [])]
        if len(matches) != 1:
            raise ValueError("expected exactly one retrospective archive for " + key)
        group = matches[0]
        lock = datetime.fromisoformat(group["archive_lock_created_at"].replace("Z", "+00:00"))
        if lock.tzinfo is None:
            raise ValueError("archive lock lacks timezone")
        lock_day = lock.astimezone(timezone.utc).date()
        cases.append({
            "event_key": key,
            "fda_action_date": action_day.isoformat(),
            "archive_lock_date": lock_day.isoformat(),
            "archive_lock_after_fda_action": lock_day > action_day,
            "archive_lock_is_prospective_evidence": False,
            "independently_verified": False,
        })
    return {
        "research_only": True,
        "trading_authorized": False,
        "retrospective_cases_checked": len(cases),
        "archives_locked_after_action": sum(x["archive_lock_after_fda_action"] for x in cases),
        "verified_prospective_predictions": 0,
        "cases": cases,
    }
