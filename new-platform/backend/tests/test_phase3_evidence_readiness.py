from app.phase3_evidence_readiness import evidence_readiness

def test_initial_phase3_has_only_current_requirements():
    r = evidence_readiness(exact_key="NCT123|drug|indication", phase="phase3",
                           evidence={}, as_of="2026-10-27")
    assert r["applicableCount"] == 13
    assert r["verifiedCount"] == 0
    assert r["dataReadinessPercent"] == 0
    assert r["predictionConfidencePercent"] is None
    assert not r["predictionReady"] and not r["tradeAuthorized"]
    assert next(x for x in r["items"] if x["key"] == "pdufa_date")["status"] == "NOT_YET_APPLICABLE"

def test_verified_requires_provenance_and_nonfuture_date():
    r = evidence_readiness(exact_key="NCT123|drug|indication", phase="phase3",
        evidence={"primary_endpoint": {"status": "VERIFIED",
            "source_url": "https://clinicaltrials.gov/study/NCT123",
            "source_date": "2026-10-01"},
                  "effect_size": {"status": "VERIFIED",
            "source_url": "http://example.org", "source_date": "2026-10-01"},
                  "safety": {"status": "VERIFIED",
            "source_url": "https://example.org", "source_date": "2026-12-01"}},
        as_of="2026-10-27")
    assert r["verifiedCount"] == 1
    assert r["dataReadinessPercent"] == round(100 / 13, 1)

def test_filing_expands_denominator_without_fabricating_data():
    r = evidence_readiness(exact_key="NCT123|drug|indication", phase="filing",
                           evidence={}, as_of="2026-10-27")
    assert r["applicableCount"] == 16
    assert r["predictionConfidencePercent"] is None
