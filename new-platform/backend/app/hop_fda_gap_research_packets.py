"""Offline evidence-search packets for unverified FDA original application gaps.

Group selected published *letter references* into application identity
research tasks, with explicit separate tickets for ambiguous identity rows.
Never infer approval, nonapproval, FDA review-cycle count, or model readiness.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date
from urllib.parse import urlparse

SOURCE_SHA = re.compile(r"[0-9a-f]{64}\Z")
APP = re.compile(r"(?:NDA|BLA)[0-9]{6}\Z")
REASONS = {
    "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION",
    "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION",
    "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE",
}
SOURCE_DOMAINS = {"www.accessdata.fda.gov", "accessdata.fda.gov",
                  "www.fda.gov", "fda.gov", "www.regulations.gov",
                  "api.fda.gov", "download.open.fda.gov"}
SOURCE_TYPES = {
    "FDA_APPROVAL_LETTER", "FDA_COMPLETE_RESPONSE_LETTER",
    "FDA_APPLICATION_HISTORY", "FDA_REFUSAL_TO_FILE_LETTER",
    "FDA_OTHER_OR_UNCLASSIFIED_DOCUMENT",
}
VERIFICATION = "UNVERIFIED_FDA_SOURCE_LEAD_REQUIRES_INDEPENDENT_REVIEW"


def _official_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return (parsed.scheme == "https" and parsed.hostname in SOURCE_DOMAINS
                and parsed.username is None and parsed.password is None
                and parsed.port is None and bool(parsed.path and parsed.path != "/")
                and not parsed.fragment and len(url) <= 1200
                and not any(c.isspace() for c in url))
    except (ValueError, TypeError):
        return False


def build_source_search_packets(
    source_queue: list[dict],
    *,
    as_of: date,
    pinned_audit: dict,
) -> tuple[list[dict], dict]:
    """Generate immutable grouped review leads, never a decision label."""
    if (not isinstance(as_of, date)
            or not isinstance(source_queue, list)
            or not isinstance(pinned_audit, dict)
            or pinned_audit.get("status") != "PUBLISHED_FDA_LETTER_IDENTITY_GAPS_UNVERIFIED"
            or pinned_audit.get("research_cutoff") != as_of.isoformat()
            or pinned_audit.get("fda_original_actions_independently_verified") != 0
            or pinned_audit.get("complete_original_nda_bla_decision_denominator_verified") is not False
            or pinned_audit.get("model_eligible_records") != 0
            or pinned_audit.get("prediction_probability") is not None
            or pinned_audit.get("review_queue_references") != len(source_queue)):
        raise ValueError("Published letter queue must match pinned unverified audit")
    seen = set()
    grouped: dict[str, list[dict]] = defaultdict(list)
    ambiguous = []
    for item in source_queue:
        if not isinstance(item, dict) or not isinstance(item.get("source_record_sha256"), str):
            raise ValueError("Missing source record")
        digest = item["source_record_sha256"]
        app = item.get("application_candidate")
        reason = item.get("review_reason")
        if (not SOURCE_SHA.fullmatch(digest) or digest in seen
                or reason not in REASONS
                or item.get("review_priority") != str((
                    "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION",
                    "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION",
                    "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE",
                ).index(reason) + 1)
                or item.get("original_application_review_cycle") is not None
                or item.get("fda_action_outcome") is not None
                or item.get("evidence_independently_adjudicated") is not False
                or item.get("model_eligible") is not False):
            raise ValueError("Tampered source identities or FDA decision claims")
        if (not isinstance(item.get("published_letter_type"), str)
                or item["published_letter_type"] not in {
                    "COMPLETE RESPONSE", "TENTATIVE APPROVAL",
                    "PROVISIONAL DETERMINATION",
                    "CORRECTED PROVISIONAL DETERMINATION",
                    "REFUSAL TO FILE", "RESCIND COMPLETE RESPONSE",
                    "UNCLASSIFIED",
                }):
            raise ValueError("Unknown published FDA letter class")
        seen.add(digest)
        if reason == "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION":
            if app is not None:
                raise ValueError("Ambiguous FDA letter cannot have verified app candidate")
            ambiguous.append(item)
        else:
            if not isinstance(app, str) or not APP.fullmatch(app):
                raise ValueError("Invalid original NDA/BLA application candidate")
            grouped[app].append(item)
    packets = []
    for app, letters in sorted(grouped.items()):
        reasons = {x["review_reason"] for x in letters}
        if len(reasons) != 1:
            raise ValueError("Published application has incompatible source gap categories")
        if any(x.get("repeated_published_letter_references_for_candidate") != len(letters)
               for x in letters):
            raise ValueError("Repeated letter counts do not reconcile by application")
        packets.append({
            "packet_id": app,
            "packet_kind": "APPLICATION_IDENTITY_RESEARCH",
            "application_id_candidate": app,
            "published_letter_source_hashes": sorted(
                x["source_record_sha256"] for x in letters
            ),
            "published_letter_references": len(letters),
            "source_gap_reason": next(iter(reasons)),
            "published_letter_type_counts": dict(sorted(Counter(
                x["published_letter_type"] for x in letters
            ).items())),
            "research_query_text": (
                app[:3] + " " + app[3:] + " original FDA action letter"
            ),
            "manual_evidence_lead_url": "",
            "manual_evidence_document_type": "",
            "manual_evidence_sha256": "",
            "manual_research_notes": "",
            "evidence_lead_status": VERIFICATION,
            "original_review_cycle": None,
            "fda_action_outcome": None,
            "adjudicator_authenticated": False,
            "model_eligible": False,
        })
    for item in sorted(ambiguous, key=lambda x: x["source_record_sha256"]):
        packets.append({
            "packet_id": "LETTER_" + item["source_record_sha256"],
            "packet_kind": "AMBIGUOUS_APPLICATION_ID_RESEARCH",
            "application_id_candidate": None,
            "published_letter_source_hashes": [item["source_record_sha256"]],
            "published_letter_references": 1,
            "source_gap_reason": item["review_reason"],
            "published_letter_type_counts": {item["published_letter_type"]: 1},
            "research_query_text": "FDA published letter source identity review",
            "manual_evidence_lead_url": "",
            "manual_evidence_document_type": "",
            "manual_evidence_sha256": "",
            "manual_research_notes": "",
            "evidence_lead_status": VERIFICATION,
            "original_review_cycle": None,
            "fda_action_outcome": None,
            "adjudicator_authenticated": False,
            "model_eligible": False,
        })
    kinds = Counter(p["packet_kind"] for p in packets)
    refs = sum(p["published_letter_references"] for p in packets)
    repeated = sum(p["published_letter_references"] > 1 for p in packets
                   if p["packet_kind"] == "APPLICATION_IDENTITY_RESEARCH")
    if (refs != len(source_queue)
            or kinds["APPLICATION_IDENTITY_RESEARCH"] != pinned_audit.get(
                "distinct_candidate_applications_needing_source_research")
            or kinds["AMBIGUOUS_APPLICATION_ID_RESEARCH"] != pinned_audit.get(
                "ambiguous_or_unparseable_letter_references")
            or repeated != pinned_audit.get(
                "candidate_applications_with_repeated_published_letters")
            or max((p["published_letter_references"] for p in packets
                    if p["packet_kind"] == "APPLICATION_IDENTITY_RESEARCH"),
                   default=0) != pinned_audit.get(
                    "maximum_published_letter_references_for_one_missing_application")
            or sum(p["published_letter_references"] for p in packets
                   if p["packet_kind"] == "APPLICATION_IDENTITY_RESEARCH")
               != pinned_audit.get("nda_bla_no_original_spine_letter_references")):
        raise ValueError("Grouped FDA source packets do not match frozen audit")
    return packets, {
        "status": "ORIGINAL_FDA_APPLICATION_EVIDENCE_SEARCH_PACKETS_UNVERIFIED",
        "research_cutoff": as_of.isoformat(),
        "source_letter_references": refs,
        "unverified_application_research_packets":
            kinds["APPLICATION_IDENTITY_RESEARCH"],
        "ambiguous_letter_identity_packets":
            kinds["AMBIGUOUS_APPLICATION_ID_RESEARCH"],
        "total_evidence_search_packets": len(packets),
        "applications_with_repeated_letter_references": repeated,
        "letter_references_grouped_under_application_research":
            sum(len(v) for v in grouped.values()),
        "nonmatches_are_not_fda_negative_labels": True,
        "independently_adjudicated_original_review_cycles": 0,
        "complete_fda_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
        "private_grouped_packets_not_exported": True,
    }


def screen_private_evidence_leads(
    original_packets: list[dict],
    submitted_packets: list[dict],
) -> dict:
    """Screen human-provided URLs as leads only, with zero outcome promotion."""
    if (not isinstance(original_packets, list)
            or not isinstance(submitted_packets, list)
            or len(original_packets) != len(submitted_packets)):
        raise ValueError("Missing/duplicate research packets")
    baseline = {p["packet_id"]: p for p in original_packets}
    if len(baseline) != len(original_packets):
        raise ValueError("Duplicate baseline research packet")
    allowed_changes = {
        "manual_evidence_lead_url", "manual_evidence_document_type",
        "manual_evidence_sha256", "manual_research_notes",
    }
    counters = Counter()
    seen = set()
    for p in submitted_packets:
        if (not isinstance(p, dict)
                or p.get("packet_id") not in baseline
                or p["packet_id"] in seen):
            raise ValueError("Unrecognized or duplicated FDA source research packet")
        seen.add(p["packet_id"])
        source = baseline[p["packet_id"]]
        if (set(source) != set(p)
                or any(p[key] != source[key] for key in source
                       if key not in allowed_changes)):
            raise ValueError("Published identity or scientific quarantine fields modified")
        url = p["manual_evidence_lead_url"]
        doc_type = p["manual_evidence_document_type"]
        digest = p["manual_evidence_sha256"]
        notes = p["manual_research_notes"]
        if (not isinstance(url, str)
                or not isinstance(doc_type, str)
                or not isinstance(digest, str)):
            raise ValueError("Malformed evidence lead fields")
        if (not isinstance(notes, str) or len(notes) > 1500
                or notes.lstrip().startswith(("=", "+", "-", "@"))
                or "\x00" in notes):
            raise ValueError("Unsafe FDA evidence lead notes")
        if not (url or doc_type or digest):
            counters["NO_OFFICIAL_SOURCE_LEAD"] += 1
            continue
        if not _official_url(url) or doc_type not in SOURCE_TYPES:
            raise ValueError("FDA evidence lead requires official HTTPS URL and document class")
        if digest and (not isinstance(digest, str) or not SOURCE_SHA.fullmatch(digest)):
            raise ValueError("Original source bytes digest malformed")
        if digest:
            counters["OFFICIAL_URL_WITH_UNAUTHENTICATED_SOURCE_DIGEST_CLAIM"] += 1
        else:
            counters["OFFICIAL_URL_UNVERIFIED_NO_SOURCE_DIGEST"] += 1
    return {
        "status": "UNVERIFIED_OFFICIAL_FDA_EVIDENCE_LEADS_SCREENED",
        "research_packets": len(original_packets),
        "lead_screening_counts": dict(sorted(counters.items())),
        "original_fda_documents_independently_authenticated": 0,
        "independently_adjudicated_original_review_cycles": 0,
        "complete_fda_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
    }
