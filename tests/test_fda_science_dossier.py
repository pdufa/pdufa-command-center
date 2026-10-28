"""Real reconstruction dossier integration; no test-derived accuracy claims."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from research.fda_science_dossier import build_scientific_dossier
from research.fda_verification_queue import build_verification_queue

ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT/"new-platform/backend/app/science_40_question_catalog.json").read_text())


@pytest.fixture
def cases():
    queue = build_verification_queue(ROOT/"data/prediction_engine_history.csv",
        ROOT/"research/evidence/2025_holdout_fda_action_evidence.json",
        reconstruction_manifest=ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json",
        as_of=date(2026,10,28))
    return {row["ticker"]:row["predecision_reconstruction"] for row in queue["queue"]
            if "predecision_reconstruction" in row}


def flat(dossier):
    return [q for layer in dossier["layers"] for q in layer["questions"]]


def test_all_six_source_matrices_preserve_existing_framework_and_no_certification(cases):
    for case in cases.values():
        unchanged = deepcopy(case)
        dossier = build_scientific_dossier(case,CATALOG)
        assert case == unchanged
        questions=flat(dossier)
        assert [q["question_id"] for q in questions] == [f"S{i:02d}" for i in range(1,41)]
        assert len(dossier["layers"]) == 8
        assert all(len(layer["questions"]) == 5 for layer in dossier["layers"])
        assert dossier["summary"]["independently_completed_assessments"] == 0
        assert dossier["summary"]["eligible_frozen_features"] == 0
        assert dossier["summary"]["scientific_score"] is None
        assert dossier["summary"]["approval_probability"] is None
        assert dossier["historical_comparison"]["model_eligible_comparisons"] == 0
        assert dossier["depth_framework"]["required_levels"] == list(range(1,21))
        assert len(dossier["depth_framework"]["levels"]) == 20
        assert dossier["depth_framework"]["independently_reviewed_levels"] == []
        assert all(q["assessment_status"] == "NOT_INDEPENDENTLY_ASSESSED" for q in questions)
        assert all(q["scientific_conclusion"] is None for q in questions)


def test_only_audited_precutoff_research_observations_enter_questions(cases):
    for case in cases.values():
        dossier=build_scientific_dossier(case,CATALOG)
        allowed={s["source_id"] for s in case["source_classification"]
                 if s["classification"] == "PREDECISION_RESEARCH_CANDIDATE"}
        rejected={s["source_id"] for s in case["source_classification"]
                  if s["classification"] != "PREDECISION_RESEARCH_CANDIDATE"}
        observed={s["source_id"] for q in flat(dossier) for s in q["observations"]}
        assert observed <= allowed and not observed & rejected
        excluded={s["source_id"] for q in flat(dossier) for s in q["excluded_or_quarantined_sources"]}
        assert excluded == rejected


def test_precutoff_cmc_weakness_and_trial_counterevidence_remain_source_bound(cases):
    uncy=build_scientific_dossier(cases["UNCY"],CATALOG)
    cmc=next(layer for layer in uncy["layers"] if layer["layer_name"] == "Manufacturing and quality")
    assert any("deficien" in obs["source_reported_finding"].lower()
        for q in cmc["questions"] for obs in q["observations"])
    cort=build_scientific_dossier(cases["CORT"],CATALOG)
    findings=[obs["source_reported_finding"] for q in flat(cort) for obs in q["observations"]]
    assert any("GRADIENT" in f and "between" in f for f in findings)
    assert cort["counterevidence_review"]["opposing_context"] == cases["CORT"]["opposing_factors"]


def test_missing_sources_are_unknown_and_do_not_create_a_fail_assessment(cases):
    case=deepcopy(cases["NVAX"])
    case["source_classification"]=[]
    dossier=build_scientific_dossier(case,CATALOG)
    assert all(q["research_status"] == "MISSING_PREDECISION_SOURCE" for q in flat(dossier))
    assert dossier["summary"]["questions_with_research_observations"] == 0
    assert all(q["scientific_conclusion"] is None for q in flat(dossier))


def test_numeric_depth_boundaries_are_not_invented_semantic_definitions(cases):
    depth=build_scientific_dossier(cases["VNDA"],CATALOG)["depth_framework"]
    assert depth["semantic_level_definitions_status"] == "NOT_DEFINED_IN_EXISTING_CATALOG"
    assert all(row["independently_reviewed_question_ids"] == [] for row in depth["levels"])


@pytest.mark.parametrize("field,value",[("independently_reviewed",True),("eligible_for_frozen_prediction",True)])
def test_submitted_certification_cannot_promote_scientific_readiness(cases,field,value):
    case=deepcopy(cases["TNXP"])
    case["source_classification"][0][field]=value
    with pytest.raises(ValueError,match="certification or frozen"):
        build_scientific_dossier(case,CATALOG)


def test_an_outcome_cannot_enter_research_observations_even_if_classification_is_spoofed(cases):
    case=deepcopy(cases["NVAX"])
    outcome=next(s for s in case["source_classification"] if s["source_role"] == "OUTCOME_ONLY")
    outcome["classification"]="PREDECISION_RESEARCH_CANDIDATE"
    with pytest.raises(ValueError,match="outcome evidence"):
        build_scientific_dossier(case,CATALOG)


def test_catalog_contract_drift_requires_review(cases):
    catalog=deepcopy(CATALOG)
    catalog["questions"][0]["id"]="S40"
    with pytest.raises(ValueError,match="identity"):
        build_scientific_dossier(cases["TNXP"],catalog)


def test_duplicate_source_ids_cannot_inflate_observation_counts(cases):
    case=deepcopy(cases["NVAX"])
    case["source_classification"].append(case["source_classification"][0])
    with pytest.raises(ValueError,match="unique"):
        build_scientific_dossier(case,CATALOG)


@pytest.mark.parametrize("field,value",[("available_on","2026-01-01"),
    ("availability_basis","PRINTED_DATE_ONLY"),("availability_source_url",None)])
def test_candidate_label_alone_does_not_replace_predecision_availability(cases,field,value):
    case=deepcopy(cases["TNXP"])
    candidate=next(s for s in case["source_classification"] if s["classification"] == "PREDECISION_RESEARCH_CANDIDATE")
    candidate[field]=value
    with pytest.raises(ValueError,match="pre-cutoff availability"):
        build_scientific_dossier(case,CATALOG)
