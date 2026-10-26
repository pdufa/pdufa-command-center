"""Synthetic private visual rendering of no-text FDA pages; NEVER OCR/outcomes."""
from __future__ import annotations

from copy import deepcopy
import hashlib

import pytest

from app.hop_fda_visual_page_review import (
    PNG_MAGIC, render_counts_only, render_private_nontext_pages,
)
from app.hop_fda_pdf_page_candidate_sampling import inspect_candidate_pages


def observation():
    # Only tests that need bitmap rendering require PyMuPDF. Production code
    # and ordinary FastAPI CI need no visual rendering dependency.
    fitz = pytest.importorskip("fitz")
    doc = fitz.open()
    page0 = doc.new_page(width=300, height=220)
    page0.draw_rect(fitz.Rect(20, 20, 110, 110), color=(0, 0, 0))
    page1 = doc.new_page(width=300, height=220)
    page1.insert_text((25, 50), "NDA 123456")
    pdf = doc.tobytes()
    doc.close()
    source = hashlib.sha256(pdf).hexdigest()
    selected = {
        "historical_pdf_sha256": source,
        "official_fda_pdf_url": "https://download.open.fda.gov/crl/synthetic-test.pdf",
        "candidate_application_ids": ["NDA123456"],
        "published_letter_references_sharing_file": 1,
    }
    checked = inspect_candidate_pages(
        selected, pdf, page_count=2,
        extract_text=lambda i: "" if i == 0 else "NDA123456",
    )
    return pdf, checked


def test_exact_source_hash_generates_private_png_for_one_no_text_page(tmp_path):
    pdf, observed = observation()
    assert observed["private_no_text_page_indices_zero_based"] == [0]
    assert observed["pages_with_no_extractable_text"] == 1
    assert observed["provisional_candidate_app_page_indices_zero_based"] == {
        "NDA123456": [1]
    }
    private = tmp_path / "private_images"
    manifest = render_private_nontext_pages(pdf, observed, private_image_dir=private)
    assert len(manifest) == 1
    assert manifest[0]["pdf_page_index_zero_based"] == 0
    assert manifest[0]["source_full_pdf_sha256"] == hashlib.sha256(pdf).hexdigest()
    image = private / manifest[0]["private_rendered_png_name"]
    body = image.read_bytes()
    assert body.startswith(PNG_MAGIC)
    assert hashlib.sha256(body).hexdigest() == manifest[0]["rendered_png_sha256"]
    assert manifest[0]["human_visual_review_completed"] is False
    assert manifest[0]["original_fda_action_page_verified"] is False
    assert manifest[0]["model_eligible"] is False
    counts = render_counts_only([observed], manifest, requested_documents=1)
    assert counts["no_text_pages_identified"] == 1
    assert counts["private_page_png_images_rendered"] == 1
    assert counts["human_visual_page_reviews_completed"] == 0
    assert counts["independently_verified_original_fda_review_cycles"] == 0
    assert counts["model_eligible_records"] == 0
    assert counts["prediction_probability"] is None
    assert "private_rendered_png_name" not in str(counts)
    # Re-running same immutable observation is safe; differing bytes aren't.
    assert render_private_nontext_pages(pdf, observed, private_image_dir=private) == manifest


@pytest.mark.parametrize("tamper", [
    "fake_pdf_bytes", "wrong_source_sha", "missing_page", "duplicate_page",
    "bad_type", "out_of_scope_page", "fabricated_model_eligibility",
    "false_original_action_page", "false_verified_review_cycle",
    "incorrect_no_text_count",
])
def test_forged_source_or_pdf_page_rejected(tmp_path, tamper):
    pdf, observed = observation()
    claimed = deepcopy(observed)
    if tamper == "fake_pdf_bytes":
        pdf = pdf + b"tampered trailing bytes"
    elif tamper == "wrong_source_sha":
        claimed["retrieved_full_pdf_sha256"] = "f" * 64
    elif tamper == "missing_page":
        claimed["private_no_text_page_indices_zero_based"] = []
    elif tamper == "duplicate_page":
        claimed["private_no_text_page_indices_zero_based"] = [0, 0]
        claimed["pages_with_no_extractable_text"] = 2
    elif tamper == "bad_type":
        claimed["private_no_text_page_indices_zero_based"] = ["0"]
    elif tamper == "out_of_scope_page":
        claimed["private_no_text_page_indices_zero_based"] = [2]
    elif tamper == "fabricated_model_eligibility":
        claimed["model_eligible_records"] = 1
    elif tamper == "false_original_action_page":
        claimed["original_action_page_ranges_independently_verified"] = 1
    elif tamper == "false_verified_review_cycle":
        claimed["independently_verified_review_cycles"] = 1
    elif tamper == "incorrect_no_text_count":
        claimed["pages_with_no_extractable_text"] = 2
    with pytest.raises(ValueError):
        render_private_nontext_pages(pdf, claimed, private_image_dir=tmp_path / "private")


def test_count_only_report_cannot_claim_completed_human_review(tmp_path):
    pdf, observed = observation()
    manifest = render_private_nontext_pages(
        pdf, observed, private_image_dir=tmp_path / "private",
    )
    bad = deepcopy(manifest)
    bad[0]["human_visual_review_completed"] = True
    with pytest.raises(ValueError):
        render_counts_only([observed], bad, requested_documents=1)
    with pytest.raises(ValueError):
        render_counts_only([observed], [], requested_documents=1)


def test_empty_text_page_list_produces_zero_rendered_images(tmp_path):
    pdf, observed = observation()
    observed["private_no_text_page_indices_zero_based"] = []
    observed["pages_with_no_extractable_text"] = 0
    pngs = render_private_nontext_pages(
        pdf, observed, private_image_dir=tmp_path / "private",
    )
    assert pngs == []
    assert not (tmp_path / "private").exists()
    assert render_counts_only([observed], pngs, requested_documents=1)[
        "private_page_png_images_rendered"
    ] == 0



def test_actual_19_source_fda_no_text_pages_rendered_without_review():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "research_sources"
    result = json.loads(
        (root / "hop_fda_nontext_page_visual_render_20261025.json")
        .read_text(encoding="utf-8")
    )
    previous = json.loads(
        (root / "hop_fda_page_candidate_sample_20261025.json")
        .read_text(encoding="utf-8")
    )
    second = json.loads(
        (root / "hop_fda_page_candidate_second_batch_20261025.json")
        .read_text(encoding="utf-8")
    )
    assert result["status"] == (
        "FDA_NONEXTRACTABLE_PDF_PAGES_RENDERED_PRIVATELY_NOT_REVIEWED"
    )
    assert result["source_pdf_count"] == 16
    assert result["source_prior_sha256_verified_pdfs"] == 16
    assert result["source_pages_examined_for_text"] == (
        previous["pages_examined_for_candidate_app_tokens"] +
        second["pages_examined_for_candidate_app_tokens"]
    ) == 100
    assert len(result["visual_render_batches"]) == 2
    assert result["visual_render_batches"][0]["offset"] == 0
    assert result["visual_render_batches"][1]["offset"] == 8
    assert result["visual_render_batches"][0]["private_png_pages_rendered"] == (
        previous["pages_without_extractable_text"] == 9
    )
    assert result["visual_render_batches"][1]["private_png_pages_rendered"] == (
        second["pages_without_extractable_text"] == 10
    )
    assert result["total_no_extractable_text_pages"] == 19
    assert result["total_private_png_rendered"] == 19
    assert result["render_failures"] == 0
    assert result["manual_visual_review_completed_pages"] == 0
    assert result["source_page_verified_original_fda_action_count"] == 0
    assert result["independently_adjudicated_original_fda_review_cycles"] == 0
    assert result["complete_nda_bla_historical_decision_denominator_verified"] is False
    assert result["model_eligible_records"] == 0
    assert result["approval_rate"] is None
    assert result["prediction_probability"] is None
    assert result["predictive_accuracy"] is None
    assert result["private_page_image_hash_and_page_mapping_not_exported"] is True
    assert result["private_pngs_are_ephemeral_runner_files"] is True
    assert result["durable_authenticated_human_review_storage_ready"] is False
