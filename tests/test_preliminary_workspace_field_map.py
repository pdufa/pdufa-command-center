import pytest
from research.preliminary_workspace_field_map import map_published_row


def test_actual_published_fields_are_not_sufficient_to_certify_listing_or_restrictions():
    row = {"programId": "PDUFA-000001", "ticker": "EXAMPLE",
           "marketCap": 500000000, "capSource": "https://example.com/market",
           "capChecked": "2026-10-29", "pdufaDate": "2026-12-01",
           "fdaSource": "https://www.fda.gov/example",
           "checkStatus": "FDA_VERIFIED"}
    result = map_published_row(row)
    assert result["cap_source_present"] is True
    assert result["fda_source_present"] is True
    assert result["listing_verified"] is False
    assert result["restrictions_verified"] is False
    assert result["scope"] == "BLOCKED"


def test_missing_market_cap_provenance_does_not_pass():
    row = {"programId": "PDUFA-000002", "marketCap": 500000000,
           "pdufaDate": "2026-12-01"}
    result = map_published_row(row)
    assert result["cap_source_present"] is False
    assert result["candidate"]["market_cap_usd"] is None


def test_non_fda_source_cannot_claim_fda_target_provenance():
    row = {"programId": "PDUFA-000004", "pdufaDate": "2026-12-01",
           "fdaSource": "https://not-fda.example/announcement",
           "checkStatus": "FDA_VERIFIED"}
    result = map_published_row(row)
    assert result["fda_source_present"] is False
    assert result["candidate"]["fda_pdufa_target_confirmed"] is False
    assert result["scope"] == "BLOCKED"


def test_unparseable_market_cap_check_date_is_not_provenance():
    row = {"programId": "PDUFA-000005", "marketCap": 500000000,
           "capSource": "https://example.com/market", "capChecked": "not-a-date"}
    result = map_published_row(row)
    assert result["cap_source_present"] is False
    assert result["candidate"]["market_cap_usd"] is None


@pytest.mark.parametrize('source', ['https://', 'https://user:secret@www.fda.gov/doc',
                                    'https://www.fda.gov:bad/doc', 'https://www.fda.gov/doc\n'])
def test_malformed_fda_sources_fail_closed_without_crashing(source):
    row = {'programId': 'PDUFA-000001', 'pdufaDate': '2026-12-01',
           'fdaSource': source, 'checkStatus': 'FDA_VERIFIED'}
    result = map_published_row(row)
    assert not result['fda_source_present']
    assert result['scope'] == 'BLOCKED'


@pytest.mark.parametrize('date_value', ['2026-99-99', 'unknown', '20261201'])
def test_invalid_target_dates_are_not_confirmed(date_value):
    row = {'programId': 'PDUFA-000001', 'pdufaDate': date_value,
           'fdaSource': 'https://www.fda.gov/doc', 'checkStatus': 'FDA_VERIFIED'}
    assert not map_published_row(row)['fda_source_present']


@pytest.mark.parametrize('checked', ['2026-10-20', '2026-10-30', '2026-10-29T14:00:00Z',
                                     '2026-10-29T00:00:00', '2026-10-29-junk'])
def test_stale_future_or_unreliable_cap_clock_is_not_supported(checked):
    row = {'programId': 'PDUFA-000001', 'marketCap': 500000000,
           'capSource': 'https://example.com/market', 'capChecked': checked}
    assert not map_published_row(row, as_of='2026-10-29T12:00:00Z')['cap_source_present']


def test_aware_backend_cap_timestamp_is_preserved_as_timely_source_claim():
    row = {'programId': 'PDUFA-000001', 'marketCap': 500000000,
           'capSource': 'https://example.com/market', 'capChecked': '2026-10-29T11:00:00Z'}
    report = map_published_row(row, as_of='2026-10-29T12:00:00Z')
    assert report['cap_source_present']
    assert not report['listing_verified'] and not report['restrictions_verified']
    assert report['scope'] == 'BLOCKED'


def test_sec_sponsor_disclosure_does_not_masquerade_as_fda_verification():
    # Pending PDUFA goal dates are often disclosed by sponsors through SEC
    # filings. A filing URL is a lead for application-level review, not proof
    # that FDA independently published or confirmed the pending goal date.
    row = {"programId": "PDUFA-SEC-001", "pdufaDate": "2026-12-01",
           "fdaSource": "https://www.sec.gov/Archives/edgar/data/123/filing.htm",
           "checkStatus": "FDA_VERIFIED"}
    result = map_published_row(row)
    assert result["fda_source_present"] is False
    assert result["candidate"]["fda_pdufa_target_confirmed"] is False
    assert result["scope"] == "BLOCKED"


def test_sec_sponsor_lead_is_not_fda_verified_or_prediction_ready():
    row = {"programId": "PDUFA-SEC-002", "pdufaDate": "2026-12-01",
           "sponsorSource": "https://www.sec.gov/Archives/edgar/data/123/filing.htm",
           "checkStatus": "FDA_VERIFIED"}
    result = map_published_row(row)
    assert result["sponsor_disclosure_lead"] is True
    assert result["fda_source_present"] is False
    assert result["candidate"]["fda_pdufa_target_confirmed"] is False
    assert result["scope"] == "BLOCKED"


@pytest.mark.parametrize("source", [
    "https://sec.gov.evil.example/filing",
    "http://www.sec.gov/Archives/filing",
    "https://user@sec.gov/filing",
    "https://www.sec.gov/filing#fragment",
])
def test_untrusted_sponsor_source_is_not_a_lead(source):
    row = {"programId": "PDUFA-SEC-003", "pdufaDate": "2026-12-01",
           "sponsorSource": source}
    result = map_published_row(row)
    assert result["sponsor_disclosure_lead"] is False
