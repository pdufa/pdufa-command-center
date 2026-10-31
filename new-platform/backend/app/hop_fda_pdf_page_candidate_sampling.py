"""Bounded private sampling of previously pinned FDA published PDF page hints.

Each sampled official PDF must match its *earlier actual observed SHA-256*
before any page text is used. Page numbers where a candidate application
number appears are provisional navigation hints, never verified FDA action
pages or outcome decisions. Only aggregate counts leave the private runner.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from urllib.parse import urlparse

PDF_PREFIX = "https://download.open.fda.gov/crl/"
SOURCE_SHA = re.compile(r"[a-f0-9]{64}\Z")
APP = re.compile(r"(?:NDA|BLA)[0-9]{6}\Z")
MAX_DOCUMENTS = 12
MAX_PDF_BYTES = 20_000_000
MAX_PDF_PAGES = 300
MAX_INSPECT_PAGES = 40


def _official_url(value: str) -> bool:
    if not isinstance(value, str) or not value.startswith(PDF_PREFIX):
        return False
    try:
        u = urlparse(value)
        return (
            u.scheme == "https"
            and u.hostname == "download.open.fda.gov"
            and u.username is None and u.password is None
            and u.port is None and u.query == "" and u.fragment == ""
            and u.path.startswith("/crl/") and u.path.lower().endswith(".pdf")
            and len(value) <= 500
            and not any(ch.isspace() for ch in value)
        )
    except ValueError:
        return False


def select_pinned_pdf_sample(
    enriched_packets: list[dict], *, limit: int = 8, offset: int = 0
) -> tuple[list[dict], dict]:
    if (type(limit) is not int or not 1 <= limit <= MAX_DOCUMENTS
            or type(offset) is not int or offset < 0):
        raise ValueError("Invalid PDF sample limit or offset")
    if not isinstance(enriched_packets, list) or not enriched_packets:
        raise ValueError("Private FDA source packets missing")
    known = {}
    seen_packets = set()
    seen_source = set()
    for packet in enriched_packets:
        if not isinstance(packet, dict):
            raise ValueError("Malformed source evidence packet")
        pid = packet.get("packet_id")
        app = packet.get("application_id_candidate")
        leads = packet.get("previously_probed_published_pdf_leads")
        sources = packet.get("published_letter_source_hashes")
        if (
            not isinstance(pid, str) or pid in seen_packets
            or (app is not None and (not isinstance(app, str) or not APP.fullmatch(app) or pid != app))
            or not isinstance(sources, list)
            or not isinstance(leads, list)
            or len(sources) != len(leads)
            or len(sources) != len(set(sources))
            or set(sources) != {
                lead.get("published_letter_source_sha256")
                for lead in leads if isinstance(lead, dict)
            }
            or packet.get("published_letter_references") != len(leads)
            or packet.get("model_eligible") is not False
            or packet.get("adjudicator_authenticated") is not False
            or packet.get("fda_action_outcome") is not None
            or packet.get("original_review_cycle") is not None
        ):
            raise ValueError("FDA source packet identity or outcome flags not quarantined")
        seen_packets.add(pid)
        for lead in leads:
            if not isinstance(lead, dict):
                raise ValueError("Invalid FDA source document lead")
            sid = lead.get("published_letter_source_sha256")
            sha = lead.get("historically_observed_full_pdf_sha256")
            url = lead.get("official_fda_pdf_url")
            if not isinstance(sid, str) or not SOURCE_SHA.fullmatch(sid) or sid in seen_source:
                raise ValueError("Duplicate or invalid FDA published letter identity")
            seen_source.add(sid)
            if (
                lead.get("model_eligible") is not False
                or lead.get("review_cycle_independently_verified") is not False
                or lead.get("action_page_range_independently_verified") is not False
                or lead.get("pdf_bytes_revalidated_in_current_run") is not False
            ):
                raise ValueError("Published FDA source lead was promoted")
            if url is None:
                if sha is not None or lead.get("pdf_lead_status") != "NO_RELEASED_PDF_SOURCE_LEAD":
                    raise ValueError("Unreleased PDF cannot have source bytes")
                continue
            if (
                not _official_url(url)
                or not isinstance(sha, str) or not SOURCE_SHA.fullmatch(sha)
                or lead.get("pdf_lead_status") != "PRIOR_FDA_PDF_BYTES_PROBED_ACTION_UNVERIFIED"
            ):
                raise ValueError("Untrusted official PDF source or source fingerprint")
            # Multiple letters may share the same full PDF. Same bytes with a
            # different URL is a source inconsistency; do not guess which.
            prior = known.get(sha)
            if prior is None:
                known[sha] = {"sha256": sha, "url": url, "applications": set(),
                              "source_references": 0}
            elif prior["url"] != url:
                raise ValueError("Same FDA PDF digest has conflicting publication URL")
            known[sha]["source_references"] += 1
            if app is not None:
                known[sha]["applications"].add(app)

    # Source-index ordering is immaterial; exact PDF digest makes selection
    # reproducible and lets audits compare the same sample on later runs.
    if offset >= len(known):
        raise ValueError("Requested FDA PDF sample offset is outside pinned corpus")
    selected = []
    for sha, source in sorted(known.items())[offset:offset + limit]:
        selected.append({
            "historical_pdf_sha256": sha,
            "official_fda_pdf_url": source["url"],
            "candidate_application_ids": sorted(source["applications"]),
            "published_letter_references_sharing_file": source["source_references"],
        })
    return selected, {
        "status": "FDA_PUBLISHED_PDF_SOURCE_PAGE_SAMPLE_PLANNED_UNVERIFIED",
        "entire_private_evidence_packet_count": len(enriched_packets),
        "all_unique_previous_pdf_digests": len(known),
        "selected_unique_pdf_documents": len(selected),
        "requested_sample_offset": offset,
        "selected_sample_end_exclusive": offset + len(selected),
        "selected_full_pdf_hashes_sha256": hashlib.sha256(
            "\n".join(item["historical_pdf_sha256"] for item in selected).encode("ascii")
        ).hexdigest(),
        "selected_published_letter_references": sum(
            item["published_letter_references_sharing_file"] for item in selected),
        "sample_selected_by": "SORTED_PRIOR_CONFIRMED_FULL_PDF_SHA256",
        "original_fda_review_cycles_verified": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "readiness": "REVIEW_REQUIRED",
    }


def inspect_candidate_pages(
    selected: dict,
    pdf_bytes: bytes,
    *,
    page_count: int,
    extract_text,
    max_pages: int = MAX_INSPECT_PAGES,
) -> dict:
    """Return only PRIVATE source-navigation hints; NO review-cycle labels."""
    if (
        not isinstance(selected, dict)
        or not _official_url(selected.get("official_fda_pdf_url"))
        or not isinstance(selected.get("historical_pdf_sha256"), str)
        or not SOURCE_SHA.fullmatch(selected["historical_pdf_sha256"])
        or not isinstance(pdf_bytes, bytes)
        or not 100 <= len(pdf_bytes) <= MAX_PDF_BYTES
        or not pdf_bytes.startswith(b"%PDF-")
        or hashlib.sha256(pdf_bytes).hexdigest() != selected["historical_pdf_sha256"]
        or type(page_count) is not int or not 1 <= page_count <= MAX_PDF_PAGES
        or type(max_pages) is not int or not 1 <= max_pages <= MAX_INSPECT_PAGES
        or not callable(extract_text)
    ):
        raise ValueError("Exact previously confirmed FDA PDF bytes/page bounds not reconciled")
    apps = selected.get("candidate_application_ids")
    if (
        not isinstance(apps, list)
        or len(apps) != len(set(apps))
        or any(not isinstance(app, str) or not APP.fullmatch(app) for app in apps)
    ):
        raise ValueError("Unresolved or duplicated provisional FDA application identity")
    checked = min(page_count, max_pages)
    hits = {app: [] for app in apps}
    pages_without_text = 0
    no_text_page_indices = []
    pages_with_multiple_app_numbers = 0
    for idx in range(checked):
        text = extract_text(idx)
        if not isinstance(text, str):
            raise ValueError("PDF page text extraction did not return text")
        cleaned = re.sub(r"\s+", " ", text)
        if not cleaned.strip():
            pages_without_text += 1
            no_text_page_indices.append(idx)
        matched_apps = 0
        for app in apps:
            number = app[-6:]
            # Published FDA letter may print "NDA 206627" or "206627".
            # Mere presence on a page is NOT independent action attribution.
            if re.search(r"(?<!\d)" + re.escape(number) + r"(?!\d)", cleaned):
                hits[app].append(idx)
                matched_apps += 1
        if matched_apps > 1:
            pages_with_multiple_app_numbers += 1
    return {
        "status": "PRIOR_FDA_PDF_HASH_RECONFIRMED_PAGE_HINTS_UNVERIFIED",
        "official_fda_pdf_url": selected["official_fda_pdf_url"],
        "retrieved_full_pdf_sha256": selected["historical_pdf_sha256"],
        "pdf_page_count": page_count,
        "pages_inspected": checked,
        "remaining_pages_not_inspected": page_count - checked,
        "pages_with_no_extractable_text": pages_without_text,
        "private_no_text_page_indices_zero_based": no_text_page_indices,
        "pages_containing_multiple_candidate_app_numbers": pages_with_multiple_app_numbers,
        "provisional_candidate_app_page_indices_zero_based": hits,
        "published_letter_references_sharing_file":
            selected["published_letter_references_sharing_file"],
        "source_full_pdf_hash_confirmed_against_prior_probe": True,
        "original_action_page_ranges_independently_verified": 0,
        "independently_verified_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "readiness": "REVIEW_REQUIRED",
    }


def aggregate_sample(sample_plan: dict, checked: list[dict], *, fetch_failures: int) -> dict:
    if (
        not isinstance(sample_plan, dict)
        or sample_plan.get("status") != "FDA_PUBLISHED_PDF_SOURCE_PAGE_SAMPLE_PLANNED_UNVERIFIED"
        or not isinstance(checked, list)
        or type(fetch_failures) is not int or fetch_failures < 0
        or len(checked) + fetch_failures != sample_plan["selected_unique_pdf_documents"]
        or sample_plan["model_eligible_records"] != 0
    ):
        raise ValueError("FDA source PDF sample completion count does not reconcile")
    if any(
        not isinstance(item, dict)
        or item.get("status") != "PRIOR_FDA_PDF_HASH_RECONFIRMED_PAGE_HINTS_UNVERIFIED"
        or item.get("model_eligible_records") != 0
        or item.get("independently_verified_review_cycles") != 0
        or item.get("source_full_pdf_hash_confirmed_against_prior_probe") is not True
        for item in checked
    ):
        raise ValueError("Invalid or promoted source PDF page observations")
    return {
        "status": "FDA_PRIOR_PUBLISHED_PDF_PAGE_SAMPLE_OBSERVED_NOT_ADJUDICATED",
        "sampled_unique_pdf_documents_requested": sample_plan["selected_unique_pdf_documents"],
        "requested_sample_offset": sample_plan["requested_sample_offset"],
        "selected_sample_end_exclusive": sample_plan["selected_sample_end_exclusive"],
        "selected_full_pdf_hashes_sha256": sample_plan["selected_full_pdf_hashes_sha256"],
        "sampled_pdf_bytes_sha256_reconfirmed": len(checked),
        "sampled_pdf_documents_not_retrieved_or_parsed": fetch_failures,
        "source_sample_unique_pdf_population": sample_plan["all_unique_previous_pdf_digests"],
        "pages_examined_for_candidate_app_tokens": sum(x["pages_inspected"] for x in checked),
        "pages_without_extractable_text": sum(x["pages_with_no_extractable_text"] for x in checked),
        "pages_with_multiple_provisional_app_candidates": sum(
            x["pages_containing_multiple_candidate_app_numbers"] for x in checked
        ),
        "candidate_application_numbers_with_page_hits": sum(
            bool(pages) for x in checked
            for pages in x["provisional_candidate_app_page_indices_zero_based"].values()
        ),
        "original_action_page_ranges_independently_verified": 0,
        "review_cycles_independently_verified": 0,
        "complete_nda_bla_original_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
        "private_pdf_page_hints_not_exported": True,
    }
