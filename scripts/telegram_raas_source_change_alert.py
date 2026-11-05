#!/usr/bin/env python3
"""Opt-in Telegram notice for saved RAAS FDA research evidence differences.

Only the existing scheduled/manual workflow can invoke this after successful
artifact publication. A calendar rollover, an uncomparable previous run, or an
unreviewed outcome candidate is never called an FDA action or model prediction.
No source URLs, case metadata, secrets, or untrusted field contents in messages.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

if __package__:
    from .telegram_scan_alert import main as send_telegram
else:
    from telegram_scan_alert import main as send_telegram

SCOPE = "RAAS_NIGHTLY_FDA_THREE_WAY_EVIDENCE_READINESS_RESEARCH_ONLY"
COMPARED = "COMPARED_SAVED_SOURCE_AND_INTAKE_METADATA_ONLY"
ALLOWED_TYPES = {
    "SAVED_RESEARCH_CASE_ADDED",
    "SAVED_RESEARCH_CASE_REMOVED",
    "SAVED_SOURCE_OR_INTAKE_METADATA_CHANGED",
}
ALLOWED_FIELDS = {
    "caseKey", "sourceFingerprint", "sourceUrl", "savedSnapshotAsOf",
    "originalFirstGoalDate", "listedTargetDate", "formalGoalRevisionPresent",
    "trialNctId", "phase3SourceEligibility", "researchReceiptCount",
    "structurallyCompleteReceiptCount", "blockedReceiptCount",
    "outcomeSourceCandidateCount", "outcomeReviewState",
    "outstandingEvidenceProofIds",
}
SAFE_FIELD = re.compile(r"^[A-Za-z][A-Za-z0-9]{1,80}$")
MAX_BYTES = 3_000_000


def verified_research_delta_summary(report: object) -> str | None:
    """Only a valid comparison and a nonempty research metadata diff may alert."""
    if not isinstance(report, dict) or report.get("schemaVersion") != 1:
        return None
    if report.get("scope") != SCOPE or report.get(
        "sourceChangeComparisonStatus") != COMPARED:
        return None
    if report.get("sourceChangedSincePreviousRun") is not True:
        return None
    changes = report.get("savedSourceChanges")
    if not isinstance(changes, list) or not (1 <= len(changes) <= 10000):
        return None
    records = report.get("records")
    if not isinstance(records, list) or len(records) > 10000:
        return None
    score = report.get("threeWayScorecard")
    counts = report.get("counts")
    if not isinstance(score, dict) or not isinstance(counts, dict):
        return None
    if score.get("independentValidatedAccuracyPct") is not None:
        return None
    if counts.get("independentlyAuthenticatedForecasts") != 0:
        return None
    if counts.get("qualifiedForecastOutcomePairs") != 0:
        return None
    if counts.get("approvedTradingSignals") != 0:
        return None
    fingerprints = (report.get("savedSourceEvidenceFingerprint"), report.get(
        "auditStateFingerprint"))
    if any(not isinstance(x, str) or not re.fullmatch(r"[a-f0-9]{64}", x)
           for x in fingerprints):
        return None

    kinds = {kind: 0 for kind in ALLOWED_TYPES}
    changed_fields: set[str] = set()
    case_keys: set[str] = set()
    for row in changes:
        if not isinstance(row, dict):
            return None
        kind = row.get("type")
        key = row.get("caseKey")
        fields = row.get("changedEvidenceFields")
        if kind not in ALLOWED_TYPES or not isinstance(key, str) or not (
            3 <= len(key) <= 160) or not re.fullmatch(r"[A-Za-z0-9._|:-]+", key):
            return None
        if key in case_keys or row.get("fdaDecisionVerified") is not False:
            return None
        case_keys.add(key)
        if not isinstance(fields, list) or not fields or len(fields) > 30:
            return None
        if not all(isinstance(f, str) and f in ALLOWED_FIELDS and
                   SAFE_FIELD.fullmatch(f) for f in fields):
            return None
        if kind in {"SAVED_RESEARCH_CASE_ADDED", "SAVED_RESEARCH_CASE_REMOVED"}:
            if fields != ["caseKey"]:
                return None
        elif "caseKey" in fields:
            return None
        kinds[kind] += 1
        changed_fields.update(fields)

    # Neither evidence contents nor case keys are copied into the notification.
    # This notification is an auditable *research metadata* change, not an
    # externally verified new FDA original-cycle filing or outcome.
    added = kinds["SAVED_RESEARCH_CASE_ADDED"]
    removed = kinds["SAVED_RESEARCH_CASE_REMOVED"]
    updated = kinds["SAVED_SOURCE_OR_INTAKE_METADATA_CHANGED"]
    return (
        f"Saved RAAS FDA research evidence metadata changed for {len(changes)} "
        f"application/cycle record(s): {updated} updated, {added} added, "
        f"{removed} removed. "
        "Original-goal date passage and source-age rollover do NOT trigger "
        "this alert. No independently adjudicated FDA outcome, authenticated "
        "forecast, calibrated accuracy rating or trade is implied. "
        "Open the nightly RAAS evidence-gap report to review."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        source = Path(args.report)
        if source.stat().st_size > MAX_BYTES:
            raise ValueError("OVER_LIMIT")
        report = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        print("RAAS saved-evidence comparison missing/invalid; no Telegram alert.")
        return 0
    details = verified_research_delta_summary(report)
    if details is None:
        print("No authenticated run-to-run SAVED research metadata change to notify.")
        return 0
    args_for_sender = [
        "--event", "raas-evidence-change", "--details", details,
        "--url", args.run_url,
    ]
    if args.dry_run:
        args_for_sender.append("--dry-run")
    return send_telegram(args_for_sender)


if __name__ == "__main__":
    sys.exit(main())
