from outcome_fda_receipt_certification_workqueue import build_receipt_certification_workqueue


def test_known_receipt_gaps_are_actionable_and_not_certified():
    report = build_receipt_certification_workqueue()
    assert report["status"] == "RESEARCH_ONLY_NOT_CERTIFIED"
    assert report["open_tasks"] == 3
    assert report["certified_review_cycles_added"] == 0
    assert report["prediction_accuracy_estimate"] is None
    assert {x["application_id"] for x in report["tasks"]} == {"BLA:125745", "BLA:125840"}
    for task in report["tasks"]:
        assert task["action_date"]
        assert task["evidence_gap"]["evidence"]["next_evidence"]
        assert task["fda_receipt_verified"] is False
        assert task["model_eligible"] is False


def test_workqueue_has_unique_prioritized_source_backed_tasks():
    report = build_receipt_certification_workqueue()
    tasks = report["tasks"]
    assert len({task["task_id"] for task in tasks}) == len(tasks)
    assert [task["action_date"] for task in tasks] == sorted(task["action_date"] for task in tasks)
    for task in tasks:
        assert task["priority"] == "BLOCKING_CERTIFICATION"
        assert task["next_required_document"]
        assert task["receipt_blocker"]
        assert task["original_fda_action_source"].startswith("https://")
