"""Integration with real research packets; no claim of validated FDA accuracy."""
from collections import Counter
from datetime import date
import json
from pathlib import Path

import pytest

from research.fda_verification_queue import build_verification_queue

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data/prediction_engine_history.csv"
ACTIONS = ROOT / "research/evidence/2025_holdout_fda_action_evidence.json"
PACKET = ROOT / "research/evidence/2025_holdout_predecision_reconstruction.json"


def audited():
    return build_verification_queue(HISTORY,ACTIONS,reconstruction_manifest=PACKET,as_of=date(2026,10,28))


def test_saved_six_case_research_packet_joins_history_without_promoting_any_prediction():
    unchanged = HISTORY.read_bytes()
    queue = audited()
    summary = queue["predecision_reconstruction_summary"]
    assert queue["total_records"] == summary["history_records"] == 146
    assert summary["priority_cases_analyzed"] == 6
    assert summary["validated_cases"] == summary["eligible_for_validation"] == 0
    assert summary["science_framework"]["layer_count"] == 8
    assert all(value is None for value in summary["metrics"].values())
    cases = [row["predecision_reconstruction"] for row in queue["queue"] if "predecision_reconstruction" in row]
    assert len(cases) == 6
    assert sum(case["predecision_research_candidate_count"] for case in cases) == 13
    classifications = Counter(source["classification"] for case in cases for source in case["source_classification"])
    assert classifications == {"PREDECISION_RESEARCH_CANDIDATE":13,"EXCLUDED_OUTCOME_ONLY":7,
                               "EXCLUDED_AFTER_RECONSTRUCTION_CUTOFF":1,"QUARANTINED_PRINTED_DATE_ONLY":1}
    for case in cases:
        assert case["original_prediction_cutoff"] is None
        assert case["frozen_prediction_source_count"] == case["independently_certified_assessments"] == 0
        assert len(case["science_worklist"]) == 40 and len(case["depth_worklist"]) == 20
        assert all(row["status"] == "NOT_CERTIFIED" for row in case["science_worklist"]+case["depth_worklist"])
        assert set(row["layer"] for row in case["science_worklist"]) == set(range(1,9))
        assert case["main"]["prediction_model_version"] is None
        assert case["main"]["evidence_completeness"]["status"] == "INCOMPLETE"
        assert case["main"]["status"] == case["outcome"]["status"] == "INSUFFICIENT_EVIDENCE"
        assert case["main"]["pass_probability"] is None and case["main"]["fail_probability"] is None
        assert not case["eligible_for_validation"] and not case["model_eligible"]
    assert HISTORY.read_bytes() == unchanged


def test_goal_action_discrepancies_and_outcome_documents_cannot_supply_predecision_features():
    cases = {row["ticker"]:row["predecision_reconstruction"] for row in audited()["queue"]
             if "predecision_reconstruction" in row}
    assert cases["NVAX"]["reconstruction_cutoff"] == "2025-03-31"
    assert cases["UNCY"]["reconstruction_cutoff"] == "2025-06-26"
    assert cases["BCRX"]["reconstruction_cutoff"] == "2025-12-10"
    assert sum(case["legacy_goal_differs_from_action"] for case in cases.values()) == 3
    for ticker,source_id in (("CORT","CORT-CORRECTED-CRL"),("UNCY","UNCY-LATER-CYCLE"),
                             ("VNDA","VNDA-FDA-ORIGINAL-ACTION")):
        case = cases[ticker]
        observation = next(row for row in case["source_classification"] if row["source_id"]==source_id)
        assert observation["classification"] == "EXCLUDED_OUTCOME_ONLY"
        assert all(source_id not in row["source_ids"] for row in case["science_worklist"])


def test_action_evidence_preserves_original_versus_corrected_and_partial_document_status():
    data=json.loads(ACTIONS.read_text())
    assert data["action_evidence_verified_count"] == 6
    assert data["primary_fda_action_document_verified_count"] == 4
    assert data["original_fda_action_document_partial_text_count"] == 1
    cases={row["ticker"]:row for row in data["records"]}
    assert "220152Orig1s000Approv.pdf" in cases["VNDA"]["fda_document_url"]
    assert "PARTIAL_TEXT" in cases["UNCY"]["original_action_document_status"]
    assert "CORRECTED_DOCUMENT_ONLY" in cases["CORT"]["original_action_document_status"]
    assert all(row["eligible_for_training"] is False for row in data["records"])


def test_duplicate_action_event_evidence_is_not_silently_overwritten(tmp_path):
    data=json.loads(ACTIONS.read_text())
    data["records"].append(dict(data["records"][0]))
    path=tmp_path/"duplicate.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="duplicate FDA action evidence"):
        build_verification_queue(HISTORY,path)


def test_duplicate_json_object_key_is_not_silently_overwritten(tmp_path):
    path=tmp_path/"duplicate-key.json"
    path.write_text('{"records":[],"records":[]}')
    with pytest.raises(ValueError,match="duplicate JSON field"):
        build_verification_queue(HISTORY,path)


def test_false_snapshot_does_not_fall_back_to_todays_date():
    with pytest.raises(ValueError,match="as_of must be a date"):
        build_verification_queue(HISTORY,ACTIONS,reconstruction_manifest=PACKET,as_of=False)


def test_changed_uncy_action_cannot_admit_actual_action_day_as_predecision(tmp_path):
    data=json.loads(PACKET.read_text())
    case=next(row for row in data["cases"] if row["ticker"]=="UNCY")
    case["action_date"]="2025-06-28"
    case["reconstruction_cutoff"]="2025-06-27"
    case["observations"][0]["available_on"]="2025-06-27"
    path=tmp_path/"shifted-action.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="action date conflicts"):
        build_verification_queue(HISTORY,ACTIONS,reconstruction_manifest=path,as_of=date(2026,10,28))


def test_action_manifest_application_mismatch_blocks_reconstruction(tmp_path):
    data=json.loads(ACTIONS.read_text())
    data["records"][0]["application_id"]="NDA 000001"
    path=tmp_path/"wrong-application.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match="application conflicts"):
        build_verification_queue(HISTORY,path,reconstruction_manifest=PACKET,as_of=date(2026,10,28))


def test_reconstruction_cannot_skip_its_action_evidence_manifest():
    with pytest.raises(ValueError,match="linked FDA action manifest"):
        build_verification_queue(HISTORY,reconstruction_manifest=PACKET,as_of=date(2026,10,28))


def test_recovered_archive_identity_does_not_become_a_predecision_prediction_freeze():
    # Consistency of the committed audit, not a repeat audit of private archive bytes.
    archive=json.loads((ACTIONS.parent/"2025_holdout_archive_provenance_audit.json").read_text())
    packet=json.loads(PACKET.read_text())
    keys={case["event_key"] for case in packet["cases"]}
    assert archive["matched_priority_cases"] == len(keys) == 6
    assert {key for row in archive["prediction_archives"] for key in row["matched_priority_event_keys"]} == keys
    assert archive["validated_cases"] == 0 and archive["accuracy"] is None
    assert archive["original_2025_prediction_timestamps_verified"] is False
    bindings={key:row for row in archive["prediction_archives"] for key in row["matched_priority_event_keys"]}
    for case in packet["cases"]:
        provenance=case["prediction_provenance"]
        binding=bindings[case["event_key"]]
        assert provenance["model_hash"] == binding["model_sha256"] == archive["model_spec"]["computed_sha256"]
        assert provenance["prediction_lock_created_at"] == binding["archive_lock_created_at"]
        assert provenance["prediction_generated_at"] is None
        assert provenance["model_training_end"] is None
    for row in audited()["queue"]:
        if "predecision_reconstruction" in row:
            blockers=row["predecision_reconstruction"]["blockers"]
            assert "model_frozen_at_after_reconstruction_cutoff" in blockers
            assert "prediction_lock_created_at_after_reconstruction_cutoff" in blockers
