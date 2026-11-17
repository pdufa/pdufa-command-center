"""Synthetic queue test: no false completion or missing-source judgement."""
from datetime import date
from copy import deepcopy
from app.scientific_advanced_research_queue import build_advanced_research_queue
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from app.candidate_assessments import score_candidate, compact, fingerprint
from test_scientific_levels_nine_to_twenty import NCT, intake, reviewed_record


def build(phase="PHASE3", status="COMPLETED", evidence=None):
    level_one = intake(phase, status)
    levels = assess_levels_nine_to_twenty(level_one, trial_id=NCT, evidence=evidence)
    return build_advanced_research_queue(level_one, levels, trial_id=NCT)


def test_exact_nct_unreviewed_work_queue_all_twelve_levels():
    result = build()
    assert result["status"] == "RESEARCH_QUEUE_READY"
    assert len(result["tasks"]) == 60
    assert result["reviewedCriteria"] == 0
    assert result["tasks"][0]["id"] == NCT + ":L09:benefitEvidence"
    assert result["tasks"][0]["action"] == "COLLECT_AND_REVIEW_SOURCE"
    assert result["tasks"][0]["priorityOrder"] == 1
    assert result["tasks"][-1]["priorityOrder"] == 60
    assert all(t["id"].startswith(NCT + ":L") for t in result["tasks"])
    assert result["score"] is None
    assert result["fdaPrediction"] == "ABSTAIN"
    assert result["sourceReviewCompletion"] == "NOT_ESTABLISHED"


def test_rejected_source_in_first_workflow_class_without_claiming_urgency():
    record = reviewed_record()
    record["sourceVerified"] = False
    result = build(evidence={"20.officialActionAndDate": record})
    assert result["tasks"][0]["id"] == NCT + ":L20:officialActionAndDate"
    assert result["tasks"][0]["action"] == "RESOLVE_REJECTED_SOURCE"
    assert result["tasks"][0]["rejectionReason"] == "SOURCE_NOT_VERIFIED"
    assert result["score"] is None


def test_unpublished_and_unverified_unpublished_are_not_merged():
    missing = {"nctId": NCT, "availability": "NOT_PUBLIC",
               "checkedAt": "2026-01-16",
               "source": "https://clinicaltrials.gov/study/" + NCT,
               "searchRationale": "Synthetic checked index; no publication identified."}
    wrong = {**missing, "checkedAt": "2026-03-01"}
    result = build(evidence={"11.remainingUnmetNeed": missing,
                             "12.independentStudyIdentity": wrong})
    tasks = {t["id"]: t for t in result["tasks"]}
    assert tasks[NCT + ":L11:remainingUnmetNeed"]["action"] == "RECHECK_REPORTED_UNPUBLISHED"
    assert tasks[NCT + ":L12:independentStudyIdentity"]["action"] == "VERIFY_PUBLICATION_CLAIM"


def test_early_phase_tasks_defer_not_yet_expected_criteria():
    result = build(phase="PHASE1", status="RECRUITING")
    ids = {x["id"] for x in result["deferred"]}
    assert NCT + ":L13:acceptedFiling" in ids
    assert NCT + ":L16:inspectionEvidence" in ids
    assert NCT + ":L20:officialActionAndDate" in ids
    assert NCT + ":L13:acceptedFiling" not in {t["id"] for t in result["tasks"]}
    assert result["status"] == "RESEARCH_QUEUE_READY"


def test_wrong_phase_wrong_trial_or_nonabstaining_level_blocks_all_tasks():
    level_one = intake()
    levels = assess_levels_nine_to_twenty(level_one, trial_id=NCT)
    for intake_change, level_change, trial in (
        ({"phase": "NOT_REAL"}, None, NCT),
        (None, {"score": 99}, NCT),
        (None, {"fdaPrediction": "APPROVED"}, NCT),
        (None, None, "NCT00000002"),
    ):
        candidate_intake = {**level_one, **(intake_change or {})}
        candidate_levels = deepcopy(levels)
        if level_change:
            candidate_levels["15"].update(level_change)
        result = build_advanced_research_queue(
            candidate_intake, candidate_levels, trial_id=trial)
        assert result["status"] == "BLOCKED_UNVERIFIED_INTAKE"
        assert result["tasks"] == []


def test_candidate_compact_and_version_history_preserve_queue():
    registry = {"nct_id": NCT, "phases": ["PHASE3"], "status": "COMPLETED",
                "last_update_posted": {"date": "2026-01-15"}}
    row = {"id": "TRIAL|" + NCT, "nctId": NCT}
    original = score_candidate(row, registry, registry_checked="2026-01-20",
                               today=date(2026, 2, 1))
    assert original["advancedEvidenceQueue"]["status"] == "RESEARCH_QUEUE_READY"
    assert compact(original)["advancedEvidenceQueue"] == original["advancedEvidenceQueue"]
    edited = deepcopy(original)
    edited["advancedEvidenceQueue"]["tasks"][0]["state"] = "REJECTED_EVIDENCE"
    assert fingerprint(original) != fingerprint(edited)
    assert original["advancedEvidenceQueue"]["tasks"][0]["state"] == "NOT_ASSESSED"
