"""Private, unreviewed A/B FDA original-source handoffs for application gaps.

Source input is the 101 *private* enriched research packets. Historical
downloaded PDF SHA-256 links are still leads, not independently authenticated
application review-cycle decisions. Preparing two blank packets is NOT review.
No network, production database, prediction, or external reviewer access.
"""
from __future__ import annotations

import re
from copy import deepcopy
from collections import Counter
from datetime import date
from urllib.parse import urlparse

from .hop_fda_prior_pdf_lead_join import PUBLISHED_LEAD_STATUS
from .hop_fda_gap_research_packets import VERIFICATION

SHA = re.compile(r"[0-9a-f]{64}\Z")
APP = re.compile(r"(?:NDA|BLA)[0-9]{6}\Z")
EXPECTED_PACKET_FIELDS = {
    "packet_id", "packet_kind", "application_id_candidate",
    "published_letter_source_hashes", "published_letter_references",
    "source_gap_reason", "published_letter_type_counts", "research_query_text",
    "manual_evidence_lead_url", "manual_evidence_document_type",
    "manual_evidence_sha256", "manual_research_notes", "evidence_lead_status",
    "original_review_cycle", "fda_action_outcome", "adjudicator_authenticated",
    "model_eligible", "previously_probed_published_pdf_leads",
}
EXPECTED_PDF_FIELDS = {
    "published_letter_source_sha256", "official_fda_pdf_url",
    "historically_observed_full_pdf_sha256", "published_letter_type",
    "published_letter_date_not_adjudicated_action_date", "pdf_lead_status",
    "pdf_bytes_revalidated_in_current_run",
    "action_page_range_independently_verified",
    "review_cycle_independently_verified", "model_eligible",
}
REASON_BY_KIND = {
    "APPLICATION_IDENTITY_RESEARCH": {
        "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE",
        "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION",
    },
    "AMBIGUOUS_APPLICATION_ID_RESEARCH": {
        "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION",
    },
}
STATUS = "BLANK_FDA_ORIGINAL_SOURCE_INSPECTION_NOT_ADJUDICATED"


def _known_prior_pdf_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    try:
        p = urlparse(url)
        return (p.scheme == "https" and p.hostname == "download.open.fda.gov"
                and p.path.startswith("/crl/") and p.path.lower().endswith(".pdf")
                and p.port is None and not p.username and not p.password
                and not p.query and not p.fragment and len(url) <= 1200)
    except ValueError:
        return False


def prepare_gap_source_review_handoffs(
    private_enriched: list[dict], *, pinned_audit: dict, as_of: date,
) -> tuple[list[dict], list[dict], dict]:
    """Return separate blank reviewer files and aggregate-only research audit.

    Each reviewer must verify any original PDF and actual FDA action themselves.
    This code neither authenticates reviewers nor claims a regulatory result.
    """
    if (as_of != date(2026, 10, 25)
            or not isinstance(pinned_audit, dict)
            or pinned_audit.get("status") !=
               "ORIGINAL_FDA_APPLICATION_EVIDENCE_SEARCH_PACKETS_UNVERIFIED"
            or pinned_audit.get("research_cutoff") != as_of.isoformat()
            or pinned_audit.get("independently_adjudicated_original_review_cycles") != 0
            or pinned_audit.get("complete_fda_decision_denominator_verified") is not False
            or pinned_audit.get("model_eligible_records") != 0
            or pinned_audit.get("prediction_probability") is not None
            or pinned_audit.get("private_grouped_packets_not_exported") is not True
            or not isinstance(private_enriched, list)
            or not private_enriched
            or len(private_enriched) != pinned_audit.get("total_evidence_search_packets")):
        raise ValueError("Require pinned, fully quarantined FDA source search inputs")
    first, second = [], []
    seen_packets, seen_letters = set(), set()
    types = Counter()
    source_links = Counter()
    for packet in private_enriched:
        if not isinstance(packet, dict) or set(packet) != EXPECTED_PACKET_FIELDS:
            raise ValueError("Unknown or missing private FDA source packet field")
        pid = packet.get("packet_id")
        kind = packet.get("packet_kind")
        app = packet.get("application_id_candidate")
        hashes = packet.get("published_letter_source_hashes")
        count = packet.get("published_letter_references")
        sources = packet.get("previously_probed_published_pdf_leads")
        if (not isinstance(pid, str) or pid in seen_packets
                or kind not in REASON_BY_KIND
                or packet.get("source_gap_reason") not in REASON_BY_KIND[kind]
                or not isinstance(hashes, list) or not hashes
                or not all(isinstance(x, str) and SHA.fullmatch(x) for x in hashes)
                or sorted(set(hashes)) != hashes
                or type(count) is not int or count != len(hashes)
                or not isinstance(sources, list) or len(sources) != count
                or packet.get("model_eligible") is not False
                or packet.get("adjudicator_authenticated") is not False
                or packet.get("fda_action_outcome") is not None
                or packet.get("original_review_cycle") is not None
                or packet.get("evidence_lead_status") != VERIFICATION
                or any(packet.get(key) != "" for key in (
                    "manual_evidence_lead_url", "manual_evidence_document_type",
                    "manual_evidence_sha256", "manual_research_notes"))):
            raise ValueError("Unreviewed FDA packet integrity/absence-of-labels required")
        if kind == "APPLICATION_IDENTITY_RESEARCH":
            if not isinstance(app, str) or not APP.fullmatch(app) or pid != app:
                raise ValueError("Invalid original NDA/BLA application source identity")
        else:
            if app is not None or count != 1 or pid != "LETTER_" + hashes[0]:
                raise ValueError("Ambiguous original FDA application must remain separate")
        seen_packets.add(pid)
        if seen_letters.intersection(hashes):
            raise ValueError("FDA published reference assigned to multiple packets")
        seen_letters.update(hashes)
        lead_types = Counter()
        checked = set()
        public_leads = []
        for lead in sources:
            if not isinstance(lead, dict) or set(lead) != EXPECTED_PDF_FIELDS:
                raise ValueError("Unknown FDA PDF lead fields")
            digest = lead.get("published_letter_source_sha256")
            url = lead.get("official_fda_pdf_url")
            observed_hash = lead.get("historically_observed_full_pdf_sha256")
            status = lead.get("pdf_lead_status")
            doc_type = lead.get("published_letter_type")
            if (digest not in hashes or digest in checked
                    or not isinstance(doc_type, str) or not doc_type
                    or any(lead.get(field) is not False for field in (
                        "pdf_bytes_revalidated_in_current_run",
                        "action_page_range_independently_verified",
                        "review_cycle_independently_verified", "model_eligible"))):
                raise ValueError("Previously probed FDA PDF was promoted or altered")
            checked.add(digest)
            if status == PUBLISHED_LEAD_STATUS:
                if not _known_prior_pdf_url(url) or not isinstance(observed_hash, str) or not SHA.fullmatch(observed_hash):
                    raise ValueError("Previously observed FDA document provenance is invalid")
                source_links["previously_confirmed_pdf_letter_links"] += 1
            elif status == "NO_RELEASED_PDF_SOURCE_LEAD":
                if url is not None or observed_hash is not None:
                    raise ValueError("Unavailable FDA PDF cannot claim confirmed bytes")
                source_links["unavailable_pdf_letter_links"] += 1
            else:
                raise ValueError("Unknown historical FDA document evidence status")
            lead_types[doc_type] += 1
            public_leads.append({
                "published_letter_source_sha256": digest,
                "official_fda_pdf_url": url,
                "historical_pdf_byte_sha256_lead": observed_hash,
                "historical_byte_probe_only_not_original_action_verified": True,
            })
        if checked != set(hashes) or lead_types != packet.get("published_letter_type_counts"):
            raise ValueError("FDA packet letter types or original source list disagrees")
        types[kind] += 1
        immutable = {
            "packet_id": pid,
            "application_id_candidate_not_verified": app,
            "source_gap_reason": packet["source_gap_reason"],
            "original_published_letter_hashes": hashes.copy(),
            "previously_probed_pdf_leads": sorted(
                public_leads, key=lambda x: x["published_letter_source_sha256"]),
        }
        for role, destination in (("FIRST", first), ("SECOND", second)):
            destination.append({
                **deepcopy(immutable),
                "packet_role": role,
                "packet_status": STATUS,
                "reviewer_identity": "",
                "reviewer_observed_original_pdf_sha256": "",
                "reviewer_observed_application_id": "",
                "reviewer_observed_action_date": "",
                "reviewer_observed_action_type": "",
                "reviewer_observed_review_cycle": "",
                "reviewer_original_source_page_range": "",
                "reviewer_source_notes": "",
                "fda_decision_independently_adjudicated": False,
                "model_eligible": False,
                "prediction_probability": None,
            })
    expected = (
        pinned_audit.get("unverified_application_research_packets"),
        pinned_audit.get("ambiguous_letter_identity_packets"),
    )
    if (tuple(types[k] for k in (
            "APPLICATION_IDENTITY_RESEARCH",
            "AMBIGUOUS_APPLICATION_ID_RESEARCH")) != expected
            or len(seen_letters) != pinned_audit.get("source_letter_references")
            or len(seen_packets) != len(private_enriched)):
        raise ValueError("FDA A/B source handoffs do not match frozen research totals")
    return first, second, {
        "status": "PRIVATE_BLANK_FDA_SOURCE_REVIEW_HANDOFF_PREPARED",
        "research_cutoff": as_of.isoformat(),
        "original_source_search_packets": len(private_enriched),
        "published_letter_source_references": len(seen_letters),
        "first_blank_review_packets": len(first),
        "second_blank_review_packets": len(second),
        "pdf_lead_counts": dict(sorted(source_links.items())),
        "reviewer_identities_authenticated": False,
        "independent_review_pairs_completed": 0,
        "fda_review_cycle_outcomes_independently_verified": 0,
        "complete_original_nda_bla_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "private_per_application_records_not_exported": True,
        "note": "Two unsigned, blank source review copies do not establish original FDA decisions.",
    }
