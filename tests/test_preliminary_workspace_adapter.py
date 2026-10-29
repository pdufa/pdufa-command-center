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
    assert result["field_mapping_applied"] is True


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


def test_more_than_ten_thousand_pipeline_programs_not_truncated():
    total = 10001
    def page(offset, limit, version):
        end = min(offset + limit, total)
        return {"version": "v-large", "asOf": "2026-10-29T00:00:00Z",
                "total": total, "offset": offset, "limit": limit,
                "rows": [{"programId": f"PDUFA-{i:06d}"} for i in range(offset, end)],
                "nextOffset": offset + limit if offset + limit < total else None}
    report = triage_workspace_pages(page)
    assert report["total"] == total
    assert report["blocked"] == total
    assert report["candidate_for_evidence_review"] == 0
    assert report["records"][-1]["program_id"] == "PDUFA-010000"


def test_field_evidence_counts_without_promoting_eligibility():
    def page(offset, limit, version):
        return {"version": "v1", "asOf": "2026-10-29T00:00:00Z",
                "total": 1, "offset": offset, "limit": limit,
                "nextOffset": None,
                "rows": [{"programId": "PDUFA-000003", "marketCap": 500000000,
                          "capSource": "https://example.com/market",
                          "capChecked": "2026-10-29", "pdufaDate": "2026-12-01",
                          "fdaSource": "https://www.fda.gov/example",
                          "checkStatus": "FDA_VERIFIED"}]}
    result = triage_workspace_pages(page)
    assert result["market_cap_evidence_present"] == 1
    assert result["fda_target_evidence_present"] == 1
    assert result["blocked"] == 1
    assert result["prediction_status"] == "ABSTAIN"
