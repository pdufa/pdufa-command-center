"""R60 exact original registry challenge and fail-closed prediction/review gate."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy

import pytest

from test_focus_clinical_review_packets_r55 import scenario
from scripts.assemble_focus_clinical_review_packets_r55 import assemble
from scripts.build_focus_scientific_review_queue_r59 import build as build_r59
from scripts.build_focus_original_result_challenge_r60 import build, summary


def cases(tmp_path):
    manifest, r54, r46, original_dir = scenario(tmp_path)
    r55 = assemble(manifest, r46, r54, original_dir)
    r46_sha = "a" * 64
    r55_sha = "b" * 64
    r59 = build_r59(manifest, r55, r46, r55_sha256=r55_sha)
    r59["inputOriginalR46Sha256"] = r46_sha
    return manifest, r46, r55, r59, original_dir


def run(args):
    manifest, r46, r55, r59, originals = args
    return build(manifest, r46, r55, r59, originals,
                 r46_sha="a" * 64, r55_sha="b" * 64, r59_sha="c" * 64)


def test_29_original_trials_23_application_groups_deduplicated_with_no_fda_forecast(tmp_path):
    report = run(cases(tmp_path))
    assert report["canonicalUniqueNctCount"] == 29
    assert report["provisionalApplicationCycleCount"] == 23
    assert report["sourceVerifiedCurrentPrimaryTrialCount"] == 1
    assert report["sourceVerifiedCurrentSafetyArmTrialCount"] == 1
    assert report["sourceReportedPrimaryTables"] == 1
    assert report["sourceReportedStatisticalComparisons"] == 1
    assert report["sourceReportedSeriousAeTermRows"] == 1
    assert report["sourceReportedOtherAeTermRows"] == 1
    assert len(report["uniqueTrialOriginalResultChallenges"]) == 29
    assert len(report["applicationSourceReviewCrosswalk"]) == 23
    assert report["qualifiedClinicalOrStatisticalSignoffs"] == 0
    assert report["independentlyValidatedFdaForecasts"] == 0
    assert report["fdaApprovalProbability"] is None
    assert report["measuredPredictionAccuracy"] is None
    assert report["officialFutureFdaOutcome"] == "ABSTAIN"
    assert report["officialFutureReviewTiming"] == "ABSTAIN"
    assert report["reviewerLedgerProductionWritesOrModelTraining"] is False
    row = next(x for x in report["uniqueTrialOriginalResultChallenges"]
               if x["nct"] == "NCT04544293")
    assert row["sourceReportedPrimaryTables"][0]["analysisAsReported"][0]["pValueLiteral"] == "0.0007"
    assert row["sourceReportedPrimaryTables"][0]["analysisAsReported"][0]["effectEstimateLiteral"] == "6.0"
    assert row["sourceReportedSafetyArms"][0]["seriousAffectedAndAtRisk"] == [14, 81]
    assert row["sourceReportedSafetyArms"][1]["seriousAffectedAndAtRisk"] == [20, 83]
    assert row["independentlyQualifiedSafetyJudgment"] is None
    assert "NCT04544293" in summary(report)


def test_missing_current_result_does_not_make_a_negative_trial(tmp_path):
    report = run(cases(tmp_path))
    row = next(x for x in report["uniqueTrialOriginalResultChallenges"]
               if x["nct"] == "NCT05126758")
    assert row["sourceReportedPrimaryTables"] == []
    assert "NO_CURRENT_POSTED_PRIMARY_TABLE_CHECK_OTHER_ORIGINALS" in row["reviewExceptionCodes"]
    assert row["fdaOutcome"] == "ABSTAIN"
    assert report["noRegistryResultDoesNotProveTrialFailure"] is True


def test_shared_trial_research_only_once_and_two_application_references(tmp_path):
    report = run(cases(tmp_path))
    nct = "NCT02500381"
    assert sum(r["nct"] == nct for r in report["uniqueTrialOriginalResultChallenges"]) == 1
    assert sum(nct in a["supportingExactNcts"]
               for a in report["applicationSourceReviewCrosswalk"]) == 2


@pytest.mark.parametrize("poison", [
    lambda r46,r55,r59: r59.update(inputOriginalR55Sha256="d" * 64),
    lambda r46,r55,r59: r59.update(inputOriginalR46Sha256="d" * 64),
    lambda r46,r55,r59: r59.update(validatedFDAApplicationPredictions=1),
    lambda r46,r55,r59: r55.update(signedScientificReviews=1),
    lambda r46,r55,r59: r55.update(modelTrainingAuthorized=True),
    lambda r46,r55,r59: r55["originalUniqueTrialEvidence"][0].update(scientificScore=92),
    lambda r46,r55,r59: r59["uniqueTrialSourceTasks"][0].update(fdaPredictionValidated=True),
    lambda r46,r55,r59: r55["originalUniqueTrialEvidence"][0].update(seriousAeTermRowCount=17),
    lambda r46,r55,r59: r55["currentSourceCasePackets"][0].update(exactNcts=["NCT99999999"]),
    lambda r46,r55,r59: r46["records"][0].update(sourceResponseSha256="e" * 64),
])
def test_reject_original_source_drift_or_forged_review_certification(tmp_path, poison):
    manifest, r46, r55, r59, originals = cases(tmp_path)
    r46, r55, r59 = deepcopy(r46), deepcopy(r55), deepcopy(r59)
    poison(r46, r55, r59)
    with pytest.raises(ValueError):
        run((manifest, r46, r55, r59, originals))


def test_mismatched_original_source_bytes_rejected_even_when_metadata_unchanged(tmp_path):
    args = cases(tmp_path)
    target = args[-1] / "NCT04544293.json"
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ValueError, match="ORIGINAL_REGISTRY_BYTES_OR_SHA_CHANGED"):
        run(args)


def test_source_title_disagreement_is_review_exception_not_fda_rejection(tmp_path):
    manifest, r46, r55, r59, originals = cases(tmp_path)
    nct = "NCT04544293"
    path = originals / (nct + ".json")
    raw = json.loads(path.read_text())
    raw["protocolSection"]["outcomesModule"]["primaryOutcomes"][0]["measure"] = "Earlier different primary name"
    path.write_text(json.dumps(raw))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = next(x for x in r46["records"] if x["nct"] == nct)
    receipt["sourceResponseSha256"] = digest
    receipt["sourceResponseBytes"] = path.stat().st_size
    source = next(x for x in r55["originalUniqueTrialEvidence"] if x["nct"] == nct)
    source["currentRegistrySourceSha256"] = digest
    source["postedPrimaryOutcomeTables"][0]["sameTitleAndTimeFrameAsCurrentRegistration"] = False
    queued = next(x for x in r59["uniqueTrialSourceTasks"] if x["nct"] == nct)
    queued["currentOriginalRegistrySha256"] = digest
    report = run((manifest, r46, r55, r59, originals))
    row = next(x for x in report["uniqueTrialOriginalResultChallenges"] if x["nct"] == nct)
    assert "CURRENT_REGISTRATION_AND_POSTED_PRIMARY_TITLE_OR_TIME_DIFFER" in row["reviewExceptionCodes"]
    assert row["fdaOutcome"] == "ABSTAIN"
