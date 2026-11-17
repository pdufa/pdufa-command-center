"""Synthetic Level 13–14 application and designation gates."""
from copy import deepcopy
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_levels_nine_to_twenty import NCT, intake, reviewed_record


def official(measurements):
    value = reviewed_record()
    value["source"] = "https://www.fda.gov/drugs/research/official-original-record"
    value.update(sourceDate="2026-01-27", sourceRetrievedAt="2026-01-28",
                 sourceVerifiedAt="2026-01-29", reviewedAt="2026-01-30")
    value["measurements"] = measurements
    return value


def app():
    return {"applicationType": "NDA", "applicationNumber": "123456",
            "reviewCycle": 1, "indication": "Fictional disease", "linkedNct": NCT}


def evidence():
    return {"13.exactApplicationIdentity": official(app()),
            "13.acceptedFiling": official({**app(), "receivedDate": "2026-01-03",
                                         "acceptanceDate": "2026-01-09"})}


def assess(inputs):
    return assess_levels_nine_to_twenty(intake(), trial_id=NCT, evidence=inputs)


def test_filing_date_and_identity_reconciliation_is_not_approval():
    result = assess(evidence())["13"]["filingContext"]
    assert result["status"] == "DATED_FILING_RECORDS_RECONCILED_NOT_AGENCY_CERTIFICATION"
    assert result["candidateApplicationCycle"]["applicationNumber"] == "123456"
    assert result["fdaFilingVerified"] is False
    assert result["approvalStatus"] == "NOT_INFERRED"
    assert result["fdaPrediction"] == "ABSTAIN"
    assert result["score"] is None


def test_filing_identity_mismatch_and_invalid_cycle_fail_closed():
    for mutation in ({"linkedNct": "NCT00000009"},
                     {"applicationNumber": "123457"},
                     {"reviewCycle": True},
                     {"indication": "Another disease"}):
        data = evidence()
        data["13.acceptedFiling"]["measurements"].update(mutation)
        assert assess(data)["13"]["filingContext"]["status"] == "REJECTED_IDENTITY"


def test_future_acceptance_and_reversed_receipt_fail_closed():
    for mutation in ({"acceptanceDate": "2026-03-01"},
                     {"receivedDate": "2026-01-12", "acceptanceDate": "2026-01-09"}):
        data = evidence()
        data["13.acceptedFiling"]["measurements"].update(mutation)
        assert assess(data)["13"]["filingContext"]["status"] == "REJECTED_CHRONOLOGY"


def test_unverified_or_unofficial_filing_not_used():
    data = evidence()
    data["13.exactApplicationIdentity"]["source"] = "https://company.example/nda"
    assert assess(data)["13"]["filingContext"]["status"] == "NOT_ASSESSED"
    data = evidence()
    data["13.acceptedFiling"]["sourceRetrievedAt"] = "2026-03-01"
    assert assess(data)["13"]["filingContext"]["status"] == "NOT_ASSESSED"


def test_preapplication_designation_lead_does_not_require_filing():
    data = {"14.officialDesignationEvidence": official({
        "designation": "FAST_TRACK", "indication": "Fictional disease",
        "linkedNct": NCT, "designationDate": "2026-01-03"
    })}
    value = assess(data)["14"]["designationContext"]
    assert value["status"] == "SOURCE_REVIEWED_DESIGNATION_LEAD_ONLY"
    assert value["applicationRelationship"] == "PRE_APPLICATION_OR_UNMAPPED"
    assert value["officialDesignationConfirmed"] is False


def test_designation_indication_disagreement_not_promoted():
    data = evidence()
    data["14.officialDesignationEvidence"] = official({
        "designation": "ORPHAN_DRUG", "indication": "Different indication",
        "linkedNct": NCT, "designationDate": "2026-01-03"
    })
    result = assess(data)["14"]["designationContext"]
    assert result["applicationRelationship"] == "INDICATION_DISAGREEMENT"
    assert result["fdaPrediction"] == "ABSTAIN"


def test_postcutoff_designation_and_wrong_trial_rejected():
    for mutation in ({"designationDate": "2026-03-01"},
                     {"linkedNct": "NCT00000002"},
                     {"designation": "MADE_UP"}):
        values = {"designation": "PRIORITY_REVIEW", "indication": "Fictional disease",
                  "linkedNct": NCT, "designationDate": "2026-01-10"}
        values.update(mutation)
        data = {"14.officialDesignationEvidence": official(values)}
        assert assess(data)["14"]["designationContext"]["status"] == "REJECTED_MEASUREMENTS"
