"""Independent scientific-review projection: no fabricated grades or phase leakage."""
from app.medical_method_projection import project_trial_history
import pytest

NCT = "NCT06081894"


def history(phase_events=None, review_events=None):
    return {"nct": NCT, "phaseEvents": phase_events or [], "reviewEvents": review_events or []}


def phase(ident="p1", name="PHASE3"):
    return {"phase_event_id": ident, "verified_phase": name}


def review(idx=1, method=1, disposition="SCORED", grade=4, revision=1, phase_id="p1"):
    return {"assessment_index": idx, "method_index": method, "disposition": disposition,
            "grade": grade, "revision": revision, "review_event_id": f"r{revision}",
            "verified_phase": "PHASE3", "phase_event_id": phase_id,
            "reviewer_id": "independent-reviewer", "evidence_reviewed_at": "2026-11-08T12:00:00Z",
            "rationale": "Prespecified endpoint comparison was independently checked",
            "evidence": [{"sourceUrl": "https://clinicaltrials.gov/study/" + NCT,
                          "stageDocumentSha256": "a"*64}]}


def test_unverified_phase_is_800_pending_not_zero_or_rank():
    x = project_trial_history(history(), assessment_index=1)
    assert x["totalPositions"] == 800 and x["counts"]["VERIFY_PHASE"] == 800
    assert x["verifiedPhase"] is None
    assert x["selectedAssessment"]["methods"][0]["grade"] is None
    assert all(a["scoreOutOf100"] is None for a in x["assessments"])
    assert x["fdaPredictions"]["APPROVAL"] == "ABSTAIN"


def test_phase_verified_without_independent_review_has_no_grades():
    x = project_trial_history(history([phase()]))
    assert x["counts"]["UNREVIEWED"] == 800
    assert x["counts"]["SCORED"] == 0
    assert x["assessments"][0]["status"] == "NOT_REVIEWED"


def test_only_current_verifiable_reviews_count_in_provisional_100_point_grade():
    na = review(method=2, disposition="NOT_APPLICABLE", grade=None)
    x = project_trial_history(history([phase()], [review(), na]), assessment_index=1)
    assert x["counts"]["SCORED"] == 1 and x["counts"]["NOT_APPLICABLE"] == 1
    assert x["selectedAssessment"]["scoreOutOf100"] == 80.0
    assert x["selectedAssessment"]["status"] == "PROVISIONAL"
    assert x["selectedAssessment"]["applicableMethods"] == 19
    assert x["selectedAssessment"]["pendingMethods"] == 18
    assert x["selectedAssessment"]["methods"][0]["sourceEvidence"][0]["sourceUrl"].endswith(NCT)
    assert len(x["selectedAssessment"]["methods"]) == 20
    assert x["selectedAssessment"]["methods"][0]["reviewerId"] == "independent-reviewer"
    assert x["historicalReviewEvents"] == 2


def test_retraction_supersedes_but_preserves_append_only_history():
    gone = review(disposition="RETRACTED", grade=None, revision=2)
    x = project_trial_history(history([phase()], [review(), gone]), assessment_index=1)
    assert x["counts"]["RETRACTED"] == 1 and x["counts"]["SCORED"] == 0
    assert x["selectedAssessment"]["scoreOutOf100"] is None
    assert x["historicalReviewEvents"] == 2


def test_new_phase_event_even_with_same_phase_needs_fresh_review():
    x = project_trial_history(history([phase(), phase("p2")], [review()]), assessment_index=1)
    assert x["counts"]["STALE_PHASE"] == 1 and x["counts"]["SCORED"] == 0
    assert x["selectedAssessment"]["methods"][0]["grade"] is None


def test_only_a_full_assessment_of_real_scores_gets_complete_status():
    rows = [review(method=i, grade=5) for i in range(1, 21)]
    x = project_trial_history(history([phase()], rows))
    assert x["assessments"][0]["status"] == "COMPLETE"
    assert x["assessments"][0]["scoreOutOf100"] == 100
    assert x["assessments"][1]["scoreOutOf100"] is None


def test_invalid_assessment_and_malformed_grades_fail_closed():
    with pytest.raises(ValueError, match="1 to 40"):
        project_trial_history(history(), assessment_index=41)
    with pytest.raises(ValueError, match="grade"):
        project_trial_history(history([phase()], [review(grade=9)]))
    with pytest.raises(ValueError, match="revision"):
        project_trial_history(history([phase()], [review(revision=0)]))


def test_history_retains_previous_phase_and_retraction_without_counting_them():
    first = review()
    second = review(disposition="RETRACTED", grade=None, revision=2)
    second["supersedes_event_id"] = first["review_event_id"]
    h = history([phase(), phase("p2")], [first, second])
    h["explicitGapEvents"] = [
        {"assessment_index": 1, "method_index": None, "gap_code": "PROTOCOL_MISSING"},
        {"assessment_index": 1, "method_index": 2, "gap_code": "CONTRADICTORY_EVIDENCE"},
        {"assessment_index": 2, "method_index": 1, "gap_code": "SAP_MISSING"},
    ]
    import copy
    original = copy.deepcopy(h)
    x = project_trial_history(h, assessment_index=1)
    method = x["selectedAssessment"]["methods"][0]
    assert x["counts"]["SCORED"] == 0
    assert method["grade"] is None and method["status"] == "STALE_PHASE"
    assert [r["grade"] for r in method["history"]] == [4, None]
    assert method["history"][1]["supersedes_event_id"] == first["review_event_id"]
    assert len(method["evidenceGaps"]) == 1
    assert len(x["selectedAssessment"]["methods"][1]["evidenceGaps"]) == 2
    assert method["gapResolutionStatus"] == "NOT_ADJUDICATED"
    assert x["recordedGapEvents"] == 3
    assert x["phaseHistory"] == h["phaseEvents"]
    assert h == original


def test_phase_verification_alone_does_not_claim_partial_scientific_review():
    assert project_trial_history(history([phase()]))["status"] == "PHASE_VERIFIED_NOT_REVIEWED"


def test_duplicate_older_revision_cannot_hide_behind_newer_grade():
    with pytest.raises(ValueError, match="Duplicate"):
        project_trial_history(history([phase()], [review(revision=2), review(), review()]))
