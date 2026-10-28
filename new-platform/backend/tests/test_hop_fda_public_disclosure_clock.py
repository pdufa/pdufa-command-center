"""Real issuer/FDA public announcements are NOT date-certified review-cycle labels."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from app.hop_fda_public_disclosure_clock import (
    _no_duplicate_json_fields, audit_public_outcome_disclosure_leads,
    load_historical_fda_public_outcome_packet,
    load_public_outcome_disclosure_leads,
)

SOURCE = Path(__file__).resolve().parents[1] / "app" / "research_sources"
CUTOFF = date(2026, 10, 28)
APPROVED = "NDA213973_ORIGINAL_1_20200515_APPROVED"
CRL = "BLA761303_ORIGINAL_1_20240322_CRL"


def fixtures():
    return (
        json.loads((SOURCE / "hop_fda_public_outcome_disclosure_leads.json").read_text()),
        json.loads((SOURCE / "hop_fda_primary_action_letter_samples.json").read_text()),
    )


def audit(disclosures=None, letters=None, as_of=CUTOFF):
    originals, source_letters = fixtures()
    return audit_public_outcome_disclosure_leads(
        originals if disclosures is None else disclosures,
        source_letters if letters is None else letters, as_of=as_of)


def test_two_distinct_real_fda_action_clocks_three_public_source_leads():
    result = audit()
    assert result["status"] == "PUBLISHER_REPORTED_PUBLIC_OUTCOME_LEADS_RESEARCH_ONLY"
    assert result["totalPublicReleaseLeads"] == 3
    assert result["independentlyVerifiedModelLabels"] == 0
    assert result["independentHistoricalBacktests"] == 0
    assert result["approvalProbability"] is None
    assert result["trainingAuthorized"] is False
    assert len(result["blockers"]) >= 6
    assert result["exactUnitPublicMappingVerified"] is False
    assert result["fdaLetterOriginalPublicationDateVerified"] is False
    approved = result["publicReleaseLeadsByLetter"][APPROVED]
    crl = result["publicReleaseLeadsByLetter"][CRL]
    assert approved["signedFdaActionDate"] == "2020-05-15"
    assert approved["earliestDateAmongSelectedReleasePages"] == "2020-05-15"
    assert approved["distinctPublishingOrigins"] == 2
    assert [r["reportedPublishedAt"] for r in approved["releaseObservations"]] == [
        "2020-05-15T15:44:00-04:00", "2020-05-15T16:05:00-04:00",
    ]
    assert crl["signedFdaActionDate"] == "2024-03-22"
    assert crl["earliestDateAmongSelectedReleasePages"] == "2024-03-25"
    assert crl["distinctPublishingOrigins"] == 1
    for case in (approved, crl):
        assert case["earliestActualPublicOutcomeDateIndependentlyVerified"] is None
        assert case["FDAoriginalLetterPublicationDate"] is None
        assert case["exactFDAapplicationOriginalUnitPubliclyMapped"] is False
        assert case["eligibleAsVerifiedHistoricalLabel"] is False
        for release in case["releaseObservations"]:
            assert release["eligibleAsExactReviewCycleLabel"] is False
            assert release["exactApplicationAndOriginalUnitNamed"] is False
            assert release["originalReleaseBytesRetained"] is False
            assert release["reportedPublicationDate"] >= case["signedFdaActionDate"]


def test_cannot_retroactively_represent_2026_research_capture_as_2024_evidence():
    for cutoff in [date(2020, 5, 14), date(2024, 3, 25),
                   date(2025, 12, 31), date(2026, 10, 27)]:
        result = audit(as_of=cutoff)
        assert result["status"] == "SOURCE_REGISTER_NOT_AVAILABLE_AT_AS_OF"
        assert result["totalPublicReleaseLeads"] == 0
        assert result["publicReleaseLeadsByLetter"] == {}
        assert result["independentlyVerifiedModelLabels"] == 0
        assert result["approvalProbability"] is None
        assert result["trainingAuthorized"] is False


@pytest.mark.parametrize("update", [
    {"source_reported_publication_time": "2020-05-14T15:44:00-04:00"},
    {"source_reported_publication_time": "2020-05-15T15:44:00"},
    {"source_reported_publication_time": "2020-05-15T15:44:00Z"},
    {"source_reported_publication_time": "2020-05-15T15:44:00+00:00"},
    {"source_reported_publication_time": "2020-05-15"},
    {"source_observed_on": "2026-10-29"},
    {"source_observed_on": "2020-05-15"},
    {"source_reported_outcome": "COMPLETE_RESPONSE"},
    {"drug": "odronextamab"},
    {"publisher_origin": "REGENERON PHARMACEUTICALS"},
    {"channel": "ISSUER_OWN_SITE"},
    {"source_url": "http://www.prnewswire.com/announcement"},
    {"source_url": "https://www.prnewswire.com@attacker.invalid/announcement"},
    {"source_url": "https://www.prnewswire.com/announcement#fake"},
    {"source_url": "https://www.deciphera.com/announcement"},
    {"source_url": "https://www.prnewswire.com/announcement?return=unsafe"},
    {"indication_scope": ""},
    {"source_claim": "false"},
    {"exact_application_id_named_in_release": True},
    {"exact_original_unit_named_in_release": True},
    {"release_original_bytes_sha256": "b" * 64},
    {"independently_adjudicated_as_cycle_label": True},
    {"related_letter_record_id": "BLA999999_ORIGINAL_1_20240322_CRL"},
])
def test_forged_or_chronologically_impossible_press_metadata_blocks(update):
    sources, _ = fixtures()
    sources["events"][0].update(update)
    with pytest.raises(ValueError):
        audit(disclosures=sources)


def test_duplicate_release_does_not_become_second_independent_source():
    sources, _ = fixtures()
    sources["events"][1]["event_id"] = sources["events"][0]["event_id"]
    with pytest.raises(ValueError, match="Duplicate"):
        audit(disclosures=sources)
    sources, _ = fixtures()
    sources["events"][1]["source_url"] = sources["events"][0]["source_url"]
    with pytest.raises(ValueError, match="Duplicate"):
        audit(disclosures=sources)


def test_crl_multiple_indications_cannot_be_mapped_to_original_2_or_other_application():
    sources, _ = fixtures()
    sources["events"][2]["related_letter_record_id"] = APPROVED
    with pytest.raises(ValueError):
        audit(disclosures=sources)
    sources, _ = fixtures()
    sources["events"][2]["related_letter_record_id"] = "BLA761303_ORIGINAL_2_20240322_CRL"
    with pytest.raises(ValueError, match="unrecognized"):
        audit(disclosures=sources)


def test_fda_letter_relabel_cannot_change_public_source_claim():
    sources, letters = fixtures()
    letters["letters"][1]["action"] = "APPROVED"
    with pytest.raises(ValueError, match="outcome"):
        audit(disclosures=sources, letters=letters)
    sources, letters = fixtures()
    letters["letters"][1]["drug"] = "unrelated drug"
    with pytest.raises(ValueError, match="drug"):
        audit(disclosures=sources, letters=letters)


def test_duplicate_json_keys_are_rejected_in_source_records():
    with pytest.raises(ValueError, match="Duplicate"):
        json.loads('{"schema_version":"x","schema_version":"y"}',
                   object_pairs_hook=_no_duplicate_json_fields)


def test_read_only_combined_packet_keeps_all_real_cases_untrained():
    packet = load_historical_fda_public_outcome_packet(as_of=CUTOFF)
    assert packet["mode"] == "READ_ONLY_HISTORICAL_FDA_ACTION_AND_DISCLOSURE_RESEARCH"
    assert packet["actionLetterResearch"]["sourceLettersInspected"] == 2
    assert packet["publicDisclosureResearch"]["totalPublicReleaseLeads"] == 3
    assert packet["independentModelEligibleCycles"] == 0
    assert packet["independentHistoricalBacktests"] == 0
    assert packet["accuracy"] is None
    assert packet["approvalProbability"] is None
    assert packet["predictionStatus"] == "INSUFFICIENT_EVIDENCE"
    assert packet["trainingAuthorized"] is False
    assert packet["databaseWritten"] is False
    assert packet["spreadsheetWritten"] is False
    assert packet["tradeAuthorized"] is False


