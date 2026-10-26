import pytest

from app.hop_fda_identity_review_queue import (
    create_fda_identity_review_queue,
    STATUS_MATCH, STATUS_NONMATCH, STATUS_UNRESOLVED, STATUS_AMBIGUOUS,
)


def digest(char):
    return char * 64


def record(char, ids, date="03/15/2024"):
    return {
        "source_record_sha256": digest(char),
        "model_eligible": False,
        "source_partition": "https://download.open.fda.gov/transparency/crl/file.json.zip",
        "source_record_index": int(char, 16),
        "file_name_as_published": "sample-letter.pdf",
        "company_name_as_published": "Public name",
        "letter_date_as_published": date,
        "letter_type_as_published": "COMPLETE RESPONSE",
        "application_numbers": ids,
    }


def link(row, status, candidates=None):
    return {
        "letter_record_sha256": row["source_record_sha256"],
        "model_eligible": False,
        "complete_cohort_verified": False,
        "point_in_time_outcome_verified": False,
        "identity_link_status": status,
        "source_application_identifiers_as_published": row["application_numbers"],
        "canonical_application_candidates": candidates or [],
        "matched_registry_application_candidates": [],
        "letter_date_as_published": row["letter_date_as_published"],
        "letter_type_as_published": row["letter_type_as_published"],
    }


def sources(records, links):
    return {
        "status": "IDENTITY_LINKAGE_ONLY_NOT_A_REVIEW_CYCLE_OUTCOME_COHORT",
        "records": links,
    }, {
        "status": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
        "source_export_date": "2026-10-21",
        "records": records,
    }


def test_identity_review_queue_reconciles_all_source_letters():
    missing = record("a", ["BL 125845"])
    ambiguous = record("b", ["NDA 214410/Original 2", "NDA 210854/S-05"])
    nonmatch = record("c", ["BLA 761401"])
    matched = record("d", ["NDA 213378/Original 2", "NDA 213378"])
    crosswalk, audit = create_fda_identity_review_queue(*sources(
        [missing, ambiguous, nonmatch, matched],
        [
            link(missing, STATUS_UNRESOLVED),
            link(ambiguous, STATUS_AMBIGUOUS, ["NDA210854", "NDA214410"]),
            link(nonmatch, STATUS_NONMATCH, ["BLA761401"]),
            link(matched, STATUS_MATCH, ["NDA213378"]),
        ],
    ))
    assert audit["published_letter_records"] == 4
    assert audit["review_queue_records"] == 3
    assert audit["already_identity_linked_records"] == 1
    assert audit["review_reason_counts"] == {
        STATUS_UNRESOLVED: 1, STATUS_AMBIGUOUS: 1, STATUS_NONMATCH: 1,
    }
    assert [r["review_priority"] for r in crosswalk["records"]] == [1, 2, 3]
    assert crosswalk["records"][0]["source_record_sha256"] == digest("a")
    assert crosswalk["records"][0]["source_document_url"] is None
    assert all(r["model_eligible"] is False for r in crosswalk["records"])
    assert all(r["identity_verified"] is False for r in crosswalk["records"])
    assert audit["model_eligible_records"] == 0
    assert audit["independently_verified_review_cycles"] == 0
    assert audit["prediction_probability"] is None


def test_cannot_adjudicate_rejection_from_registry_nonmatch():
    row = record("a", ["BLA 761401"])
    queue, audit = create_fda_identity_review_queue(
        *sources([row], [link(row, STATUS_NONMATCH, ["BLA761401"])]))
    assert "nonmatch does not establish rejection" in queue["records"][0]["required_reviewer_action"]
    assert queue["records"][0]["review_cycle_verified"] is False
    assert audit["complete_application_denominator_verified"] is False


@pytest.mark.parametrize("bad_field,value", [
    ("model_eligible", True),
    ("complete_cohort_verified", True),
    ("point_in_time_outcome_verified", True),
])
def test_source_promotion_fails_closed(bad_field, value):
    row = record("a", ["BLA 761401"])
    linked = link(row, STATUS_NONMATCH, ["BLA761401"])
    linked[bad_field] = value
    with pytest.raises(ValueError, match="cannot be promoted"):
        create_fda_identity_review_queue(*sources([row], [linked]))


def test_duplicate_unknown_or_missing_source_digest_fails_closed():
    row = record("a", ["NDA 123456"])
    one = link(row, STATUS_UNRESOLVED)
    with pytest.raises(ValueError, match="duplicate or unknown source digest"):
        create_fda_identity_review_queue(*sources([row, record("b", ["NDA 987654"])], [one, one]))
    with pytest.raises(ValueError, match="counts differ"):
        create_fda_identity_review_queue(*sources([row], []))


def test_tampered_published_identity_or_date_fails_closed():
    row = record("a", ["NDA 123456"])
    linked = link(row, STATUS_UNRESOLVED)
    linked["source_application_identifiers_as_published"] = ["NDA 999999"]
    with pytest.raises(ValueError, match="do not reconcile"):
        create_fda_identity_review_queue(*sources([row], [linked]))
    linked = link(row, STATUS_NONMATCH)
    linked["letter_date_as_published"] = "01/01/2021"
    with pytest.raises(ValueError, match="do not reconcile"):
        create_fda_identity_review_queue(*sources([row], [linked]))


def test_unknown_link_status_rejected():
    row = record("a", ["NDA 123456"])
    with pytest.raises(ValueError, match="unrecognized"):
        create_fda_identity_review_queue(
            *sources([row], [link(row, "FDA_APPROVED")]))



def test_matched_letter_provenance_still_reconciled_before_skipping_queue():
    row = record("e", ["NDA 213378"])
    linked = link(row, STATUS_MATCH, ["NDA213378"])
    linked["letter_type_as_published"] = "TENTATIVE APPROVAL"
    with pytest.raises(ValueError, match="published letter fields do not reconcile"):
        create_fda_identity_review_queue(*sources([row], [linked]))


def test_unresolved_legacy_bl_is_not_silently_converted_to_bla():
    row = record('a', ['BL 125845'])
    queue, audit = create_fda_identity_review_queue(
        *sources([row], [link(row, STATUS_UNRESOLVED)]))
    item = queue['records'][0]
    assert item['application_ids_as_published'] == ['BL 125845']
    assert item['canonical_application_candidates'] == []
    assert item['identity_verified'] is False
    assert item['review_cycle_verified'] is False
    assert item['model_eligible'] is False
    assert audit['model_eligible_records'] == 0


def test_ambiguous_two_application_letter_remains_one_quarantined_ticket():
    row = record('b', ['NDA 214410/Original 2', 'NDA 210854/S-05'])
    queue, audit = create_fda_identity_review_queue(*sources(
        [row], [link(row, STATUS_AMBIGUOUS, ['NDA214410', 'NDA210854'])]))
    assert len(queue['records']) == 1
    assert queue['records'][0]['identity_link_status'] == STATUS_AMBIGUOUS
    assert queue['records'][0]['identity_verified'] is False
    assert queue['records'][0]['review_cycle_verified'] is False
    assert audit['independently_verified_review_cycles'] == 0
