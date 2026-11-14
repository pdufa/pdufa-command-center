"""Render source-locked, text-unextractable FDA PDF pages for PRIVATE visual review.

PNG creation is NOT visual inspection, OCR, document authentication, or
FDA decision adjudication. Page images and source mappings remain on the
isolated research runner, never in its public_aggregate_only artifact.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

SHA = re.compile(r"[a-f0-9]{64}\Z")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_RENDER_PIXELS = 6_000_000
MAX_RENDERED_PNG_BYTES = 8_000_000
MAX_RENDERED_PAGES_PER_PDF = 40
SCALE = 1.25


def render_private_nontext_pages(
    original_pdf_bytes: bytes,
    observed: dict,
    *,
    private_image_dir: Path,
) -> list[dict]:
    """Create bounded PNGs for the already hash-verified absent-text pages.

    The source index and all PNG hashes remain PRIVATE, not uploaded.
    """
    if (not isinstance(original_pdf_bytes, bytes)
            or not isinstance(observed, dict)
            or not isinstance(private_image_dir, Path)
            or observed.get("status") !=
                "PRIOR_FDA_PDF_HASH_RECONFIRMED_PAGE_HINTS_UNVERIFIED"
            or observed.get("model_eligible_records") != 0
            or observed.get("original_action_page_ranges_independently_verified") != 0
            or observed.get("independently_verified_review_cycles") != 0
            or observed.get("source_full_pdf_hash_confirmed_against_prior_probe") is not True):
        raise ValueError("Untrusted or promoted FDA page sample")
    source_sha = observed.get("retrieved_full_pdf_sha256")
    if (not isinstance(source_sha, str) or not SHA.fullmatch(source_sha)
            or hashlib.sha256(original_pdf_bytes).hexdigest() != source_sha):
        raise ValueError("Full FDA original PDF source digest does not match visual queue")
    indices = observed.get("private_no_text_page_indices_zero_based")
    inspected = observed.get("pages_inspected")
    if (not isinstance(indices, list) or type(inspected) is not int
            or not 0 <= inspected <= 40
            or len(indices) > MAX_RENDERED_PAGES_PER_PDF
            or len(indices) != observed.get("pages_with_no_extractable_text")
            or any(type(page) is not int or not 0 <= page < inspected
                   for page in indices)
            or indices != sorted(set(indices))):
        raise ValueError("Private FDA no-text page list does not match source observations")
    # Import locally: production backend/ordinary test suite need no PDF bitmap
    # renderer, which is installed only in the isolated research workflow.
    import fitz
    rendered = []
    with fitz.open(stream=original_pdf_bytes, filetype="pdf") as doc:
        if (doc.page_count != observed.get("pdf_page_count")
                or doc.is_encrypted or doc.page_count > 300):
            raise ValueError("PDF visual render source page count/encryption mismatch")
        if indices:
            private_image_dir.mkdir(parents=True, exist_ok=True)
        for idx in indices:
            page = doc.load_page(idx)
            width = int(page.rect.width * SCALE + 1)
            height = int(page.rect.height * SCALE + 1)
            if (width <= 0 or height <= 0
                    or width * height > MAX_RENDER_PIXELS):
                raise ValueError("FDA page bitmap dimensions exceed private review cap")
            raster = page.get_pixmap(
                matrix=fitz.Matrix(SCALE, SCALE),
                colorspace=fitz.csRGB,
                alpha=False,
            )
            if (raster.width * raster.height > MAX_RENDER_PIXELS
                    or raster.width <= 0 or raster.height <= 0):
                raise ValueError("PDF renderer returned oversize bitmap")
            png = raster.tobytes(output="png")
            if (not png.startswith(PNG_MAGIC)
                    or len(png) > MAX_RENDERED_PNG_BYTES):
                raise ValueError("FDA private bitmap encoding exceeded cap")
            name = f"{source_sha}_page_{idx:03d}.png"
            target = private_image_dir / name
            if target.exists():
                if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(png).digest():
                    raise ValueError("Private FDA bitmap filename collided with different bytes")
            else:
                target.write_bytes(png)
            rendered.append({
                "source_full_pdf_sha256": source_sha,
                "pdf_page_index_zero_based": idx,
                "private_rendered_png_name": name,
                "rendered_png_sha256": hashlib.sha256(png).hexdigest(),
                "rendered_pixel_width": raster.width,
                "rendered_pixel_height": raster.height,
                "source_page_without_extractable_text": True,
                "human_visual_review_completed": False,
                "original_fda_action_page_verified": False,
                "model_eligible": False,
            })
    return rendered


def render_counts_only(
    observations: list[dict],
    private_manifest: list[dict],
    *,
    requested_documents: int,
) -> dict:
    """Never expose PDF/page mappings or image hashes in the public artifact."""
    if (not isinstance(observations, list) or not isinstance(private_manifest, list)
            or type(requested_documents) is not int or requested_documents < 1
            or len(observations) > requested_documents):
        raise ValueError("Invalid FDA visual source count cohort")
    expected = sum(obs.get("pages_with_no_extractable_text", -1)
                   for obs in observations if isinstance(obs, dict))
    if expected < 0 or len(private_manifest) != expected:
        raise ValueError("FDA visual PNG count differs from extracted text gaps")
    if any(
        not isinstance(row, dict)
        or row.get("human_visual_review_completed") is not False
        or row.get("original_fda_action_page_verified") is not False
        or row.get("model_eligible") is not False
        for row in private_manifest
    ):
        raise ValueError("Visual image rows cannot claim FDA adjudication")
    return {
        "status": "FDA_NONEXTRACTABLE_PDF_PAGES_RENDERED_PRIVATELY_NOT_REVIEWED",
        "source_pdf_documents_in_sample": requested_documents,
        "source_pdf_documents_with_reconfirmed_hashes": len(observations),
        "no_text_pages_identified": expected,
        "private_page_png_images_rendered": len(private_manifest),
        "private_page_png_render_failures": 0,
        "source_page_text_extraction_gaps_still_need_human_review": expected,
        "human_visual_page_reviews_completed": 0,
        "independently_verified_original_fda_action_pages": 0,
        "independently_verified_original_fda_review_cycles": 0,
        "complete_original_nda_bla_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
        "private_page_images_not_exported": True,
        "private_page_mapping_not_exported": True,
    }
