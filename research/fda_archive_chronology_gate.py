"""Fail-closed chronology gate for historical FDA prediction claims.

Archive hashes prove byte identity, not pre-action forecasting. A model locked
after an FDA action cannot validate a purported prospective prediction.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path


def audit_archive_chronology(archive, reconstruction):
    if archive.get("research_only") is not True or reconstruction.get("research_only") is not True:
        raise ValueError("research-only source packets required")
    freeze = datetime.fromisoformat(archive["model_spec"]["frozen_at_utc"].replace("Z", "+00:00"))
    if freeze.tzinfo is None:
        raise ValueError("model freeze must include timezone")
    locks = [datetime.fromisoformat(x["archive_lock_created_at"].replace("Z", "+00:00"))
             for x in archive["prediction_archives"]]
    if any(x.tzinfo is None for x in locks):
        raise ValueError("prediction lock must include timezone")
    results = []
    for case in reconstruction["cases"]:
        action = date.fromisoformat(case["action_date"])
        key = case["event_key"]
        matching = [x for x in archive["prediction_archives"] if key in x["matched_priority_event_keys"]]
        if len(matching) != 1:
            raise ValueError("each priority event requires exactly one matching archive")
        lock = datetime.fromisoformat(matching[0]["archive_lock_created_at"].replace("Z", "+00:00"))
        after_action = freeze.astimezone(timezone.utc).date() > action or lock.astimezone(timezone.utc).date() > action
        results.append({
            "event_key": key,
            "model_freeze_after_fda_action": freeze.astimezone(timezone.utc).date() > action,
            "prediction_archive_lock_after_fda_action": lock.astimezone(timezone.utc).date() > action,
            "historical_prospective_claim": "NOT_ESTABLISHED",
            "eligible_for_independent_prediction_validation": False,
            "reason": "POST_ACTION_ARCHIVE_CANNOT_PROVE_PRE_ACTION_PREDICTION" if after_action
                      else "ORIGINAL_PREDICTION_TIME_NOT_INDEPENDENTLY_VERIFIED",
        })
    return {"cases": results, "eligible_cases": 0, "research_only": True,
            "trading_authorized": False, "historical_accuracy": None}


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m research.fda_archive_chronology_gate archive.json reconstruction.json")
    a = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    b = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    print(json.dumps(audit_archive_chronology(a, b), indent=2))
