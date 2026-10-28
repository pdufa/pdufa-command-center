"""FDA original action letters: real-source examples, never training clearance."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from app.hop_primary_action_letter_samples import (
    audit_primary_letter_samples,
    load_primary_letter_samples,
)

SOURCE = (Path(__file__).resolve().parents[1] / "app" / "research_sources"
          / "hop_fda_primary_action_letter_samples.json")
CUTOFF = date(2026, 10, 28)


def source():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_two_real_fda_letters_opposite_actions_but_zero_model_eligible_cases():
    r = load_primary_letter_samples(as_of=CUTOFF)
    assert r["status"] == "REAL_FDA_LETTER_SAMPLES_RESEARCH_ONLY"
    assert r["sourceLettersInspected"] == 2
    assert r["outcomeObservations"] == {"APPROVED": 1, "COMPLETE_RESPONSE": 1}
    assert r["selectionBasis"] == "PURPOSIVE_NONREPRESENTATIVE"
    assert r["independentlyAdjudicatedModelCycles"] == 0
    assert r["independentlyBacktestedCases"] == 0
    assert r["approvalProbability"] is None
    assert r["trainingAuthorized"] is False
    assert len(r["blockedReasons"]) >= 7
    assert r["records"][0]["applicationId"] == "NDA213973"
    assert r["records"][0]["fdaActionDateInSignedLetter"] == "2020-05-15"
    assert r["records"][1]["applicationId"] == "BLA761303"
    assert r["records"][1]["submissionUnit"] == "ORIGINAL_1"
    assert r["records"][1]["fdaActionDateInSignedLetter"] == "2024-03-22"
    for row in r["records"]:
        assert row["pdfBytesRetained"] is False
        assert row["originalDocumentSha256"] is None
        assert row["reviewCycle"] is None
        assert row["outcomePublicAsOf"] is None
        assert row["modelEligible"] is False
        assert row["verifiedPredecisionFeatures"] is False
        assert row["sourceStatus"] == "SIGNED_FDA_LETTER_INSPECTED_RESEARCH_ONLY"


def test_a_retrospective_cutoff_cannot_see_later_research_capture():
    r = load_primary_letter_samples(as_of=date(2024, 12, 31))
    assert r["status"] == "NOT_AVAILABLE_AT_AS_OF"
    assert r["sourceLettersInspected"] == 0
    assert r["outcomeObservations"] == {}
    assert r["records"] == []
    assert r["trainingAuthorized"] is False


@pytest.mark.parametrize("mutator", [
    lambda r: r["letters"].pop(),
    lambda r: r["letters"][0].update(action="COMPLETE_RESPONSE"),
    lambda r: r["letters"][0].update(fda_action_date="2020-05-16"),
    lambda r: r["letters"][0].update(signature_date_observed="2020-05-14"),
    lambda r: r["letters"][0].update(document_action_heading="COMPLETE RESPONSE"),
    lambda r: r["letters"][1].update(submission_unit="ORIGINAL_2"),
    lambda r: r["letters"][1].update(submission_unit_basis="UNVERIFIED"),
    lambda r: r["letters"][1].update(review_cycle=1),
    lambda r: r["letters"][1].update(original_publication_date_verified="2024-03-22"),
    lambda r: r["letters"][1].update(first_known_label_public_as_of="2024-03-22"),
    lambda r: r["letters"][0].update(frozen_predecision_features_as_of="2020-05-14"),
    lambda r: r["letters"][0].update(source_document_bytes_sha256="a" * 64),
    lambda r: r["letters"][0].update(source_document_bytes_retained=True),
    lambda r: r["letters"][0].update(application_cycle_independently_adjudicated=True),
    lambda r: r["letters"][1].update(original_action_independently_adjudicated=True),
    lambda r: r["letters"][1].update(eligible_for_training=True),
    lambda r: r["letters"][0].update(pdufa_target_history_verified=True),
    lambda r: r["letters"][1].update(original_document_url="https://fake.fda.gov/crl/test.pdf"),
    lambda r: r["letters"][1].update(original_document_url="https://download.open.fda.gov@evil.com/test.pdf"),
    lambda r: r["letters"][1].update(original_document_url="https://download.open.fda.gov/a.pdf#secret"),
    lambda r: r["letters"][1].update(inspected_pages=[0, 0]),
    lambda r: r["letters"][1].update(inspected_pages=[1, 6]),
    lambda r: r["letters"][1].update(document_reference_id="wrong"),
    lambda r: r["letters"][0].update(record_id="NDA999999_ORIGINAL_1_20200515_APPROVED"),
    lambda r: r["letters"][1].update(source_observation=""),
    lambda r: r["letters"][1].update(indication="lymphoma", limitation="Missing evidence"),
])
def test_invalid_or_falsely_promoted_real_source_metadata_fails_closed(mutator):
    data = source()
    mutator(data)
    with pytest.raises(ValueError):
        audit_primary_letter_samples(data, as_of=CUTOFF)


def test_duplicate_source_and_application_date_claims_rejected():
    data = source()
    data["letters"][1]["document_reference_id"] = data["letters"][0]["document_reference_id"]
    with pytest.raises(ValueError, match="Duplicated"):
        audit_primary_letter_samples(data, as_of=CUTOFF)
    data = source()
    data["letters"][1] = deepcopy(data["letters"][0])
    with pytest.raises(ValueError, match="Duplicated"):
        audit_primary_letter_samples(data, as_of=CUTOFF)


def test_crl_is_specific_nonapproval_not_permanent_rejection():
    r = load_primary_letter_samples(as_of=CUTOFF)
    crl = next(x for x in r["records"] if x["actionObservedInFDAHostedLetter"] == "COMPLETE_RESPONSE")
    assert crl["applicationId"] == "BLA761303"
    assert crl["submissionUnit"] == "ORIGINAL_1"
    assert "REJECTED" not in r["outcomeObservations"]
    assert crl["outcomePublicAsOf"] is None
    assert crl["modelEligible"] is False


def test_cannot_use_a_current_source_manifest_as_retrospective_training_evidence():
    for cutoff in [date(2020, 5, 14), date(2024, 3, 21),
                   date(2025, 12, 31), date(2026, 10, 27)]:
        x = load_primary_letter_samples(as_of=cutoff)
        assert x["trainingAuthorized"] is False
        assert x["sourceLettersInspected"] == 0


def test_unexpected_schema_and_missing_provenance_rejected():
    data = source()
    data["schema_version"] = "unreviewed"
    with pytest.raises(ValueError, match="schema"):
        audit_primary_letter_samples(data, as_of=CUTOFF)
    data = source()
    data["collection_policy"] = "COMPLETE_REPRESENTATIVE_COHORT"
    with pytest.raises(ValueError, match="cohort"):
        audit_primary_letter_samples(data, as_of=CUTOFF)
    data = source()
    data["letters"][0].pop("original_document_url")
    with pytest.raises(ValueError):
        audit_primary_letter_samples(data, as_of=CUTOFF)
    with pytest.raises(ValueError, match="research audit date"):
        audit_primary_letter_samples(source(), as_of="2026-10-28")
