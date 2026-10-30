"""Audit six historical research reconstructions without validating forecasts.

The conservative research window is not a recovered prediction timestamp.
Source observations remain unadjudicated candidates, including SEC disclosures.
No caller-supplied flag, lock name or source URL can certify FDA accuracy here.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
import re
from urllib.parse import urlsplit


QUESTION_IDS = tuple(f"S{i:02d}" for i in range(1, 41))
PRIORITY_APPLICATIONS = {
    "NVAX|2025-04-01": "BLA125817",
    "UNCY|2025-06-28": "NDA218607",
    "TNXP|2025-08-15": "NDA219428",
    "BCRX|2025-12-12": "NDA219776",
    "CORT|2025-12-30": "NDA219398",
    "VNDA|2025-12-30": "NDA220152",
}
SOURCE_HOSTS = frozenset({"sec.gov", "www.sec.gov", "fda.gov", "www.fda.gov",
                          "accessdata.fda.gov", "www.accessdata.fda.gov", "download.open.fda.gov"})
SEC_HOSTS = frozenset({"sec.gov", "www.sec.gov"})
HASH = re.compile(r"[0-9a-f]{64}\Z")
CERTIFICATION_FLAGS = frozenset({
    "independently_reviewed", "independently_certified", "certified", "model_validated",
    "eligible_for_training", "model_eligible", "prediction_ready", "trading_authorized",
    "predecision_inputs_verified", "program_family_disjoint_verified",
    "sampling_denominator_verified", "independent_review_complete",
})
UNAVAILABLE_NUMBERS = frozenset({
    "approval_probability", "nonapproval_probability", "pass_probability", "fail_probability",
    "probability", "prediction_confidence", "scientific_score",
})


def _day(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO date") from error


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 6000:
        raise ValueError(f"{field} must be nonempty bounded text")
    return value.strip()


def _source_url(value):
    if not isinstance(value, str) or any(character.isspace() for character in value):
        raise ValueError("source_url must be a public official FDA or SEC HTTPS URL")
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == "https" and parsed.hostname in SOURCE_HOSTS
                 and parsed.username is None and parsed.password is None
                 and parsed.port is None and not parsed.fragment
                 and parsed.path not in ("", "/"))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("source_url must be a public official FDA or SEC HTTPS URL")
    return parsed


def _sequence(value, field):
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{field} must be a sequence")
    return list(value)


def _filing_index(value, source):
    """Require the index of the same accession, not a generic SEC-host claim.

    This validates citation identity only. A source reviewer must still inspect
    the actual filing index and its acceptance/publication chronology.
    """
    index = _source_url(value)
    if index.hostname not in SEC_HOSTS or index.query:
        raise ValueError("SEC availability requires the matching official filing index")
    directory = re.fullmatch(r"(/Archives/edgar/data/[0-9]+/([0-9]{18})/)[^/]+", source.path)
    if directory is None or not index.path.startswith(directory[1]):
        raise ValueError("SEC availability index must match the source accession directory")
    accession = directory[2]
    dashed = accession[:10] + "-" + accession[10:12] + "-" + accession[12:]
    if not re.fullmatch(re.escape(directory[1] + dashed) + r"-index\.html?", index.path):
        raise ValueError("SEC availability requires the matching official filing index")
    return value


def _no_promotions(value):
    """Reject self-certification, including numeric false/true aliases."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in CERTIFICATION_FLAGS and item is not False and item is not None:
                raise ValueError("reconstruction input cannot self-certify evidence or model readiness")
            if key in UNAVAILABLE_NUMBERS and item is not None:
                raise ValueError("reconstruction input cannot supply unvalidated probabilities or scores")
            _no_promotions(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _no_promotions(item)


def _hash_or_none(value, field):
    if value is not None and (not isinstance(value, str) or not HASH.fullmatch(value)):
        raise ValueError(f"{field} must be an actual SHA-256 or null")
    return value


def _timestamp_or_none(value, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an aware ISO timestamp or null")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timezone missing")
    except ValueError as error:
        raise ValueError(f"{field} must be an aware ISO timestamp or null") from error
    return timestamp.astimezone(timezone.utc)


def _provenance(provenance, cutoff, event_key):
    if not isinstance(provenance, Mapping):
        raise ValueError("prediction_provenance must be an object")
    blockers = ["original_prediction_freeze_not_independently_proven",
                "frozen_feature_sources_not_independently_verified",
                "program_family_disjointness_not_independently_verified",
                "representative_sampling_denominator_not_independently_verified",
                "independent_scientific_and_source_review_incomplete"]
    model_hash = _hash_or_none(provenance.get("model_hash"), "model_hash")
    lock_hash = _hash_or_none(provenance.get("lock_model_hash"), "lock_model_hash")
    if model_hash is None:
        blockers.append("missing_linked_model_hash")
    if _hash_or_none(provenance.get("feature_snapshot_hash"), "feature_snapshot_hash") is None:
        blockers.append("missing_frozen_feature_hash")
    lock_keys = provenance.get("lock_event_keys")
    if lock_keys is None:
        blockers.append("missing_exact_prediction_lock_membership")
    else:
        lock_keys = _sequence(lock_keys, "lock_event_keys")
        if any(not isinstance(key, str) for key in lock_keys):
            raise ValueError("lock_event_keys must contain exact event strings")
        if (not lock_keys or len(lock_keys) != len(set(lock_keys)) or event_key not in lock_keys):
            blockers.append("prediction_lock_membership_mismatch")
        if model_hash is None or lock_hash is None or model_hash != lock_hash:
            blockers.append("prediction_lock_model_hash_mismatch_or_missing")
    training_end = provenance.get("model_training_end")
    if training_end is None:
        blockers.append("missing_model_training_chronology")
    elif _day(training_end, "model_training_end") >= cutoff:
        blockers.append("supplied_model_training_not_before_reconstruction_cutoff")
    for field in ("model_frozen_at", "prediction_generated_at", "prediction_lock_created_at"):
        timestamp = _timestamp_or_none(provenance.get(field), field)
        if timestamp is None:
            blockers.append("missing_" + field)
        elif timestamp.date() > cutoff:
            blockers.append(field + "_after_reconstruction_cutoff")
    return blockers


def _observations(records, cutoff, as_of, question_ids, original_cutoff):
    records = _sequence(records, "observations")
    seen = set()
    result = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("observation must be an object")
        source_id = _text(record.get("id"), "observation id")
        if source_id in seen:
            raise ValueError("duplicate observation id within a case")
        seen.add(source_id)
        parsed = _source_url(record.get("source_url"))
        finding = _text(record.get("finding"), "finding")
        questions = _sequence(record.get("science_question_ids"), "science_question_ids")
        if any(not isinstance(key, str) or key not in question_ids for key in questions) or len(set(questions)) != len(questions):
            raise ValueError("invalid or duplicate SCIENCE question identity")
        basis = record.get("availability_basis")
        if basis not in {"SEC_FILING_INDEX", "PRINTED_DATE_ONLY", "UNKNOWN"}:
            raise ValueError("unknown availability basis")
        role = record.get("source_role")
        if role not in {"PREDECISION_RESEARCH", "OUTCOME_ONLY"}:
            raise ValueError("unknown source role")
        published = record.get("available_on")
        available = None if published is None else _day(published, "available_on")
        if basis == "SEC_FILING_INDEX" and parsed.hostname not in SEC_HOSTS:
            raise ValueError("SEC filing-index availability requires a SEC source")
        index_url = None
        if basis == "SEC_FILING_INDEX":
            index_url = _filing_index(record.get("availability_source_url"), parsed)
        if role == "OUTCOME_ONLY":
            status = "EXCLUDED_OUTCOME_ONLY"
        elif available is None or basis == "UNKNOWN":
            status = "QUARANTINED_UNKNOWN_AVAILABILITY"
        elif available > as_of:
            status = "EXCLUDED_AFTER_AUDIT_SNAPSHOT"
        elif available > cutoff:
            status = "EXCLUDED_AFTER_RECONSTRUCTION_CUTOFF"
        elif basis == "PRINTED_DATE_ONLY":
            status = "QUARANTINED_PRINTED_DATE_ONLY"
        else:
            status = "PREDECISION_RESEARCH_CANDIDATE"
        if original_cutoff is None:
            original_comparison = "ORIGINAL_CUTOFF_UNKNOWN"
        elif available is None:
            original_comparison = "SUPPLIED_SOURCE_DATE_UNKNOWN"
        elif available > original_cutoff:
            original_comparison = "AFTER_SUPPLIED_ORIGINAL_CUTOFF"
        else:
            original_comparison = "ON_OR_BEFORE_SUPPLIED_ORIGINAL_CUTOFF"
        result.append({
            "source_id": source_id, "source_url": record["source_url"],
            "available_on": published, "availability_basis": basis,
            "availability_source_url": index_url,
            "source_role": role, "classification": status, "finding": finding,
            "science_question_ids": questions, "independently_reviewed": False,
            "scope": "RECONSTRUCTED_RESEARCH_ONLY_NOT_A_VERIFIED_FROZEN_FEATURE",
            "supplied_source_date_vs_original_cutoff": original_comparison,
            "eligible_for_frozen_prediction": False,
        })
    return result


def _insufficient():
    return {"status": "INSUFFICIENT_EVIDENCE", "pass_probability": None,
            "fail_probability": None, "prediction_confidence": None,
            "model_validated": False, "trading_authorized": False}


def audit_reconstructions(packet, history_rows, *, as_of: date, question_ids=QUESTION_IDS):
    """Audit linked research windows; never certify empirical FDA performance."""
    if type(as_of) is not date:
        raise ValueError("as_of must be a date")
    question_ids = _sequence(question_ids, "question_ids")
    if (len(question_ids) != 40 or any(not isinstance(key, str) for key in question_ids)
            or set(question_ids) != set(QUESTION_IDS)):
        raise ValueError("the existing 40 SCIENCE question identities are required")
    if (not isinstance(packet, Mapping) or type(packet.get("schema_version")) is not int
            or packet.get("schema_version") != 1 or packet.get("research_only") is not True):
        raise ValueError("version 1 research-only reconstruction packet required")
    _no_promotions(packet)
    cases = _sequence(packet.get("cases"), "cases")
    if len(cases) != 6 or any(not isinstance(case, Mapping) for case in cases):
        raise ValueError("exactly six case objects required")
    case_keys = [case.get("event_key") for case in cases]
    if any(not isinstance(key, str) for key in case_keys) or set(case_keys) != set(PRIORITY_APPLICATIONS):
        raise ValueError("exact six priority event identities required without duplicates")
    history_rows = _sequence(history_rows, "history_rows")
    if any(not isinstance(row, Mapping) for row in history_rows):
        raise ValueError("history rows must be objects")
    history_counts = Counter(row.get("event_key") for row in history_rows
                             if isinstance(row.get("event_key"), str))
    reports = []
    for case in cases:
        event_key = case["event_key"]
        if history_counts[event_key] != 1:
            raise ValueError("each priority case must match one unique history event")
        history = next(row for row in history_rows if row.get("event_key") == event_key)
        ticker, goal_text = event_key.split("|")
        if history.get("ticker") != ticker or history.get("pdufa_date") != goal_text:
            raise ValueError("history ticker/goal does not match the exact event")
        if case.get("application_id") != PRIORITY_APPLICATIONS[event_key]:
            raise ValueError("case application does not match the priority event")
        for field in ("indication", "program_family"):
            _text(case.get(field), field)
        goal = _day(case.get("legacy_goal_date"), "legacy_goal_date")
        action = _day(case.get("action_date"), "action_date")
        cutoff = _day(case.get("reconstruction_cutoff"), "reconstruction_cutoff")
        if goal.isoformat() != goal_text:
            raise ValueError("legacy goal must match the unchanged history event")
        if cutoff != min(goal, action) - timedelta(days=1):
            raise ValueError("reconstruction cutoff must precede the earlier goal/action by one day")
        if action > as_of:
            raise ValueError("historical action must not follow the audit snapshot")
        original = case.get("original_prediction_cutoff")
        original_date = None
        blockers = _provenance(case.get("prediction_provenance"), cutoff, event_key)
        if original is None:
            blockers.append("original_prediction_cutoff_unavailable")
        else:
            original_date = _day(original, "original_prediction_cutoff")
            if original_date >= action:
                blockers.append("original_prediction_cutoff_not_predecision")
            if original_date > cutoff:
                blockers.append("original_prediction_cutoff_after_legacy_research_window")
        observations = _observations(case.get("observations"), cutoff, as_of, set(question_ids), original_date)
        counts = Counter(source["classification"] for source in observations)
        candidates = [source for source in observations
                      if source["classification"] == "PREDECISION_RESEARCH_CANDIDATE"]
        factors = {}
        for field in ("missing_documents", "supporting_factors", "opposing_factors"):
            factors[field] = [_text(item, field) for item in _sequence(case.get(field), field)]
        precedents = _sequence(case.get("related_precedents"), "related_precedents")
        if any(not isinstance(item, Mapping) for item in precedents):
            raise ValueError("related precedents must be source-linked research objects")
        for precedent in precedents:
            if "source_url" in precedent:
                _source_url(precedent["source_url"])
        if factors["missing_documents"]:
            blockers.append("required_source_documents_incomplete")
        if not candidates:
            blockers.append("no_dated_predecision_research_candidates")
        other_issuer_events = sorted(row["event_key"] for row in history_rows
                                    if row.get("ticker") == ticker and row.get("event_key") != event_key
                                    and isinstance(row.get("event_key"), str))
        reports.append({
            "event_key": event_key, "application_id": case["application_id"],
            "indication": case["indication"], "program_family": case["program_family"],
            "legacy_goal_date": goal.isoformat(), "action_date": action.isoformat(),
            "reconstruction_cutoff": cutoff.isoformat(),
            "original_prediction_cutoff": original,
            "cutoff_scope": "CONSERVATIVE_RESEARCH_WINDOW_NOT_RECOVERED_PREDICTION_FREEZE",
            "legacy_goal_differs_from_action": goal != action,
            "source_classification": observations, "source_classification_counts": dict(sorted(counts.items())),
            "predecision_research_candidate_count": len(candidates),
            "frozen_prediction_source_count": 0,
            "independently_certified_assessments": 0,
            "science_worklist_scope": "CONSERVATIVE_RESEARCH_WINDOW_NOT_ORIGINAL_FORECAST_FEATURES",
            "science_worklist": [{"question_id": question,
                                  "source_ids": [source["source_id"] for source in candidates
                                                 if question in source["science_question_ids"]],
                                  "status": "NOT_CERTIFIED", "scientific_score": None}
                                 for question in question_ids],
            "depth_worklist": [{"depth_level": level, "status": "NOT_CERTIFIED"}
                               for level in range(1, 21)],
            "issuer_history_events_for_program_review": other_issuer_events,
            "issuer_overlap_is_not_program_identity": True,
            "related_precedents": [dict(item) for item in precedents],
            **factors, "blockers": sorted(set(blockers)),
            "eligible_for_validation": False, "model_eligible": False,
            "outcome": _insufficient(), "main": _insufficient(),
        })
    return {
        "schema_version": 1, "research_only": True, "as_of": as_of.isoformat(),
        "history_records": len(history_rows), "priority_cases_analyzed": len(reports),
        "case_reports": reports, "validated_cases": 0, "eligible_for_validation": 0,
        "independently_certified_assessments": 0,
        "metrics": {key: None for key in ("accuracy", "balanced_accuracy", "brier_score",
                                          "log_loss", "auroc", "calibration", "confidence_intervals", "coverage")},
        "coverage_status": "NOT_MEASURED_NO_VALIDATED_FORECASTS",
        "outcome": _insufficient(), "main": _insufficient(), "trading_authorized": False,
    }
