"""Scientific quantitative registry values: bounded, verbatim, no inferred success."""
import gzip
import hashlib
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.scientific_quantitative_results import reported_quantitative_results

NCT = "NCT04280705"


def source_record():
    return {
        "protocolSection": {"identificationModule": {"nctId": NCT}},
        "hasResults": True,
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [
                    {
                        "type": "PRIMARY",
                        "title": "Time to Recovery",
                        "timeFrame": "Day 1 to Day 29",
                        "paramType": "MEDIAN",
                        "unitOfMeasure": "Days",
                        "groups": [
                            {"id": "OG000", "title": "Placebo"},
                            {"id": "OG001", "title": "Remdesivir"},
                        ],
                        "analyses": [{
                            "groupIds": ["OG000", "OG001"],
                            "nonInferiorityType": "SUPERIORITY",
                            "statisticalMethod": "Log Rank",
                            "paramType": "Cox Proportional Hazard",
                            "paramValue": "1.29",
                            "pValue": "<0.001",
                            "ciPctValue": "95",
                            "ciNumSides": "TWO_SIDED",
                            "ciLowerLimit": "1.12",
                            "ciUpperLimit": "1.48",
                        }],
                    },
                    {
                        "type": "SECONDARY", "title": "Second outcome",
                        "analyses": [{"pValue": "0.23", "paramValue": "-0.02"}]
                    },
                ]
            },
            "adverseEventsModule": {
                "eventGroups": [{"id": "EG000"}, {"id": "EG001"}],
                "seriousEvents": [{
                    "term": "Respiratory failure",
                    "organSystem": "Respiratory disorders",
                    "stats": [
                        {"groupId": "EG000", "numAffected": "5", "numAtRisk": "100", "numEvents": "5"},
                        {"groupId": "EG001", "numAffected": "3", "numAtRisk": "98"},
                    ],
                }],
                "otherEvents": [],
            },
        },
    }


def test_verbatim_reported_analyses_and_safety_with_exact_json_paths():
    result = reported_quantitative_results(NCT, source_record())
    assert result["sourceStatus"] == "registry_reported_not_independently_verified"
    assert result["outcomeCountTotal"] == result["outcomeCountShown"] == 2
    assert result["analysisCountTotal"] == result["analysisCountShown"] == 2
    assert result["reportedPValuesShown"] == 2
    assert result["reportedConfidenceIntervalsShown"] == 1
    primary = result["outcomes"][0]
    assert primary["outcomeType"] == "PRIMARY"
    assert primary["groups"][0] == {"id": "OG000", "title": "Placebo"}
    analysis = primary["analyses"][0]
    assert analysis["pValueReported"] == "<0.001"  # Never coerce to exactly 0.001
    assert analysis["reportedEstimate"] == "1.29"
    assert analysis["confidenceIntervalLower"] == "1.12"
    assert analysis["confidenceIntervalUpper"] == "1.48"
    assert analysis["sourceFieldPath"] == (
        "resultsSection.outcomeMeasuresModule.outcomeMeasures[0].analyses[0]"
    )
    assert result["outcomes"][1]["analyses"][0]["sourceFieldPath"].endswith(
        "outcomeMeasures[1].analyses[0]"
    )
    stats = result["safety"]["seriousEventTermsShown"][0]["groupStats"][0]
    assert stats["numAffected"] == "5"
    assert stats["numAtRisk"] == "100"
    assert stats["numEvents"] == "5"
    assert result["safety"]["denominatorsNotInterpreted"] is True
    assert result["independentlyVerified"] is False
    assert result["effectivenessConclusion"] is None
    assert result["statisticalSignificanceConclusion"] is None
    assert result["approvalProbability"] is None


def test_absent_results_does_not_infer_zero_effect():
    result = reported_quantitative_results(NCT, {
        "protocolSection": {"identificationModule": {"nctId": NCT}},
        "hasResults": False,
    })
    assert result["outcomeCountTotal"] == 0
    assert result["reportedPValuesShown"] == 0
    assert result["outcomes"] == []
    assert result["hasResultsFlag"] is False
    assert result["effectivenessConclusion"] is None


def test_bounded_extraction_and_untrusted_numeric_rejection():
    record = source_record()
    measures = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]
    measures[:] = [{
        "type": "PRIMARY",
        "title": "M" * 500,
        "analyses": [
            {"pValue": "not a number", "paramValue": "nan", "ciLowerLimit": "inf",
             "ciUpperLimit": "0.1"} for _ in range(10)
        ],
        "groups": [{"id": "G" + str(i), "title": "Group"} for i in range(40)]
    } for _ in range(45)]
    events = record["resultsSection"]["adverseEventsModule"]
    events["seriousEvents"] = [{
        "term": "Sample Event",
        "stats": [{"groupId": "G", "numAffected": "0"} for _ in range(20)]
    } for _ in range(30)]
    r = reported_quantitative_results(NCT, record)
    assert r["truncated"] is True
    assert r["outcomeCountTotal"] == 45 and r["outcomeCountShown"] == 30
    assert r["analysisCountTotal"] == 450 and r["analysisCountShown"] == 150
    assert len(r["outcomes"][0]["groups"]) == 12
    assert len(r["outcomes"][0]["title"]) == 180 + 60  # outcome title cap
    assert r["reportedPValuesShown"] == 0
    assert r["outcomes"][0]["analyses"][0]["reportedEstimate"] is None
    assert r["outcomes"][0]["analyses"][0]["confidenceIntervalLower"] is None
    assert len(r["safety"]["seriousEventTermsShown"]) == 20
    assert len(r["safety"]["seriousEventTermsShown"][0]["groupStats"]) == 12


@pytest.mark.parametrize("bad", ["NCT0000", "NCT042807050", "bad", ""])
def test_bad_nct_id_rejected(bad):
    with pytest.raises(ValueError, match="Exact NCT"):
        reported_quantitative_results(bad, source_record())


def test_different_nct_id_rejected():
    with pytest.raises(ValueError, match="identity mismatch"):
        reported_quantitative_results("NCT02142738", source_record())


def test_an_authenticated_api_is_unscored_and_checksum_gated(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://test.invalid/review")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "quantitative-test-key")
    record = source_record()
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    with Session(engine) as session:
        session.add(main.FullTrialRecord(
            nct_id=NCT, payload_gzip=gzip.compress(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            summary={"nctId": NCT}, statistics=[],
            fetched_at=datetime(2026, 9, 20, tzinfo=timezone.utc)))
        session.commit()
    client = TestClient(main.app)
    url = "/api/scientific-assessment?exact_id=TRIAL%7C" + NCT
    assert client.get(url).status_code == 401
    headers = {"x-pdufa-internal-key": "quantitative-test-key"}
    result = client.get(url, headers=headers)
    assert result.status_code == 200
    body = result.json()
    data = body["quantitativeResults"]
    assert data["outcomes"][0]["analyses"][0]["pValueReported"] == "<0.001"
    assert data["independentlyVerified"] is False
    assert body["assessment"]["overall_score"] is None
    with Session(engine) as session:
        item = session.get(main.FullTrialRecord, NCT)
        item.sha256 = "0" * 64
        session.commit()
    bad_result = client.get(url, headers=headers).json()
    assert bad_result["registryEvidenceStatus"] == "record_unavailable_or_invalid"
    assert bad_result["quantitativeResults"] is None
    engine.dispose()
