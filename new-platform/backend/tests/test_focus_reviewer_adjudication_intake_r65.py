"""R65: original R63 snapshot is a human review intake, never a signed grade.

These adversarial tests use the archived original R63 bytes supplied by an
isolated test workflow. No user credentials, clinical ledger or FDA outcomes.
"""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.build_focus_reviewer_adjudication_intake_r65 import (
    R63_SHA, build, summary,
)


@pytest.fixture
def original():
    src=os.environ.get("R65_ORIGINAL_R63_PATH")
    if not src:
        pytest.skip("R65_ORIGINAL_R63_PATH must be provided by original artifact CI")
    path=Path(src)
    import hashlib
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==R63_SHA
    return json.loads(raw)


def result(original):
    return build(original,source_sha256=R63_SHA)


def test_232_source_review_tasks_require_real_independent_human_phase_first(original):
    out=result(original)
    assert out["schema"]=="MAIN_R65_ORIGINAL_SOURCE_HUMAN_ADJUDICATION_INTAKE_ONLY"
    assert out["exactNctCount"]==29
    assert out["provisionalApplicationCount"]==23
    assert out["scientificReviewerTasks"]==232
    assert out["originalMachinePdfPageLeads"]==466
    assert out["originalPdfFilesWithLeads"]==22
    assert out["sourceTrialsWithCurrentPdfLeads"]==12
    assert out["sourceTrialsMissingCurrentPdfLeads"]==17
    assert len(out["trialIndependentReviewPackets"])==29
    assert len({t["nct"] for t in out["trialIndependentReviewPackets"]})==29
    assert out["qualifiedReviewerAttestationsRecorded"]==0
    assert out["independentVerifiedPhaseEventsRecorded"]==0
    assert out["independentlyCompletedMethodGrades"]==0
    assert out["independentStatisticalOrSafetySignoffs"]==0
    assert out["independentlyValidatedFDAApplicationPredictions"]==0
    assert out["measuredOutOfTimeForecastAccuracy"] is None
    assert out["officialFDAOutcome"]=="ABSTAIN"
    assert out["fdaReviewTiming"]=="ABSTAIN"
    assert out["gradeOrProbabilityReleasePermitted"] is False
    assert out["reviewWritesEnabled"] is False
    assert out["productionOrLedgerWrites"] is False
    assert out["historicalOutcomeDataAccessed"] is False
    assert all(t["mustVerifyTrialPhaseFirst"] is True
               and t["phaseVerifiedByIndependentReviewer"] is False
               and t["clinicalAssessmentLevel"]=="UNASSESSED_SOURCE_ONLY"
               and t["completedClinicalMethodScores"]==0
               and len(t["trialReviewSlots"])==8
               for t in out["trialIndependentReviewPackets"])
    assert "0 signed clinical assessments" in summary(out)


def test_savara_original_pages_are_unscored_and_require_original_sap_chronology(original):
    out=result(original)
    trial=next(t for t in out["trialIndependentReviewPackets"]
               if t["nct"]=="NCT04544293")
    assert trial["currentPostedPrimaryTables"]==1
    assert trial["currentReportedSafetyArmCount"]==2
    assert sum(len(x["exactOriginalPageLeads"])
               for x in trial["trialReviewSlots"])==47
    assert "CURRENT_SAP_DOCUMENT_DATE_EARLIER_THAN_LATEST_ATTACHED_PROTOCOL_DATE_AMENDMENT_REVIEW" in trial["protocolSapVersionAndChronologyFlags"]
    primary=trial["trialReviewSlots"][0]
    assert primary["phaseVerification"]=="REQUIRED_NOT_ATTESTED"
    assert primary["readyToRecordClinicalMethodGrade"] is False
    assert primary["reviewerAttestation"] is None
    assert primary["grade"] is None
    assert primary["studySuccessOrFailure"]=="UNDETERMINED"
    first=primary["exactOriginalPageLeads"][0]
    assert first["originalUrl"]=="https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/Prot_000.pdf"
    assert first["pdfPageOneBased"]==2
    assert first["possibleContentsOrIntroPage"] is True
    assert first["matchedPhraseNotClinicalJudgment"]=="primary endpoint"


def test_17_no_attached_leads_always_remain_retrieval_not_failed_efficacy(original):
    out=result(original)
    without=[t for t in out["trialIndependentReviewPackets"]
             if all(not s["exactOriginalPageLeads"] for s in t["trialReviewSlots"])]
    assert len(without)==17
    assert all(s["sourceReviewStatus"]==
               "NO_CURRENT_ATTACHED_DOCUMENT_SEARCH_OTHER_ORIGINALS"
               and s["studySuccessOrFailure"]=="UNDETERMINED"
               and s["grade"] is None
               for trial in without for s in trial["trialReviewSlots"])


def test_shared_trial_is_one_source_task_across_two_application_links(original):
    out=result(original)
    shared=[t for t in out["trialIndependentReviewPackets"] if t["nct"]=="NCT02500381"]
    assert len(shared)==1
    assert len(shared[0]["applicationCycleIds"])==2


@pytest.mark.parametrize("poison",[
    lambda src:src.update(independentlySignedScientificAssessments=1),
    lambda src:src.update(validatedFDAForecasts=23),
    lambda src:src.update(independentHistoricalBacktests=1),
    lambda src:src.update(modelTrainingAuthorized=True),
    lambda src:src["trialMethodReviewerQueue"].pop(),
    lambda src:src["applicationMethodReviewerQueue"].pop(),
    lambda src:src["trialMethodReviewerQueue"][0].update(clinicalMethodScore=5),
    lambda src:src["trialMethodReviewerQueue"][0].update(qualifiedReviewerSigned=True),
    lambda src:src["trialMethodReviewerQueue"][0].update(applicationCycleIds=["invalid"]),
    lambda src:src["trialMethodReviewerQueue"][0]["machineSourceReviewDimensions"][0].update(independentScientificJudgment="PASS"),
    lambda src:src["trialMethodReviewerQueue"][0]["machineSourceReviewDimensions"][0].update(qualifiedReviewerSignoff=True),
    lambda src:src["trialMethodReviewerQueue"][0]["machineSourceReviewDimensions"][0]["sourceLeads"].pop(),
    lambda src:src["trialMethodReviewerQueue"][0]["machineSourceReviewDimensions"][0]["sourceLeads"][0].update(pdfPageOneBased=0),
    lambda src:src["trialMethodReviewerQueue"][0]["machineSourceReviewDimensions"][0]["sourceLeads"][0].update(originalUrl="https://attacker.example/pdf"),
])
def test_malicious_source_or_fake_human_signature_rejected(original,poison):
    altered=deepcopy(original)
    poison(altered)
    with pytest.raises((ValueError,TypeError,KeyError,IndexError)):
        build(altered,source_sha256=R63_SHA)


def test_invalid_source_digest_refused_even_when_unscored(original):
    with pytest.raises(ValueError):
        build(original,source_sha256="not-a-sha")


def test_individual_domain_checklists_differ_and_never_claim_method_score(original):
    out=result(original)
    trial=next(t for t in out["trialIndependentReviewPackets"]
               if t["nct"]=="NCT04544293")
    questions=[tuple(s["requiredIndependentReviewQuestions"])
               for s in trial["trialReviewSlots"]]
    assert len(set(questions))==8
    assert all("originalDocumentContentSha256" in s["requiredEvidenceAndSignoffFields"]
               and "firstPublicDateEvidence" in s["requiredEvidenceAndSignoffFields"]
               and "secondIndependentVerifier" in s["requiredEvidenceAndSignoffFields"]
               and s["finalDisposition"]=="PENDING_QUALIFIED_HUMAN_ADJUDICATION"
               for s in trial["trialReviewSlots"])
