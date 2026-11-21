"""Synthetic FDA reviewer handoff tests. All review-cycle outcomes are null."""
from copy import deepcopy
from datetime import date

import pytest

from app.hop_fda_identity_gap_dual_review import (
    blank_identity_gap_dual_reviews, reconcile_identity_gap_review_claims,
)

CUTOFF = date(2026, 10, 25)
PDF_SHA = "b" * 64
URL = "https://download.open.fda.gov/crl/sample.pdf"


def packet(app, sourceids, *, unavailable=None):
    unavailable = set(unavailable or ())
    return {
        "packet_id": app or "LETTER_" + f"{sourceids[0]:064x}",
        "packet_kind": (
            "APPLICATION_IDENTITY_RESEARCH" if app
            else "AMBIGUOUS_APPLICATION_ID_RESEARCH"
        ),
        "application_id_candidate": app,
        "published_letter_source_hashes": [f"{i:064x}" for i in sourceids],
        "published_letter_references": len(sourceids),
        "original_review_cycle": None,
        "fda_action_outcome": None,
        "adjudicator_authenticated": False,
        "model_eligible": False,
        "evidence_lead_status": "UNVERIFIED_FDA_SOURCE_LEAD_REQUIRES_INDEPENDENT_REVIEW",
        "manual_evidence_lead_url": "",
        "manual_evidence_document_type": "",
        "manual_evidence_sha256": "",
        "manual_research_notes": "",
        "previously_probed_published_pdf_leads": [
            {
                "published_letter_source_sha256": f"{i:064x}",
                "official_fda_pdf_url": None if i in unavailable else URL,
                "historically_observed_full_pdf_sha256":
                    None if i in unavailable else PDF_SHA,
                "published_letter_type": "COMPLETE RESPONSE" if i != 3 else "UNCLASSIFIED",
                "published_letter_date_not_adjudicated_action_date": "01/01/2020",
                "pdf_lead_status": (
                    "NO_RELEASED_PDF_SOURCE_LEAD" if i in unavailable else
                    "PRIOR_FDA_PDF_BYTES_PROBED_ACTION_UNVERIFIED"
                ),
                "pdf_bytes_revalidated_in_current_run": False,
                "action_page_range_independently_verified": False,
                "review_cycle_independently_verified": False,
                "model_eligible": False,
            } for i in sourceids
        ],
    }


def sources():
    return [
        packet("NDA000001", [1, 2]),
        packet(None, [3], unavailable=[3]),
        packet("BLA000004", [4]),
    ]


def populate(row, token, app="NDA000001", action="COMPLETE_RESPONSE"):
    row.update({
        "reviewer_token": token,
        "observed_application_id": app,
        "observed_submission_class": "ORIGINAL",
        "observed_letter_pages": "2-3",
        "observed_fda_action_date": "2020-01-01",
        "observed_document_class": action,
        "observed_review_cycle": "1",
        "source_evidence_notes": "Fictitious test observation only, not FDA evidence.",
    })


def test_source_locked_dual_handoff_counts_and_no_promotion():
    a, b, audit = blank_identity_gap_dual_reviews(sources())
    assert len(a) == len(b) == 4
    assert audit["private_research_group_count"] == 3
    assert audit["published_letter_references"] == 4
    assert audit["first_reviewer_blank_rows"] == 4
    assert audit["second_reviewer_blank_rows"] == 4
    assert audit["references_without_source_pdf"] == 1
    assert audit["source_classification_rows"] == {
        "AMBIGUOUS_APPLICATION_ID_RESEARCH": 1,
        "APPLICATION_IDENTITY_RESEARCH": 3,
    }
    assert audit["model_eligible_records"] == 0
    assert audit["review_cycle_outcomes_verified"] == 0
    assert audit["independent_reviews_completed"] == 0
    assert audit["prediction_probability"] is None
    assert all(x["review_packet_status"] ==
               "BLANK_FDA_IDENTITY_GAP_REVIEW_NOT_ADJUDICATED" for x in a+b)
    assert all(x["reviewer_token"] == "" and x["model_eligible"] is False
               and x["observed_review_cycle"] == "" for x in a+b)
    assert a[0]["source_lock_sha256"] == b[0]["source_lock_sha256"]


def test_two_matching_claims_stay_unverified_and_missing_source_stays_blocked():
    a, b, _ = blank_identity_gap_dual_reviews(sources())
    left, right = deepcopy(a), deepcopy(b)
    for row in left:
        populate(row, "reviewerAlpha", app=row["application_id_candidate"] or "NDA000001")
    for row in right:
        populate(row, "reviewerBeta", app=row["application_id_candidate"] or "NDA000001")
    result = reconcile_identity_gap_review_claims(a, b, left, right, as_of=CUTOFF)
    assert result["review_category_counts"] == {
        "SOURCE_DATA_INCONSISTENCY": 1,
        "TWO_CLAIMS_DIFFER": 0,
        "CLAIMS_INCOMPLETE": 0,
        "MATCHING_TEXT_UNVERIFIED": 3,
    }
    assert result["claimed_distinct_reviewer_tokens"] == 2
    assert result["reviewer_identities_authenticated"] is False
    assert result["independently_verified_original_fda_actions"] == 0
    assert result["model_eligible_records"] == 0
    assert result["approval_rate"] is None
    assert result["prediction_probability"] is None


def test_identity_claim_disagreement_flags_fields_not_reviewer_notes():
    a, b, _ = blank_identity_gap_dual_reviews(sources())
    left, right = deepcopy(a), deepcopy(b)
    for row in left:
        populate(row, "reviewerAlpha", app=row["application_id_candidate"] or "NDA000001")
    for row in right:
        populate(row, "reviewerBeta", app=row["application_id_candidate"] or "NDA000001")
    right[0]["observed_document_class"] = "APPROVAL"
    result = reconcile_identity_gap_review_claims(a, b, left, right, as_of=CUTOFF)
    assert result["review_category_counts"]["TWO_CLAIMS_DIFFER"] == 1
    assert result["unverified_differences_needing_reviewer_attention"] == [{
        "source_record_sha256": right[0]["published_letter_source_sha256"],
        "disputed_fields": ["observed_document_class"],
    }]
    assert "reviewerAlpha" not in str(result)
    assert "Fictitious test" not in str(result)


@pytest.mark.parametrize("tamper", [
    "duplicate_source", "false_model_eligible", "forged_app",
    "published_type", "fake_pdf_source", "unavailable_pdf_claim",
    "pdf_sha_claim", "source_page_claim", "reclassified_packet",
])
def test_corrupted_private_sources_cannot_enter_dual_review(tamper):
    raw = sources()
    if tamper == "duplicate_source":
        raw[2]["previously_probed_published_pdf_leads"][0][
            "published_letter_source_sha256"
        ] = raw[0]["previously_probed_published_pdf_leads"][0][
            "published_letter_source_sha256"
        ]
    elif tamper == "false_model_eligible":
        raw[0]["model_eligible"] = True
    elif tamper == "forged_app":
        raw[0]["application_id_candidate"] = "NDA999999"
    elif tamper == "published_type":
        raw[0]["previously_probed_published_pdf_leads"][0][
            "published_letter_type"
        ] = "PREDICTED APPROVAL"
    elif tamper == "fake_pdf_source":
        raw[0]["previously_probed_published_pdf_leads"][0][
            "official_fda_pdf_url"
        ] = "https://download.open.fda.gov.evil.test/crl/fake.pdf"
    elif tamper == "unavailable_pdf_claim":
        raw[1]["previously_probed_published_pdf_leads"][0][
            "historically_observed_full_pdf_sha256"
        ] = PDF_SHA
    elif tamper == "pdf_sha_claim":
        raw[0]["previously_probed_published_pdf_leads"][0][
            "historically_observed_full_pdf_sha256"
        ] = "incorrect"
    elif tamper == "source_page_claim":
        raw[0]["previously_probed_published_pdf_leads"][0][
            "action_page_range_independently_verified"
        ] = True
    elif tamper == "reclassified_packet":
        raw[0]["packet_kind"] = "AMBIGUOUS_APPLICATION_ID_RESEARCH"
    with pytest.raises(ValueError):
        blank_identity_gap_dual_reviews(raw)


@pytest.mark.parametrize("tamper", [
    "change_source_url", "change_source_sha", "source_role",
    "model_approval", "reviewer_claims_authenticated",
    "malicious_notes", "future_date", "invalid_page_range",
    "same_reviewer_identity", "missing_row", "duplicate_row",
    "made_up_review_cycle",
])
def test_tampered_claims_and_false_signoffs_rejected(tamper):
    a, b, _ = blank_identity_gap_dual_reviews(sources())
    lhs, rhs = deepcopy(a), deepcopy(b)
    for row in lhs:
        populate(row, "reviewerAlpha", app=row["application_id_candidate"] or "NDA000001")
    for row in rhs:
        populate(row, "reviewerBeta", app=row["application_id_candidate"] or "NDA000001")
    if tamper == "change_source_url":
        lhs[0]["historical_fda_pdf_url"] = "https://www.evil.test/fake.pdf"
    elif tamper == "change_source_sha":
        lhs[0]["source_lock_sha256"] = "f" * 64
    elif tamper == "source_role":
        lhs[0]["packet_role"] = "SECOND"
    elif tamper == "model_approval":
        lhs[0]["model_eligible"] = True
    elif tamper == "reviewer_claims_authenticated":
        rhs[0]["reviewer_authentication_verified"] = True
    elif tamper == "malicious_notes":
        lhs[0]["source_evidence_notes"] = "=HYPERLINK(1)"
    elif tamper == "future_date":
        lhs[0]["observed_fda_action_date"] = "2027-01-01"
    elif tamper == "invalid_page_range":
        lhs[0]["observed_letter_pages"] = "9-2"
    elif tamper == "same_reviewer_identity":
        rhs[0]["reviewer_token"] = "reviewerAlpha"
    elif tamper == "missing_row":
        rhs.pop()
    elif tamper == "duplicate_row":
        rhs.append(deepcopy(rhs[0]))
    elif tamper == "made_up_review_cycle":
        lhs[0]["observed_review_cycle"] = "cycle-hundred"
    with pytest.raises(ValueError):
        reconcile_identity_gap_review_claims(a, b, lhs, rhs, as_of=CUTOFF)


def test_blank_role_packets_compare_as_incomplete_except_missing_source():
    a, b, _ = blank_identity_gap_dual_reviews(sources())
    result = reconcile_identity_gap_review_claims(a, b, a, b, as_of=CUTOFF)
    assert result["review_category_counts"]["CLAIMS_INCOMPLETE"] == 3
    assert result["review_category_counts"]["SOURCE_DATA_INCONSISTENCY"] == 1
    assert result["model_eligible_records"] == 0



def test_matching_reviewer_text_with_wrong_fda_application_is_not_agreement():
    a, b, _ = blank_identity_gap_dual_reviews(sources())
    lhs, rhs = deepcopy(a), deepcopy(b)
    for row in lhs:
        populate(row, "reviewerAlpha", app="NDA999999")
    for row in rhs:
        populate(row, "reviewerBeta", app="NDA999999")
    result = reconcile_identity_gap_review_claims(a, b, lhs, rhs, as_of=CUTOFF)
    assert result["review_category_counts"]["SOURCE_DATA_INCONSISTENCY"] == 4
    assert result["review_category_counts"]["MATCHING_TEXT_UNVERIFIED"] == 0
    assert result["model_eligible_records"] == 0
    assert result["prediction_probability"] is None



def test_real_pinned_source_review_handoff_counts_and_no_reviewed_decisions():
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "research_sources"
    handoff = json.loads(
        (root / "hop_fda_identity_gap_dual_review_handoff_20261025.json")
        .read_text(encoding="utf-8")
    )
    upstream = json.loads(
        (root / "hop_fda_prior_pdf_lead_coverage_20261025.json")
        .read_text(encoding="utf-8")
    )
    assert handoff["status"] == "BLANK_DUAL_FDA_IDENTITY_GAP_REVIEW_PACKETS_PREPARED"
    assert handoff["private_research_group_count"] == upstream[
        "total_private_original_application_research_packets"] == 101
    assert handoff["published_letter_references"] == upstream[
        "published_letter_references_in_packets"] == 124
    assert handoff["first_reviewer_blank_rows"] == 124
    assert handoff["second_reviewer_blank_rows"] == 124
    assert handoff["references_without_source_pdf"] == upstream[
        "unavailable_published_pdf_letter_references"] == 1
    assert handoff["source_classification_rows"] == {
        "AMBIGUOUS_APPLICATION_ID_RESEARCH": 17,
        "APPLICATION_IDENTITY_RESEARCH": 107,
    }
    assert handoff["reviewer_identity_authenticated"] is False
    assert handoff["independent_reviews_completed"] == 0
    assert handoff["review_cycle_outcomes_verified"] == 0
    assert handoff["complete_original_nda_bla_denominator_verified"] is False
    assert handoff["model_eligible_records"] == 0
    assert handoff["prediction_probability"] is None
    assert handoff["approval_rate"] is None
    assert handoff["reviewer_detail_records_not_exported"] is True


def _call_private_packet_cli(monkeypatch, source, first, second, audit):
    import sys
    from scripts.prepare_hop_fda_identity_gap_dual_review import main
    monkeypatch.setattr(sys, "argv", [
        "prepare_hop_fda_identity_gap_dual_review.py",
        "--private-enriched-packets", str(source),
        "--private-first-review-json", str(first),
        "--private-second-review-json", str(second),
        "--public-audit-json", str(audit),
    ])
    return main()


def test_private_reviewer_cli_excludes_public_audit_and_prevents_overwrite(tmp_path, monkeypatch):
    import json
    import stat
    payload = tmp_path / "source.json"
    payload.write_text(json.dumps(sources()), encoding="utf-8")
    first = tmp_path / "private" / "first.json"
    second = tmp_path / "private" / "second.json"
    audit = tmp_path / "public" / "counts.json"
    assert _call_private_packet_cli(monkeypatch, payload, first, second, audit) == 0
    assert first.exists() and second.exists() and audit.exists()
    assert stat.S_IMODE(first.stat().st_mode) == 0o600
    assert stat.S_IMODE(second.stat().st_mode) == 0o600
    assert stat.S_IMODE(first.parent.stat().st_mode) == 0o700
    report = json.loads(audit.read_text(encoding="utf-8"))
    assert report["first_reviewer_blank_rows"] == 4
    assert report["second_reviewer_blank_rows"] == 4
    assert report["model_eligible_records"] == 0
    assert "source_lock_sha256" not in report
    assert "reviewer_token" not in report
    before = first.read_bytes()
    with pytest.raises(ValueError, match="new output names"):
        _call_private_packet_cli(monkeypatch, payload, first, second, audit)
    assert first.read_bytes() == before


@pytest.mark.parametrize("layout", ["same_directory", "inside_public_dir", "public_in_private_dir", "wrong_role_directory"])
def test_private_cli_rejects_paths_that_can_leak_reviewer_packets(
    tmp_path, monkeypatch, layout,
):
    import json
    payload = tmp_path / "source.json"
    payload.write_text(json.dumps(sources()), encoding="utf-8")
    private = tmp_path / "private"
    public = tmp_path / "public"
    first = private / "first.json"
    second = private / "second.json"
    audit = public / "counts.json"
    if layout == "same_directory":
        audit = private / "counts.json"
    elif layout == "inside_public_dir":
        first = public / "first.json"
        second = public / "second.json"
    elif layout == "public_in_private_dir":
        audit = private / "public" / "counts.json"
    elif layout == "wrong_role_directory":
        second = tmp_path / "other-private" / "second.json"
    with pytest.raises(ValueError, match="separate safe directory"):
        _call_private_packet_cli(monkeypatch, payload, first, second, audit)
    assert not first.exists()
    assert not second.exists()
    assert not audit.exists()
