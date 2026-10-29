import pytest
from research.preliminary_workspace_adapter import triage_workspace_pages


def _page(offset, limit, version):
    rows = [{"programId": "PDUFA-000001"}, {"programId": "PDUFA-000002"}]
    return {"version": "v1", "asOf": "2026-10-29T00:00:00Z", "total": 2,
            "offset": offset, "limit": limit, "rows": rows[offset:offset+limit],
            "nextOffset": offset+limit if offset+limit < 2 else None}


def test_pagination_does_not_fabricate_eligibility():
    result = triage_workspace_pages(_page, page_size=1)
    assert result["backend_rows_received"] == 2
    assert result["blocked"] == 2
    assert result["candidate_for_evidence_review"] == 0
    assert result["prediction_status"] == "ABSTAIN"


def test_rejects_snapshot_version_drift():
    def changed(offset, limit, version):
        page = _page(offset, limit, version)
        if offset:
            page["version"] = "v2"
        return page
    with pytest.raises(ValueError, match="changed"):
        triage_workspace_pages(changed, page_size=1)


def test_rejects_inconsistent_pagination():
    def broken(offset, limit, version):
        page = _page(offset, limit, version)
        page["nextOffset"] = None
        return page
    with pytest.raises(ValueError, match="pagination"):
        triage_workspace_pages(broken, page_size=1)
