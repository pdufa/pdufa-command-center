from app.science_independent_investigation import scientific_investigation, DOMAINS

def test_empty_evidence_is_not_scientific_pass():
    result = scientific_investigation(exact_key="NCT123", evidence={}, as_of="2026-10-27")
    assert len(result["sections"]) == 8
    assert result["reviewed"] == 0
    assert result["scientificScore"] is None
    assert result["approvalProbability"] is None
    assert result["independentScientificConclusion"] is None

def test_verified_challenge_is_visible():
    evidence = {"primary_endpoint": {"review_status": "VERIFIED",
        "published_at": "2026-01-01", "source_url": "https://example.org/study",
        "finding": "Effect uncertain due to missingness",
        "interpretation": "CHALLENGES"}}
    result = scientific_investigation(exact_key="NCT123", evidence=evidence, as_of="2026-10-27")
    assert result["reviewed"] == 1
    assert result["criticalQuestions"] == ["primary_endpoint"]

def test_future_claim_not_counted():
    evidence = {"mechanism": {"review_status": "VERIFIED",
        "published_at": "2027-01-01", "source_url": "https://example.org/study",
        "finding": "Post-cutoff disclosure", "interpretation": "SUPPORTS"}}
    result = scientific_investigation(exact_key="NCT123", evidence=evidence, as_of="2026-10-27")
    assert result["reviewed"] == 0
