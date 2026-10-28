from app.phase3_deep_evidence import (
    validate_snapshot, find_historical_analogs, contradiction_flags,
)

def test_future_information_is_excluded():
    row = {"exactKey": "HIST", "sourceUrl": "https://example.org/a",
           "publishedAt": "2026-11-01", "observedAt": "2026-11-02",
           "reviewStatus": "VERIFIED", "indication": "GIST"}
    assert not validate_snapshot(row, cutoff="2026-10-27")["eligible"]
    result = find_historical_analogs({"exactKey": "CURRENT", "indication": "GIST"},
                                     [row], prediction_as_of="2026-10-27")
    assert result["analogs"] == []
    assert result["approvalProbability"] is None

def test_matching_does_not_leak_outcome():
    row = {"exactKey": "HIST", "sourceUrl": "https://example.org/a",
           "publishedAt": "2025-01-01", "observedAt": "2025-01-02",
           "reviewStatus": "VERIFIED", "indication": "GIST",
           "endpoint": "PFS", "outcome": "APPROVED"}
    result = find_historical_analogs(
        {"exactKey": "CURRENT", "indication": "GIST", "endpoint": "PFS"},
        [row], prediction_as_of="2026-10-27")
    assert result["analogs"][0]["similarity"] == 1
    assert result["analogs"][0]["outcome"] is None

def test_contradictions_require_matching_endpoint_and_cutoff():
    base = {"exactKey": "TRIAL", "endpoint": "PFS", "population": "ITT",
            "unit": "months", "analysisCutoff": "2026-01-01",
            "reviewStatus": "VERIFIED"}
    rows = [{**base, "value": 12.0, "sourceUrl": "https://a.org"},
            {**base, "value": 14.0, "sourceUrl": "https://b.org"}]
    assert len(contradiction_flags(rows)) == 1
    rows[1]["analysisCutoff"] = "2026-02-01"
    assert contradiction_flags(rows) == []
