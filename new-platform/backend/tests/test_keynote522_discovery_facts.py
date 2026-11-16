"""Regression checks for the discovery-only KEYNOTE-522 source extract.

These checks protect against accidental changes and post-decision leakage.
They do not independently authenticate source bytes or archival availability.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "docs/data/keynote522_2020_predecision_extracted_facts.json"


def test_discovery_extract_matches_2020_published_abstract():
    record = json.loads(DATA.read_text(encoding="utf-8"))
    source = record["source"]
    facts = record["reported_trial_facts"]
    assert source["doi"] == "10.1056/NEJMoa1910549"
    assert source["pmid"] == "32101663"
    assert source["publication_date"] == "2020-02-26"
    assert (facts["total_randomized"], facts["pembrolizumab_group"], facts["placebo_group"]) == (1174, 784, 390)
    assert facts["pcr_interim_sample"] == 602
    assert (facts["pcr_pembrolizumab_percent"], facts["pcr_placebo_percent"]) == (64.8, 51.2)
    assert facts["pcr_difference_percentage_points"] == 13.6
    assert facts["event_free_survival_95ci"] == [0.43, 0.93]
    assert facts["median_followup_months"] == 15.5


def test_discovery_extract_is_never_a_blind_snapshot():
    record = json.loads(DATA.read_text(encoding="utf-8"))
    assert record["controls"]["status"] == "DISCOVERY_ONLY"
    assert record["controls"]["blind_cohort_eligible"] is False
    assert record["controls"]["accuracy_evaluated"] is False
    assert record["controls"]["approval_prediction"] is None
    assert record["controls"]["scientific_score"] is None
    assert record["source"]["source_bytes_sha256"] is None
    assert record["source"]["point_in_time_snapshot_verified"] is False


def test_later_event_free_survival_findings_not_mixed_into_2020_extract():
    record = json.loads(DATA.read_text(encoding="utf-8"))
    facts = record["reported_trial_facts"]
    assert "event_free_survival_at_36_months" not in facts
    assert "overall_survival_at_60_months" not in facts
    assert "exploratory" in facts["event_free_survival_hazard_ratio_context"].lower()
