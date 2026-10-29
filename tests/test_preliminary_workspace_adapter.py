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


def test_duplicate_program_ids_across_ten_thousand_record_boundary_rejected():
    import pytest
    total = 10001
    def page(offset, limit, version):
        rows = [{"programId": f"PDUFA-{i:06d}"} for i in range(offset, min(offset + limit, total))]
        if offset == 10000:
            rows[0]["programId"] = "PDUFA-000000"
        return {"version": "v1", "asOf": "2026-10-29T00:00:00Z",
                "total": total, "offset": offset, "limit": limit,
                "nextOffset": offset + limit if offset + limit < total else None,
                "rows": rows}
    with pytest.raises(ValueError, match="duplicate programId"):
        triage_workspace_pages(page)


def test_rejects_duplicate_program_id_across_ten_thousand_boundary():
    total = 10001
    def page(offset, limit, version):
        rows = [{"programId": f"PDUFA-{i:06d}"} for i in range(offset, min(offset + limit, total))]
        if offset == 10000:
            rows[0]["programId"] = "PDUFA-000000"
        return {"version": "v1", "asOf": "2026-10-29T00:00:00Z",
                "total": total, "offset": offset, "limit": limit,
                "rows": rows,
                "nextOffset": offset + limit if offset + limit < total else None}
    with pytest.raises(ValueError, match="duplicate programId"):
        triage_workspace_pages(page)


def test_summary_before_and_after_reconciles_snapshot_and_hashes():
    calls = []
    def summary():
        calls.append('summary')
        return {'pipeline': 2, 'asOf': '2026-10-29T00:00:00Z', 'sourceState': 'COMPLETE_PUBLISHED'}
    report = triage_workspace_pages(_page, page_size=1, get_summary=summary,
                                   now='2026-10-29T12:00:00Z')
    assert calls == ['summary', 'summary']
    assert report['summary_reconciled'] and report['retrieval_complete']
    assert report['snapshot_freshness_checked']
    assert report['page_count'] == len(report['page_sha256']) == 2
    assert len(report['source_rows_sha256']) == 64
    assert not report['data_authenticity_verified']
    assert report['prediction_status'] == 'ABSTAIN'


def test_same_version_cannot_hide_changing_total():
    def page(offset, limit, version):
        result = _page(offset, limit, version)
        if offset:
            result['total'] = 3
            result['nextOffset'] = 2
        return result
    with pytest.raises(ValueError, match='total changed'):
        triage_workspace_pages(page, page_size=1)


@pytest.mark.parametrize('bad_summary', [
    {'pipeline': 3, 'asOf': '2026-10-29T00:00:00Z', 'sourceState': 'PARTIAL'},
    {'pipeline': 2, 'asOf': '2026-10-28T00:00:00Z', 'sourceState': 'PARTIAL'},
    {'pipeline': 2, 'asOf': '2026-10-29T00:00:00Z', 'sourceState': 'STALE'},
    {'pipeline': True, 'asOf': '2026-10-29T00:00:00Z', 'sourceState': 'PARTIAL'},
])
def test_summary_must_agree_with_pages(bad_summary):
    with pytest.raises(ValueError, match='summary'):
        triage_workspace_pages(_page, get_summary=lambda: bad_summary)


def test_post_retrieval_summary_change_invalidates_result():
    calls = iter([{'pipeline': 2, 'asOf': '2026-10-29T00:00:00Z', 'sourceState': 'PARTIAL'},
                  {'pipeline': 3, 'asOf': '2026-10-29T00:00:00Z', 'sourceState': 'PARTIAL'}])
    with pytest.raises(ValueError, match='summary changed'):
        triage_workspace_pages(_page, get_summary=lambda: next(calls))


@pytest.mark.parametrize('stamp', [None, '2026-10-29T00:00:00',
                                  '2026-10-27T00:00:00Z', '2026-10-30T00:00:00Z'])
def test_missing_stale_future_or_naive_source_clock_rejected(stamp):
    def page(**kwargs):
        result = _page(**kwargs)
        result['asOf'] = stamp
        return result
    with pytest.raises(ValueError, match='timestamp|snapshot'):
        triage_workspace_pages(page, now='2026-10-29T12:00:00Z')


def test_short_intermediate_page_fails_before_next_request():
    calls = []
    def page(**kwargs):
        calls.append(kwargs['offset'])
        result = _page(**kwargs)
        result['rows'] = result['rows'][:1]
        return result
    with pytest.raises(ValueError, match='incomplete'):
        triage_workspace_pages(page)
    assert calls == [0]


def test_different_permanent_ids_cannot_alias_one_exact_source_program_across_batches():
    total = 10001
    def page(offset, limit, version):
        rows = [{'programId': f'PDUFA-{i:06d}', 'id': f'TRIAL|SYNTHETIC|{i}'}
                for i in range(offset, min(offset + limit, total))]
        if offset == 10000:
            rows[0]['id'] = 'TRIAL|SYNTHETIC|0'
        return {'version': 'v1', 'asOf': '2026-10-29T00:00:00Z', 'total': total,
                'offset': offset, 'limit': limit, 'rows': rows,
                'nextOffset': offset + limit if offset + limit < total else None}
    with pytest.raises(ValueError, match='duplicate exact source'):
        triage_workspace_pages(page)


@pytest.mark.parametrize('field,value', [('offset', False), ('limit', True), ('nextOffset', True)])
def test_boolean_page_bounds_never_alias_integer_bounds(field, value):
    def page(**kwargs):
        result = _page(**kwargs)
        result[field] = value
        return result
    with pytest.raises(ValueError, match='bounds|pagination'):
        triage_workspace_pages(page, page_size=1)


def test_backend_los_angeles_calendar_date_accepted():
    def page(offset, limit, version):
        return {"version": "v1", "asOf": "2026-10-29", "total": 1,
                "offset": offset, "limit": limit, "nextOffset": None,
                "rows": [{"programId": "PDUFA-000001"}]}
    result = triage_workspace_pages(page, now="2026-10-29T18:00:00+00:00")
    assert result["source_time_precision"] == "CALENDAR_DATE_LOS_ANGELES"
    assert result["blocked"] == 1


@pytest.mark.parametrize("as_of", ["2026-10-28", "2026-10-30", "2026-02-30", "2026-10-29T18:00:00"])
def test_rejects_stale_future_invalid_or_naive_source_clock(as_of):
    def page(offset, limit, version):
        return {"version": "v1", "asOf": as_of, "total": 1,
                "offset": offset, "limit": limit, "nextOffset": None,
                "rows": [{"programId": "PDUFA-000001"}]}
    with pytest.raises(ValueError):
        triage_workspace_pages(page, now="2026-10-29T18:00:00+00:00")


def _source_pages(rows, as_of):
    def page(offset, limit, version):
        return {'version': 'calendar-v1', 'asOf': as_of, 'total': len(rows),
                'offset': offset, 'limit': limit, 'rows': rows[offset:offset + limit],
                'nextOffset': offset + limit if offset + limit < len(rows) else None}
    return page


def test_calendar_snapshot_counts_cap_claims_against_actual_observation_without_certifying_eligibility():
    rows = [
        {'programId': f'PDUFA-{i:06d}', 'id': f'TRIAL|SYNTHETIC|{i}',
         'marketCap': 500000000, 'capSource': 'https://example.com/cap',
         'capChecked': checked}
        for i, checked in enumerate([
            '2026-10-29', '2026-10-20', '2026-10-30',
            '2026-10-29T18:00:01Z', '2026-10-29T17:00:00Z', '2026-10-29'])
    ]
    rows[-1].pop('capSource')
    rows[-1].pop('id')
    report = triage_workspace_pages(_source_pages(rows, '2026-10-29'), page_size=2,
        get_summary=lambda: {'pipeline': len(rows), 'asOf': '2026-10-29', 'sourceState': 'PARTIAL'},
        now='2026-10-29T18:00:00Z')
    assert report['market_cap_evidence_present'] == 2
    assert report['workspace_as_of'] == '2026-10-29'
    assert report['source_time_precision'] == 'CALENDAR_DATE_LOS_ANGELES'
    assert report['freshness_basis'] == 'CURRENT_LA_CALENDAR_DATE'
    assert report['observation_timestamp'] == '2026-10-29T18:00:00Z'
    assert report['cap_freshness_reference_timestamp'] == report['observation_timestamp']
    assert report['cap_freshness_reference_basis'] == 'OBSERVATION_TIME_NOT_SOURCE_PUBLICATION'
    assert report['workspace_total'] == report['backend_rows_received'] == 6
    assert report['page_count'] == 3
    assert report['unique_program_ids'] == 6
    assert report['unique_source_program_ids'] == 5
    assert report['source_program_ids_missing'] == 1
    assert report['duplicate_program_ids'] == report['duplicate_source_program_ids'] == report['missing_records'] == 0
    assert report['summary_reconciled'] and report['retrieval_complete']
    assert report['blocked'] == 6 and report['candidate_for_evidence_review'] == 0
    assert report['prediction_status'] == 'ABSTAIN' and not report['data_authenticity_verified']


def test_calendar_snapshot_without_observation_keeps_cap_claims_unverified():
    row = {'programId': 'PDUFA-000001', 'marketCap': 500000000,
           'capSource': 'https://example.com/cap', 'capChecked': '2026-10-29'}
    report = triage_workspace_pages(_source_pages([row], '2026-10-29'))
    assert report['market_cap_evidence_present'] == 0
    assert report['freshness_basis'] == 'NOT_CHECKED'
    assert not report['snapshot_freshness_checked']
    assert report['observation_timestamp'] is None
    assert report['cap_freshness_reference_timestamp'] is None
    assert report['cap_freshness_reference_basis'] == 'UNAVAILABLE'
    assert report['blocked'] == 1


def test_calendar_business_date_survives_utc_boundary_without_inventing_publication_clock():
    row = {'programId': 'PDUFA-000001', 'marketCap': 500000000,
           'capSource': 'https://example.com/cap', 'capChecked': '2026-10-30T01:00:00Z'}
    report = triage_workspace_pages(_source_pages([row], '2026-10-29'),
                                   now='2026-10-30T02:00:00Z')
    assert report['workspace_as_of'] == '2026-10-29'
    assert report['cap_freshness_reference_timestamp'] == '2026-10-30T02:00:00Z'
    assert report['market_cap_evidence_present'] == 1
    assert report['freshness_basis'] == 'CURRENT_LA_CALENDAR_DATE'
    assert report['prediction_status'] == 'ABSTAIN'


def test_legacy_aware_snapshot_retains_source_cutoff_even_with_later_observation():
    row = {'programId': 'PDUFA-000001', 'marketCap': 500000000,
           'capSource': 'https://example.com/cap', 'capChecked': '2026-10-29T01:00:00Z'}
    report = triage_workspace_pages(_source_pages([row], '2026-10-29T00:00:00Z'),
                                   now='2026-10-29T12:00:00Z')
    assert report['market_cap_evidence_present'] == 0
    assert report['source_time_precision'] == 'OFFSET_TIMESTAMP'
    assert report['freshness_basis'] == 'OFFSET_TIMESTAMP_AGE'
    assert report['observation_timestamp'] == '2026-10-29T12:00:00Z'
    assert report['cap_freshness_reference_timestamp'] == '2026-10-29T00:00:00Z'
    assert report['cap_freshness_reference_basis'] == 'WORKSPACE_AS_OF_OFFSET_TIMESTAMP'


@pytest.mark.parametrize('identity', ['programId', 'id'])
def test_calendar_snapshot_still_rejects_global_duplicate_identities(identity):
    rows = [{'programId': f'PDUFA-{i:06d}', 'id': f'TRIAL|SYNTHETIC|{i}'} for i in range(3)]
    rows[-1][identity] = rows[0][identity]
    with pytest.raises(ValueError, match='duplicate'):
        triage_workspace_pages(_source_pages(rows, '2026-10-29'), page_size=1,
                               now='2026-10-29T18:00:00Z')


def test_aggregate_fda_evidence_diagnostics_do_not_promote_prediction():
    def page(offset, limit, version):
        return {"version": "v-diagnostic", "asOf": "2026-10-29", "total": 4,
                "offset": offset, "limit": limit, "nextOffset": None,
                "rows": [
                    {"programId": "PDUFA-101", "pdufaDate": "2026-12-01",
                     "fdaSource": "https://www.fda.gov/approved", "checkStatus": "FDA_VERIFIED"},
                    {"programId": "PDUFA-102", "pdufaDate": "2026-12-02",
                     "fdaSource": "https://example.org/unverified", "checkStatus": "NOT VERIFIED"},
                    {"programId": "PDUFA-103", "pdufaDate": "2026-02-30",
                     "fdaSource": "https://www.fda.gov/example", "checkStatus": "VERIFIED"},
                    {"programId": "PDUFA-104"},
                ]}
    result = triage_workspace_pages(page, page_size=4, now="2026-10-29T18:00:00Z")
    assert result["raw_target_date_present"] == 3
    assert result["valid_target_date_present"] == 2
    assert result["fda_host_evidence_present"] == 2
    assert result["accepted_fda_verification_status_present"] == 2
    assert result["fda_target_evidence_present"] == 1
    assert result["blocked"] == 4
    assert result["prediction_status"] == "ABSTAIN"
