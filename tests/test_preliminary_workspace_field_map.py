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
