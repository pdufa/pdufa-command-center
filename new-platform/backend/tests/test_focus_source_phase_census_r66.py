"""MAIN R66 source-locked Phase 3 registry labels, no clinical phase signoff."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts.build_focus_source_phase_census_r66 import (
    R46_SHA,R65_SHA,SCHEMA,build,summary,guarded_json
)
from scripts.refresh_focus_public_sources_r40 import APPS,ROSTER,_read_json,build_manifest


def setup_sources():
    required=("R66_R46","R66_R65","R66_REGISTRY_DIR")
    if any(not os.getenv(x) for x in required):
        pytest.skip("Original R53 and R65 research artifacts are not mounted")
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    r46,h46=guarded_json(Path(os.environ["R66_R46"]))
    r65,h65=guarded_json(Path(os.environ["R66_R65"]))
    assert h46==R46_SHA and h65==R65_SHA
    return manifest,r46,r65,Path(os.environ["R66_REGISTRY_DIR"])


def process(src):
    manifest,r46,r65,originals=src
    return build(manifest,r46,r65,originals,
                 hashes={"r46":R46_SHA,"r65":R65_SHA})


def test_real_29_original_registry_phase_and_status_reported_not_adjudicated():
    r=process(setup_sources())
    assert r["schema"]==SCHEMA
    assert r["exactNcts"]==29 and r["provisionalApplicationCycles"]==23
    assert r["registryReportedPhase3Only"]==28
    assert r["registryReportedPhase2Phase3"]==1
    assert r["registryReportedCompleted"]==19
    assert r["registryReportedActiveNotRecruiting"]==8
    assert r["registryReportedRecruiting"]==2
    assert r["registryReportedRandomized"]==28
    assert r["registryReportedAllocationNA"]==1
    assert r["independentlyQualifiedPhaseReviews"]==0
    assert r["signedScientificMethodGrades"]==0
    assert r["futureFDAOutcomePredictionsValidated"]==0
    assert r["measuredForecastAccuracy"] is None
    assert r["officialFutureFDAOutcome"]=="ABSTAIN"
    assert r["officialFDAReviewDelay"]=="ABSTAIN"
    assert r["productionOrReviewerLedgerWrites"] is False
    assert r["historicalOutcomesInspected"] is False
    assert r["phaseFieldsFromSourceAreNotClinicalOrRegulatoryAdjudications"]
    assert len(r["originalRegistryPhaseEvidence"])==29
    assert len(r["provisionalApplicationPhaseEvidence"])==23
    assert all(row["independentPhaseReviewEventId"] is None and
               row["requiresHumanPhaseValidation"] is True and
               row["fdaPrediction"]=="ABSTAIN" for row in r["originalRegistryPhaseEvidence"])
    assert "not 29 independent clinical" not in summary(r)


def test_combined_phase2_phase3_and_unrandomized_rare_trial_are_visible():
    r=process(setup_sources())
    combined=[x for x in r["originalRegistryPhaseEvidence"]
              if x["sourceReportedPhases"]==["PHASE2","PHASE3"]]
    assert len(combined)==1
    assert combined[0]["nct"]=="NCT04871282"
    assert "COMBINED_PHASE2_PHASE3_REVIEW_STUDY_DESIGN" in combined[0]["phaseReviewFlags"]
    nonrandom=[x for x in r["originalRegistryPhaseEvidence"]
               if x["sourceReportedAllocation"]=="NA"]
    assert len(nonrandom)==1 and nonrandom[0]["nct"]=="NCT06331299"
    assert "NON_RANDOMIZED_ALLOCATION_LABEL_NEEDS_DESIGN_REVIEW" in nonrandom[0]["phaseReviewFlags"]
    assert nonrandom[0]["clinicalMethodGradesCalculated"]==0


def test_completed_trial_or_missing_posted_results_does_not_become_success():
    r=process(setup_sources())
    completed=next(x for x in r["originalRegistryPhaseEvidence"]
                   if x["nct"]=="NCT02500381")
    assert completed["sourceReportedStatus"]=="COMPLETED"
    assert completed["fdaPrediction"]=="ABSTAIN"
    assert completed["independentPhaseReviewEventId"] is None
    capr=next(x for x in r["originalRegistryPhaseEvidence"]
              if x["nct"]=="NCT05126758")
    assert capr["sourceReportedPhases"]==["PHASE3"]
    assert capr["sourceReportedStatus"]=="ACTIVE_NOT_RECRUITING"
    assert capr["fdaPrediction"]=="ABSTAIN"
    assert all(x["officialFDAOutcome"]=="ABSTAIN"
               and x["FDAApplicationStageConfirmedByThisRegistryCensus"] is False
               for x in r["provisionalApplicationPhaseEvidence"])


def test_shared_sarepta_nct_one_unique_trial_two_applicative_links():
    r=process(setup_sources())
    n="NCT02500381"
    assert sum(x["nct"]==n for x in r["originalRegistryPhaseEvidence"])==1
    assert sum(n in x["linkedNcts"] for x in r["provisionalApplicationPhaseEvidence"])==2


@pytest.mark.parametrize("tamper",[
    lambda a,b: b.update(independentVerifiedPhaseEventsRecorded=1),
    lambda a,b: b.update(independentlyValidatedFDAApplicationPredictions=23),
    lambda a,b: b.update(gradeOrProbabilityReleasePermitted=True),
    lambda a,b: b.update(historicalOutcomeDataAccessed=True),
    lambda a,b: b["trialIndependentReviewPackets"][0].update(phaseVerifiedByIndependentReviewer=True),
    lambda a,b: b["trialIndependentReviewPackets"][0].update(completedClinicalMethodScores=8),
    lambda a,b: b["trialIndependentReviewPackets"][0].update(validatedFDAOutcome="APPROVAL"),
    lambda a,b: a["records"][0].update(sourceResponseSha256="0"*64),
    lambda a,b: a["records"][0].update(sourceResponseBytes=1),
    lambda a,b: b["trialIndependentReviewPackets"][0].update(applicationCycleIds=["fabricated-app"]),
])
def test_source_receipts_signed_phase_or_predicted_approval_fail_closed(tamper):
    manifest,r46,r65,originals=setup_sources()
    r46,r65=copy.deepcopy(r46),copy.deepcopy(r65)
    tamper(r46,r65)
    with pytest.raises(ValueError):
        build(manifest,r46,r65,originals,hashes={"r46":R46_SHA,"r65":R65_SHA})


def test_raw_registry_bytes_modified_without_receipt_change_fails(tmp_path):
    manifest,r46,r65,originals=setup_sources()
    # Only clone 29 public JSON bodies, never alter the original source archive.
    moved=tmp_path/"original"
    moved.mkdir()
    for item in originals.glob("NCT*.json"):
        (moved/item.name).write_bytes(item.read_bytes())
    target=moved/"NCT04544293.json"
    target.write_bytes(target.read_bytes()+b"\n")
    with pytest.raises(ValueError,match="ORIGINAL_SHA_OR_PHASE_REVIEW_MEMBERSHIP_MISMATCH"):
        build(manifest,r46,r65,moved,hashes={"r46":R46_SHA,"r65":R65_SHA})
