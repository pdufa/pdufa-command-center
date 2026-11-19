"""Score locked binary FDA forecasts and export spreadsheet-ready reports."""

import csv
import json
from math import sqrt
from pathlib import Path
from statistics import NormalDist


LEVELS = tuple(f"L{number:02d}" for number in range(1, 7))
OUTCOMES = ("APPROVE", "CRL")
PREDICTIONS = (*OUTCOMES, "ABSTAIN")
RESULT_FIELDS = (
    "event_id", "ticker", "drug", "indication", "decision_date", "cutoff_date",
    "level", "prediction", "reason", "actual_outcome", "correct",
    "lock_sha256",
)


def wilson_interval(correct, answered):
    if not answered:
        return None, None
    proportion = correct / answered
    z = NormalDist().inv_cdf(0.975)
    adjustment = z * z / answered
    denominator = 1 + adjustment
    center = (proportion + adjustment / 2) / denominator
    margin = z * sqrt(
        proportion * (1 - proportion) / answered + adjustment / (4 * answered)
    ) / denominator
    lower = 0.0 if correct == 0 else center - margin
    upper = 1.0 if correct == answered else center + margin
    return lower, upper


def prediction_grid(predictions):
    event_ids = set()
    seen = set()
    for row in predictions:
        event_id = row["event_id"]
        level = row["level"]
        key = (event_id, level)
        if not isinstance(event_id, str) or not event_id or event_id != event_id.strip():
            raise ValueError(f"Invalid locked event ID: {event_id!r}")
        if level not in LEVELS or row["prediction"] not in PREDICTIONS:
            raise ValueError(f"Unsupported prediction or level for {key}")
        if key in seen:
            raise ValueError(f"Duplicate locked assessment: {key}")
        seen.add(key)
        event_ids.add(event_id)
    if not event_ids or len(seen) != len(event_ids) * len(LEVELS):
        raise ValueError("Prediction lock must contain all six levels for every event")
    return event_ids


def verified_truth(outcomes, event_ids):
    truth = {}
    for row in outcomes:
        event_id = row.get("event_id")
        if not event_id or not event_id.strip() or event_id != event_id.strip():
            raise ValueError("Outcome row has a missing or invalid event_id")
        if event_id in truth:
            raise ValueError(f"Duplicate outcome: {event_id}")
        outcome = (row.get("actual_outcome") or "").strip().upper()
        if outcome not in OUTCOMES:
            raise ValueError(f"Unsupported outcome for {event_id}: {outcome!r}")
        truth[event_id] = outcome
    if set(truth) != event_ids:
        missing = sorted(event_ids - truth.keys())
        unexpected = sorted(truth.keys() - event_ids)
        raise ValueError(
            f"Event IDs differ between prediction lock and outcomes. "
            f"Missing: {missing}. Unexpected: {unexpected}."
        )
    return truth


def assessment_results(predictions, truth, lock_digest):
    results = []
    for row in predictions:
        outcome = truth[row["event_id"]]
        correct = None if row["prediction"] == "ABSTAIN" else row["prediction"] == outcome
        results.append({
            **{field: row.get(field) for field in RESULT_FIELDS},
            "actual_outcome": outcome,
            "correct": correct,
            "lock_sha256": lock_digest,
        })
    return results


def accuracy_by_level(results, truth, lock_digest, locked):
    summary = []
    always_approve_correct = list(truth.values()).count("APPROVE")
    for level in LEVELS:
        counts = {(actual, predicted): 0 for actual in OUTCOMES for predicted in PREDICTIONS}
        for row in results:
            if row["level"] == level:
                counts[row["actual_outcome"], row["prediction"]] += 1
        total = sum(counts.values())
        abstained = counts["APPROVE", "ABSTAIN"] + counts["CRL", "ABSTAIN"]
        answered = total - abstained
        correct = counts["APPROVE", "APPROVE"] + counts["CRL", "CRL"]
        lower, upper = wilson_interval(correct, answered)
        always_approve_on_answered = counts["APPROVE", "APPROVE"] + counts["APPROVE", "CRL"]
        summary.append({
            "level": level,
            "events": total,
            "predicted": answered,
            "abstained": abstained,
            "correct": correct,
            "incorrect": answered - correct,
            "coverage": answered / total,
            "accuracy": correct / answered if answered else None,
            "accuracy_ci95_wilson_low": lower,
            "accuracy_ci95_wilson_high": upper,
            "always_approve_accuracy_all": always_approve_correct / total,
            "always_approve_accuracy_answered": always_approve_on_answered / answered if answered else None,
            **{
                f"actual_{actual.lower()}_predicted_{predicted.lower()}": count
                for (actual, predicted), count in counts.items()
            },
            "protocol": locked["protocol"],
            "rule_set": locked.get("rule_set"),
            "lock_sha256": lock_digest,
        })
    return summary


def write_csv(path, rows, fields):
    def escape_spreadsheet(value):
        if isinstance(value, str) and (
            value.lstrip().startswith(("=", "+", "-", "@"))
            or value.startswith(("\t", "\r", "\n"))
        ):
            return "'" + value
        return value

    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({
            field: escape_spreadsheet(row[field])
            for field in fields
        } for row in rows)


def score(args, verify_lock, load_csv):
    output = Path(args.output)
    summary_csv = getattr(args, "summary_csv", None)
    results_csv = getattr(args, "results_csv", None)
    outputs = [output.resolve(), *(Path(path).resolve() for path in (summary_csv, results_csv) if path)]
    if len(outputs) != len(set(outputs)) or set(outputs) & {
        Path(args.locked).resolve(), Path(args.outcomes).resolve()
    }:
        raise ValueError("Score output files must be distinct and separate from input files")
    locked = json.loads(Path(args.locked).read_text(encoding="utf-8"))
    frozen_digest = getattr(args, "expected_lock_sha256", None)
    predictions = verify_lock(locked, frozen_digest)
    event_ids = prediction_grid(predictions)
    if locked.get("expected_events") != len(event_ids):
        raise ValueError("Prediction lock event count differs from the assessment grid")
    truth = verified_truth(load_csv(args.outcomes), event_ids)
    lock_digest = frozen_digest or locked["predictions_sha256"]
    results = assessment_results(predictions, truth, lock_digest)
    summary = accuracy_by_level(results, truth, lock_digest, locked)
    formatted = json.dumps(summary, indent=2)
    output.write_text(formatted + "\n", encoding="utf-8")
    if summary_csv:
        write_csv(summary_csv, summary, tuple(summary[0]))
    if results_csv:
        write_csv(results_csv, results, RESULT_FIELDS)
    print(formatted)
