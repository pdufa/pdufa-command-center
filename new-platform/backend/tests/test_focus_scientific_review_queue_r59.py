"""R59 guards: source triage is not clinical scoring, prospective prediction or calibration."""
from __future__ import annotations

from copy import deepcopy
import pytest

from test_focus_clinical_review_packets_r55 import scenario
from scripts.assemble_focus_clinical_review_packets_r55 import assemble
from scripts.build_focus_scientific_review_queue_r59 import build, markdown_report


def fixture(tmp_path):
    manifest, r54, r46, registry = scenario(tmp_path)
    return manifest, assemble(manifest, r46, r54, registry)


def test_canonical_29_trial_23_cycle_review_queue_and_zero_predictions(tmp_path):
    manifest, packets = fixture(tmp_path)
    report = build(manifest, packets, r55_sha256="a" * 64)
    assert report["canonicalUniqueNctTrials"] == 29
    assert report["provisionalApplicationCycles"] == 23
    assert len(report["uniqueTrialSourceTasks"]) == 29
    assert len(report["applicationReviewQueue"]) == 23
    assert report["currentTrialsWithPostedPrimary"] == 1
    assert report["currentTrialsWithPostedSafetyArms"] == 1
    assert report["attachedOriginalProtocolSapDocuments"] == 23
    assert report["signedIndependentClinicalReviews"] == 0
    assert report["validatedFDAApplicationPredictions"] == 0
    assert report["measuredHistoricalAccuracy"] is None
    assert report["calibratedFDAProbability"] is None
    assert report["allFutureFDAOutcomes"] == "ABSTAIN"
    assert report["noModelTrainingOrProductionWrites"] is True
    svra = next(x for x in report["uniqueTrialSourceTasks"] if x["nct"] == "NCT04544293")
    assert svra["reportedPrimaryTables"] == 1
    assert svra["reportedPrimaryComparisons"] == 1
    assert svra["currentAdverseEventArms"] == 2
    assert svra["currentAttachedProtocolSapDocuments"] == 2
    assert "INDEPENDENTLY_RECONCILE_PRIMARY_RESULTS_AND_SAP" in svra["reviewTasks"]
    assert svra["phaseIndependentlyAdjudicated"] is False
    assert "FDA outcome/timing" in markdown_report(report)


def test_missing_registry_results_only_emits_alternative_original_recovery_tasks(tmp_path):
    manifest, packets = fixture(tmp_path)
    report = build(manifest, packets, r55_sha256="b" * 64)
    capr = next(a for a in report["applicationReviewQueue"]
                if a["applicationCycleId"] == "capr-deramiocel")
    assert capr["currentPrimaryTables"] == 0
    assert capr["currentProtocolSapDocuments"] == 0
    assert capr["sourceCoverageBucketNotClinicalGrade"] == "ALTERNATIVE_ORIGINAL_SOURCE_RECOVERY_REQUIRED"
    assert capr["forecastApprovalOrCRL"] == "ABSTAIN"
    nct = next(t for t in report["uniqueTrialSourceTasks"] if t["nct"] == "NCT05126758")
    assert "FIND_PRIMARY_EFFICACY_IN_SPONSOR_JOURNAL_REGULATORY_ORIGINALS" in nct["reviewTasks"]
    assert "RECOVER_ORIGINAL_PROTOCOL_SAP_OUTSIDE_CURRENT_REGISTRY" in nct["reviewTasks"]
    assert nct["currentRegistryMissingDoesNotMeanOtherSourceMissingOrTrialFailed"] is True


def test_shared_trial_not_double_counted_as_evidence_record(tmp_path):
    manifest, packets = fixture(tmp_path)
    report = build(manifest, packets, r55_sha256="c" * 64)
    shared = "NCT02500381"
    assert len([x for x in report["uniqueTrialSourceTasks"] if x["nct"] == shared]) == 1
    assert sum(shared in a["supportingExactNcts"] for a in report["applicationReviewQueue"]) == 2


@pytest.mark.parametrize("tamper", [
    lambda p: p.update(independentlyValidatedFDAApplicationForecasts=1),
    lambda p: p.update(clinicalOrProductionWrites=True),
    lambda p: p.update(sourceVerifiedCurrentProtocolSAPDocuments=24),
    lambda p: p["originalUniqueTrialEvidence"].pop(),
    lambda p: p["currentSourceCasePackets"].pop(),
    lambda p: p["originalUniqueTrialEvidence"][0].update(currentRegistrySourceSha256="0" * 64),
    lambda p: p["originalUniqueTrialEvidence"][0].update(scientificScore=85),
    lambda p: p["originalUniqueTrialEvidence"][0].update(independentReviewerSigned=True),
    lambda p: p["currentSourceCasePackets"][0].update(fdaProbability=0.95),
    lambda p: p["currentSourceCasePackets"][0].update(officialFDAOutcomePrediction="APPROVAL"),
    lambda p: p["currentSourceCasePackets"][0].update(linkedCurrentProtocolSAPDocs=777),
])
def test_forged_evidence_source_or_false_forecast_fails_closed(tmp_path, tamper):
    manifest, packets = fixture(tmp_path)
    poisoned = deepcopy(packets)
    tamper(poisoned)
    with pytest.raises(ValueError):
        build(manifest, poisoned, r55_sha256="d" * 64)


def test_invalid_original_source_sha_is_rejected(tmp_path):
    manifest, packets = fixture(tmp_path)
    with pytest.raises(ValueError):
        build(manifest, packets, r55_sha256="not-an-original-source-hash")
