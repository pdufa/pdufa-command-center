#!/usr/bin/env python3
"""Nonqualifying, auditable intake for six commercial-rights review checks per NCT.

Source references are bound to the 741-NCT source-linked research worklist.
Reviewer-reported findings are not authenticated legal determinations, and do
not promote a trial into Pipeline, GEM JR or GEM.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.phase3_rights_review_worklist import REQUIRED_REVIEW

EXPECTED_TRIALS = 741
REVIEW_CHECKS = len(REQUIRED_REVIEW)
NCT = re.compile(r"^NCT[0-9]{8}$")
SHA = re.compile(r"^[0-9a-fA-F]{64}$")
CANDIDATE_HOST = re.compile(r"^[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
REVIEW_STATES = (
    "PENDING",
    "REVIEWER_REPORTS_SUPPORT",
    "REVIEWER_REPORTS_NO_SUPPORT",
    "REVIEWER_INCONCLUSIVE",
)
REVIEWED = set(REVIEW_STATES) - {"PENDING"}
SLOT_STATES = (
    "NOT_SUBMITTED",
    "PENDING_SOURCE_REVIEW",
    "REVIEWER_REPORTED_SUPPORT_NOT_ADJUDICATED",
    "REVIEWER_REPORTED_NO_SUPPORT_NOT_ADJUDICATED",
    "REVIEWER_REPORTED_INCONCLUSIVE",
    "REVIEWER_REPORTS_CONFLICT",
)
MAX_SUBMISSIONS = EXPECTED_TRIALS * REVIEW_CHECKS * 3
MAX_TEXT = 1600


def timestamp(value, label):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError(f"Invalid {label}")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid {label}") from exc
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0:
        raise ValueError(f"UTC timestamp required for {label}")
    if dt > datetime.now(timezone.utc):
        raise ValueError(f"Future timestamp: {label}")
    return dt


def source_url(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 1500:
        raise ValueError("Invalid source URL")
    if value != value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError("Malformed source URL")
    url = urlsplit(value)
    host = url.hostname
    if (url.scheme != "https" or not host
        or not CANDIDATE_HOST.fullmatch(host)
        or host.lower().endswith((".local", ".internal", ".localhost"))
        or url.username is not None or url.password is not None
        or url.port is not None or url.fragment):
        raise ValueError("Expected an unambiguous publicly routable HTTPS source")
    return value


def source_fetched(row):
    documents = row.get("sec_source_documents_fetched")
    if not isinstance(documents, list) or len(documents) > 2:
        raise ValueError("Malformed source-backed fetched SEC documents")
    verified = {}
    for doc in documents:
        if (not isinstance(doc, dict)
            or doc.get("scope") != "ISSUER_DOCUMENT_ONLY_NOT_TRIAL_RIGHTS"
            or not isinstance(doc.get("sha256"), str) or not SHA.fullmatch(doc["sha256"])):
            raise ValueError("Unverified SEC document provenance in worklist")
        link = source_url(doc.get("url"))
        if link in verified:
            raise ValueError("Duplicate primary document source")
        verified[link] = doc["sha256"]
    return verified


def slot_state(submissions):
    if not submissions:
        return "NOT_SUBMITTED"
    reviewed = {x["reviewer_status"] for x in submissions if x["reviewer_status"] in REVIEWED}
    if "REVIEWER_REPORTS_SUPPORT" in reviewed and "REVIEWER_REPORTS_NO_SUPPORT" in reviewed:
        return "REVIEWER_REPORTS_CONFLICT"
    if "REVIEWER_REPORTS_NO_SUPPORT" in reviewed:
        return "REVIEWER_REPORTED_NO_SUPPORT_NOT_ADJUDICATED"
    if "REVIEWER_REPORTS_SUPPORT" in reviewed:
        return "REVIEWER_REPORTED_SUPPORT_NOT_ADJUDICATED"
    if "REVIEWER_INCONCLUSIVE" in reviewed:
        return "REVIEWER_REPORTED_INCONCLUSIVE"
    return "PENDING_SOURCE_REVIEW"


def build_review_coverage(worklist, submissions):
    records = worklist.get("items") if isinstance(worklist, dict) else None
    if (not isinstance(worklist, dict)
        or worklist.get("report_type") != "MAIN_PHASE3_COMMERCIAL_RIGHTS_REVIEW_WORKLIST_RESEARCH_ONLY"
        or worklist.get("total_trials") != EXPECTED_TRIALS
        or worklist.get("total_issuer_research_pointers") != 130
        or worklist.get("rights_checks_required_per_trial") != REVIEW_CHECKS
        or worklist.get("independently_verified_current_rights") != 0
        or worklist.get("qualified_pipeline_total") is not None
        or not isinstance(records, list) or len(records) != EXPECTED_TRIALS):
        raise ValueError("Expected complete fail-closed 741-trial rights worklist")
    if not isinstance(submissions, list) or len(submissions) > MAX_SUBMISSIONS:
        raise ValueError("Evidence submissions must be a bounded JSON list")

    worklist_index = {}
    review_positions = set()
    for row in records:
        if not isinstance(row, dict):
            raise ValueError("Malformed rights worklist record")
        nct, rank = row.get("nct_id"), row.get("research_review_queue_position")
        if (not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in worklist_index
            or type(rank) is not int or not 1 <= rank <= EXPECTED_TRIALS or rank in review_positions
            or not isinstance(row.get("ticker"), str) or not row["ticker"]
            or not isinstance(row.get("issuer_sec_cik"), str)
            or not re.fullmatch(r"[0-9]{10}", row["issuer_sec_cik"])
            or not isinstance(row.get("registry_source_sha256"), str)
            or not SHA.fullmatch(row["registry_source_sha256"])
            or row.get("commercial_rights_verified") is not False
            or row.get("qualified_pipeline") is not None
            or row.get("rights_review_checklist") != {check: "NOT_VERIFIED" for check in REQUIRED_REVIEW}):
            raise ValueError("Worklist source identity, ranking or qualification altered")
        worklist_index[nct] = row
        review_positions.add(rank)

    collected = {(nct, check): [] for nct in worklist_index for check in REQUIRED_REVIEW}
    distinct_sources = set()
    reported_status_counts = Counter()
    now = datetime.now(timezone.utc)
    for item in submissions:
        if not isinstance(item, dict):
            raise ValueError("Malformed review evidence item")
        nct, check, reported = (item.get("nct_id"), item.get("check"),
                                item.get("reviewer_status"))
        if nct not in worklist_index or check not in REQUIRED_REVIEW or reported not in REVIEW_STATES:
            raise ValueError("Unknown NCT, checklist requirement or reported review status")
        row = worklist_index[nct]
        if (item.get("ticker") != row["ticker"]
            or item.get("issuer_sec_cik") != row["issuer_sec_cik"]):
            raise ValueError("Reviewer source mismatched issuer/trial identity")
        link = source_url(item.get("source_url"))
        key = (nct, check, link)
        if key in distinct_sources:
            raise ValueError("Duplicate source for same trial and checklist requirement")
        distinct_sources.add(key)
        claim = item.get("claim")
        if not isinstance(claim, str) or not 10 <= len(claim.strip()) <= MAX_TEXT:
            raise ValueError("Bounded, substantive reviewer evidence claim required")
        observed = timestamp(item.get("observed_at_utc"), "observation date")
        retrieved = source_fetched(row)
        expected_digest = retrieved.get(link)
        digest = item.get("source_sha256")
        if digest is not None and (not isinstance(digest, str) or not SHA.fullmatch(digest)):
            raise ValueError("Invalid original document SHA256")
        if digest is not None and (expected_digest is None or digest != expected_digest):
            raise ValueError("Claimed hash is not from an actually retrieved issuer primary document")
        document_provenance = ("EXACT_FETCHED_ISSUER_PRIMARY_DOCUMENT"
                               if expected_digest is not None else "SOURCE_LINK_NOT_FETCHED_IN_THIS_RUN")
        reviewer, reviewed_at = item.get("reviewer"), item.get("reviewed_at_utc")
        if reported in REVIEWED:
            if (not isinstance(reviewer, str) or not 3 <= len(reviewer.strip()) <= 120
                or not isinstance(reviewed_at, str) or digest != expected_digest
                or expected_digest is None):
                raise ValueError("Reviewer-attested claim requires reviewer, time and exact fetched primary SEC bytes")
            when = timestamp(reviewed_at, "reported reviewer date")
            if when < observed:
                raise ValueError("Review date precedes source observation")
        elif reviewer is not None or reviewed_at is not None:
            raise ValueError("Pending items cannot imply completed review")
        normalized = {
            "nct_id": nct, "check": check,
            "ticker": row["ticker"], "issuer_sec_cik": row["issuer_sec_cik"],
            "source_url": link, "source_sha256": digest,
            "source_provenance": document_provenance,
            "observed_at_utc": observed.isoformat(),
            "claim": claim.strip(),
            "reviewer_status": reported,
            "reported_reviewer": reviewer.strip() if reported in REVIEWED else None,
            "reported_reviewed_at_utc": reviewed_at if reported in REVIEWED else None,
            "result": "RESEARCH_REPORT_ONLY_NOT_AN_INDEPENDENT_RIGHTS_DETERMINATION",
        }
        collected[(nct, check)].append(normalized)
        reported_status_counts[reported] += 1

    items = []
    slots = Counter()
    trial_any = 0
    trial_all_submitted = 0
    trial_all_reported_reviewed = 0
    source_documents = set()
    for row in records:
        nct = row["nct_id"]
        checks = {}
        any_submission = True
        all_submission = True
        all_reviewed = True
        for check in REQUIRED_REVIEW:
            evidence = collected[(nct, check)]
            state = slot_state(evidence)
            checks[check] = {
                "status": state, "evidence_count": len(evidence),
                "reviewer_attestations_count": sum(x["reviewer_status"] in REVIEWED for x in evidence),
                "submissions": evidence,
            }
            slots[state] += 1
            if not evidence:
                all_submission = False
            if not any(x["reviewer_status"] in REVIEWED for x in evidence):
                all_reviewed = False
            for x in evidence:
                if x["source_provenance"] == "EXACT_FETCHED_ISSUER_PRIMARY_DOCUMENT":
                    source_documents.add((nct, x["source_url"]))
        any_submission = any(checks[k]["evidence_count"] > 0 for k in REQUIRED_REVIEW)
        trial_any += any_submission
        trial_all_submitted += all_submission
        trial_all_reported_reviewed += all_reviewed
        items.append({
            "nct_id": nct, "ticker": row["ticker"],
            "research_review_queue_position": row["research_review_queue_position"],
            "priority": row["research_priority"], "source_review_stage": row["source_review_stage"],
            "checks": checks,
            "checklist_independently_verified": False,
            "commercial_rights_verified": False, "qualified_pipeline": None,
        })
    total_slots = EXPECTED_TRIALS * REVIEW_CHECKS
    slots_with_submissions = total_slots - slots["NOT_SUBMITTED"]
    slots_with_reviewed_claims = sum(
        1 for entry in items for detail in entry["checks"].values()
        if detail["reviewer_attestations_count"] > 0)
    return {
        "report_type": "MAIN_PHASE3_RIGHTS_REVIEW_SUBMISSIONS_COVERAGE_RESEARCH_ONLY",
        "generated_at_utc": now.isoformat(),
        "trial_denominator": EXPECTED_TRIALS,
        "requirements_per_trial": REVIEW_CHECKS,
        "checklist_slot_denominator": total_slots,
        "submitted_evidence_item_count": len(submissions),
        "distinct_review_slots_with_submissions": slots_with_submissions,
        "review_slots_without_submissions": slots["NOT_SUBMITTED"],
        "review_slots_with_reviewer_reported_findings": slots_with_reviewed_claims,
        "trial_count_with_any_submissions": trial_any,
        "trials_with_all_six_submitted_checks": trial_all_submitted,
        "trials_with_all_six_reviewer_reported_checks": trial_all_reported_reviewed,
        "reviewer_reported_status_counts": {key: reported_status_counts[key] for key in REVIEW_STATES},
        "checklist_slot_state_counts": {key: slots[key] for key in SLOT_STATES},
        "trial_document_source_links_in_review_submissions": len(source_documents),
        "independently_verified_commercial_rights": 0,
        "qualified_pipeline_total": None,
        "items": items,
        "limitations": (
            "A reviewer status is a reported assertion, not independently authenticated "
            "or legally adjudicated current US commercial rights. A pending URL that was "
            "not fetched is NOT verified; zero submissions means none recorded in this "
            "repository review intake, not no rights evidence in the world. "
            "No Pipeline, GEM JR, GEM, FS/FA change or regulatory inference."
        ),
    }


def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: phase3_rights_review_submissions.py <worklist.json> <submissions.json> <output.json>")
    worklist = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    submissions = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    report = build_review_coverage(worklist, submissions)
    output = Path(sys.argv[3])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Rights review submissions: {report['submitted_evidence_item_count']} items, "
        f"{report['distinct_review_slots_with_submissions']}/"
        f"{report['checklist_slot_denominator']} requirements with submissions; "
        f"{report['trial_count_with_any_submissions']}/741 trials submitted, "
        f"{report['independently_verified_commercial_rights']}/741 rights verified; "
        "Pipeline qualification UNKNOWN"
    )


if __name__ == "__main__":
    main()
