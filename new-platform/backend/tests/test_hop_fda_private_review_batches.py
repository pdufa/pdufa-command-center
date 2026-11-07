"""Synthetic-only deterministic FDA identity-gap review batching tests."""
from __future__ import annotations

from copy import deepcopy

import pytest

from app.hop_fda_identity_gap_dual_review import CLAIM_FIELDS, _lock, REVIEW_STATUS
from app.hop_fda_private_review_batches import prepare_private_review_batches


def make_pair(pid: str, sid: str, *, ambiguous=False, missing=False):
    kind = ("AMBIGUOUS_APPLICATION_ID_RESEARCH" if ambiguous
            else "APPLICATION_IDENTITY_RESEARCH")
    base = {
        "packet_id": pid,
        "packet_kind": kind,
        "application_id_candidate": None if ambiguous else pid,
        "published_letter_source_sha256": sid,
        "published_letter_type": "UNCLASSIFIED" if missing else "COMPLETE RESPONSE",
        "source_letter_date_as_published": "02/27/2026",
        "historical_fda_pdf_url": (
            None if missing else "https://download.open.fda.gov/crl/synthetic.pdf"),
        "historical_fda_pdf_sha256": None if missing else "b" * 64,
        "prior_pdf_source_status": (
            "NO_RELEASED_PDF_SOURCE_LEAD" if missing
            else "PRIOR_FDA_PDF_BYTES_PROBED_ACTION_UNVERIFIED"),
        "historical_pdf_not_revalidated_now": True,
    }
    base["source_lock_sha256"] = _lock(base)
    role_rows = []
    for role in ("FIRST", "SECOND"):
        role_rows.append({
            **base,
            "packet_role": role,
            "review_packet_status": REVIEW_STATUS,
            "reviewer_token": "",
            **{field: "" for field in CLAIM_FIELDS},
            "reviewer_authentication_verified": False,
            "independent_regulatory_adjudication_verified": False,
            "model_eligible": False,
        })
    return role_rows


def realistic_synthetic_queue():
    a, b = [], []
    for i in range(1, 18):
        sid = f"{i:064x}"
        left, right = make_pair("LETTER_" + sid, sid, ambiguous=True, missing=i==1)
        a.append(left)
        b.append(right)
    refid = 17
    for group in range(1, 85):
        count = 3 if group <= 3 else 2 if group <= 20 else 1
        for _ in range(count):
            refid += 1
            left, right = make_pair(f"NDA{group:06d}", f"{refid:064x}")
            a.append(left)
            b.append(right)
    assert len(a) == len(b) == 124
    return a, b


def test_pinned_124_references_form_private_deterministic_dual_review_batches():
    first, second = realistic_synthetic_queue()
    batches, audit = prepare_private_review_batches(
        first, second, expected_references=124, expected_groups=101
    )
    assert audit["published_letter_references"] == 124
    assert audit["application_research_groups"] == 101
    assert audit["category_counts"]["AMBIGUOUS_ID_source_references"] == 17
    assert audit["category_counts"]["APPLICATION_ID_source_references"] == 107
    assert audit["category_counts"]["AMBIGUOUS_ID_groups"] == 17
    assert audit["category_counts"]["APPLICATION_ID_groups"] == 84
    assert audit["category_counts"]["AMBIGUOUS_ID_batches"] == 1
    assert audit["total_batches"] == len(batches)
    assert all(1 <= batch["source_references"] <= 20 for batch in batches)
    assert sum(x["source_references"] for x in batches) == 124
    assert len([r for batch in batches for r in batch["first_blank_reviewer_sources"]]) == 124
    assert batches[0]["batch_id"] == "AMBIGUOUS_ID-01"
    assert all(x["review_category"] == "APPLICATION_ID" for x in batches[1:])
    assert all(x["independently_adjudicated_fda_actions"] == 0 for x in batches)
    assert audit["independently_completed_reviewer_pairs"] == 0
    assert audit["original_fda_review_cycles_verified"] == 0
    assert audit["complete_nda_bla_decision_denominator_verified"] is False
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None
    assert "NDA000001" not in str(audit)
    assert "download.open.fda.gov" not in str(audit)
    assert "source_lock_sha256" not in str(audit)
    for batch in batches:
        assert all(row["packet_role"] == "FIRST" for row in batch["first_blank_reviewer_sources"])
        assert all(row["packet_role"] == "SECOND" for row in batch["second_blank_reviewer_sources"])


def test_application_group_never_split_and_source_copies_independent():
    first, second = realistic_synthetic_queue()
    batches, audit = prepare_private_review_batches(first, second, max_references=7)
    ownership = {}
    for item in batches:
        for row in item["first_blank_reviewer_sources"]:
            pid = row["packet_id"]
            assert pid not in ownership or ownership[pid] == item["batch_id"]
            ownership[pid] = item["batch_id"]
    batches[0]["first_blank_reviewer_sources"][0]["published_letter_type"] = "EDITED"
    assert batches[0]["second_blank_reviewer_sources"][0]["published_letter_type"] != "EDITED"


@pytest.mark.parametrize("case", [
    "bad_lock", "fake_review", "fake_model", "wrong_role", "identity_mismatch",
    "duplicate_first", "missing_second", "ambiguous_promoted", "pdf_invented",
    "source_digest_changed", "nonblank_claim", "bad_limit", "wrong_frozen_totals",
])
def test_false_source_claims_or_bad_pairing_fail_closed(case):
    first, second = realistic_synthetic_queue()
    opts = {}
    if case == "bad_lock":
        first[0]["source_lock_sha256"] = "f" * 64
    elif case == "fake_review":
        second[0]["reviewer_authentication_verified"] = True
    elif case == "fake_model":
        first[0]["model_eligible"] = True
    elif case == "wrong_role":
        second[0]["packet_role"] = "FIRST"
    elif case == "identity_mismatch":
        second[0]["source_letter_date_as_published"] = "01/01/2020"
        second[0]["source_lock_sha256"] = _lock(second[0])
    elif case == "duplicate_first":
        first[1] = deepcopy(first[0])
    elif case == "missing_second":
        second.pop()
    elif case == "ambiguous_promoted":
        first[0]["application_id_candidate"] = "NDA123456"
        first[0]["source_lock_sha256"] = _lock(first[0])
    elif case == "pdf_invented":
        first[0]["historical_fda_pdf_sha256"] = "c" * 64
        first[0]["source_lock_sha256"] = _lock(first[0])
    elif case == "source_digest_changed":
        first[0]["published_letter_source_sha256"] = "c" * 64
    elif case == "nonblank_claim":
        second[0]["observed_document_class"] = "APPROVAL"
    elif case == "bad_limit":
        opts["max_references"] = 0
    elif case == "wrong_frozen_totals":
        opts["expected_groups"] = 100
    with pytest.raises(ValueError):
        prepare_private_review_batches(first, second, **opts)


def test_per_batch_summary_never_claims_reviewer_identity_or_fda_decision():
    a, b = realistic_synthetic_queue()
    batches, summary = prepare_private_review_batches(a, b)
    assert summary["reviewer_identities_authenticated"] is False
    assert summary["individual_source_records_not_exported"] is True
    assert all(x["reviewer_pairs_completed"] == 0 for x in summary["per_batch_aggregate_counts"])
    assert all(x["verified_original_review_cycles"] == 0 for x in summary["per_batch_aggregate_counts"])
    assert sum(x["reference_count"] for x in summary["per_batch_aggregate_counts"]) == 124

def _write_synthetic_private_batches(tmp_path):
    import json
    from app.hop_fda_private_review_custody import MANIFEST_NAME
    folder = tmp_path / "private-fda-batches"
    folder.mkdir(mode=0o700)
    folder.chmod(0o700)
    first, second = realistic_synthetic_queue()
    batches, audit = prepare_private_review_batches(
        first, second, expected_references=124, expected_groups=101,
    )
    for batch in batches:
        for role, key in (
            ("FIRST", "first_blank_reviewer_sources"),
            ("SECOND", "second_blank_reviewer_sources"),
        ):
            path = folder / (batch["batch_id"] + "_" + role + "_unreviewed.json")
            path.write_text(json.dumps(batch[key], indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
            path.chmod(0o600)
    assert not (folder / MANIFEST_NAME).exists()
    return folder


def test_private_blank_reviewer_custody_detects_changed_bytes_or_missing_a_b(tmp_path):
    from app.hop_fda_private_review_custody import (
        MANIFEST_NAME, save_private_blank_batch_manifest,
        verify_private_blank_batch_manifest,
    )
    folder = _write_synthetic_private_batches(tmp_path)
    inventory = save_private_blank_batch_manifest(folder)
    assert inventory["batch_count"] == 7
    assert inventory["file_count"] == 14
    assert inventory["published_letter_references"] == 124
    assert inventory["research_groups"] == 101
    assert inventory["reviewer_records_per_role"] == 124
    assert inventory["model_eligible_records"] == 0
    assert inventory["prediction_probability"] is None
    assert all("download.open.fda.gov" not in str(x) for x in inventory["files"])
    result = verify_private_blank_batch_manifest(folder)
    assert result["private_role_files_integrity_checked"] == 14
    assert result["original_fda_review_cycles_verified"] == 0
    with pytest.raises(FileExistsError):
        save_private_blank_batch_manifest(folder)

    # A previously valid JSON file with modified *bytes* fails the inventory.
    path = folder / "APPLICATION_ID-01_FIRST_unreviewed.json"
    old = path.read_bytes()
    path.write_bytes(old + b"\n")
    with pytest.raises(ValueError, match="differs from saved"):
        verify_private_blank_batch_manifest(folder)
    path.write_bytes(old)
    assert verify_private_blank_batch_manifest(folder)["source_batch_count"] == 7

    # A blank FDA role is not allowed to disappear or be swapped.
    path.unlink()
    with pytest.raises(ValueError, match="pair"):
        verify_private_blank_batch_manifest(folder)
    assert (folder / MANIFEST_NAME).exists()


def test_private_custody_checks_protect_baseline_and_paths(tmp_path):
    from app.hop_fda_private_review_custody import (
        MANIFEST_NAME, save_private_blank_batch_manifest,
        verify_private_blank_batch_manifest,
    )
    folder = _write_synthetic_private_batches(tmp_path)
    target = folder / "AMBIGUOUS_ID-01_SECOND_unreviewed.json"
    target.chmod(0o644)
    with pytest.raises(ValueError, match="permissions"):
        save_private_blank_batch_manifest(folder)
    target.chmod(0o600)
    save_private_blank_batch_manifest(folder)
    baseline = folder / MANIFEST_NAME
    baseline.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from saved"):
        verify_private_blank_batch_manifest(folder)


def test_private_custody_rejects_reviewed_claims_and_extra_files(tmp_path):
    import json
    from app.hop_fda_private_review_custody import save_private_blank_batch_manifest
    folder = _write_synthetic_private_batches(tmp_path)
    source = folder / "APPLICATION_ID-01_FIRST_unreviewed.json"
    rows = json.loads(source.read_text(encoding="utf-8"))
    rows[0]["reviewer_token"] = "claimedReviewerId"
    source.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError, match="not blank"):
        save_private_blank_batch_manifest(folder)
    source.unlink()
    with pytest.raises(ValueError):
        save_private_blank_batch_manifest(folder)
