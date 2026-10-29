"""Registry structure/safety tests; synthetic changes are not prediction trials."""
from copy import deepcopy
import hashlib
import json

import pytest

from research.historical_decision_registry import (
    ACTION_MANIFEST, DEFAULT_PROGRAM, RECONSTRUCTION_MANIFEST, ROOT,
    SCIENTIFIC_FIELDS, action_label_review, build_historical_registry,
    main, predecision_view, registry_summary, validate_registry,
)


def registry():
    return build_historical_registry()


def case(packet, ticker="TNXP"):
    return next(row for row in packet["records"] if row["ticker"] == ticker)


def feature(observation, *, conflicts=None):
    return {"value": "Synthetic source-reported feature", "source_observation_ids": [observation],
        "assessment_ids": ["S01"], "uncertainty": "Synthetic test claim, not independent scientific review",
        "conflicting_observation_ids": conflicts or [], "independently_reviewed": False}


def test_existing_six_cases_and_26_narratives_import_without_scientific_promotion():
    result = registry()
    assert len(result["records"]) == 6
    assert {row["ticker"] for row in result["records"]} == {"NVAX", "UNCY", "TNXP", "BCRX", "CORT", "VNDA"}
    assert sum(len(row["observations"]) for row in result["records"]) == 26
    for row in result["records"]:
        assert row["company"] is None
        assert set(row["scientific_fields"]) == set(SCIENTIFIC_FIELDS)
        assert all(value is None for value in row["scientific_fields"].values())
        assert row["review_cycle_independently_adjudicated"] is False
        assert row["original_prediction_cutoff"] is None


def test_local_manifest_checksums_do_not_claim_original_fda_source_hashes():
    result = registry()
    for row in result["records"]:
        for artifact in row["source_artifacts"]:
            assert artifact["local_manifest_sha256"] == hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            assert artifact["hash_scope"] == "LOCAL_CURATED_MANIFEST_NOT_ORIGINAL_FDA_SOURCE_BYTES"
        assert row["reported_action"]["source_document_sha256"] is None
        assert row["reported_action"]["decision_at"] is None
        assert row["reported_action"]["source_published_at"] is None


def test_original_label_gate_blocks_all_six_without_manufacturing_timestamps_or_digests():
    result = registry_summary(registry(), program_id=DEFAULT_PROGRAM)
    assert result["historical_records_collected"] == 6
    assert result["source_observations_retained"] == 26
    assert result["independently_verified_decision_cycles"] == 0
    assert result["historically_backtested_cases"] == 0
    assert result["scientific_comparison_features_adjudicated"] == 0
    assert result["prediction_readiness"] == "NOT_READY"
    assert result["prediction_action"] == "ABSTAIN"
    assert result["prediction_probabilities"] is None
    for row in result["records"]:
        review = row["label_review"]
        assert review["accepted_for_research_review"] is False
        assert "invalid document SHA-256" in review["errors"]
        assert "decision and publication timestamps must include timezone" in review["errors"]
        assert review["eligible_for_predictive_training"] is False
        assert review["eligible_for_validated_accuracy"] is False


@pytest.mark.parametrize("ticker,target,action", [
    ("NVAX", "2025-04-01", "2025-05-16"),
    ("UNCY", "2025-06-28", "2025-06-27"),
    ("BCRX", "2025-12-12", "2025-12-11"),
])
def test_corrected_actual_action_dates_remain_separate_from_legacy_pdufa_targets(ticker,target,action):
    row = case(registry(), ticker)
    assert row["pdufa_target_date"] == target
    assert row["reported_action"]["action_date"] == action


def test_cort_corrected_letter_and_uncy_partial_original_are_explicit_not_six_complete_originals():
    result = registry()
    assert case(result, "CORT")["review_cycle_id"] is None
    assert case(result, "UNCY")["review_cycle_id"] is None
    assert "CORRECTED_DOCUMENT_ONLY" in case(result, "CORT")["reported_action"]["document_status"]
    assert "PARTIAL_TEXT" in case(result, "UNCY")["reported_action"]["document_status"]
    assert case(result, "UNCY")["reported_action"]["source_url"].endswith("20250627.pdf")
    assert case(result, "NVAX")["reported_action"]["reported_outcome"] == "PASS"
    assert case(result, "NVAX")["reported_action"]["action_date"] != case(result, "NVAX")["pdufa_target_date"]


def test_missed_target_without_document_or_action_date_remains_unresolved():
    packet = registry(); row = case(packet)
    row["reported_action"].update(reported_outcome="UNRESOLVED", action_date=None,
        source_url=None, decision_document_id=None, curated_outcome_claim="MISSED_TARGET",
        document_status="NO_ATTRIBUTABLE_FDA_ACTION_DOCUMENT",
        source_context="Synthetic missed-target record: no attributable FDA action has been recovered.")
    checked = validate_registry(packet, program_id=DEFAULT_PROGRAM)
    assert case(checked)["reported_action"]["reported_outcome"] == "UNRESOLVED"
    assert action_label_review(row)["accepted_for_research_review"] is False
    view = predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"])
    assert view["prediction_action"] == "ABSTAIN"


@pytest.mark.parametrize("outcome,claim", [("PASS", "APPROVED"), ("CRL", "CRL"), ("EXTENSION", "EXTENSION")])
def test_formal_outcomes_cannot_omit_actual_action_date_or_source(outcome,claim):
    packet = registry(); row = case(packet)
    row["reported_action"].update(reported_outcome=outcome, action_date=None, source_url=None,
                                  curated_outcome_claim=claim)
    with pytest.raises(ValueError): validate_registry(packet, program_id=DEFAULT_PROGRAM)


@pytest.mark.parametrize("url", ["https://fda.gov.evil.test/action.pdf", "https://www.sec.gov/action.pdf"])
def test_formal_fda_action_claim_cannot_point_at_lookalike_or_secondary_document_host(url):
    packet = registry(); row = case(packet)
    row["reported_action"]["source_url"] = url
    with pytest.raises(ValueError, match="official FDA host"):
        validate_registry(packet, program_id=DEFAULT_PROGRAM)


def test_tnxp_linked_trial_identifiers_and_endpoints_are_actual_quarantined_source_leads():
    packet = registry(); row = case(packet)
    leads = {item["trial_name"]: item for item in row["linked_trial_metadata"]}
    assert set(leads) == {"RELIEF", "RALLY", "RESILIENT"}
    assert leads["RELIEF"]["trial_id"] == "F304"
    assert leads["RALLY"]["trial_id"] == "F306"
    assert leads["RESILIENT"]["trial_id"] == "F307"
    assert leads["RESILIENT"]["registry_id"] == "NCT05273749"
    assert leads["RELIEF"]["registry_id"] is leads["RALLY"]["registry_id"] is None
    for trial in leads.values():
        assert trial["reported_primary_endpoint"] == "pain numeric rating score"
        assert trial["reported_primary_analysis_method"] == "MMRM_WITH_MULTIPLE_IMPUTATION"
        assert trial["public_availability_verified"] is False
        assert trial["eligible_as_prediction_feature"] is False
    assert row["scientific_fields"]["clinical_trial_identifiers"] is None
    view = predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"])
    assert view["linked_trial_metadata_status"] == "SOURCE_LEADS_EXCLUDED_ORIGINAL_PUBLIC_AVAILABILITY_UNVERIFIED"
    assert "NCT05273749" not in json.dumps(view)


def test_linked_trial_metadata_cannot_self_certify_prediction_eligibility():
    packet = registry(); row = case(packet)
    row["linked_trial_metadata"][0]["eligible_as_prediction_feature"] = True
    with pytest.raises(ValueError): validate_registry(packet, program_id=DEFAULT_PROGRAM)


def test_unknown_source_availability_remains_unknown_and_withholds_finding():
    packet = registry(); row = case(packet)
    row["observations"][0]["available_on"] = None
    view = predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"])
    assert {item["observation_id"]:item["reason"] for item in view["excluded_observations"]}["TNXP-PREDECISION-RESILIENT"] == "PUBLIC_AVAILABILITY_UNKNOWN"


def test_admitted_narratives_are_17_predecision_reported_observations_not_verified_assessments():
    packet = registry()
    views = [predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"]) for row in packet["records"]]
    assert sum(len(row["source_reported_research_observations"]) for row in views) == 17
    assert sum(len(row["excluded_observations"]) for row in views) == 9
    for view in views:
        assert view["outcome_labels_included"] is False
        assert "reported_action" not in view
        assert view["prediction_action"] == "ABSTAIN"
        assert view["independently_reviewed_assessments"] == 0
        for observation in view["source_reported_research_observations"]:
            assert observation["source_role"] == "PREDECISION_RESEARCH"
            assert observation["available_on"] <= view["evidence_cutoff"]
            assert observation["availability_basis"] == "SEC_FILING_INDEX"
            assert observation["independently_reviewed"] is False


def test_postdecision_and_late_source_narratives_are_not_exposed_as_predecision_features():
    packet = registry()
    view = predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id="NVAX|2025-04-01")
    assert {row["observation_id"]: row["reason"] for row in view["excluded_observations"]} == {
        "NVAX-AFTER-GOAL-STATEMENT": "AFTER_EVIDENCE_CUTOFF", "NVAX-FDA-ACTION": "OUTCOME_ONLY"}
    raw_text = json.dumps(view)
    assert "An April 23 issuer statement" not in raw_text
    assert "FDA original license letter records May 16" not in raw_text


@pytest.mark.parametrize("alteration", ["cross_program", "observation_scope", "duplicate_case", "duplicate_cycle", "duplicate_action",
    "bad_date", "cutoff_after_action", "cutoff_at_target", "wrong_application", "self_review", "original_timestamp",
    "source_hash", "source_bytes", "verified_observation", "unknown_question", "unsafe_source", "unknown_feature",
    "source_role", "future_original_cutoff", "false_negative_company", "outcome_promotion"])
def test_invalid_or_self_certified_registry_records_fail_closed(alteration):
    packet = registry(); row = case(packet)
    if alteration == "cross_program": row["program_id"] = "OTHER_PROGRAM"
    elif alteration == "observation_scope": row["observations"][0]["program_id"] = "OTHER_PROGRAM"
    elif alteration == "duplicate_case": packet["records"].append(deepcopy(row))
    elif alteration in ("duplicate_cycle", "duplicate_action"):
        duplicate = deepcopy(row); duplicate["record_id"] = "SYNTHETIC-ALIAS"
        if alteration == "duplicate_action": duplicate["review_cycle_id"] = "Orig2s000"
        packet["records"].append(duplicate)
    elif alteration == "bad_date": row["pdufa_target_date"] = "2025-02-30"
    elif alteration == "cutoff_after_action": row["evidence_cutoff"] = "2025-08-15"; row["pdufa_target_date"] = "2025-08-16"
    elif alteration == "cutoff_at_target": row["evidence_cutoff"] = row["pdufa_target_date"]
    elif alteration == "wrong_application": row["application_id"] = "219428"
    elif alteration == "self_review": row["review_cycle_independently_adjudicated"] = True
    elif alteration == "original_timestamp": row["reported_action"]["decision_at"] = row["reported_action"]["action_date"] + "T00:00:00Z"
    elif alteration == "source_hash": row["reported_action"]["source_document_sha256"] = "a" * 64
    elif alteration == "source_bytes": row["observations"][0]["source_bytes_retained"] = True
    elif alteration == "verified_observation": row["observations"][0]["independently_reviewed"] = True
    elif alteration == "unknown_question": row["observations"][0]["assessment_ids"] = ["S41"]
    elif alteration == "unsafe_source": row["observations"][0]["source_url"] = "http://www.sec.gov/unsafe.htm"
    elif alteration == "unknown_feature": row["scientific_fields"]["invented_prediction"] = "PASS"
    elif alteration == "source_role": row["observations"][0]["source_role"] = "FDA_VALIDATED"
    elif alteration == "future_original_cutoff": row["original_prediction_cutoff"] = "2025-08-14"
    elif alteration == "false_negative_company": row["company"] = False
    else: row["reported_action"]["reported_outcome"] = "EXTENSION"
    with pytest.raises(ValueError): validate_registry(packet, program_id=DEFAULT_PROGRAM)


def test_program_namespace_is_explicit_and_cannot_read_a_different_program_packet():
    packet = build_historical_registry(program_id="RESEARCH_ALPHA")
    assert all(row["program_id"] == "RESEARCH_ALPHA" for row in packet["records"])
    with pytest.raises(ValueError, match="cross-program"):
        predecision_view(packet, program_id="RESEARCH_BETA", record_id="TNXP|2025-08-15")
    with pytest.raises(ValueError, match="not available"):
        predecision_view(packet, program_id="RESEARCH_ALPHA", record_id="NONEXISTENT")


def test_source_bound_feature_is_reported_only_and_missing_does_not_mean_negative():
    packet = registry(); row = case(packet)
    row["scientific_fields"]["efficacy_findings"] = feature("TNXP-PREDECISION-RESILIENT")
    before = deepcopy(packet)
    view = predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"])
    assert view["scientific_fields"]["efficacy_findings"]["independently_reviewed"] is False
    assert view["scientific_field_statuses"]["efficacy_findings"] == "SOURCE_REPORTED_NOT_INDEPENDENTLY_REVIEWED"
    assert view["scientific_fields"]["manufacturing_findings"] is None
    assert view["scientific_field_statuses"]["manufacturing_findings"] == "MISSING"
    assert packet == before


def test_outcome_only_feature_is_masked_even_if_caller_claims_it_is_a_scientific_feature():
    packet = registry(); row = case(packet)
    row["scientific_fields"]["efficacy_findings"] = feature("TNXP-FDA-ACTION")
    view = predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"])
    assert view["scientific_fields"]["efficacy_findings"] is None
    assert view["scientific_field_statuses"]["efficacy_findings"] == "SOURCE_NOT_AVAILABLE_AT_CUTOFF"
    assert "Synthetic source-reported feature" not in json.dumps(view)


def test_timely_conflicting_evidence_withholds_feature_and_requires_review():
    packet = registry(); row = case(packet)
    row["scientific_fields"]["efficacy_findings"] = feature("TNXP-PREDECISION-RESILIENT", conflicts=["TNXP-10K-TRIAL-CONSISTENCY"])
    view = predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"])
    assert view["scientific_fields"]["efficacy_findings"] is None
    assert view["scientific_field_statuses"]["efficacy_findings"] == "CONFLICTED_REQUIRES_SCIENTIFIC_REVIEW"


def test_future_conflict_does_not_leak_or_retroactively_poison_predecision_feature():
    packet = registry(); row = case(packet)
    row["scientific_fields"]["efficacy_findings"] = feature("TNXP-PREDECISION-RESILIENT", conflicts=["TNXP-FDA-ACTION"])
    view = predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"])
    assert view["scientific_fields"]["efficacy_findings"]["conflicting_observation_ids"] == []
    assert view["scientific_field_statuses"]["efficacy_findings"] == "SOURCE_REPORTED_NOT_INDEPENDENTLY_REVIEWED"


@pytest.mark.parametrize("change", ["foreign_source", "self_verified", "missing_uncertainty", "no_sources", "numeric_result"])
def test_feature_provenance_and_independence_cannot_be_bypassed(change):
    packet = registry(); row = case(packet); value = feature("TNXP-PREDECISION-RESILIENT")
    if change == "foreign_source": value["source_observation_ids"] = ["CORT-PREDECISION-GRACE"]
    elif change == "self_verified": value["independently_reviewed"] = True
    elif change == "missing_uncertainty": value["uncertainty"] = ""
    elif change == "no_sources": value["source_observation_ids"] = []
    else: value["value"] = 0.99
    row["scientific_fields"]["efficacy_findings"] = value
    with pytest.raises(ValueError): validate_registry(packet, program_id=DEFAULT_PROGRAM)


def test_deterministic_cli_snapshot_can_be_checked_against_actual_source_artifacts(tmp_path,capsys):
    snapshot = tmp_path / "historical-registry.json"
    assert main(["--output", str(snapshot)]) == 0
    assert main(["--output", str(snapshot), "--check"]) == 0
    result = json.loads(snapshot.read_text())
    assert result == registry()
    snapshot.write_text("{}")
    with pytest.raises(SystemExit) as failure:
        main(["--output", str(snapshot), "--check"])
    assert failure.value.code == 1
    assert "ABSTAIN" in capsys.readouterr().out


def test_importer_and_predecision_views_leave_original_source_files_unchanged():
    paths = [ACTION_MANIFEST, RECONSTRUCTION_MANIFEST, ROOT / "data/prediction_engine_history.csv"]
    before = {path: path.read_bytes() for path in paths}
    packet = registry()
    for row in packet["records"]:
        predecision_view(packet, program_id=DEFAULT_PROGRAM, record_id=row["record_id"])
        action_label_review(row)
    assert {path: path.read_bytes() for path in paths} == before
