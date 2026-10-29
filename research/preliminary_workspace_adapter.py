"""Research-only adapter for the existing authenticated workspace page endpoint.

Caller provides an HTTP GET function; this module never stores credentials,
writes to the backend, or treats backend membership as independently verified.
"""
from research.preliminary_pipeline_batch import triage_pipeline_export
from research.preliminary_workspace_field_map import map_published_row


def triage_workspace_pages(get_page, *, page_size=100, max_rows=20000):
    if not callable(get_page) or not 1 <= page_size <= 100:
        raise ValueError("valid GET function and page size 1..100 required")
    version = None
    as_of = None
    rows = []
    offset = 0
    while True:
        page = get_page(offset=offset, limit=page_size, version=version or "")
        if not isinstance(page, dict):
            raise ValueError("invalid workspace page")
        page_version = page.get("version")
        if not isinstance(page_version, str) or not page_version:
            raise ValueError("workspace version missing")
        if version is None:
            version = page_version
            as_of = page.get("asOf")
        if page_version != version or page.get("asOf") != as_of:
            raise ValueError("workspace snapshot changed during pagination")
        if page.get("offset") != offset or page.get("limit") != page_size:
            raise ValueError("workspace page bounds mismatch")
        chunk = page.get("rows")
        total = page.get("total")
        if not isinstance(chunk, list) or not isinstance(total, int) or isinstance(total, bool):
            raise ValueError("invalid workspace rows or count")
        if total < 0 or total > max_rows or len(chunk) > page_size:
            raise ValueError("workspace size exceeds safe limit")
        if offset + len(chunk) > total:
            raise ValueError("workspace page exceeds total")
        rows.extend(chunk)
        expected_next = offset + page_size if offset + page_size < total else None
        if page.get("nextOffset") != expected_next:
            raise ValueError("workspace pagination mismatch")
        if expected_next is None:
            if len(rows) != total:
                raise ValueError("incomplete workspace pagination")
            break
        if not chunk:
            raise ValueError("empty intermediate workspace page")
        offset = expected_next

    # Backend field names are not equivalent to the research screening claims.
    # Never silently infer public listing, market cap, restriction membership,
    # or FDA confirmation from an unverified backend row.
    candidates = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid workspace record")
        identity = row.get("programId")
        if not isinstance(identity, str) or not identity:
            raise ValueError("stable backend programId required")
        candidates.append(map_published_row(row)["candidate"])
    reports = []
    for start in range(0, len(candidates), 10000):
        reports.append(triage_pipeline_export(candidates[start:start + 10000]))
    if not reports:
        reports.append(triage_pipeline_export([]))
    report = {
        'records': [item for group in reports for item in group['records']],
        'total': len(candidates),
        'candidate_for_evidence_review': sum(group['candidate_for_evidence_review'] for group in reports),
        'blocked': sum(group['blocked'] for group in reports),
        'prediction_status': 'ABSTAIN',
        'research_only': True,
        'data_authenticity_verified': False,
    }
    return {
        **report,
        "workspace_version": version,
        "workspace_as_of": as_of,
        "backend_rows_received": len(rows),
        "screening_fields_verified": False,
        "field_mapping_applied": True,
        "market_cap_evidence_present": sum(bool(map_published_row(row)["cap_source_present"]) for row in rows),
        "fda_target_evidence_present": sum(bool(map_published_row(row)["fda_source_present"]) for row in rows),
        "prediction_status": "ABSTAIN",
    }
