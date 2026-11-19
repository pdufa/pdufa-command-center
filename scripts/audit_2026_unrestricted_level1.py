#!/usr/bin/env python3
"""Audit a source-defined 2026 Level 1 cohort without scoring reconstructions."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

IDENTITY = ("application_id", "review_cycle", "supplement", "indication")
REQUIRED = IDENTITY + (
    "pdufa_date", "goal_source_url", "prediction", "prediction_kind",
    "prediction_frozen_at", "evidence_cutoff_at", "latest_evidence_published_at",
    "freeze_source_url", "model_version", "actual_outcome", "outcome_action_date",
    "outcome_published_at", "source_url",
)
# The original seed is still accepted as an unverified input. New evidence
# columns must be supplied before any row can qualify for scoring.
SEED_COLUMNS = {
    "application_id", "review_cycle", "indication", "pdufa_date",
    "prediction", "prediction_frozen_at", "evidence_cutoff_at",
    "actual_outcome", "outcome_published_at", "source_url",
}
DIRECTIONS = {"APPROVE", "APPROVAL", "CRL"}


def timestamp(value):
    if not value:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Timestamp requires a time zone")
    return result.astimezone(timezone.utc)


def source_url(value):
    try:
        parts = urlsplit(value)
        return (parts.scheme == "https" and bool(parts.hostname)
                and not parts.username and not parts.password
                and not any(c.isspace() for c in value))
    except ValueError:
        return False


def identity(row):
    return tuple(" ".join(row[field].upper().split()) for field in IDENTITY)


def score_rows(rows, asof):
    issues = []
    identities = Counter(map(identity, rows))
    correct = incorrect = historical = prospective = unresolved = 0
    for index, row in enumerate(rows, 2):
        app, cycle, supplement, indication = key = identity(row)
        try:
            due = date.fromisoformat(row["pdufa_date"])
            action = date.fromisoformat(row["outcome_action_date"]) if row["outcome_action_date"] else None
            frozen, cutoff, latest, published = (
                timestamp(row[field]) for field in (
                    "prediction_frozen_at", "evidence_cutoff_at",
                    "latest_evidence_published_at", "outcome_published_at",
                )
            )
        except ValueError:
            issues.append({"row": index, "issue": "invalid date or timestamp"})
            continue
        if (identities[key] > 1 or not re.fullmatch(r"(NDA|BLA)\d{6}", app)
                or any(value in {"", "UNKNOWN", "UNRESOLVED"} for value in (cycle, supplement, indication))):
            issues.append({"row": index, "issue": "incomplete or duplicate event identity"})
            continue
        if due.year != 2026 or not source_url(row["goal_source_url"]):
            issues.append({"row": index, "issue": "invalid 2026 goal or goal source"})
            continue
        if action and action <= asof:
            historical += 1
        elif due > asof:
            prospective += 1
            continue
        else:
            unresolved += 1
            continue
        if not (
            row["prediction_kind"] == "FROZEN_PRE_OUTCOME"
            and frozen and cutoff and latest and published
            and latest <= cutoff <= frozen < published
            and frozen.date() < action <= published.date() <= asof
            and frozen.date() <= due
            and source_url(row["source_url"]) and source_url(row["freeze_source_url"])
            and row["model_version"].strip()
            and row["prediction"] in DIRECTIONS and row["actual_outcome"] in DIRECTIONS
        ):
            issues.append({"row": index, "issue": "no eligible frozen Level 1 comparison"})
            continue
        if (row["prediction"] == "CRL") == (row["actual_outcome"] == "CRL"):
            correct += 1
        else:
            incorrect += 1
    eligible = correct + incorrect
    return {
        "historical": historical, "future": prospective, "past_goal_unresolved": unresolved,
        "correct": correct, "incorrect": incorrect, "verified_comparisons": eligible,
        "accuracy_pct": round(100 * correct / eligible, 2) if eligible else None,
        "issues": issues,
    }


def audit(path, asof, expected=None):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(SEED_COLUMNS - set(reader.fieldnames or []))
        if missing:
            raise ValueError("Missing columns: " + ", ".join(missing))
        rows = [dict.fromkeys(REQUIRED, "") | row for row in reader]
    result = score_rows(rows, asof)
    if expected is not None and len(rows) != expected:
        result["issues"].append({"issue": "cohort count mismatch", "expected": expected, "actual": len(rows)})
    return {"as_of": asof.isoformat(), "target": expected, "rows": len(rows),
            **result, "complete": expected is not None and not result["issues"]}


def validate_snapshot(directory):
    """Validate the frozen export without accepting display text as evidence."""
    directory = Path(directory)
    rows = json.loads((directory / "assessments.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "completion-manifest.json").read_text(encoding="utf-8"))
    with (directory / "assessments.csv").open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    expected_csv_rows = [
        {
            k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
            for k, v in row.items()
        }
        for row in rows
    ]
    if csv_rows != expected_csv_rows:
        raise ValueError("Assessment JSON and CSV differ")
    if len({r["record_id"] for r in rows}) != len(rows):
        raise ValueError("Repeated worklist record ID")

    verified = [r for r in rows if r["verification_status"] == "VERIFIED"]
    if len({identity(r) for r in verified}) != len(verified):
        raise ValueError("Repeated verified application-cycle identity")
    for row in rows:
        if not row["evidence_gaps"] or not row["rationale"]:
            raise ValueError("Missing evidence disposition")
        if row["assessment"] not in {"APPROVE", "CRL", "INDETERMINATE"}:
            raise ValueError("Unsupported assessment")
        if row["assessment_kind"] == "OUTCOME_AWARE" and row["prediction"]:
            raise ValueError("Outcome-aware assessment presented as a prediction")
        if row["actual_outcome"] and row["assessment_kind"] != "OUTCOME_AWARE":
            raise ValueError("Known outcome omitted from temporal classification")
        receipts = {entry["url"] for entry in row["source_receipts"]}
        if row["verification_status"] == "VERIFIED" and row["goal_source_url"] not in receipts:
            raise ValueError("Verified goal missing retrieval receipt")
        for entry in row["source_receipts"]:
            if not (source_url(entry["url"]) and timestamp(entry["retrieved_at"])
                    and re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
                raise ValueError("Invalid source receipt")
            if entry.get("representation") == "UTF-8 source excerpt":
                digest = hashlib.sha256(entry["document_excerpt"].encode()).hexdigest()
                if digest != entry["sha256"]:
                    raise ValueError("Source-excerpt digest differs")
        current_goals = [item for item in row["goal_date_history"] if item["status"] == "CURRENT"]
        if row["goal_source_url"] and (
            len(current_goals) != 1 or current_goals[0]["date"] != row["pdufa_date"]
            or current_goals[0]["source_url"] != row["goal_source_url"]
        ):
            raise ValueError("Current goal and amendment history diverge")
        if row["prediction_kind"] == "PROSPECTIVE":
            cutoff = timestamp(row["evidence_cutoff_at"])
            frozen = timestamp(row["prediction_frozen_at"])
            if not (
                row["verification_status"] == "VERIFIED" and row["model_version"]
                and cutoff and frozen and cutoff <= frozen
                and frozen.date() < date.fromisoformat(row["pdufa_date"])
                and not row["actual_outcome"] and row["evidence_sources"]
            ):
                raise ValueError("Invalid prospective freeze")
            for source in row["evidence_sources"]:
                if not source_url(source["url"]):
                    raise ValueError("Invalid prospective evidence URL")
                if source["published_on"] and date.fromisoformat(source["published_on"]) > cutoff.date():
                    raise ValueError("Publication after prospective cutoff")
                if source.get("retrieved_at") and timestamp(source["retrieved_at"]) > cutoff:
                    raise ValueError("Retrieved evidence after prospective cutoff")

    measured = score_rows(verified, timestamp(manifest["as_of"]).date())
    measured.pop("issues")
    clinical = [r for r in rows if r["phase"]]
    checked = {
        "goal_worklist_rows": len(rows),
        "distinct_verified_events": len(verified),
        "goal_worklist_unverified_rows": len(rows) - len(verified),
        "source_linked_clinical_assessments": len(clinical),
        "clinical_assessments_of_verified_events": sum(bool(r["phase"]) for r in verified),
        "verified_events_with_clinical_evidence_blocker": sum(not r["phase"] for r in verified),
        "historical_scoring": measured,
    }
    if any(manifest[k] != value for k, value in checked.items()):
        raise ValueError("Manifest totals diverge from assessment records")
    if manifest["complete"] or manifest["full_year_denominator"] is not None:
        raise ValueError("Snapshot has no verified full-year denominator")
    if not measured["verified_comparisons"] and manifest["calibration"] is not None:
        raise ValueError("Calibration requires eligible observed predictions")
    if (directory / "lead-reconciliation.json").exists():
        validate_lead_reconciliation(directory, rows, manifest)
    return checked


def validate_lead_reconciliation(directory, rows, manifest):
    """Require a traceable disposition for every inherited unverified row."""
    previous = json.loads((directory.parent / "assessments.json").read_text(encoding="utf-8"))
    ledger = json.loads((directory / "lead-reconciliation.json").read_text(encoding="utf-8"))
    with (directory / "lead-reconciliation.csv").open(newline="", encoding="utf-8") as handle:
        displayed = list(csv.DictReader(handle))
    if displayed != [
        {key: json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
         for key, value in item.items()}
        for item in ledger
    ]:
        raise ValueError("Lead ledger CSV and JSON differ")
    old = {row["record_id"]: row for row in previous}
    current = {row["record_id"]: row for row in rows}
    reviewed = Counter(item["record_id"] for item in ledger)
    expected = {key for key, row in old.items() if row["verification_status"] != "VERIFIED"}
    if set(reviewed) != expected or any(count != 1 for count in reviewed.values()):
        raise ValueError("Every prior lead requires exactly one disposition")
    if not set(old) <= set(current):
        raise ValueError("Inherited worklist record removed")
    dispositions = Counter()
    for item in ledger:
        key = item["record_id"]
        before, after = old[key], current[key]
        category = item["disposition"]
        dispositions[category] += 1
        if category not in {"VERIFIED", "DUPLICATE", "NOT_PDUFA", "BLOCKED"}:
            raise ValueError("Unknown lead disposition")
        if category != after["verification_status"] or not item["reason"] or not timestamp(item["reviewed_at"]):
            raise ValueError("Lead disposition is not supported by the event row")
        if item["previous_goal_date"] != before["pdufa_date"]:
            raise ValueError("Inherited lead date changed in the provenance ledger")
        if not item["source_urls"] or not all(source_url(url) for url in item["source_urls"]):
            raise ValueError("Invalid lead reconciliation provenance")
        if category == "DUPLICATE":
            canonical = current.get(item.get("canonical_record_id"))
            if not canonical or canonical["verification_status"] != "VERIFIED" or canonical is after:
                raise ValueError("Duplicate lacks a distinct verified canonical record")
    if dict(dispositions) != manifest["prior_lead_dispositions"]:
        raise ValueError("Manifest disposition totals disagree with the ledger")
    preserved = ("prediction", "prediction_kind", "prediction_frozen_at",
                 "evidence_cutoff_at", "model_version", "prior_prediction_artifacts")
    for key, row in old.items():
        if row["prediction_frozen_at"] and any(row[field] != current[key][field] for field in preserved):
            raise ValueError("Inherited prediction freeze changed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--as-of", default="2026-11-18")
    parser.add_argument("--expected", type=int)
    parser.add_argument("--snapshot", action="store_true")
    args = parser.parse_args()
    result = (validate_snapshot(args.csv) if args.snapshot
              else audit(args.csv, date.fromisoformat(args.as_of), args.expected))
    print(json.dumps(result, indent=2))
