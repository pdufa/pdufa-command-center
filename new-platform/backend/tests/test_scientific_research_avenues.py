"""Unsearched source leads must not be counted as reviewed trial evidence."""
from app.scientific_research_avenues import candidate_research_avenues
from test_scientific_levels_nine_to_twenty import NCT, intake
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from app.scientific_advanced_research_queue import build_advanced_research_queue


def test_exact_trial_public_routes_and_no_search_success_claims():
    avenues = candidate_research_avenues(NCT)
    assert set(avenues) == {str(n) for n in range(9, 21)}
    assert avenues["9"]["sourceLeads"][0]["url"] == (
        "https://clinicaltrials.gov/study/" + NCT)
    assert avenues["12"]["sourceLeads"][1]["url"] == (
        "https://pubmed.ncbi.nlm.nih.gov/?term=" + NCT)
    assert all(a["status"] == "UNSEARCHED_CANDIDATE_LEADS" and
               a["reviewResult"] is None and a["fdaPrediction"] == "ABSTAIN"
               for a in avenues.values())


def test_fda_application_routes_are_never_inferred_from_nct():
    avenues = candidate_research_avenues(NCT)
    for number in (13, 14, 15, 16, 20):
        item = avenues[str(number)]
        assert len(item["sourceLeads"]) == 1
        assert item["sourceLeads"][0]["url"] == "https://www.fda.gov/drugsatfda"
        assert "Exact application" in item["identityGate"]
        assert "approval" not in item.get("reviewResult", "").__str__()


def test_internal_freeze_lead_has_no_fake_public_link():
    item = candidate_research_avenues(NCT)["19"]
    assert item["sourceLeads"] == []
    assert item["reviewResult"] is None
    assert "owner-controlled" in item["identityGate"]


def test_unverified_trial_does_not_generate_search_urls():
    for invalid in ("NCT0000000X", "NCT123", "", None, "NCT00000001?x=y"):
        assert candidate_research_avenues(invalid) == {}


def test_built_work_queue_leads_remain_unsearched_and_not_scientific_scores():
    entry = intake()
    inventory = assess_levels_nine_to_twenty(entry, trial_id=NCT)
    queue = build_advanced_research_queue(entry, inventory, trial_id=NCT)
    assert set(queue["researchAvenues"]) == {str(n) for n in range(9, 21)}
    assert queue["unresolvedCriteria"] == 60
    assert queue["reviewedCriteria"] == 0
    assert queue["score"] is None
    assert queue["researchAvenues"]["13"]["reviewResult"] is None
