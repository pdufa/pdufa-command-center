#!/usr/bin/env python3
"""Application-level replay audit for the standalone medical intelligence preview.

This module evaluates categorical historical calls. It does not produce a medical
score, numerical FDA probability, forecast, or historical prediction. Source dates
are asserted metadata, not proof that a URL or an archived page was retrieved.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports/deep-medical-intelligence"
FDA_OUTCOMES = frozenset({"Traditional", "Accelerated", "CRL", "Withdrawal", "Indeterminate"})
TIMING_OUTCOMES = frozenset({"ByGoal", "FormalExtension", "MissedWithoutFormal", "Indeterminate"})
APPROVALS = frozenset({"Traditional", "Accelerated"})
DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
FORBIDDEN_PREDICTION_FIELDS = frozenset({
    "actualOutcomeDate", "actualOutcome", "outcomeLabel", "actualTimingOutcome",
    "timingOutcomeDate", "outcomeHistory", "outcomeEvidence", "actualFdaOutcome",
})


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def prediction_id(event):
    """Hash the complete event body; changing any field changes the identifier."""
    body = {k: v for k, v in event.items() if k != "eventId"}
    return "sha256:" + hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def seal_prediction(payload):
    event = copy.deepcopy(payload)
    event.pop("eventId", None)
    event["eventId"] = prediction_id(event)
    return event


def assert_append_only(previous, current):
    """Reject removal, reordering, mutation, duplicate IDs, and invalid hashes."""
    if not isinstance(previous, list) or not isinstance(current, list):
        raise ValueError("PREDICTION_HISTORY_MUST_BE_LIST")
    if len(current) < len(previous) or current[:len(previous)] != previous:
        raise ValueError("PREDICTION_HISTORY_NOT_APPEND_ONLY")
    seen = set()
    for event in current:
        if not isinstance(event, dict) or event.get("eventId") != prediction_id(event):
            raise ValueError("PREDICTION_EVENT_HASH_MISMATCH")
        if event["eventId"] in seen:
            raise ValueError("DUPLICATE_PREDICTION_EVENT_ID")
        seen.add(event["eventId"])


def append_prediction(history, payload):
    """Return a new list, preserving the supplied ledger and every prior value."""
    assert_append_only([], history)
    event = copy.deepcopy(payload) if payload.get("eventId") else seal_prediction(payload)
    updated = copy.deepcopy(history) + [event]
    assert_append_only(history, updated)
    return updated


def _instant(value, *, end_of_day=False, require_timestamp=False):
    if not isinstance(value, str):
        raise ValueError("DATE_OR_TIMESTAMP_REQUIRED")
    if DATE_ONLY.fullmatch(value):
        if require_timestamp:
            raise ValueError("TIMEZONE_AWARE_PREDICTION_TIMESTAMP_REQUIRED")
        day = date.fromisoformat(value)
        return datetime.combine(day, time.max if end_of_day else time.min, timezone.utc)
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("TIMEZONE_REQUIRED")
    return stamp.astimezone(timezone.utc)


def application_key(record):
    """NCTs are supporting metadata, never the unit used to match decisions."""
    application = record.get("applicationId")
    cycle = record.get("reviewCycle")
    if not isinstance(application, str) or not application.strip():
        raise ValueError("EXACT_APPLICATION_ID_REQUIRED")
    if isinstance(cycle, bool) or not isinstance(cycle, (str, int)) or not str(cycle).strip():
        raise ValueError("EXACT_REVIEW_CYCLE_REQUIRED")
    return application.strip(), str(cycle).strip()


def audit_sources(sources, key, cutoff, *, allow_synthetic=False):
    """Validate temporal and identity metadata without fetching or grading sources."""
    errors, observations = [], []
    if not isinstance(sources, list) or not sources:
        return ["PUBLIC_SOURCE_EVIDENCE_REQUIRED"], observations
    for index, source in enumerate(sources):
        prefix = "source[" + str(index) + "]:"
        if not isinstance(source, dict):
            errors.append(prefix + "SOURCE_MUST_BE_OBJECT")
            continue
        try:
            if application_key(source) != key:
                errors.append(prefix + "SOURCE_APPLICATION_OR_REVIEW_CYCLE_MISMATCH")
        except ValueError as exc:
            errors.append(prefix + str(exc))
        url = source.get("sourceUrl", "")
        parsed = urlsplit(url) if isinstance(url, str) else urlsplit("")
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            errors.append(prefix + "PUBLIC_HTTPS_SOURCE_URL_REQUIRED")
        elif not allow_synthetic and (parsed.hostname in {"example.com", "example.org", "example.net"}
                                      or parsed.hostname.endswith((".example", ".test", ".invalid", ".localhost"))):
            errors.append(prefix + "SYNTHETIC_SOURCE_URL_IN_PRODUCTION")
        try:
            public = _instant(source.get("publicEvidenceDate"), end_of_day=True)
            if public > cutoff:
                errors.append(prefix + "SOURCE_PUBLIC_AFTER_CUTOFF")
            if source.get("contentAsOf") and _instant(source["contentAsOf"], end_of_day=True) > cutoff:
                errors.append(prefix + "SOURCE_CONTENT_AFTER_CUTOFF")
        except (ValueError, TypeError):
            errors.append(prefix + "VALID_PUBLIC_EVIDENCE_DATE_REQUIRED")
        if not isinstance(source.get("observation"), str) or not source["observation"].strip():
            errors.append(prefix + "CITED_OBSERVATION_REQUIRED")
        observations.append({
            "sourceUrl": url, "publicEvidenceDate": source.get("publicEvidenceDate"),
            "retrievalVerification": "NOT_PERFORMED_BY_BACKTEST",
        })
    return errors, observations


def _ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None}


def _records(payload):
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("HISTORY_REQUIRES_RECORDS_ARRAY")
    return records


def _timing_check(prediction, outcome, cutoff, *, allow_synthetic=False):
    """Check timing against the goal frozen in the prediction, not a revised goal."""
    label = outcome.get("timingLabel", "Indeterminate")
    if label == "Indeterminate":
        return ["TIMING_OUTCOME_INDETERMINATE"]
    if label not in TIMING_OUTCOMES:
        return ["INVALID_TIMING_OUTCOME_LABEL"]
    if outcome.get("timingAdjudicationStatus", outcome.get("adjudicationStatus")) != "ADJUDICATED":
        return ["TIMING_NOT_ADJUDICATED"]
    errors = []
    try:
        predicted_at = _instant(prediction["predictionTimestamp"], require_timestamp=True)
        goal = date.fromisoformat(prediction["goalDate"])
        if outcome.get("goalDate") != prediction["goalDate"]:
            errors.append("TIMING_GOAL_DOES_NOT_MATCH_FROZEN_PREDICTION_GOAL")
        observed_at = _instant(outcome.get("timingOutcomeDate"), end_of_day=False)
        if not predicted_at < observed_at:
            errors.append("TIMING_OBSERVATION_NOT_AFTER_PREDICTION")
        if observed_at > cutoff:
            errors.append("TIMING_OBSERVATION_AFTER_REPORT_CUTOFF")
        observed_day = observed_at.date()
        if label == "ByGoal":
            action = _instant(outcome.get("actualOutcomeDate"))
            if outcome.get("outcomeLabel") not in FDA_OUTCOMES - {"Indeterminate"}:
                errors.append("BY_GOAL_REQUIRES_KNOWN_ACTION")
            if action.date() > goal or action > observed_at:
                errors.append("BY_GOAL_ACTION_AFTER_GOAL_OR_OBSERVATION")
        elif label == "MissedWithoutFormal":
            if observed_day <= goal:
                errors.append("MISSED_GOAL_REQUIRES_OBSERVATION_AFTER_GOAL")
            if not outcome.get("absenceOfFormalExtensionReviewed"):
                errors.append("NO_FORMAL_EXTENSION_REQUIRES_EXPLICIT_REVIEW")
            action_date = outcome.get("actualOutcomeDate")
            if action_date and _instant(action_date).date() <= goal:
                errors.append("MISSED_GOAL_CONFLICTS_WITH_KNOWN_ACTION")
        else:
            extension = outcome.get("formalExtension")
            if not isinstance(extension, dict):
                errors.append("FORMAL_EXTENSION_DOCUMENTATION_REQUIRED")
            else:
                extension_at = _instant(extension.get("publicEvidenceDate"), end_of_day=True)
                if extension.get("originalGoalDate") != prediction["goalDate"]:
                    errors.append("FORMAL_EXTENSION_ORIGINAL_GOAL_MISMATCH")
                if date.fromisoformat(extension.get("newGoalDate", "")) <= goal:
                    errors.append("FORMAL_EXTENSION_REVISED_GOAL_MUST_BE_LATER")
                if extension_at <= predicted_at:
                    errors.append("EXTENSION_ALREADY_KNOWN_AT_PREDICTION")
                if extension_at.date() > observed_day:
                    errors.append("FORMAL_EXTENSION_SOURCE_AFTER_TIMING_OBSERVATION")
                extension_errors, _ = audit_sources([extension], application_key(outcome), cutoff,
                                                     allow_synthetic=allow_synthetic)
                errors.extend(extension_errors)
        source_errors, _ = audit_sources(outcome.get("timingSources"), application_key(outcome), cutoff,
                                         allow_synthetic=allow_synthetic)
        errors.extend(source_errors)
    except (KeyError, ValueError, TypeError):
        errors.append("VALID_TIMING_DATES_REQUIRED")
    return errors


def evaluate_history(predictions, outcomes, *, as_of=None, include_synthetic=False):
    """Replay the earliest eligible immutable event per application/review cycle.

    Withdrawals remain a distinct categorical outcome. They are excluded from CRL
    binary diagnostics because application withdrawal is not an adjudicated FDA
    approval/CRL decision. Abstentions and unavailable outcomes are never negatives.
    """
    prediction_rows, outcome_rows = _records(predictions), _records(outcomes)
    cutoff = _instant(as_of, end_of_day=True) if as_of else datetime.now(timezone.utc)
    issues, exclusions, source_audit = [], [], []
    outcome_index, duplicate_outcomes = {}, set()
    for index, outcome in enumerate(outcome_rows):
        try:
            key = application_key(outcome)
        except (ValueError, AttributeError) as exc:
            issues.append({"kind": "OUTCOME_SCHEMA", "index": index, "error": str(exc)})
            continue
        if key in outcome_index:
            duplicate_outcomes.add(key)
            issues.append({"kind": "OUTCOME_IDENTITY", "application": list(key),
                           "error": "DUPLICATE_OUTCOME_APPLICATION_REVIEW_CYCLE"})
        outcome_index[key] = outcome

    candidates, seen_ids = {}, set()
    for index, prediction in enumerate(prediction_rows):
        errors = []
        if not isinstance(prediction, dict):
            issues.append({"kind": "PREDICTION_SCHEMA", "index": index, "error": "PREDICTION_MUST_BE_OBJECT"})
            continue
        event_id = prediction.get("eventId")
        if event_id in seen_ids:
            errors.append("DUPLICATE_PREDICTION_EVENT_ID")
        seen_ids.add(event_id)
        try:
            if event_id != prediction_id(prediction):
                errors.append("PREDICTION_EVENT_HASH_MISMATCH")
        except (ValueError, TypeError):
            errors.append("PREDICTION_EVENT_NOT_CANONICAL_JSON")
        if not include_synthetic and prediction.get("isSynthetic"):
            exclusions.append({"eventId": event_id, "reasons": ["SYNTHETIC_PREDICTION_EXCLUDED"]})
            continue
        if FORBIDDEN_PREDICTION_FIELDS & prediction.keys():
            errors.append("OUTCOME_DATA_PRESENT_IN_PREDICTION")
        try:
            key = application_key(prediction)
            stamp = _instant(prediction.get("predictionTimestamp"), require_timestamp=True)
            if stamp > cutoff:
                errors.append("PREDICTION_AFTER_REPORT_CUTOFF")
            if prediction.get("outcomePrediction") not in FDA_OUTCOMES:
                errors.append("INVALID_FDA_PREDICTION_LABEL")
            if prediction.get("timingPrediction") not in TIMING_OUTCOMES:
                errors.append("INVALID_TIMING_PREDICTION_LABEL")
            source_errors, audit = audit_sources(prediction.get("evidence"), key, stamp,
                                                 allow_synthetic=include_synthetic)
            errors.extend(source_errors)
            source_audit.extend({"eventId": event_id, **row} for row in audit)
            if key in duplicate_outcomes:
                errors.append("AMBIGUOUS_OUTCOME_APPLICATION_REVIEW_CYCLE")
        except (ValueError, TypeError) as exc:
            errors.append(str(exc))
        if errors:
            issues.extend({"kind": "PREDICTION_QA", "eventId": event_id, "error": error} for error in errors)
            exclusions.append({"eventId": event_id, "reasons": errors})
            continue
        candidates.setdefault(key, []).append((stamp, index, prediction))

    cases, fda_abstentions, timing_abstentions, fda_excluded, timing_excluded = [], [], [], [], []
    confusion = Counter({"truePositive": 0, "falsePositive": 0, "trueNegative": 0, "falseNegative": 0})
    timing_confusion, categorical = Counter(), Counter()
    for key, events in sorted(candidates.items()):
        events.sort(key=lambda row: (row[0], row[2]["eventId"]))
        _, _, prediction = events[0]
        for _, _, later in events[1:]:
            exclusions.append({"eventId": later["eventId"], "application": list(key),
                               "reasons": ["LATER_SNAPSHOT_SAME_APPLICATION_REVIEW_CYCLE"]})
        event_id = prediction["eventId"]
        outcome = outcome_index.get(key)
        case = {"applicationId": key[0], "reviewCycle": key[1], "eventId": event_id,
                "predictionTimestamp": prediction["predictionTimestamp"],
                "nctIds": prediction.get("nctIds", []), "fdaEligible": False, "timingEligible": False}
        cases.append(case)
        if not outcome or (outcome.get("isSynthetic") and not include_synthetic):
            reason = "NO_MATCHING_ADJUDICATED_OUTCOME" if not outcome else "SYNTHETIC_OUTCOME_EXCLUDED"
            fda_excluded.append({"eventId": event_id, "reason": reason})
            timing_excluded.append({"eventId": event_id, "reason": reason})
            continue
        label = outcome.get("outcomeLabel", "Indeterminate")
        fda_errors = []
        if label not in FDA_OUTCOMES:
            fda_errors.append("INVALID_FDA_OUTCOME_LABEL")
        elif label == "Indeterminate":
            fda_errors.append("FDA_OUTCOME_INDETERMINATE")
        if outcome.get("adjudicationStatus") != "ADJUDICATED":
            fda_errors.append("FDA_OUTCOME_NOT_ADJUDICATED")
        try:
            action = _instant(outcome.get("actualOutcomeDate"))
            if not _instant(prediction["predictionTimestamp"], require_timestamp=True) < action:
                fda_errors.append("PREDICTION_NOT_BEFORE_ACTUAL_OUTCOME")
            if action > cutoff:
                fda_errors.append("FDA_OUTCOME_AFTER_REPORT_CUTOFF")
        except (ValueError, TypeError):
            fda_errors.append("VALID_ACTUAL_OUTCOME_DATE_REQUIRED")
        source_errors, audit = audit_sources(outcome.get("sources"), key, cutoff,
                                             allow_synthetic=include_synthetic)
        fda_errors.extend(source_errors)
        source_audit.extend({"outcomeApplication": list(key), **row} for row in audit)
        call = prediction["outcomePrediction"]
        if fda_errors:
            fda_excluded.append({"eventId": event_id, "reasons": fda_errors})
        else:
            case.update(fdaEligible=True, actualOutcome=label, predictedOutcome=call)
            categorical[(label, call)] += 1
            if call == "Indeterminate":
                fda_abstentions.append(event_id)
            if label == "Withdrawal":
                fda_excluded.append({"eventId": event_id, "reason": "WITHDRAWAL_EXCLUDED_FROM_CRL_BINARY"})
            elif call not in APPROVALS | {"CRL"}:
                fda_excluded.append({"eventId": event_id, "reason": "NO_BINARY_CRL_CALL"})
            elif label == "CRL":
                confusion["truePositive" if call == "CRL" else "falseNegative"] += 1
            else:
                confusion["falsePositive" if call == "CRL" else "trueNegative"] += 1
        timing_errors = _timing_check(prediction, outcome, cutoff, allow_synthetic=include_synthetic)
        timing_call = prediction["timingPrediction"]
        if timing_errors:
            timing_excluded.append({"eventId": event_id, "reasons": timing_errors})
        elif timing_call == "Indeterminate":
            timing_abstentions.append(event_id)
        else:
            case.update(timingEligible=True, actualTiming=outcome["timingLabel"], predictedTiming=timing_call)
            timing_confusion[(outcome["timingLabel"], timing_call)] += 1

    tp, fp = confusion["truePositive"], confusion["falsePositive"]
    tn, fn = confusion["trueNegative"], confusion["falseNegative"]
    correct_timing = sum(v for (actual, predicted), v in timing_confusion.items() if actual == predicted)
    return {
        "schemaVersion": 1, "generatedAt": datetime.now(timezone.utc).isoformat(),
        "asOf": cutoff.isoformat(), "status": "QA_ISSUES" if issues else "AUDITED",
        "method": "EARLIEST_ELIGIBLE_EVENT_PER_EXACT_APPLICATION_REVIEW_CYCLE",
        "sourceValidation": "METADATA_IDENTITY_AND_TIME_ONLY_NOT_LIVE_URL_VERIFICATION",
        "syntheticFixturesIncluded": include_synthetic,
        "inputCounts": {"predictionEvents": len(prediction_rows), "outcomeRecords": len(outcome_rows)},
        "evaluatedApplicationCycles": len(cases), "cases": cases,
        "fda": {
            "actualOutcomeCounts": dict(Counter(c["actualOutcome"] for c in cases if c["fdaEligible"])),
            "categoricalConfusion": [{"actual": a, "predicted": p, "count": v}
                                     for (a, p), v in sorted(categorical.items())],
            "crlBinaryDenominator": tp + fp + tn + fn, "confusion": dict(confusion),
            "crlSensitivity": _ratio(tp, tp + fn), "crlSpecificity": _ratio(tn, tn + fp),
            "crlPrecision": _ratio(tp, tp + fp),
            "abstentionCount": len(fda_abstentions), "abstentions": fda_abstentions,
            "excluded": fda_excluded,
            "negativeClass": "ADJUDICATED_TRADITIONAL_OR_ACCELERATED_APPROVAL_ONLY",
        },
        "timing": {"denominator": sum(timing_confusion.values()),
                   "accuracy": _ratio(correct_timing, sum(timing_confusion.values())),
                   "confusion": [{"actual": a, "predicted": p, "count": v}
                                 for (a, p), v in sorted(timing_confusion.items())],
                   "abstentionCount": len(timing_abstentions), "abstentions": timing_abstentions,
                   "excluded": timing_excluded},
        "predictionExclusions": exclusions, "qaIssues": issues, "sourceAudit": source_audit,
        "limitations": [
            "No historical prediction is reconstructed from known outcomes.",
            "Source publication dates and application identities require external provenance review.",
            "Date-only public evidence is available at UTC day end; date-only action dates begin at UTC day start.",
            "Multiple trials supporting one application do not create additional independent outcomes.",
            "Diagnostic proportions describe this adjudicated cohort and are not FDA approval probabilities.",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", required=True)
    parser.add_argument("--prediction-history", type=Path, default=REPORT_DIR / "prediction-history.json")
    parser.add_argument("--outcome-history", type=Path, default=REPORT_DIR / "outcome-history.json")
    parser.add_argument("--output", type=Path, default=REPORT_DIR / "backtest-report.json")
    parser.add_argument("--as-of")
    args = parser.parse_args(argv)
    try:
        predictions = json.loads(args.prediction_history.read_text())
        outcomes = json.loads(args.outcome_history.read_text())
        report = evaluate_history(predictions, outcomes, as_of=args.as_of)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, "Backtest input error: " + str(exc) + "\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"status": report["status"], "output": str(args.output),
                      "evaluatedApplicationCycles": report["evaluatedApplicationCycles"],
                      "crlBinaryDenominator": report["fda"]["crlBinaryDenominator"],
                      "timingDenominator": report["timing"]["denominator"],
                      "qaIssueCount": len(report["qaIssues"])}))
    return 1 if report["qaIssues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
