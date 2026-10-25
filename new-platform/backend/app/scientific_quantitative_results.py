"""Read-only quantitative results inventory from a checksum-verified CT.gov v2 archive.

The values are verbatim *reported* registry values, not independent evidence
validation, positive trial calls, efficacy scores, or FDA approval predictions.
Numerical string parsing is deliberately conservative and never computes
effect direction, p-value thresholds, relative risk, or treatment success.
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from .scientific_investigation_20 import NCT_PATTERN, _lookup

MAX_OUTCOMES = 30
MAX_ANALYSES_PER_OUTCOME = 5
MAX_GROUPS_PER_OUTCOME = 12
MAX_EVENTS_PER_CLASS = 20
MAX_EVENT_GROUP_STATS = 12
MAX_TEXT = 180


def _dict(obj: Any) -> Mapping[str, Any]:
    return obj if isinstance(obj, Mapping) else {}


def _list(obj: Any) -> list:
    return obj if isinstance(obj, list) else []


def _text(value: Any, *, limit: int = MAX_TEXT) -> str | None:
    if not isinstance(value, str):
        return None
    v = value.strip()
    # Do not expose multiline text or arbitrary registry narratives in a compact result.
    if not v:
        return None
    return v[:limit]


def _decimal(value: Any) -> str | None:
    """Normalize finite numeric values only, without inventing precision."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    raw = str(value).strip()
    if not raw or len(raw) > 40:
        return None
    try:
        number = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    return raw if number.is_finite() else None


def _p_value(raw: Any) -> str | None:
    """Preserve reported inequalities: '<0.001' is NOT the exact value .001."""
    if isinstance(raw, bool):
        return None
    v = _text(str(raw), limit=40) if isinstance(raw, (str, int, float)) else None
    if v is None:
        return None
    if v.startswith(("<=", ">=", "<", ">")):
        marker = "<=" if v.startswith("<=") else ">=" if v.startswith(">=") else v[0]
        return v if _decimal(v[len(marker):].strip()) is not None else None
    return v if _decimal(v) is not None else None


def _group_ids(value: Any) -> list[str]:
    return [v[:24] for v in _list(value)[:MAX_GROUPS_PER_OUTCOME]
            if isinstance(v, str) and v][:MAX_GROUPS_PER_OUTCOME]


def _analysis(item: Mapping[str, Any], outcome_index: int, analysis_index: int) -> dict:
    return {
        "analysisNumber": analysis_index,
        "groupIds": _group_ids(item.get("groupIds")),
        "comparisonType": _text(item.get("nonInferiorityType")),
        "method": _text(item.get("statisticalMethod")),
        "parameterType": _text(item.get("paramType")),
        "reportedEstimate": _decimal(item.get("paramValue")),
        "pValueReported": _p_value(item.get("pValue")),
        "confidenceIntervalPercent": _decimal(item.get("ciPctValue")),
        "confidenceIntervalSides": _text(item.get("ciNumSides")),
        "confidenceIntervalLower": _decimal(item.get("ciLowerLimit")),
        "confidenceIntervalUpper": _decimal(item.get("ciUpperLimit")),
        "comments": _text(item.get("otherAnalysisDescription")),
        "sourceFieldPath": ("resultsSection.outcomeMeasuresModule."
                            f"outcomeMeasures[{outcome_index}].analyses[{analysis_index - 1}]"),
        "independentlyVerified": False,
    }


def _outcome(measure: Mapping[str, Any], index: int) -> dict:
    analyses = _list(measure.get("analyses"))
    return {
        "resultIndex": index,
        "outcomeType": _text(measure.get("type")),
        "title": _text(measure.get("title"), limit=240),
        "timeFrame": _text(measure.get("timeFrame")),
        "parameterType": _text(measure.get("paramType")),
        "unit": _text(measure.get("unitOfMeasure")),
        "reportedAnalyses": len(analyses),
        "analyses": [
            _analysis(_dict(a), index, i + 1)
            for i, a in enumerate(analyses[:MAX_ANALYSES_PER_OUTCOME])
        ],
        "groupCount": len(_list(measure.get("groups"))),
        "groups": [
            {"id": _text(_dict(g).get("id"), limit=24),
             "title": _text(_dict(g).get("title"))}
            for g in _list(measure.get("groups"))[:MAX_GROUPS_PER_OUTCOME]
        ],
        "sourceFieldPath": f"resultsSection.outcomeMeasuresModule.outcomeMeasures[{index}]",
        "independentlyVerified": False,
    }


def _event(event: Mapping[str, Any], index: int, source_class: str) -> dict:
    stats = _list(event.get("stats"))
    return {
        "term": _text(event.get("term")),
        "organSystem": _text(event.get("organSystem")),
        "classification": source_class,
        "reportedGroupStats": len(stats),
        "groupStats": [
            {
                "groupId": _text(_dict(group).get("groupId"), limit=24),
                "numAffected": _decimal(_dict(group).get("numAffected")),
                "numAtRisk": _decimal(_dict(group).get("numAtRisk")),
                "numEvents": _decimal(_dict(group).get("numEvents")),
            } for group in stats[:MAX_EVENT_GROUP_STATS]
        ],
        "sourceFieldPath": f"resultsSection.adverseEventsModule.{source_class}[{index}]",
        "independentlyVerified": False,
    }


def reported_quantitative_results(nct_id: str, record: Mapping[str, Any]) -> dict:
    """Read bounded posted outcomes and adverse events; never score/grade efficacy."""
    if not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT ID required")
    if not isinstance(record, Mapping) or _lookup(record, "protocolSection.identificationModule.nctId") != nct_id:
        raise ValueError("Source NCT identity mismatch")

    outcomes_raw = _list(_lookup(record, "resultsSection.outcomeMeasuresModule.outcomeMeasures"))
    adverse = _dict(_lookup(record, "resultsSection.adverseEventsModule"))
    serious_raw = _list(adverse.get("seriousEvents"))
    other_raw = _list(adverse.get("otherEvents"))
    outcome_sample = outcomes_raw[:MAX_OUTCOMES]
    outcomes = [_outcome(_dict(m), i) for i, m in enumerate(outcome_sample)]
    serious = [_event(_dict(e), i, "seriousEvents") for i, e in
               enumerate(serious_raw[:MAX_EVENTS_PER_CLASS])]
    other = [_event(_dict(e), i, "otherEvents") for i, e in
             enumerate(other_raw[:MAX_EVENTS_PER_CLASS])]

    full_analyses = sum(len(_list(_dict(m).get("analyses"))) for m in outcomes_raw)
    represented = sum(len(o["analyses"]) for o in outcomes)
    p_values = sum(bool(a["pValueReported"]) for o in outcomes for a in o["analyses"])
    confidence_intervals = sum(
        a["confidenceIntervalLower"] is not None and
        a["confidenceIntervalUpper"] is not None
        for o in outcomes for a in o["analyses"]
    )
    return {
        "nctId": nct_id,
        "sourceType": "archived_clinicaltrials_gov_api_v2",
        "sourceUrl": "https://clinicaltrials.gov/study/" + nct_id,
        "sourceStatus": "registry_reported_not_independently_verified",
        "hasResultsFlag": record.get("hasResults") is True,
        "outcomeCountTotal": len(outcomes_raw),
        "outcomeCountShown": len(outcomes),
        "analysisCountTotal": full_analyses,
        "analysisCountShown": represented,
        "reportedPValuesShown": p_values,
        "reportedConfidenceIntervalsShown": confidence_intervals,
        "outcomes": outcomes,
        "safety": {
            "seriousEventTermCountTotal": len(serious_raw),
            "seriousEventTermsShown": serious,
            "otherEventTermCountTotal": len(other_raw),
            "otherEventTermsShown": other,
            "adverseEventGroupCount": len(_list(adverse.get("eventGroups"))),
            "denominatorsNotInterpreted": True,
        },
        "truncated": (len(outcomes) < len(outcomes_raw) or represented < full_analyses
                      or len(serious) < len(serious_raw) or len(other) < len(other_raw)),
        "independentlyVerified": False,
        "effectivenessConclusion": None,
        "statisticalSignificanceConclusion": None,
        "approvalProbability": None,
        "note": ("Reported numerical values are copied conservatively from an archived "
                 "ClinicalTrials.gov posting; no p-value threshold, comparator direction, "
                 "confidence-interval interpretation, multiplicity adjustment, independent "
                 "source confirmation, or regulatory prediction is implied."),
    }
