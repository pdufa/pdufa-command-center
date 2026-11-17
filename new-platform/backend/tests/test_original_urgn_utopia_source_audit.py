"""URGN evidence traceability: confirmed date evidence must not become invented FDA approval."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PATH = ROOT / "research/source-links/URGN-NCT06331299-UTOPIA-NDA-source-audit-2026-11-17.json"


def source():
    return json.loads(PATH.read_text(encoding="utf8"))


def test_exact_study_and_primary_original_source_identity():
    p=source()
    assert p["nctId"]=="NCT06331299" and p["ticker"]=="URGN"
    assert p["studyDesign"]["phase"]=="PHASE3"
    assert p["studyDesign"]["design"]=="single-arm, multicenter"
    assert p["studyDesign"]["originalSponsorReportedEnrolled"]==99
    by_type={x["type"]:x for x in p["sourceLinks"]}
    assert by_type["ORIGINAL_CONFERENCE_ABSTRACT"]["doi"]=="10.1200/JCO.2026.44.16_suppl.4604"
    assert by_type["NCI_PROTOCOL_IDENTITY"]["explicitExactNctIdentifier"] is True


def test_company_reported_regulatory_acceptance_is_not_an_fda_approval():
    p=source()
    event=p["regulatoryEvent"]
    assert event["sponsorAnnouncementDate"]=="2026-10-19"
    assert event["pdufaTargetActionDate"]=="2027-06-14"
    assert event["type"]=="NDA_ACCEPTED_FOR_REVIEW_SPONSOR_REPORTED"
    assert event["approvalDecision"]=="NOT_REPORTED"
    assert event["applicationNumber"] is None
    assert event["fdaOriginalFilingLetterRetrieved"] is False
    assert event["acceptedForReviewDoesNotMeanApproved"] is True
    assert p["fdaPrediction"]=="ABSTAIN"
    assert p["allowedProductionWrites"] is False


def test_exact_3mo_response_vs_conditional_durability_denominator():
    p=source()
    r=p["sponsorReportedClinicalResults"]
    assert r["completeResponses"]==77 and r["enrolledDenominator"]==99
    assert r["responseRatePercent"]==77.8
    assert r["responseRate95CI_percent"]==[68.3,85.5]
    assert r["conditionalSixMonthDurationOfResponseKM_percent"]==94.5
    assert r["conditionalSixMonthDurationOfResponse95CI_percent"]==[86.1,97.9]
    assert "conditional" in r["caution"].lower()
    assert p["evidenceReview"]["clinicalScientificReviewComplete"] is False
    assert p["scientificScore"] is None
    assert p["fdaApprovalProbability"] is None


def test_blind_historical_prediction_and_publish_date_boundary():
    p=source()
    sources=p["sourceLinks"]
    assert next(s for s in sources if s["type"]=="SPONSOR_CLINICAL_RESULTS_RELEASE")["publicationDate"]=="2026-05-15"
    assert next(s for s in sources if s["type"]=="SPONSOR_REGULATORY_NEWS_RELEASE")["publicationDate"]=="2026-10-19"
    assert p["historicalBlindBacktestRule"]=="SOURCE_DATE_MUST_BE_BEFORE_OR_ON_FROZEN_PREDICTION_CUTOFF"
    assert p["evidenceReview"]["independentSafetyReviewComplete"] is False
