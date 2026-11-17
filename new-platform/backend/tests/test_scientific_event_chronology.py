"""Check dated claims against accepted reviewed original source receipts."""
from app.scientific_event_chronology import event_covered_by_review


def receipt():
    return {"acceptedEvidence": {
        "officialActionAndDate": {
            "sourceDate": "2026-01-25",
            "sourceRetrievedAt": "2026-01-27",
            "sourceVerifiedAt": "2026-01-28",
            "reviewedAt": "2026-01-29",
            "retrievalProvenance": "RECORDED",
        }
    }}


def test_event_after_source_publication_is_not_supported():
    assert event_covered_by_review(receipt(), "officialActionAndDate",
                                   "2026-01-25", "2026-02-01")
    assert not event_covered_by_review(receipt(), "officialActionAndDate",
                                       "2026-01-26", "2026-02-01")


def test_event_after_retrieval_or_future_review_not_eligible():
    result = receipt()
    result["acceptedEvidence"]["officialActionAndDate"]["sourceDate"] = "2026-01-28"
    assert not event_covered_by_review(result, "officialActionAndDate",
                                       "2026-01-28", "2026-02-01")
    result = receipt()
    result["acceptedEvidence"]["officialActionAndDate"]["reviewedAt"] = "2026-03-01"
    assert not event_covered_by_review(result, "officialActionAndDate",
                                       "2026-01-25", "2026-02-01")


def test_broken_chronology_or_missing_receipt_is_rejected():
    for change in ({"sourceRetrievedAt": None}, {"retrievalProvenance": "NOT_RECORDED"},
                   {"sourceDate": "2026-02-30"},
                   {"sourceVerifiedAt": "2026-01-24"}):
        item = receipt()
        item["acceptedEvidence"]["officialActionAndDate"].update(change)
        assert not event_covered_by_review(item, "officialActionAndDate",
                                           "2026-01-25", "2026-02-01")


def test_availability_check_can_follow_original_source_but_not_retrieval():
    assert event_covered_by_review(receipt(), "officialActionAndDate",
                                   "2026-01-26", "2026-02-01",
                                   source_after_event=False)
    assert not event_covered_by_review(receipt(), "officialActionAndDate",
                                       "2026-01-28", "2026-02-01",
                                       source_after_event=False)
