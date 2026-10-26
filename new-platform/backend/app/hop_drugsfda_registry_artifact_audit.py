"""Reproduce an original NDA/BLA submission audit from saved Drugs@FDA JSON.

This consumes a previously collected *approved-product-centric* research
artifact. The raw AP/TA/CR values are publication metadata, NOT FDA decision
outcomes, approval probabilities, or validated review-cycle labels.
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path

EXPECTED_FILES = frozenset({
    "drugsfda_approved_registry_audit.json",
    "drugsfda_approved_registry_quarantined.json",
})
APPLICATION_ID = re.compile(r"(?:NDA|BLA|ANDA)[0-9]{6}\Z")
HEX_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MAX_DECOMPRESSED_FILE = 100_000_000


def audit_registry_artifact(artifact_zip: str | Path, *, as_of: date,
                            expected_payload_sha256: str | None = None) -> dict:
    if not isinstance(as_of, date):
        raise ValueError("Explicit research cutoff required")
    if (expected_payload_sha256 is not None
            and not HEX_DIGEST.fullmatch(expected_payload_sha256)):
        raise ValueError("Bad expected research artifact fingerprint")
    path = Path(artifact_zip)
    with zipfile.ZipFile(path) as z:
        if set(z.namelist()) != EXPECTED_FILES or any(
            f.file_size > MAX_DECOMPRESSED_FILE for f in z.infolist()
        ):
            raise ValueError("Unexpected or oversized Drugs@FDA archive members")
        payload = z.read("drugsfda_approved_registry_quarantined.json")
        audit_bytes = z.read("drugsfda_approved_registry_audit.json")
    actual_sha = hashlib.sha256(payload).hexdigest()
    if expected_payload_sha256 and actual_sha != expected_payload_sha256:
        raise ValueError("Drugs@FDA research artifact fingerprint changed")
    data = json.loads(payload)
    prior = json.loads(audit_bytes)
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or data.get("status") != "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT"
            or not isinstance(data.get("records"), list)
            or not isinstance(prior, dict)
            or prior.get("model_eligible_records") != 0
            or prior.get("prediction_probability") is not None
            or prior.get("complete_original_nda_bla_denominator_verified") is not False
            or prior.get("independently_adjudicated_review_cycles") != 0
            or prior.get("source_export_date") != data.get("source_export_date")
            or prior.get("source_application_records") != len(data["records"])
            or prior.get("quarantined_application_records") != len(data["records"])):
        raise ValueError("Research artifact is not the quarantined approved registry")
    archive_digests = prior.get("source_archive_sha256")
    if (not isinstance(archive_digests, dict) or len(archive_digests) != 1
            or any(not HEX_DIGEST.fullmatch(v) for v in archive_digests.values())):
        raise ValueError("Missing original FDA export fingerprint")
    apps = Counter()
    orig = Counter()
    status = Counter()
    data_warnings = Counter()
    orig_keys = set()
    distinct_original_apps = set()
    originals_per_application = Counter()
    applications_seen = set()
    number_of_submissions = 0
    for idx, row in enumerate(data["records"]):
        if not isinstance(row, dict):
            raise ValueError("Malformed research application record")
        app = row.get("application_number_as_published")
        if not isinstance(app, str) or not APPLICATION_ID.fullmatch(app):
            raise ValueError("Invalid NDA/BLA/ANDA application identifier")
        if app in applications_seen:
            raise ValueError("Duplicate application identity in registry")
        applications_seen.add(app)
        typ = app[:4] if app.startswith("ANDA") else app[:3]
        if (row.get("source_record_index") != idx
                or not isinstance(row.get("record_sha256"), str)
                or not HEX_DIGEST.fullmatch(row["record_sha256"])
                or row.get("model_eligible") is not False
                or row.get("review_cycles_independently_adjudicated") is not False
                or row.get("complete_application_denominator_verified") is not False
                or row.get("point_in_time_features_verified") is not False):
            raise ValueError("Source record identity or scientific quarantine altered")
        submissions = row.get("submissions_as_published")
        if not isinstance(submissions, list):
            raise ValueError("Missing Drugs@FDA application submissions")
        apps[typ] += 1
        for sub in submissions:
            number_of_submissions += 1
            if not isinstance(sub, dict):
                raise ValueError("Malformed submission in research artifact")
            kind = sub.get("submission_type_as_published")
            if kind not in ("ORIG", "SUPPL"):
                data_warnings["UNRECOGNIZED_RAW_SUBMISSION_TYPE"] += 1
                continue
            if kind != "ORIG" or typ not in ("NDA", "BLA"):
                continue
            number = sub.get("submission_number_as_published")
            if not isinstance(number, str) or not re.fullmatch(r"[0-9]{1,5}", number):
                data_warnings["BAD_ORIGINAL_SUBMISSION_NUMBER"] += 1
                continue
            key = (app, int(number))
            if key in orig_keys:
                data_warnings["REPEATED_ORIGINAL_SUBMISSION_KEY"] += 1
                continue
            orig_keys.add(key)
            orig[typ] += 1
            distinct_original_apps.add(app)
            originals_per_application[app] += 1
            raw_status = sub.get("submission_status_as_published")
            if raw_status is None or raw_status == "":
                data_warnings["MISSING_ORIGINAL_SUBMISSION_RAW_STATUS"] += 1
                status["MISSING"] += 1
            elif isinstance(raw_status, str) and re.fullmatch(r"[A-Z0-9]{1,16}", raw_status):
                status[raw_status] += 1
            else:
                data_warnings["INVALID_ORIGINAL_SUBMISSION_RAW_STATUS"] += 1
                status["INVALID"] += 1
            raw_day = sub.get("submission_status_date_as_published")
            if raw_day is None or raw_day == "":
                data_warnings["MISSING_ORIGINAL_SUBMISSION_DATE"] += 1
            elif not isinstance(raw_day, str) or not re.fullmatch(r"[0-9]{8}", raw_day):
                data_warnings["INVALID_ORIGINAL_SUBMISSION_DATE"] += 1
            else:
                try:
                    action_date = datetime.strptime(raw_day, "%Y%m%d").date()
                except ValueError:
                    data_warnings["INVALID_ORIGINAL_SUBMISSION_DATE"] += 1
                else:
                    if action_date > as_of:
                        data_warnings["RAW_DATE_AFTER_RESEARCH_CUTOFF"] += 1
    if (dict(apps) != prior.get("application_number_prefixes")
            or sum(apps.values()) != len(data["records"])):
        raise ValueError("Approved registry totals contradict original collection")
    return {
        "status": "ACTUAL_FDA_APPROVED_REGISTRY_ORIGINAL_SPINE_QUARANTINED",
        "source_export_date": data["source_export_date"],
        "retrieved_on": data.get("retrieved_on"),
        "research_cutoff": as_of.isoformat(),
        "github_artifact_json_sha256": actual_sha,
        "fda_source_archive_sha256_as_reported_not_rehashed":
            next(iter(archive_digests.values())),
        "approved_registry_application_records": len(data["records"]),
        "application_type_counts": dict(sorted(apps.items())),
        "published_registry_submission_entries": number_of_submissions,
        "original_nda_bla_submission_entries": sum(orig.values()),
        "original_nda_bla_submission_entries_by_type": dict(sorted(orig.items())),
        "distinct_nda_bla_applications_with_original_submission":
            len(distinct_original_apps),
        "applications_with_multiple_original_submissions": sum(
            count > 1 for count in originals_per_application.values()
        ),
        "raw_original_submission_status_codes_not_outcomes": dict(sorted(status.items())),
        "source_data_warning_counts": dict(sorted(data_warnings.items())),
        "independently_adjudicated_review_cycles": 0,
        "complete_original_nda_bla_denominator_verified": False,
        "unapproved_applications_absent_from_registry_possible": True,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
        "note": (
            "The original submissions here are from an approved-product-centric "
            "registry. AP/TA/status dates are unverified metadata, not "
            "application-cycle approval or nonapproval labels."
        ),
    }
