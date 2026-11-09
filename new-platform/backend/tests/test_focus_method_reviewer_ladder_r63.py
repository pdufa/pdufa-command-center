"""R63 eight-domain source-review matrix is never a clinical grade."""
from __future__ import annotations

from copy import deepcopy

import pytest

from test_focus_clinical_review_packets_r55 import scenario
from scripts.assemble_focus_clinical_review_packets_r55 import assemble
from scripts.build_focus_scientific_review_queue_r59 import build as build59
from scripts.build_focus_original_result_challenge_r60 import build as build60
from scripts.build_focus_method_reviewer_ladder_r63 import DOMAINS, build, summary


def fixture(tmp_path):
    manifest, methods, receipts, registry = scenario(tmp_path)
    packet = assemble(manifest, receipts, methods, registry)
    queue = build59(manifest, packet, receipts, r55_sha256="b" * 64)
    queue["inputOriginalR46Sha256"] = "a" * 64
    results = build60(
        manifest, receipts, packet, queue, registry,
        r46_sha="a" * 64, r55_sha="b" * 64, r59_sha="c" * 64,
    )
    return manifest, methods, packet, results


def check(s):
    manifest, methods, packet, results = s
    return build(manifest, methods, packet, results,
                 hashes={"r54":"a"*64,"r55":"b"*64,"r60":"c"*64})


def test_29_unique_trial_slots_23_applications_8_domains_unscored(tmp_path):
    report = check(fixture(tmp_path))
    assert report["uniqueTrials"] == 29
    assert report["provisionalApplicationGroups"] == 23
    assert report["domainTrialReviewSlots"] == 232
    assert report["publicOriginalProtocolSapDocuments"] == 23
    assert report["trialsWithOriginalAttachedMethodsDocuments"] == 12
    assert report["sourceReviewDomains"] == list(DOMAINS)
    assert len(report["trialMethodReviewerQueue"]) == 29
    assert len(report["applicationMethodReviewerQueue"]) == 23
    assert report["independentlySignedScientificAssessments"] == 0
    assert report["scientificScoresCalculated"] == 0
    assert report["validatedFDAForecasts"] == 0
    assert report["independentHistoricalBacktests"] == 0
    assert report["measuredPredictionAccuracy"] is None
    assert report["officialFutureFDAOutcome"] == "ABSTAIN"
    assert report["officialReviewDelayPrediction"] == "ABSTAIN"
    assert report["productionOrClinicalLedgerWrites"] is False
    assert report["modelTrainingAuthorized"] is False
    assert report["machinePageLeadsAreNeither800CompletedTestsNorClinicalValidation"] is True
    assert "not 232 completed scientific assessments" in summary(report)


def test_savara_original_pdf_page_leads_and_chronology_do_not_get_scored(tmp_path):
    report = check(fixture(tmp_path))
    svra=next(t for t in report["trialMethodReviewerQueue"]
              if t["nct"]=="NCT04544293")
    assert svra["originalCurrentProtocolSapCount"] == 2
    assert svra["currentPostedPrimaryTables"] == 1
    assert svra["currentReportedSafetyArmCount"] == 2
    assert len(svra["machineSourceReviewDimensions"]) == 8
    assert svra["independentlyCompletedAssessmentLevel"] is None
    assert svra["clinicalMethodScore"] is None
    assert svra["officialFutureFdaDecision"] == "ABSTAIN"
    assert "CURRENT_SAP_DOCUMENT_DATE_EARLIER_THAN_LATEST_ATTACHED_PROTOCOL_DATE_AMENDMENT_REVIEW" in svra["unresolvedProtocolVersionFlags"]
    multiplicity = next(x for x in svra["machineSourceReviewDimensions"]
                        if x["domain"] == "MULTIPLICITY_CONTROL")
    assert multiplicity["sourceLeadStateNotScientificGrade"] == "LITERAL_PAGE_REFERENCE_REVIEW_REQUIRED"
    assert len(multiplicity["sourceLeads"]) == 2
    assert all(lead["pdfPageOneBased"] == 1
               and lead["originalUrl"].startswith("https://cdn.clinicaltrials.gov/")
               for lead in multiplicity["sourceLeads"])
    assert multiplicity["independentScientificJudgment"] is None
    assert multiplicity["qualifiedReviewerSignoff"] is False
    assert multiplicity["assessmentLevel"] == "UNASSESSED_SOURCE_ONLY"


def test_17_no_pdf_trials_still_have_8_unknown_review_slots(tmp_path):
    report = check(fixture(tmp_path))
    no_doc=[r for r in report["trialMethodReviewerQueue"]
            if not r["originalCurrentProtocolSapCount"]]
    assert len(no_doc)==17
    assert all(len(r["machineSourceReviewDimensions"])==8 for r in no_doc)
    assert all(d["sourceLeadStateNotScientificGrade"] ==
               "NO_CURRENT_ATTACHED_DOCUMENT_SEARCH_OTHER_ORIGINALS"
               for r in no_doc for d in r["machineSourceReviewDimensions"])


def test_shared_trial_not_double_counted_as_independent_pdf_science(tmp_path):
    report=check(fixture(tmp_path))
    trial="NCT02500381"
    assert sum(r["nct"]==trial for r in report["trialMethodReviewerQueue"])==1
    assert sum(trial in a["linkedNcts"] for a in report["applicationMethodReviewerQueue"])==2


@pytest.mark.parametrize("change",[
    lambda m,p,o: m.update(independentlySignedClinicalMethodGrades=1),
    lambda m,p,o: m.update(independentHistoricalFDAOutcomeBacktests=1),
    lambda m,p,o: m["trialMethodsReview"].pop(),
    lambda m,p,o: m["trialMethodsReview"][0].update(independentStatisticalReviewComplete=True),
    lambda m,p,o: m["trialMethodsReview"][0]["documents"][0]["machineTextEvidence"].update(statisticalReviewerSigned=True),
    lambda m,p,o: m["trialMethodsReview"][0]["documents"][0].update(sourceSha256="0"*64),
    lambda m,p,o: m["trialMethodsReview"][0]["documents"][0]["machineTextEvidence"]["eightSourceReviewDomains"]["PRIMARY_ENDPOINT"]["pageLinkedSourceLeads"][0].update(pdfPageOneBased=9999),
    lambda m,p,o: p["originalUniqueTrialEvidence"][0].update(scientificScore=91),
    lambda m,p,o: p["originalUniqueTrialEvidence"][0]["sourceMethodsPageReferences"][0]["eightScientificMethodPageLeads"]["PRIMARY_ENDPOINT"].append(99),
    lambda m,p,o: o["uniqueTrialOriginalResultChallenges"][0].update(independentlyQualifiedStatisticalJudgment="APPROVED"),
    lambda m,p,o: o.update(independentlyValidatedFdaForecasts=23),
])
def test_rejects_forged_method_pages_grades_and_identity(tmp_path,change):
    manifest, methods, packet, outcome=fixture(tmp_path)
    methods,packet,outcome=deepcopy(methods),deepcopy(packet),deepcopy(outcome)
    change(methods,packet,outcome)
    with pytest.raises(ValueError):
        build(manifest,methods,packet,outcome,
              hashes={"r54":"a"*64,"r55":"b"*64,"r60":"c"*64})
