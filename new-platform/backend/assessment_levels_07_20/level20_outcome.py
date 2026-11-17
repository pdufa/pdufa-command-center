"""Isolated Level 20 FDA outcome and timing evidence linkage.

Separates goal dates, official action dates and prediction freezes. No outcome
is admitted into pre-action prediction inputs. Never modifies production records.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")
_APP = re.compile(r"(?:NDA|BLA)[0-9]{6}")
_ACTIONS = frozenset({"APPROVAL", "COMPLETE_RESPONSE", "WITHDRAWAL",
                      "OTHER_OFFICIAL_ACTION"})


def _day(value: Any) -> date | None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc)
    except ValueError:
        return None


def validate_level20_outcome(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("nct_id", "application_id", "review_cycle_id", "indication",
                "prediction_version_id", "prediction_frozen_at", "goal_date",
                "official_action_date", "official_action", "official_source_url",
                "source_published_on", "source_retrieved_on")
    missing = sorted(k for k in required if not record.get(k))
    if not isinstance(record.get("nct_id"), str) or not _NCT.fullmatch(record["nct_id"]):
        errors.append("INVALID_EXACT_NCT")
    if not isinstance(record.get("application_id"), str) or not _APP.fullmatch(record["application_id"]):
        errors.append("INVALID_APPLICATION_ID")
    for key in ("review_cycle_id", "indication", "prediction_version_id"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append("INVALID_" + key.upper())
    if record.get("official_action") not in _ACTIONS:
        errors.append("INVALID_OFFICIAL_ACTION")
    if record.get("exact_application_cycle_link_documented") is not True:
        errors.append("EXACT_APPLICATION_CYCLE_LINK_UNDOCUMENTED")
    if record.get("prediction_record_immutable_verified") is not True:
        errors.append("PREDICTION_VERSION_NOT_VERIFIED")
    url = record.get("official_source_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        errors.append("INVALID_OFFICIAL_SOURCE")
    dates = {key: _day(record.get(key)) for key in
             ("goal_date", "official_action_date", "source_published_on", "source_retrieved_on")}
    for key, value in dates.items():
        if value is None:
            errors.append("INVALID_" + key.upper())
    if dates["source_published_on"] and dates["source_retrieved_on"]:
        if dates["source_published_on"] > dates["source_retrieved_on"]:
            errors.append("SOURCE_RETRIEVED_BEFORE_PUBLICATION")
    if dates["official_action_date"] and dates["source_published_on"]:
        if dates["source_published_on"] < dates["official_action_date"]:
            errors.append("SOURCE_PUBLISHED_BEFORE_RECORDED_ACTION")
    frozen = _utc(record.get("prediction_frozen_at"))
    if frozen is None:
        errors.append("INVALID_PREDICTION_FREEZE")
    elif dates["official_action_date"] and frozen.date() >= dates["official_action_date"]:
        errors.append("PREDICTION_NOT_PRE_ACTION")
    if record.get("outcome_exposed_at_prediction") is not False:
        errors.append("PREDICTION_OUTCOME_EXPOSURE_NOT_EXCLUDED")
    timing_days = None
    if not missing and not errors:
        timing_days = (dates["official_action_date"] - dates["goal_date"]).days
    return {
        "level": 20, "engine": "isolated-level20-outcome-timing-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED", "scientific_score": None,
        "fda_prediction": "ABSTAIN", "missing_fields": missing,
        "errors": sorted(set(errors)),
        "action_minus_goal_days": timing_days,
    }
