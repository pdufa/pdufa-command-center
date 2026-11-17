"""Synthetic Level 17–18 disclosure chronology and challenge evidence tests."""
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_levels_nine_to_twenty import NCT, intake, reviewed_record


def evidence(value):
    source = reviewed_record()
    source["measurements"] = value
    return source


def claim(text, day):
    return {"nctId": NCT, "claimKey": "primary endpoint", "claimText": text,
            "disclosureDate": day}


def challenge(title):
    return {"nctId": NCT, "hypothesis": title,
            "evidenceRationale": "Synthetic rationale", "evaluationScope": "ITT",
            "possibleDiscriminator": "Prespecified sensitivity analysis"}


def assess(data):
    return assess_levels_nine_to_twenty(intake(), trial_id=NCT, evidence=data)


def test_changed_sponsor_statement_is_review_item_not_proof_of_misconduct():
    data = {"17.datedDisclosureVersions": evidence(claim("Expected endpoint", "2026-01-01")),
            "17.materialChanges": evidence(claim("Amended endpoint", "2026-01-15"))}
    value = assess(data)["17"]["disclosureContext"]
    assert value["status"] == "CLAIM_CHANGE_REQUIRES_OWNER_REVIEW"
    assert value["misrepresentationEstablished"] is False
    assert value["materialityEstablished"] is False
    assert value["textChanged"] is True
    assert value["fdaPrediction"] == "ABSTAIN"


def test_same_text_still_not_a_consistency_certification():
    data = {"17.datedDisclosureVersions": evidence(claim("Statement", "2026-01-01")),
            "17.materialChanges": evidence(claim("Statement", "2026-01-15"))}
    value = assess(data)["17"]["disclosureContext"]
    assert value["status"] == "SAME_TEXT_NOT_PROOF_OF_CONSISTENCY"
    assert value["ownerReconciliation"] == "NOT_COMPLETED"


def test_future_wrong_trial_and_reverse_order_rejected():
    for changed, status in [
        ({"disclosureDate": "2026-03-01"}, "REJECTED_CLAIM_CONTEXT"),
        ({"nctId": "NCT00000002"}, "REJECTED_CLAIM_CONTEXT"),
        ({"disclosureDate": "2026-01-01"}, "REJECTED_CLAIM_CONTEXT"),
        ({"claimKey": "unrelated"}, "REJECTED_CLAIM_CONTEXT"),
    ]:
        data = {"17.datedDisclosureVersions": evidence(claim("Old", "2026-01-01")),
                "17.materialChanges": evidence({**claim("New", "2026-01-15"), **changed})}
        assert assess(data)["17"]["disclosureContext"]["status"] == status


def test_two_arguments_do_not_count_as_owner_synthesis():
    data = {
        "18.strongestCounterargument": evidence(challenge("Study unblinding")),
        "18.alternativeCausality": evidence(challenge("Different supportive care"))
    }
    value = assess(data)["18"]["challengeContext"]
    assert value["status"] == "COMPETING_EXPLANATIONS_DOCUMENTED_NOT_RESOLVED"
    assert value["scientificChallengeResolved"] is False
    assert value["ownerAcceptance"] == "NOT_RECORDED"
    assert value["score"] is None


def test_same_hypothesis_or_wrong_trial_not_a_challenge():
    data = {"18.strongestCounterargument": evidence(challenge("One hypothesis")),
            "18.alternativeCausality": evidence(challenge("one hypothesis"))}
    assert assess(data)["18"]["challengeContext"]["status"] == "REJECTED_ARGUMENTS"
    data["18.alternativeCausality"] = evidence({
        **challenge("Second explanation"), "nctId": "NCT00000002"})
    assert assess(data)["18"]["challengeContext"]["status"] == "REJECTED_ARGUMENTS"


def test_unverified_source_never_creates_hypothesis_review():
    data = {"18.strongestCounterargument": evidence(challenge("One")),
            "18.alternativeCausality": evidence(challenge("Two"))}
    data["18.strongestCounterargument"]["sourceRetrievedAt"] = "2026-03-05"
    assert assess(data)["18"]["challengeContext"]["status"] == "NOT_ASSESSED"
