"""Join PRIVATE FDA application research packets to previously probed PDF bytes.

Sources: pinned October 2026 official published CRL archive and previously
saved exact PDF byte-probe audit. Source PDF availability, official URL and
SHA256 are evidence LEADS, never original action review-cycle adjudication.
No network, training, production mutations, or extrapolated outcomes.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from .hop_fda_document_probe import official_document_candidate

SHA = re.compile(r"[a-f0-9]{64}\Z")
PROBE_STATUS = "PDF_FETCH_CHECK_ONLY_NOT_HISTORICAL_OUTCOME_VERIFICATION"
PUBLISHED_LEAD_STATUS = "PRIOR_FDA_PDF_BYTES_PROBED_ACTION_UNVERIFIED"


def join_prior_pdf_probes_to_research_packets(
    private_packets: list[dict], pdf_probe: dict, pdf_probe_audit: dict,
    *, pinned_pdf_index: dict, pinned_pdf_group_index: dict,
) -> tuple[list[dict], dict]:
    """Source-hash join; historical PDF bytes were checked in a prior run.

    The output is PRIVATE per-letter evidence leads plus PUBLIC counts only.
    Every source row and document must stay quarantined.
    """
    if (not isinstance(pdf_probe, dict) or pdf_probe.get("status") != PROBE_STATUS
            or not isinstance(pdf_probe.get("records"), list)
            or not isinstance(pdf_probe_audit, dict)
            or pdf_probe_audit.get("status") != PROBE_STATUS
            or not isinstance(pinned_pdf_index, dict)
            or not isinstance(pinned_pdf_group_index, dict)
            or pinned_pdf_group_index.get("status") != "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION"
            or pinned_pdf_group_index.get("model_eligible_records") != 0
            or pinned_pdf_group_index.get("complete_application_denominator_verified") is not False
            or pinned_pdf_group_index.get("independently_verified_review_cycle_outcomes") != 0
            or pinned_pdf_index.get("status") !=
                "ALL_PUBLISHED_FDA_ACTION_PDFS_QUARANTINED_NOT_VALIDATED_OUTCOMES"
            or pdf_probe_audit.get("model_eligible_records") != 0
            or pinned_pdf_index.get("model_eligible_records") != 0
            or pdf_probe_audit.get("prediction_probability") is not None
            or pinned_pdf_index.get("prediction_probability") is not None
            or pdf_probe_audit.get("independently_verified_review_cycles") != 0
            or pinned_pdf_index.get("adjudicated_review_cycle_outcomes") != 0
            or pdf_probe_audit.get("complete_application_denominator_verified") is not False
            or pinned_pdf_index.get("complete_application_denominator_verified") is not False):
        raise ValueError("Prior FDA source PDF inventory is not quarantined")
    rows = pdf_probe["records"]
    if (len(rows) != pdf_probe_audit.get("total_identity_review_cases")
            or len(rows) != pinned_pdf_index.get("published_letter_records")
            or pdf_probe_audit.get("official_pdf_bytes_confirmed") !=
                pinned_pdf_index.get("full_official_pdf_bytes_confirmed")
            or pdf_probe_audit.get("source_letter_archive_sha256") != {
                "https://download.open.fda.gov/transparency/crl/transparency-crl-0001-of-0001.json.zip":
                    pinned_pdf_index.get("original_fda_archive_sha256"),
            }):
        raise ValueError("Archived FDA PDF source inventory/version mismatch")
    index = {}
    pdf_to_url = {}
    overall = Counter()
    for row in rows:
        if (not isinstance(row, dict)
                or row.get("model_eligible") is not False
                or row.get("document_identity_adjudicated") is not False
                or row.get("review_cycle_verified") is not False
                or row.get("effective_fda_action_date_verified") is not False):
            raise ValueError("Published FDA PDF identity or decision promoted")
        source_sha = row.get("source_record_sha256")
        if (not isinstance(source_sha, str) or not SHA.fullmatch(source_sha)
                or source_sha in index):
            raise ValueError("Invalid or duplicate original FDA letter reference")
        filename = row.get("source_file_name_as_published")
        candidate_url = official_document_candidate(filename)
        fetch_status = row.get("document_fetch_status")
        url = row.get("official_fda_pdf_url_if_confirmed")
        pdf_sha = row.get("full_document_sha256_if_confirmed")
        if fetch_status == "OFFICIAL_PDF_BYTES_CONFIRMED":
            if (candidate_url is None or url != candidate_url
                    or not isinstance(pdf_sha, str) or not SHA.fullmatch(pdf_sha)):
                raise ValueError("PDF provenance URL or observed bytes digest mismatch")
            if pdf_sha in pdf_to_url and pdf_to_url[pdf_sha] != url:
                raise ValueError("Same full FDA document digest has competing source URLs")
            pdf_to_url[pdf_sha] = url
        elif fetch_status == "NO_SAFE_FILENAME_TO_CHECK":
            if candidate_url is not None or url is not None or pdf_sha is not None:
                raise ValueError("Unavailable FDA source falsely claims confirmed PDF")
        else:
            raise ValueError("Unexpected pinned FDA document fetch status")
        overall[fetch_status] += 1
        index[source_sha] = row
    expected_totals = pdf_probe_audit.get("document_fetch_status_counts")
    if (dict(overall) != expected_totals
            or overall["OFFICIAL_PDF_BYTES_CONFIRMED"] !=
               pinned_pdf_index.get("full_official_pdf_bytes_confirmed")
            or overall["NO_SAFE_FILENAME_TO_CHECK"] !=
               pinned_pdf_index.get("source_records_without_safe_pdf_filename")
            or len(pdf_to_url) != pinned_pdf_group_index.get("unique_confirmed_pdf_documents")
            or pinned_pdf_group_index.get("official_pdf_confirmed_letter_references") != overall["OFFICIAL_PDF_BYTES_CONFIRMED"]
            or pinned_pdf_group_index.get("original_fda_archive_sha256") != pinned_pdf_index.get("original_fda_archive_sha256")):
        raise ValueError("FDA document availability/unique PDF counts not verified")

    if not isinstance(private_packets, list) or not private_packets:
        raise ValueError("Missing private source-gap research worklist")
    enriched = []
    consumed_source = set()
    packet_ids = set()
    per_packet = Counter()
    source_pdf = Counter()
    for packet in private_packets:
        if (not isinstance(packet, dict)
                or not isinstance(packet.get("packet_id"), str)
                or packet["packet_id"] in packet_ids
                or packet.get("model_eligible") is not False
                or packet.get("adjudicator_authenticated") is not False
                or packet.get("fda_action_outcome") is not None
                or packet.get("original_review_cycle") is not None
                or packet.get("evidence_lead_status") !=
                    "UNVERIFIED_FDA_SOURCE_LEAD_REQUIRES_INDEPENDENT_REVIEW"
                or packet.get("manual_evidence_lead_url") != ""
                or packet.get("manual_evidence_sha256") != ""):
            raise ValueError("Private FDA evidence-search packet was promoted")
        packet_ids.add(packet["packet_id"])
        source_hashes = packet.get("published_letter_source_hashes")
        if (not isinstance(source_hashes, list) or not source_hashes
                or len(source_hashes) != len(set(source_hashes))
                or packet.get("published_letter_references") != len(source_hashes)):
            raise ValueError("FDA packet has invalid original source references")
        leads = []
        for digest in source_hashes:
            if digest not in index or digest in consumed_source:
                raise ValueError("Unknown or multiply assigned FDA published source")
            consumed_source.add(digest)
            pdf = index[digest]
            if pdf["document_fetch_status"] == "OFFICIAL_PDF_BYTES_CONFIRMED":
                source_pdf[pdf["full_document_sha256_if_confirmed"]] += 1
                leads.append({
                    "published_letter_source_sha256": digest,
                    "official_fda_pdf_url": pdf["official_fda_pdf_url_if_confirmed"],
                    "historically_observed_full_pdf_sha256":
                        pdf["full_document_sha256_if_confirmed"],
                    "published_letter_type": pdf["letter_type_as_published"],
                    "published_letter_date_not_adjudicated_action_date":
                        pdf["letter_date_as_published"],
                    "pdf_lead_status": PUBLISHED_LEAD_STATUS,
                    "pdf_bytes_revalidated_in_current_run": False,
                    "action_page_range_independently_verified": False,
                    "review_cycle_independently_verified": False,
                    "model_eligible": False,
                })
            else:
                leads.append({
                    "published_letter_source_sha256": digest,
                    "official_fda_pdf_url": None,
                    "historically_observed_full_pdf_sha256": None,
                    "published_letter_type": pdf["letter_type_as_published"],
                    "published_letter_date_not_adjudicated_action_date":
                        pdf["letter_date_as_published"],
                    "pdf_lead_status": "NO_RELEASED_PDF_SOURCE_LEAD",
                    "pdf_bytes_revalidated_in_current_run": False,
                    "action_page_range_independently_verified": False,
                    "review_cycle_independently_verified": False,
                    "model_eligible": False,
                })
        found = sum(x["official_fda_pdf_url"] is not None for x in leads)
        if found == len(leads):
            per_packet["ALL_PUBLISHED_PDF_LEADS_AVAILABLE_FROM_PRIOR_AUDIT"] += 1
        elif found == 0:
            per_packet["NO_PUBLISHED_PDF_LEAD"] += 1
        else:
            per_packet["PARTIAL_PUBLISHED_PDF_LEADS"] += 1
        per_packet["previously_confirmed_pdf_letter_links"] += found
        per_packet["unavailable_pdf_letter_links"] += len(leads) - found
        enriched.append({**packet, "previously_probed_published_pdf_leads": leads})
    if len(consumed_source) != sum(p["published_letter_references"] for p in private_packets):
        raise ValueError("Source reference not covered exactly once by packets")
    return enriched, {
        "status": "UNVERIFIED_ORIGINAL_FDA_EVIDENCE_PACKET_PDF_LEADS_JOINED",
        "total_private_original_application_research_packets": len(enriched),
        "published_letter_references_in_packets": len(consumed_source),
        "previously_probed_official_pdf_letter_references":
            per_packet["previously_confirmed_pdf_letter_links"],
        "unavailable_published_pdf_letter_references":
            per_packet["unavailable_pdf_letter_links"],
        "distinct_prior_confirmed_pdf_sha256_in_packet_worklist": len(source_pdf),
        "shared_full_pdf_digests_across_multiple_letter_references":
            sum(count > 1 for count in source_pdf.values()),
        "packet_availability_counts": {
            k: per_packet[k] for k in (
                "ALL_PUBLISHED_PDF_LEADS_AVAILABLE_FROM_PRIOR_AUDIT",
                "PARTIAL_PUBLISHED_PDF_LEADS",
                "NO_PUBLISHED_PDF_LEAD",
            )
        },
        "entire_fda_published_letter_source_reference_count": len(rows),
        "entire_fda_prior_confirmed_pdf_letter_count":
            overall["OFFICIAL_PDF_BYTES_CONFIRMED"],
        "source_pdf_probe_original_archive_sha256":
            pinned_pdf_index["original_fda_archive_sha256"],
        "source_pdf_probe_run_url":
            pinned_pdf_index["source_collection_run_url"],
        "prior_pdf_bytes_probed_not_revalidated_in_current_run": True,
        "individual_original_letter_page_ranges_verified": 0,
        "original_fda_review_cycles_independently_adjudicated": 0,
        "complete_national_nda_bla_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
        "private_pdf_source_link_records_not_exported": True,
    }
