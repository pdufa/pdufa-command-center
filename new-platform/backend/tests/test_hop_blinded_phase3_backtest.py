from copy import deepcopy
from datetime import date
import pytest

from app.hop_blinded_phase3_backtest import freeze_predecision_evidence,evaluate_replay_protocol

def source(*,day="2024-04-05"):
    return {
        "id":"pivotal-phase3-original",
        "role":"PIVOTAL_PHASE3_RESULT",
        "source_url":"https://www.sec.gov/Archives/edgar/data/1000000/original-8k.htm",
        "first_public_date":day,
        "retrieved_date":"2026-11-09",
        "as_published_version_verified":True,
        "sha256":"a"*64,
        "summary":"Synthetic Phase 3 endpoint publication with no future FDA decision embedded"
    }

def case(*,app="NDA123456",family="program-A",nct="NCT01234567"):
    return {
        "applicationId":app,
        "reviewCycle":1,
        "programFamily":family,
        "nctIds":[nct],
        "phase3ReadoutPublicOn":"2024-04-05",
        "predictionCutoff":"2024-04-06",
        "evidenceSources":[source()]
    }

def sealed(frozen,*,lean="APPROVAL_LEAN",split="development"):
    p=frozen["frozenEvidence"]
    return {
        "applicationId":p["applicationId"],
        "reviewCycle":p["reviewCycle"],
        "frozenSourceSha256":frozen["frozenSourceSha256"],
        "researchLean":lean,
        "researchVersion":"experimental-v1",
        "isolationProof":"OUTCOME_VAULT_NOT_READ_BY_FORECAST_RUN",
        "split":split,
        "createdAtUtc":"2026-11-09T16:00:00Z"
    }

def outcome(*,app="NDA123456",action="APPROVAL"):
    return {
        "applicationId":app,
        "reviewCycle":1,
        "finalAction":action,
        "actionDate":"2024-12-01",
        "firstPublicActionOn":"2024-12-02",
        "originalFdaActionSource":"https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2024/example.pdf",
        "qualifiedOutcomeReviewerSignoff":False,
        "exhaustiveFilingCohortVerified":False
    }

def test_zero_real_cases_never_claims_accuracy_or_calibration():
    r=evaluate_replay_protocol(frozen_packets=[],provisional_predictions=[],
        outcome_vault=[],as_of=date(2026,11,9))
    assert r["independentRealBacktests"]==0
    assert r["independentlyVerifiedHistoricalCases"]==0
    assert r["measuredProspectiveAccuracy"] is None
    assert r["researchCallCoverageOfPaired"] is None
    assert r["fdaProbability"] is None
    assert r["trainingAuthorized"] is False

def test_public_phase3_readout_source_freezes_without_outcome_label():
    f=freeze_predecision_evidence(case())
    assert f["frozenEvidence"]["fdaOutcomeAvailableToResearchForecaster"] is False
    assert "finalAction" not in f["frozenEvidence"]
    assert len(f["frozenSourceSha256"])==64
    assert f["officialForecast"]=="ABSTAIN"
    assert f["independentlyVerifiedHistoricCase"] is False

def test_synthetic_replay_math_stays_diagnostic_not_independent_accuracy():
    f=freeze_predecision_evidence(case())
    p=sealed(f)
    r=evaluate_replay_protocol(frozen_packets=[f],provisional_predictions=[p],
        outcome_vault=[outcome()],as_of=date(2026,11,9))
    assert r["pairedWithObservedOutcomes"]==1
    assert r["researchCallMatches"]==1
    assert r["researchMatchFractionAmongCalled"]==1
    assert r["independentRealBacktests"]==0
    assert r["measuredProspectiveAccuracy"] is None
    assert r["brierScore"] is None
    assert r["calibration"] is None

@pytest.mark.parametrize("change",[
    lambda c:c.update(finalAction="APPROVAL"),
    lambda c:c.update(predictionCutoff="2024-04-05"),
    lambda c:c["evidenceSources"][0].update(first_public_date="2024-06-01"),
    lambda c:c["evidenceSources"][0].update(as_published_version_verified=False),
    lambda c:c["evidenceSources"][0].update(sha256="forged"),
    lambda c:c["evidenceSources"][0].update(role="FDA_OUTCOME"),
    lambda c:c["evidenceSources"][0].update(source_url="https://bad.invalid"),
    lambda c:c["evidenceSources"][0].update(fdaOutcome="CRL"),
])
def test_outcome_leak_or_source_integrity_violation_refuses_frozen_case(change):
    c=case()
    change(c)
    with pytest.raises(ValueError):
        freeze_predecision_evidence(c)

def test_program_family_cannot_enter_development_and_holdout():
    f=freeze_predecision_evidence(case())
    g=freeze_predecision_evidence(case(app="BLA987654",family="program-A",nct="NCT87654321"))
    with pytest.raises(ValueError,match="CROSS_SPLIT"):
        evaluate_replay_protocol(frozen_packets=[f,g],
            provisional_predictions=[sealed(f),sealed(g,split="temporal_holdout")],
            outcome_vault=[],as_of=date(2026,11,9))

def test_retrospective_outcome_must_follow_frozen_cutoff_and_first_publication():
    f=freeze_predecision_evidence(case())
    o=outcome()
    o["actionDate"]="2024-04-01"
    with pytest.raises(ValueError,match="BEFORE_PREDICTION_CUTOFF"):
        evaluate_replay_protocol(frozen_packets=[f],provisional_predictions=[sealed(f)],
            outcome_vault=[o],as_of=date(2026,11,9))
    o=outcome();o["firstPublicActionOn"]="2024-11-20"
    with pytest.raises(ValueError,match="OUTCOME_CLOCK_INVALID"):
        evaluate_replay_protocol(frozen_packets=[f],provisional_predictions=[sealed(f)],
            outcome_vault=[o],as_of=date(2026,11,9))

def test_frozen_source_hash_mutation_refused_and_no_outcome_vault_in_forecaster():
    f=freeze_predecision_evidence(case())
    f["frozenEvidence"]["sourceVersions"][0]["summary"]="tampered after sealed cutoff"
    with pytest.raises(ValueError,match="FROZEN_EVIDENCE_HASH_MISMATCH"):
        evaluate_replay_protocol(frozen_packets=[f],provisional_predictions=[],
            outcome_vault=[],as_of=date(2026,11,9))
    f=freeze_predecision_evidence(case())
    p=sealed(f);p["isolationProof"]="UNVERIFIED"
    with pytest.raises(ValueError,match="PREDICTION_NOT_SEALED"):
        evaluate_replay_protocol(frozen_packets=[f],provisional_predictions=[p],
            outcome_vault=[outcome()],as_of=date(2026,11,9))

def test_pending_or_withdrawn_not_misclassified_as_crl_or_false_negative():
    f=freeze_predecision_evidence(case())
    r=evaluate_replay_protocol(frozen_packets=[f],
         provisional_predictions=[sealed(f,lean="ABSTAIN")],
         outcome_vault=[outcome(action="WITHDRAWN")],as_of=date(2026,11,9))
    assert r["researchCallsOnBinaryOutcomes"]==0
    assert r["researchMatchFractionAmongCalled"] is None
    assert r["sourceActionCounts"]["WITHDRAWN"]==1
    assert r["fdaProbability"] is None

def test_predecision_source_retrieved_today_allowed_only_with_original_publication_proof():
    c=case()
    assert freeze_predecision_evidence(c)["officialForecast"]=="ABSTAIN"
    c["evidenceSources"][0]["as_published_version_verified"]=False
    with pytest.raises(ValueError):
        freeze_predecision_evidence(c)


def test_refusal_to_file_is_not_a_final_fda_approval_or_crl_decision():
    """A pre-review RTF (as in Savara 2025) must stay outside final-action labels.

    RTF documents may be captured as dated regulatory/CMC risk sources, but are
    never converted to an independently adjudicated CRL or approval outcome.
    """
    frozen=freeze_predecision_evidence(case())
    with pytest.raises(ValueError,match="UNVERIFIED_FDA_ACTION_SOURCE"):
        evaluate_replay_protocol(frozen_packets=[frozen],
            provisional_predictions=[sealed(frozen,lean="CRL_LEAN")],
            outcome_vault=[outcome(action="REFUSAL_TO_FILE")],
            as_of=date(2026,11,9))
