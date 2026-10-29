"""Research-only adapter for the existing authenticated workspace page endpoint.

Caller provides an HTTP GET function; this module never stores credentials or
treats backend membership as independently verified. Backend GET processing may
refresh sources and allocate persistent program IDs; see the retrieval report.
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo
from hashlib import sha256
import json

from research.preliminary_pipeline_batch import triage_pipeline_export
from research.preliminary_workspace_field_map import map_published_row
from research.preliminary_pipeline_snapshot import _aware


def triage_workspace_pages(get_page, *, page_size=100, max_rows=20000,
                           get_summary=None, now=None, max_age_hours=24):
    if (not callable(get_page) or type(page_size) is not int or not 1 <= page_size <= 100
            or type(max_rows) is not int or not 0 <= max_rows <= 100000
            or type(max_age_hours) not in (int, float) or not 0 < max_age_hours <= 168):
        raise ValueError("valid GET function and page size 1..100 required")
    if get_summary is not None and not callable(get_summary):
        raise ValueError("summary GET function required")
    summary = get_summary() if get_summary else None
    if get_summary and (not isinstance(summary, dict) or type(summary.get('pipeline')) is not int
                        or summary.get('sourceState') not in ('COMPLETE_PUBLISHED', 'PARTIAL')):
        raise ValueError("valid published workspace summary required")
    version = None
    as_of = None
    rows = []
    offset = 0
    snapshot_total = None
    page_hashes = []
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
            # Backend source_workspace emits asOf as a Los Angeles calendar date,
            # not a timestamp. Never invent a time or timezone offset for it.
            if isinstance(as_of, str) and len(as_of) == 10:
                try:
                    source_day = date.fromisoformat(as_of)
                except ValueError:
                    raise ValueError("invalid workspace source date") from None
                if source_day.isoformat() != as_of:
                    raise ValueError("invalid workspace source date")
                if now is not None:
                    current = _aware(now)
                    if current is None:
                        raise ValueError("aware observation timestamp required")
                    local_day = current.astimezone(ZoneInfo("America/Los_Angeles")).date()
                    if source_day != local_day:
                        raise ValueError("stale or future workspace source date")
            else:
                stamp = _aware(as_of)
                if stamp is None:
                    raise ValueError("aware workspace source timestamp required")
                if now is not None:
                    current = _aware(now)
                    if current is None or not 0 <= (current - stamp).total_seconds() <= max_age_hours * 3600:
                        raise ValueError("stale or future workspace snapshot")
        if page_version != version or page.get("asOf") != as_of:
            raise ValueError("workspace snapshot changed during pagination")
        if (type(page.get("offset")) is not int or type(page.get("limit")) is not int
                or page.get("offset") != offset or page.get("limit") != page_size):
            raise ValueError("workspace page bounds mismatch")
        chunk = page.get("rows")
        total = page.get("total")
        if not isinstance(chunk, list) or not isinstance(total, int) or isinstance(total, bool):
            raise ValueError("invalid workspace rows or count")
        if total < 0 or total > max_rows or len(chunk) > page_size:
            raise ValueError("workspace size exceeds safe limit")
        if snapshot_total is None:
            snapshot_total = total
        if total != snapshot_total:
            raise ValueError("workspace total changed during pagination")
        if summary is not None and (summary['pipeline'] != total or summary.get('asOf') != as_of):
            raise ValueError("workspace summary/page reconciliation failed")
        if offset + len(chunk) > total:
            raise ValueError("workspace page exceeds total")
        if len(chunk) != min(page_size, total - offset):
            raise ValueError("incomplete workspace page")
        page_hashes.append(sha256(json.dumps(page, sort_keys=True, separators=(',', ':'),
                                            allow_nan=False).encode()).hexdigest())
        rows.extend(chunk)
        expected_next = offset + page_size if offset + page_size < total else None
        if (page.get("nextOffset") is not None and type(page.get("nextOffset")) is not int
                or page.get("nextOffset") != expected_next):
            raise ValueError("workspace pagination mismatch")
        if expected_next is None:
            if len(rows) != total:
                raise ValueError("incomplete workspace pagination")
            break
        if not chunk:
            raise ValueError("empty intermediate workspace page")
        offset = expected_next

    if get_summary:
        final_summary = get_summary()
        if not isinstance(final_summary, dict) or any(final_summary.get(k) != summary.get(k)
                for k in ('pipeline', 'asOf', 'sourceState')):
            raise ValueError("workspace summary changed during retrieval")

    # Backend field names are not equivalent to the research screening claims.
    # Never silently infer public listing, market cap, restriction membership,
    # or FDA confirmation from an unverified backend row.
    calendar_source = len(as_of) == 10
    # A business date is not an exact publication cutoff. Use the caller's
    # actual aware observation clock for cap-claim freshness in this case;
    # never invent midnight or loosen an unavailable reference to None.
    # Legacy aware source timestamps retain their stricter original cutoff.
    cap_reference = now if calendar_source and now is not None else as_of
    candidates = []
    seen_program_ids = set()
    seen_source_ids = set()
    cap_evidence_count = 0
    fda_evidence_count = 0
    raw_target_count = 0
    valid_target_count = 0
    fda_host_count = 0
    fda_status_count = 0
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid workspace record")
        identity = row.get("programId")
        if (not isinstance(identity, str) or not identity or identity != identity.strip()
                or any(ord(c) < 32 for c in identity)):
            raise ValueError("stable backend programId required")
        if identity in seen_program_ids:
            raise ValueError("duplicate programId across workspace pages")
        seen_program_ids.add(identity)
        source_id = row.get('id')
        if source_id is not None:
            if not isinstance(source_id, str) or not source_id.strip() or source_id != source_id.strip():
                raise ValueError("invalid exact source program identity")
            if source_id in seen_source_ids:
                raise ValueError("duplicate exact source program identity")
            seen_source_ids.add(source_id)
        # Aggregate diagnostics only; a date alone is not FDA confirmation.
        target_text = row.get("pdufaDate")
        raw_target_count += bool(target_text)
        if isinstance(target_text, str):
            try:
                valid_target_count += date.fromisoformat(target_text).isoformat() == target_text
            except ValueError:
                pass
        from research.preliminary_workspace_field_map import _https
        host = _https(row.get("fdaSource"))
        fda_host_count += bool(host and (host == "fda.gov" or host.endswith(".fda.gov")))
        fda_status_count += row.get("checkStatus") in ("VERIFIED", "FDA_VERIFIED")
        mapped = map_published_row(row, as_of=cap_reference)
        candidates.append(mapped["candidate"])
        cap_evidence_count += bool(mapped["cap_source_present"])
        fda_evidence_count += bool(mapped["fda_source_present"])
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
        "workspace_total": snapshot_total,
        "backend_rows_received": len(rows),
        "unique_program_ids": len(seen_program_ids),
        "unique_source_program_ids": len(seen_source_ids),
        "source_program_ids_missing": len(rows) - len(seen_source_ids),
        # These zero counts are emitted only after complete pagination and all
        # global identity checks succeed; failures never yield a success report.
        "duplicate_program_ids": 0,
        "duplicate_source_program_ids": 0,
        "missing_records": snapshot_total - len(rows),
        "retrieval_complete": True,
        "summary_reconciled": get_summary is not None,
        "snapshot_freshness_checked": now is not None,
        "source_time_precision": "CALENDAR_DATE_LOS_ANGELES" if calendar_source else "OFFSET_TIMESTAMP",
        "freshness_basis": ("NOT_CHECKED" if now is None else
                            "CURRENT_LA_CALENDAR_DATE" if calendar_source else "OFFSET_TIMESTAMP_AGE"),
        "observation_timestamp": now,
        "cap_freshness_reference_timestamp": (now if calendar_source else as_of),
        "cap_freshness_reference_basis": (
            "UNAVAILABLE" if calendar_source and now is None else
            "OBSERVATION_TIME_NOT_SOURCE_PUBLICATION" if calendar_source else
            "WORKSPACE_AS_OF_OFFSET_TIMESTAMP"),
        "page_count": len(page_hashes),
        "page_sha256": page_hashes,
        "source_rows_sha256": sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'),
                                                allow_nan=False).encode()).hexdigest(),
        "hash_scope": "RETRIEVED_JSON_NOT_INDEPENDENT_SOURCE_OR_RESTRICTION_VERIFICATION",
        "screening_fields_verified": False,
        "field_mapping_applied": True,
        "market_cap_evidence_present": cap_evidence_count,
        "fda_target_evidence_present": fda_evidence_count,
        "raw_target_date_present": raw_target_count,
        "valid_target_date_present": valid_target_count,
        "fda_host_evidence_present": fda_host_count,
        "accepted_fda_verification_status_present": fda_status_count,
        "prediction_status": "ABSTAIN",
    }
