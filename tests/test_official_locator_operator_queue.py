"""Research-only acquisition queue tests."""
from research.official_locator_operator_queue import COLUMNS, build_operator_queue


def test_operator_queue_has_one_row_per_requirement():
    rows = build_operator_queue()
    assert len(rows) == len({row["document_id"] for row in rows})
    assert len(rows) >= 1
    assert all(set(row) == set(COLUMNS) for row in rows)


def test_operator_queue_orders_known_then_derived_then_unresolved():
    rows = build_operator_queue()
    assert [r["priority"] for r in rows] == sorted(r["priority"] for r in rows)
    for row in rows:
        if row["priority"] == 3:
            assert row["source_lead"] is None
            assert row["locator_status"] == "UNRESOLVED_LOCATOR"
        else:
            assert row["source_lead"] is not None


def test_operator_queue_never_claims_verification():
    for row in build_operator_queue():
        assert row["original_bytes_acquired"] is False
        assert row["publication_clock_verified"] is False
        assert row["independently_verified"] is False
