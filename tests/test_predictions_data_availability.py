from research.predictions_data_availability import assess_data_availability


def test_missing_critical_blocks_even_if_other_fields_verified():
    rows = [
        {"category": category, "field": field, "status": "VERIFIED", "source_url": "https://www.fda.gov/example"}
        for category, field, critical in (
            ("Phase 3 efficacy", "Primary endpoint result", True),
            ("Phase 3 efficacy", "Prespecified endpoint definition", True),
            ("Safety", "Adverse event tables", True),
            ("Statistics", "Analysis population and SAP", True),
            ("FDA history", "Application and regulatory status", True),
            ("Manufacturing / CMC", "Manufacturing inspection evidence", True),
            ("Historical comparisons", "Relevant historical decisions", False),
            ("Special designations", "FDA designation documentation", False),
        )
    ]
    complete = assess_data_availability(rows)
    assert complete["available_percent"] == 100.0
    assert complete["readiness"] == "READY_FOR_FULL_ANALYSIS"
    rows[0]["status"] = "MISSING"
    result = assess_data_availability(rows)
    assert result["available_percent"] == 87.5
    assert result["readiness"] == "NOT_READY"


def test_unverified_source_does_not_count_as_available():
    result = assess_data_availability([
        {"category": "Phase 3 efficacy", "field": "Primary endpoint result", "status": "VERIFIED"}
    ])
    assert result["verified_fields"] == 0
    assert result["fields"][0]["status"] == "AVAILABLE_UNVERIFIED"


def test_optional_missing_can_allow_partial_analysis():
    from research.predictions_data_availability import REQUIRED_FIELDS
    rows = [
        {"category": category, "field": field, "status": "VERIFIED", "source_url": "https://www.fda.gov/example"}
        for category, field, critical in REQUIRED_FIELDS if critical
    ]
    result = assess_data_availability(rows)
    assert result["readiness"] == "PARTIAL_ANALYSIS_ONLY"
