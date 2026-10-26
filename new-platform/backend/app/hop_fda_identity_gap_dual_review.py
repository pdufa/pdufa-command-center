"""Private dual-review handoff for FDA published-letter identity/source gaps.

Distinct from the existing 154 shared-PDF page worksheet: this covers the 124
source references in 101 research packets that require identity/source review.
It makes two BLANK, source-locked reviewer worksheets. A matching text claim
is not a verified decision. No network, model labels, scientific release or
public submission of reviewer identities or notes.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import date
from urllib.parse import urlparse

SHA = re.compile(r"[0-9a-f]{64}\Z")
APP = re.compile(r"(?:NDA|BLA|ANDA)[0-9]{6}\Z")
REVIEWER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._@-]{2,79}\Z")
PAGES = re.compile(r"[1-9][0-9]{0,5}(?:-[1-9][0-9]{0,5})?\Z")
ROLE = ("FIRST", "SECOND")
CLAIM_FIELDS = (
    "observed_application_id",
    "observed_submission_class",
    "observed_letter_pages",
    "observed_fda_action_date",
    "observed_document_class",
    "observed_review_cycle",
    "source_evidence_notes",
)
ALLOWED_CLASS = (
    "COMPLETE_RESPONSE", "APPROVAL", "TENTATIVE_APPROVAL", "REFUSAL_TO_FILE",
    "RESCISSION_OR_CORRECTION", "OTHER_OR_UNCLASSIFIED",
)
SUBMISSION_CLASS = ("ORIGINAL", "SUPPLEMENT", "UNRESOLVED")
PUBLICATION_TYPE = {
    "COMPLETE RESPONSE", "TENTATIVE APPROVAL", "PROVISIONAL DETERMINATION",
    "CORRECTED PROVISIONAL DETERMINATION", "REFUSAL TO FILE",
    "RESCIND COMPLETE RESPONSE", "UNCLASSIFIED",
}
SOURCE_STATUS = (
    "PRIOR_FDA_PDF_BYTES_PROBED_ACTION_UNVERIFIED", "NO_RELEASED_PDF_SOURCE_LEAD",
)
REVIEW_STATUS = "BLANK_FDA_IDENTITY_GAP_REVIEW_NOT_ADJUDICATED"
LOCKED = (
    "packet_id", "packet_kind", "application_id_candidate",
    "published_letter_source_sha256", "published_letter_type",
    "source_letter_date_as_published", "historical_fda_pdf_url",
    "historical_fda_pdf_sha256", "prior_pdf_source_status",
    "historical_pdf_not_revalidated_now", "source_lock_sha256",
)
CATEGORIES = (
    "SOURCE_DATA_INCONSISTENCY",
    "TWO_CLAIMS_DIFFER",
    "CLAIMS_INCOMPLETE",
    "MATCHING_TEXT_UNVERIFIED",
)


def _official_pdf(value: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return (
            parsed.scheme == "https" and parsed.hostname == "download.open.fda.gov"
            and parsed.path.startswith("/crl/") and parsed.path.endswith(".pdf")
            and parsed.username is None and parsed.password is None
            and parsed.port is None and not parsed.query and not parsed.fragment
        )
    except ValueError:
        return False


def _lock(row: dict) -> str:
    return hashlib.sha256(json.dumps(
        {key: row[key] for key in LOCKED if key != "source_lock_sha256"},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def blank_identity_gap_dual_reviews(
    enriched_packets: list[dict],
) -> tuple[list[dict], list[dict], dict]:
    """Both roles receive source evidence only, never adjudicated outcomes."""
    if not isinstance(enriched_packets, list) or not enriched_packets:
        raise ValueError("No quarantined enriched FDA source packets")
    seen_packets = set()
    seen_sources = set()
    first, second = [], []
    missing = 0
    group_counts = Counter()
    for packet in enriched_packets:
        if not isinstance(packet, dict) or not isinstance(packet.get("packet_id"), str):
            raise ValueError("Invalid original FDA research packet")
        pid = packet["packet_id"]
        if pid in seen_packets:
            raise ValueError("Duplicate application research packet")
        seen_packets.add(pid)
        kind = packet.get("packet_kind")
        app = packet.get("application_id_candidate")
        hashes = packet.get("published_letter_source_hashes")
        leads = packet.get("previously_probed_published_pdf_leads")
        if (kind not in ("APPLICATION_IDENTITY_RESEARCH",
                         "AMBIGUOUS_APPLICATION_ID_RESEARCH")
                or not isinstance(hashes, list) or not hashes
                or len(hashes) != len(set(hashes))
                or not isinstance(leads, list) or len(leads) != len(hashes)
                or packet.get("published_letter_references") != len(hashes)
                or packet.get("original_review_cycle") is not None
                or packet.get("fda_action_outcome") is not None
                or packet.get("adjudicator_authenticated") is not False
                or packet.get("model_eligible") is not False
                or packet.get("evidence_lead_status") !=
                    "UNVERIFIED_FDA_SOURCE_LEAD_REQUIRES_INDEPENDENT_REVIEW"
                or any(packet.get(k) != "" for k in (
                    "manual_evidence_lead_url", "manual_evidence_document_type",
                    "manual_evidence_sha256", "manual_research_notes"
                ))):
            raise ValueError("Private FDA packet source linkage/model gate altered")
        if kind == "APPLICATION_IDENTITY_RESEARCH":
            if not isinstance(app, str) or not APP.fullmatch(app) or pid != app:
                raise ValueError("Source application grouping does not match packet")
        elif (app is not None or len(hashes) != 1
              or pid != "LETTER_" + hashes[0]):
            raise ValueError("Ambiguous FDA identity packet was reidentified")
        if set(hashes) != {x.get("published_letter_source_sha256")
                          for x in leads if isinstance(x, dict)}:
            raise ValueError("FDA original source hash not matched to PDF leads")
        for lead in leads:
            if not isinstance(lead, dict):
                raise ValueError("Missing source PDF lead")
            sid = lead["published_letter_source_sha256"]
            pdf_status = lead.get("pdf_lead_status")
            url = lead.get("official_fda_pdf_url")
            digest = lead.get("historically_observed_full_pdf_sha256")
            published_type = lead.get("published_letter_type")
            published_date = lead.get(
                "published_letter_date_not_adjudicated_action_date"
            )
            if (not isinstance(sid, str) or not SHA.fullmatch(sid)
                    or sid in seen_sources
                    or pdf_status not in SOURCE_STATUS
                    or published_type not in PUBLICATION_TYPE
                    or not isinstance(published_date, str)
                    or not re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}",
                                        published_date)
                    or lead.get("pdf_bytes_revalidated_in_current_run") is not False
                    or lead.get("action_page_range_independently_verified") is not False
                    or lead.get("review_cycle_independently_verified") is not False
                    or lead.get("model_eligible") is not False):
                raise ValueError("FDA published evidence has unsupported adjudication")
            if pdf_status == SOURCE_STATUS[0]:
                if not _official_pdf(url) or not isinstance(digest, str) or not SHA.fullmatch(digest):
                    raise ValueError("Confirmed PDF lead lacks trusted source fingerprint")
            else:
                if url is not None or digest is not None:
                    raise ValueError("Unavailable FDA PDF may not claim source bytes")
                missing += 1
            seen_sources.add(sid)
            immutable = {
                "packet_id": pid, "packet_kind": kind,
                "application_id_candidate": app,
                "published_letter_source_sha256": sid,
                "published_letter_type": published_type,
                "source_letter_date_as_published": published_date,
                "historical_fda_pdf_url": url,
                "historical_fda_pdf_sha256": digest,
                "prior_pdf_source_status": pdf_status,
                "historical_pdf_not_revalidated_now": True,
            }
            immutable["source_lock_sha256"] = _lock(immutable)
            group_counts[kind] += 1
            for role, store in ((ROLE[0], first), (ROLE[1], second)):
                store.append({
                    **immutable,
                    "packet_role": role,
                    "review_packet_status": REVIEW_STATUS,
                    "reviewer_token": "",
                    **{field: "" for field in CLAIM_FIELDS},
                    "reviewer_authentication_verified": False,
                    "independent_regulatory_adjudication_verified": False,
                    "model_eligible": False,
                })
    first.sort(key=lambda x: (x["packet_id"], x["published_letter_source_sha256"]))
    second.sort(key=lambda x: (x["packet_id"], x["published_letter_source_sha256"]))
    return first, second, {
        "status": "BLANK_DUAL_FDA_IDENTITY_GAP_REVIEW_PACKETS_PREPARED",
        "private_research_group_count": len(seen_packets),
        "published_letter_references": len(seen_sources),
        "first_reviewer_blank_rows": len(first),
        "second_reviewer_blank_rows": len(second),
        "references_without_source_pdf": missing,
        "source_classification_rows": dict(sorted(group_counts.items())),
        "reviewer_identity_authenticated": False,
        "independent_reviews_completed": 0,
        "review_cycle_outcomes_verified": 0,
        "complete_original_nda_bla_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "approval_rate": None,
        "readiness": "REVIEW_REQUIRED",
        "reviewer_detail_records_not_exported": True,
    }


def reconcile_identity_gap_review_claims(
    baseline_first: list[dict], baseline_second: list[dict],
    first_claims: list[dict], second_claims: list[dict], *, as_of: date
) -> dict:
    """Compare textual reviewer claims without authenticating reviewers or actions."""
    if not isinstance(as_of, date):
        raise ValueError("Missing review cutoff")
    if not isinstance(baseline_first, list) or not isinstance(baseline_second, list):
        raise ValueError("Invalid reviewer baseline")
    first = {x["published_letter_source_sha256"]: x for x in baseline_first}
    second = {x["published_letter_source_sha256"]: x for x in baseline_second}
    if len(first) != len(baseline_first) or set(first) != set(second):
        raise ValueError("Original FDA reviewer packet baseline duplicated/mismatched")
    if (any(x["packet_role"] != ROLE[0] for x in first.values())
            or any(x["packet_role"] != ROLE[1] for x in second.values())):
        raise ValueError("FDA independent review packet role changed")

    def load(claims: list[dict], base: dict, role: str) -> dict:
        if not isinstance(claims, list):
            raise ValueError("Invalid FDA reviewer claims")
        out = {}
        for row in claims:
            if not isinstance(row, dict):
                raise ValueError("Malformed FDA reviewer claim")
            sid = row.get("published_letter_source_sha256")
            if sid not in base or sid in out:
                raise ValueError("Missing, duplicate or unrecognized original source")
            original = base[sid]
            if (set(row) != set(original)
                    or any(row[k] != original[k] for k in original if k not in (
                        "reviewer_token", *CLAIM_FIELDS
                    ))
                    or row.get("packet_role") != role
                    or row.get("review_packet_status") != REVIEW_STATUS
                    or row.get("source_lock_sha256") != _lock(row)
                    or row.get("model_eligible") is not False
                    or row.get("reviewer_authentication_verified") is not False
                    or row.get("independent_regulatory_adjudication_verified") is not False):
                raise ValueError("Original FDA publication/source/model gate changed")
            token = row["reviewer_token"]
            if not isinstance(token, str) or (token and not REVIEWER.fullmatch(token)):
                raise ValueError("Invalid claimed reviewer token")
            for field in CLAIM_FIELDS:
                if not isinstance(row[field], str) or len(row[field]) > (
                    4000 if field == "source_evidence_notes" else 140
                ):
                    raise ValueError("Malformed or oversized FDA review claim")
                if row[field].lstrip().startswith(("=", "+", "-", "@")) or "\x00" in row[field]:
                    raise ValueError("Unsafe FDA reviewer claim")
            if row["observed_application_id"] and not APP.fullmatch(
                row["observed_application_id"]
            ):
                raise ValueError("Observed FDA application identifier malformed")
            if row["observed_submission_class"] and row["observed_submission_class"] not in SUBMISSION_CLASS:
                raise ValueError("Observed FDA submission class malformed")
            if row["observed_document_class"] and row["observed_document_class"] not in ALLOWED_CLASS:
                raise ValueError("Observed FDA document class malformed")
            if row["observed_letter_pages"]:
                pages = row["observed_letter_pages"]
                if not PAGES.fullmatch(pages):
                    raise ValueError("Invalid original FDA letter page interval")
                vals = [int(v) for v in pages.split("-")]
                if len(vals) == 2 and vals[0] > vals[1]:
                    raise ValueError("Reversed FDA letter page range")
            if row["observed_fda_action_date"]:
                try:
                    day = date.fromisoformat(row["observed_fda_action_date"])
                except ValueError:
                    raise ValueError("Invalid FDA action date claim") from None
                if day > as_of:
                    raise ValueError("FDA action date claim after research cutoff")
            if row["observed_review_cycle"] and not re.fullmatch(
                r"(?:[1-9][0-9]{0,2}|UNKNOWN)", row["observed_review_cycle"]
            ):
                raise ValueError("FDA original review cycle number not justified")
            out[sid] = row
        if set(out) != set(base):
            raise ValueError("Missing original FDA letter rows from reviewer packet")
        return out

    a = load(first_claims, first, ROLE[0])
    b = load(second_claims, second, ROLE[1])
    tokens_a = {row["reviewer_token"] for row in a.values() if row["reviewer_token"]}
    tokens_b = {row["reviewer_token"] for row in b.values() if row["reviewer_token"]}
    if len(tokens_a) > 1 or len(tokens_b) > 1 or tokens_a.intersection(tokens_b):
        raise ValueError("Conflicting or repeated reviewer identity claims")
    summary = Counter()
    disputes = []
    for sid in sorted(first):
        left, right = a[sid], b[sid]
        if (left["prior_pdf_source_status"] == SOURCE_STATUS[1]
                or left["application_id_candidate"] is None):
            # Missing application identity or original PDF prevents a
            # source-complete dual review, regardless of matching typed claims.
            summary[CATEGORIES[0]] += 1
            continue
        if not left["reviewer_token"] or not right["reviewer_token"] or any(
            not left[field].strip() or not right[field].strip() for field in CLAIM_FIELDS
        ):
            summary[CATEGORIES[2]] += 1
            continue
        different = [key for key in CLAIM_FIELDS if key != "source_evidence_notes"
                     and left[key] != right[key]]
        if different:
            summary[CATEGORIES[1]] += 1
            disputes.append({"source_record_sha256": sid, "disputed_fields": different})
        else:
            summary[CATEGORIES[3]] += 1
    return {
        "status": "FDA_GAP_DUAL_REVIEW_CLAIMS_COMPARED_NOT_ADJUDICATED",
        "published_letter_references": len(first),
        "review_category_counts": {name: summary[name] for name in CATEGORIES},
        "unverified_differences_needing_reviewer_attention": disputes,
        "claimed_distinct_reviewer_tokens": len(tokens_a) + len(tokens_b),
        "reviewer_identities_authenticated": False,
        "independent_regulatory_review_verified": False,
        "independently_verified_original_fda_actions": 0,
        "complete_original_nda_bla_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "readiness": "REVIEW_REQUIRED",
    }
