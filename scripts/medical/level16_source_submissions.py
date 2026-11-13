#!/usr/bin/env python3
"""Validate source-submission metadata for phase-first FOCUS Levels 1–6.

Submitted metadata is not proof of access to the original document or of an
independent source/scientific review. This module never signs off an assessment.
"""
from __future__ import annotations

from datetime import date
import re
from urllib.parse import urlsplit

NCT_RE = re.compile(r"NCT[0-9]{8}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")
ALLOWED_KINDS = frozenset({
    "REGISTRY", "PROTOCOL", "STATISTICAL_ANALYSIS_PLAN", "CLINICAL_RESULTS",
    "JOURNAL_PUBLICATION", "FDA_PRIMARY_SOURCE", "SPONSOR_DISCLOSURE",
    "CLINICAL_GUIDELINE", "OTHER_PUBLIC_SOURCE",
})
ALLOWED_ROLES = frozenset({"SUPPORTS", "CHALLENGES", "CONTEXT"})
REQUIRED = frozenset({
    "submissionId", "nct", "level", "sourceKind", "sourceUrl",
    "sourceDate", "accessedDate", "documentSha256", "locator",
    "claim", "role", "submittedBy",
})
OPTIONAL = frozenset({"candidateApplicationCycleId"})


def _nonblank(value, label, limit=2048):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label}: expected bounded nonblank text")
    return value.strip()


def _date(value, label):
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        raise ValueError(f"{label}: require YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label}: invalid calendar date") from exc


def _https(url):
    value = _nonblank(url, "sourceUrl")
    if any(c.isspace() for c in value):
        raise ValueError("Source URL cannot contain whitespace")
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or "." not in parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.hostname in {"localhost", "127.0.0.1"}):
        raise ValueError("Submission source must have an external HTTPS locator")
    return value


def validate(document, roster, applications, checkpoint):
    """Return NCT-indexed source leads, all explicitly pending authentication.

    False 'reviewed' flags, unknown attributes and prospective prediction data
    cannot pass through this intake. Real review must happen in a separate
    authenticated, independently adjudicated workflow.
    """
    if not isinstance(document, dict) or document.get("schemaVersion") != 1:
        raise ValueError("Unsupported source-submission schema")
    if document.get("kind") != "FOCUS_LEVELS_1_6_SOURCE_SUBMISSIONS":
        raise ValueError("Wrong evidence-submission kind")
    if set(document) != {"schemaVersion", "kind", "cutoffDate", "records"}:
        raise ValueError("Unknown evidence-submission document keys")
    cutoff = _date(document["cutoffDate"], "cutoffDate")
    items = document.get("records")
    if not isinstance(items, list) or len(items) > 2000:
        raise ValueError("Submission records must be a bounded list")

    # The assessment layer independently validates both canonical snapshots.
    all_ncts = set(roster)
    if set(applications) != all_ncts:
        raise ValueError("Unreconciled application identity")
    captures = checkpoint.get("results", {})
    result = {nct: [] for nct in roster}
    ids = set()
    for item in items:
        if not isinstance(item, dict) or not REQUIRED.issubset(item):
            raise ValueError("Submission is missing required metadata")
        if not set(item).issubset(REQUIRED | OPTIONAL):
            raise ValueError("Unknown or forbidden review/prediction fields")
        submission_id = _nonblank(item["submissionId"], "submissionId", 128)
        if submission_id in ids:
            raise ValueError("Duplicate evidence submission ID")
        ids.add(submission_id)
        nct = item["nct"]
        if not isinstance(nct, str) or not NCT_RE.fullmatch(nct) or nct not in all_ncts:
            raise ValueError("Evidence submission is outside exact FOCUS")
        level = item["level"]
        if isinstance(level, bool) or not isinstance(level, int) or not 1 <= level <= 6:
            raise ValueError("Evidence submission has invalid Level 1–6")
        kind = item["sourceKind"]
        role = item["role"]
        if kind not in ALLOWED_KINDS or role not in ALLOWED_ROLES:
            raise ValueError("Unknown source kind or claim role")
        url = _https(item["sourceUrl"])
        source_date = _date(item["sourceDate"], "sourceDate")
        accessed_date = _date(item["accessedDate"], "accessedDate")
        if source_date > cutoff or accessed_date > cutoff or source_date > accessed_date:
            raise ValueError("Submission is after the declared evidence cutoff")
        digest = item["documentSha256"]
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise ValueError("Original source digest must be lowercase SHA-256")
        locator = _nonblank(item["locator"], "locator", 512)
        claim = _nonblank(item["claim"], "claim", 2000)
        submitted_by = _nonblank(item["submittedBy"], "submittedBy", 200)
        cycle = item.get("candidateApplicationCycleId")
        if cycle is not None:
            cycle = _nonblank(cycle, "candidateApplicationCycleId", 128)
            valid_ids = {c["cycleId"] for c in applications[nct]["candidateApplications"]}
            if cycle not in valid_ids:
                raise ValueError("Source has mismatched application-cycle identity")
        if kind == "REGISTRY":
            capture = captures.get(nct, {})
            evidence = capture.get("evidence", {}) if capture.get("status") == "CAPTURED_UNREVIEWED" else {}
            if (url != f"https://clinicaltrials.gov/study/{nct}"
                    or evidence.get("nct") != nct or evidence.get("sha256") != digest):
                raise ValueError("Registry submission must match captured source and digest")
            fields = evidence.get("fields", {})
            if not isinstance(fields, dict) or locator not in {
                item.get("locator") for item in fields.values()
                if isinstance(item, dict) and item.get("status") == "CAPTURED_UNREVIEWED"
            }:
                raise ValueError("Registry locator was not captured for this trial")
        result[nct].append({
            "submissionId": submission_id, "level": level, "sourceKind": kind,
            "sourceUrl": url, "sourceDate": source_date.isoformat(),
            "accessedDate": accessed_date.isoformat(), "submittedDigestUnverified": digest,
            "locator": locator, "claim": claim, "role": role,
            "submittedBy": submitted_by, "candidateApplicationCycleId": cycle,
            "authenticationStatus": "SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED",
            "scientificReviewStatus": "NOT_ADJUDICATED",
        })
    return result
