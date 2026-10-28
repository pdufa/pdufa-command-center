"""SCIENCE 40: never promote unreviewed public claims to clinical readiness."""
import hashlib
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from app.science_40_dossier import evaluate_science_40, _catalog
from app.phase3_deep_analysis_orchestrator import prepare_deep_analysis
from app.phase3_research_batch import evaluate_candidate_batch


KEY = "APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130"
CUTOFF = "2026-10-27"
REVIEW_SCHEMA = "science40-adjudication-register-v1"


def evidence_record(level=1):
    return {
        "source_url": "https://investors.cogentbio.com/news-releases/peak",
        "source_kind": "ISSUER_DISCLOSURE",
        "published_at": "2026-05-30",
        "examined_at": "2026-10-27",
        "source_sha256": "a" * 64,
        "finding": "Source reported a primary endpoint efficacy comparison.",
        "interpretation": "SUPPORTS",
        "depth_level": level,
        "review_status": "VERIFIED",  # Caller cannot certify independent SCIENCE
    }


def independent_signoff(record):
    return {
        "reviewStatus": "INDEPENDENTLY_ADJUDICATED",
        "sourceUrl": record["source_url"],
        "publishedAt": record["published_at"],
        "sourceSha256": record["source_sha256"],
        "finding": record["finding"],
        "findingSha256": hashlib.sha256(record["finding"].encode()).hexdigest(),
        "interpretation": record["interpretation"],
        "reviewedAt": "2026-10-27",
        "reviewerId": "IndependentReviewer-A",
    }


def dummy_register(cases=None):
    return {"schemaVersion": REVIEW_SCHEMA, "cases": cases or {}}


def test_catalog_40_ids_eight_layers_and_twenty_depth_levels():
    q = _catalog()
    assert len(q) == 40
    assert [r["id"] for r in q] == [f"S{i:02}" for i in range(1, 41)]
    assert [sum(r["layer"] == i for r in q) for i in range(1, 9)] == [5] * 8
    r = evaluate_science_40(exact_key=KEY, evidence={}, as_of=CUTOFF)
    assert r["layers"] == 8
    assert r["totalAssessments"] == 40
    assert r["maximumInvestigationDepth"] == 20
    assert len(r["missingDepthLevels"]) == 20


def test_first_real_peak_trial_starts_at_zero_of_forty_and_abstains():
    file = Path(__file__).parent / "fixtures" / "peak_real_trial_20261027.json"
    case = json.loads(file.read_text(encoding="utf-8"))
    trial = case["candidate"]
    response = evaluate_candidate_batch([trial], as_of=case["as_of"])
    row = response["rows"][0]
    assert row["deepAnalysisEligible"]
    dossier = row["analysis"]["science40"]
    assert dossier["exactKey"] == trial["exact_key"]
    assert dossier["independentlyReviewedAssessments"] == 0
    assert dossier["submittedSourceObservations"] == 0
    assert dossier["totalAssessments"] == 40
    assert dossier["independentEvidenceCoveragePercent"] == 0.0
    assert dossier["readinessGrade"] == "RELUCTANT"
    assert dossier["independentScientificConclusion"] is None
    assert dossier["approvalProbability"] is None
    assert dossier["tradeAuthorized"] is False
    assert response["sheetPopulationStatus"] == "NOT_WRITTEN"


def test_public_claim_is_source_reported_not_independently_certified():
    record = evidence_record()
    r = evaluate_science_40(exact_key=KEY, evidence={"S01": record}, as_of=CUTOFF)
    assert r["submittedSourceObservations"] == 1
    assert r["independentlyReviewedAssessments"] == 0
    assert r["records"][0]["status"] == "SOURCE_REPORTED_UNADJUDICATED"
    assert r["records"][0]["independentlyReviewed"] is False
    assert r["readinessGrade"] == "RELUCTANT"


def test_forty_self_asserted_verified_records_cannot_create_readiness():
    evidence = {f"S{i:02}": evidence_record((i - 1) % 20 + 1) for i in range(1, 41)}
    r = evaluate_science_40(exact_key=KEY, evidence=evidence, as_of=CUTOFF)
    assert r["submittedSourceObservations"] == 40
    assert r["independentlyReviewedAssessments"] == 0
    assert r["reviewedDepthLevels"] == []
    assert r["readinessGrade"] == "RELUCTANT"


@pytest.mark.parametrize("edit", [
    {"source_url": "http://example.org"},
    {"source_url": "https://user:password@example.org/test"},
    {"source_url": "https://localhost/test"},
    {"source_sha256": "not-a-sha"},
    {"published_at": "2026-12-01"},
    {"examined_at": "2026-12-01"},
    {"published_at": "2026-10-28", "examined_at": "2026-10-27"},
    {"finding": ""},
    {"interpretation": "APPROVED"},
    {"depth_level": 21},
    {"depth_level": True},
    {"source_kind": "UNVERIFIED_AI_GUESS"},
])
def test_invalid_or_future_submission_cannot_be_counted(edit):
    item = evidence_record()
    item.update(edit)
    r = evaluate_science_40(exact_key=KEY, evidence={"S01": item}, as_of=CUTOFF)
    assert r["rejectedSourceSubmissions"] == 1
    assert r["records"][0]["status"] == "REJECTED"
    assert r["records"][0]["sourceObservation"] is None
    assert r["independentlyReviewedAssessments"] == 0


def test_signoff_requires_exact_independent_attestation_with_provenance():
    item = evidence_record()
    att = independent_signoff(item)
    approved = dummy_register({KEY: {"S01": att}})
    r = evaluate_science_40(exact_key=KEY, evidence={"S01": item},
                            as_of=CUTOFF, trusted_register=approved)
    assert r["independentlyReviewedAssessments"] == 1
    assert r["records"][0]["status"] == "INDEPENDENTLY_REVIEWED"
    assert r["reviewedDepthLevels"] == [1]
    assert r["readinessGrade"] == "RELUCTANT"
    assert r["approvalProbability"] is None
    assert r["independentScientificConclusion"] is None

    for field, altered in (
        ("sourceSha256", "0" * 64), ("sourceUrl", "https://example.org/other"),
        ("findingSha256", "0" * 64), ("interpretation", "CHALLENGES"),
        ("reviewedAt", "2026-10-28"), ("reviewerId", ""),
    ):
        bad = deepcopy(att)
        bad[field] = altered
        failed = evaluate_science_40(
            exact_key=KEY, evidence={"S01": item}, as_of=CUTOFF,
            trusted_register=dummy_register({KEY: {"S01": bad}}),
        )
        assert failed["independentlyReviewedAssessments"] == 0, field


def test_signoff_for_other_exact_case_does_not_transfer():
    item = evidence_record()
    r = evaluate_science_40(exact_key=KEY, evidence={"S01": item}, as_of=CUTOFF,
                            trusted_register=dummy_register({"ANOTHER|TRIAL": {"S01": independent_signoff(item)}}))
    assert r["independentlyReviewedAssessments"] == 0


def test_mixed_or_challenging_evidence_is_not_ignored_after_signoff():
    item = evidence_record()
    item["interpretation"] = "MIXED"
    r = evaluate_science_40(
        exact_key=KEY, evidence={"S17": item}, as_of=CUTOFF,
        trusted_register=dummy_register({KEY: {"S17": independent_signoff(item)}}),
    )
    assert r["criticalQuestions"] == ["S17"]
    assert r["approvalProbability"] is None


def test_structural_only_ready_when_forty_attested_and_twenty_depths_covered():
    # Purely synthetic test for structural rules: not a real clinical dossier.
    inputs = {f"S{i:02}": evidence_record((i - 1) % 20 + 1) for i in range(1, 41)}
    attestations = {id: independent_signoff(record) for id, record in inputs.items()}
    r = evaluate_science_40(
        exact_key=KEY, evidence=inputs, as_of=CUTOFF,
        trusted_register=dummy_register({KEY: attestations}),
    )
    assert r["independentlyReviewedAssessments"] == 40
    assert r["reviewedDepthLevels"] == list(range(1, 21))
    assert r["readinessGrade"] == "READY_FOR_ANALYSIS"
    assert r["readinessMeaning"] == "STRUCTURAL_EVIDENCE_READINESS_NOT_FDA_OUTCOME"
    assert r["approvalProbability"] is None
    assert r["tradeAuthorized"] is False
    # No inference of regulatory outcome even when synthetic schema is filled.
    inputs["S01"] = evidence_record(1)
    inputs["S01"]["source_sha256"] = "b" * 64
    failed = evaluate_science_40(
        exact_key=KEY, evidence=inputs, as_of=CUTOFF,
        trusted_register=dummy_register({KEY: attestations}),
    )
    assert failed["independentlyReviewedAssessments"] == 39
    assert failed["readinessGrade"] == "RELUCTANT"


def test_as_of_gate_blocks_all_science_prior_to_verified_public_phase3():
    output = prepare_deep_analysis(
        exact_key=KEY, phase3_results={}, pdufa_assignment={},
        scientific_evidence={"S01": evidence_record()}, as_of=CUTOFF,
    )
    assert output["status"] == "BLOCKED"
    assert output["science40"] is None
    assert output["science"] is None
    assert output["approvalProbability"] is None
    assert output["tradeAuthorized"] is False


def test_unknown_evidence_keys_not_conflated_with_forty_question_catalog():
    out = evaluate_science_40(exact_key=KEY, evidence={"primary_endpoint": evidence_record()},
                              as_of=CUTOFF)
    assert out["unmappedEvidenceKeys"] == ["primary_endpoint"]
    assert out["submittedSourceObservations"] == 0


def test_malformed_snapshot_or_register_rejected():
    with pytest.raises(ValueError):
        evaluate_science_40(exact_key="", evidence={}, as_of=CUTOFF)
    with pytest.raises(ValueError):
        evaluate_science_40(exact_key=KEY, evidence={}, as_of="2026-13-99")
    with pytest.raises(ValueError):
        evaluate_science_40(exact_key=KEY, evidence=[], as_of=CUTOFF)
    with pytest.raises(ValueError):
        evaluate_science_40(exact_key=KEY, evidence={}, as_of=CUTOFF, trusted_register={})
