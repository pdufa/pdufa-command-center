"""Fail-closed verification of a scheduled Level 2 FOCUS queue report.

Trust only a fresh report from the known local builder on the exact saved
snapshot. This never certifies hypotheses, predictions, or current live FOCUS.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime

from level2_focus_registry_research import build_source_research


def verify_queue_report(report: object, snapshot_bytes: bytes) -> bool:
    if not isinstance(report, dict) or not isinstance(snapshot_bytes, bytes):
        return False
    try:
        snapshot = json.loads(snapshot_bytes.decode("utf-8"))
        rows = snapshot["records"]
        output = report["records"]
        if (snapshot.get("schemaVersion") != 1
                or not isinstance(rows, list)
                or not (1 <= len(rows) <= 2000)
                or not isinstance(output, list)):
            return False
        required = {
            "schema_version": 1,
            "workflow": "LEVEL_2_FOCUS_RESEARCH_GAPS",
            "snapshot_as_of": snapshot["asOf"],
            "trial_count": len(rows),
            "level2_assessments_completed": 0,
            "level2_assessments_in_review": 0,
            "outcome_predictions_generated": 0,
            "readiness": "SOURCE_COLLECTION_REQUIRED",
            "source_leads_are_unverified": True,
            "current_live_focus_membership_confirmed": False,
            "original_source_fetched": False,
            "repository_modified": False,
            "production_modified": False,
            "snapshot_sha256": hashlib.sha256(snapshot_bytes).hexdigest(),
        }
        if not all(type(report.get(k)) is type(v) and report[k] == v for k, v in required.items()):
            return False
        if len(output) != len(rows):
            return False
        for raw, item in zip(rows, output):
            if not isinstance(raw, dict) or not isinstance(item, dict):
                return False
            if any(item.get(key) != raw.get(key) for key in ("nct", "ticker", "company")):
                return False
            if (item.get("status") != "SOURCE_COLLECTION_AND_HYPOTHESIS_REVIEW_REQUIRED"
                    or item.get("phase_verified_by_this_queue") is not False
                    or item.get("approval_probability") is not None):
                return False
            hypothesis = item.get("hypothesis_review")
            if (not isinstance(hypothesis, dict)
                    or hypothesis.get("nct") != raw.get("nct")
                    or hypothesis.get("assessment_complete") is not False
                    or hypothesis.get("scientifically_verified") is not False
                    or hypothesis.get("fda_prediction") is not None
                    or hypothesis.get("approval_probability") is not None
                    or hypothesis.get("score") is not None
                    or hypothesis.get("sources") != []
                    or hypothesis.get("status") != "INCOMPLETE_HYPOTHESIS_AWAITING_EVIDENCE"):
                return False
            leads = item.get("source_leads")
            if not isinstance(leads, list) or len(leads) > 2:
                return False
            expected_leads = [
                (key, raw[key]) for key in ("resultsUrl", "regulatoryUrl")
                if raw.get(key)
            ]
            if len(leads) != len(expected_leads):
                return False
            for lead, (key, url) in zip(leads, expected_leads):
                if (not isinstance(lead, dict) or lead.get("role") != key
                        or lead.get("url") != url
                        or lead.get("status") != "UNOPENED_SNAPSHOT_SOURCE_LEAD_NOT_VERIFIED"):
                    return False
        return True
    except (ValueError, KeyError, TypeError, UnicodeError):
        return False


def verify_registry_research_report(
    report: object, roster_bytes: bytes, scan_bytes: bytes
) -> bool:
    """Require exact, unpromoted contents for one saved 29-trial registry packet.

    A fresh-file check in the scheduled worker rejects old reports separately.
    Any changed cohort/source digest, FDA prediction, or science completion
    assertion must be flagged rather than posted as a green result.
    """
    if not isinstance(report, dict) or not isinstance(roster_bytes, bytes) or not isinstance(scan_bytes, bytes):
        return False
    try:
        timestamp = report.get("generated_at_utc")
        if not isinstance(timestamp, str):
            return False
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return False
        expected = build_source_research(
            json.loads(roster_bytes.decode("utf-8")),
            json.loads(scan_bytes.decode("utf-8")),
        )
        expected["roster_sha256"] = hashlib.sha256(roster_bytes).hexdigest()
        expected["saved_scan_sha256"] = hashlib.sha256(scan_bytes).hexdigest()
        observed = {key: value for key, value in report.items() if key != "generated_at_utc"}
        return observed == expected
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError):
        return False
