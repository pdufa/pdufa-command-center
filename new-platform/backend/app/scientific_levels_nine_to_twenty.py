"""Evidence-review contracts for scientific Levels 9–20.

This is deliberately NOT a suite of completed scientific engines.
No composite ratings, inferred regulatory decisions or calibrated FDA
probabilities are generated. Source-reviewed findings remain tied to the
same exact trial, phase and point-in-time cutoff as the existing Levels 2–8.
"""
from __future__ import annotations

from .scientific_levels_two_to_six import assess_review_contracts
from .scientific_benefit_harm import align_benefit_harm
from .scientific_standard_care import compare_standard_care
from .scientific_therapeutic_context import therapeutic_context
from .scientific_replication_candidates import screen_replication_candidates
from .scientific_regulatory_context import assess_filing, assess_designation
from .scientific_precedent_manufacturing import assess_precedent, assess_manufacturing
from .scientific_disclosure_challenge import assess_disclosure, assess_challenge
from .scientific_forecast_outcome_integrity import assess_prospective_metadata, assess_outcome_chronology

VERSION = "scientific-contracts-09-20-v1"

LEVELS = {
    9: ("Benefit-risk integration", (
        "benefitEvidence", "harmEvidence", "comparabilityAndFollowup",
        "clinicalContext", "contradictionsAndUncertainty")),
    10: ("Disease and standard-of-care dossier", (
        "diseaseAndSubtype", "treatmentSetting", "datedGuidelines",
        "standardOfCare", "comparatorApplicability")),
    11: ("Unmet need and therapeutic context", (
        "populationBurden", "availableAlternatives", "remainingUnmetNeed",
        "patientRelevantOutcomes", "accessAndEligibility")),
    12: ("Reproducibility and independent studies", (
        "independentStudyIdentity", "populationComparability", "endpointComparability",
        "nonduplicateCohorts", "heterogeneityAndSynthesisPlan")),
    13: ("Application and filing readiness", (
        "exactApplicationIdentity", "acceptedFiling", "submissionChronology",
        "dossierCompleteness", "agencyQuestions")),
    14: ("FDA pathways and designations", (
        "officialDesignationEvidence", "designationIndicationMatch",
        "applicationCycleLink", "pathwayRequirements", "designationChanges")),
    15: ("FDA precedent and advisory evidence", (
        "precedentSelection", "applicationAndIndicationComparability",
        "officialAdvisoryRecord", "voteAndRationale", "targetOutcomeLeakage")),
    16: ("Manufacturing and inspection uncertainty", (
        "facilityApplicationLink", "manufacturingInformation", "inspectionEvidence",
        "qualityAndSupply", "unknownVersusDeficiency")),
    17: ("Sponsor disclosure consistency", (
        "datedDisclosureVersions", "exactProgramIdentity", "contradictionLedger",
        "reconciliationEvidence", "materialChanges")),
    18: ("Scientific challenge and alternative explanations", (
        "strongestCounterargument", "alternativeCausality", "biasAndConfounding",
        "contradictionResolution", "ownerCriticalReview")),
    19: ("Prospective decisions and calibration eligibility", (
        "outcomeUnexposedSourceFreeze", "predictionModelArtifact",
        "prospectivePredictionTimestamp", "independentOutcomeSeparation",
        "outOfSampleCalibration")),
    20: ("FDA outcome and review-timing monitoring", (
        "exactApplicationCycleLink", "originalGoalDate", "goalDateRevisions",
        "officialActionAndDate", "postPredictionOutcomeComparison")),
}
assert tuple(LEVELS) == tuple(range(9, 21))

# In these phases or statuses, an absent downstream observation is not a
# negative result. Evidence explicitly supplied by the owner is still checked.
_PRE_APPLICATION = {
    13: {"acceptedFiling", "submissionChronology", "dossierCompleteness", "agencyQuestions"},
    14: {"applicationCycleLink"},
    15: {"officialAdvisoryRecord", "voteAndRationale"},
    16: {"facilityApplicationLink", "inspectionEvidence"},
    20: {"exactApplicationCycleLink", "originalGoalDate", "goalDateRevisions",
         "officialActionAndDate", "postPredictionOutcomeComparison"},
}
_PRE_RESULT = {
    9: {"benefitEvidence", "harmEvidence", "comparabilityAndFollowup",
        "contradictionsAndUncertainty"},
    12: {"populationComparability", "endpointComparability",
         "nonduplicateCohorts", "heterogeneityAndSynthesisPlan"},
}

def _reviewed_criteria(level):
    """Return criterion names with accepted source-reviewed evidence, never scores."""
    if not isinstance(level, dict) or level.get("scientificValidation") != "NOT_VERIFIED" or level.get("fdaPrediction") != "ABSTAIN" or level.get("score") is not None:
        return []
    evidence = level.get("acceptedEvidence")
    if not isinstance(evidence, dict):
        return []
    return sorted(k for k, v in evidence.items()
                  if isinstance(v, dict) and v.get("sourceVerified") is True
                  and v.get("retrievalProvenance") == "RECORDED")

def _benefit_risk_dependencies(prior_levels):
    """Require topic-specific reviewed inputs, not unrelated review counts.

    A reviewed SAP, for example, does not establish reviewed endpoint results.
    These are narrow evidence-presence gates, never scientific validity.
    """
    prior = prior_levels if isinstance(prior_levels, dict) else {}
    details = {}
    for number in ("2", "3", "4", "5", "7", "8"):
        details[number] = _reviewed_criteria(prior.get(number))
    efficacy = {"primaryEndpointResults", "effectSizeAndPrecision"}
    harms = {"adverseEvents", "seriousAdverseEvents", "discontinuations"}
    context = {"indicationDefinition", "clinicalMeaningfulness", "standardOfCareComparator"}
    return {
        "benefitEvidenceReviewed": bool(set(details["3"]) & efficacy),
        "harmEvidenceReviewed": bool(set(details["4"]) & harms
                                     or "exposureAdjustedRates" in details["8"]),
        "indicationContextReviewed": bool(set(details["5"]) & context),
        "populationEvidenceReviewed": ("populationDefinition" in details["7"]
                                       or "populationAndEligibility" in details["2"]),
        "upstreamAcceptedCriterionNames": details,
        "limitations": [
            "Upstream evidence is an inventory of reviewed source records, not a finding of efficacy or safety.",
            "Level 9 requires comparable population, endpoint definitions and follow-up plus explicit owner clinical judgment.",
            "An FDA approval outcome or probability cannot be calculated from these review counts.",
        ],
    }

def assess_levels_nine_to_twenty(level_one, *, trial_id, evidence=None, prior_levels=None):
    """Return independent phase-aware evidence contracts, without claiming engine completion."""
    intake = level_one if isinstance(level_one, dict) else {}
    evidence = evidence if isinstance(evidence, dict) else {}
    pre_app = intake.get("phase") in {"EARLY_PHASE1", "PHASE1", "PHASE2"}
    pre_result = intake.get("trialStatus") in {
        "NOT_YET_RECRUITING", "RECRUITING", "ENROLLING_BY_INVITATION"}
    not_due = set()
    for number, criteria in LEVELS.items():
        for criterion in criteria[1]:
            if (pre_app and criterion in _PRE_APPLICATION.get(number, set())) or (
                    pre_result and criterion in _PRE_RESULT.get(number, set())):
                # A supplied record still undergoes normal evidence checks.
                if not evidence.get(f"{number}.{criterion}"):
                    not_due.add((number, criterion))
    results = assess_review_contracts(
        intake, trial_id=trial_id, evidence=evidence, definitions=LEVELS,
        not_yet_expected=not_due,
    )
    for number, result in results.items():
        result["contractVersion"] = VERSION
        result["methodStatus"] = "EVIDENCE_CONTRACT_ONLY_NOT_IMPLEMENTED_SCIENTIFIC_ENGINE"
        result["validationStatus"] = "NOT_VALIDATED"
        result["limitations"] = [
            "This contract records evidence availability and owner review; it is not a completed scientific assessment.",
            "Unknown or unpublished evidence is not a negative clinical/regulatory finding.",
            "No composite score, FDA approval probability, trading signal or synthetic owner signoff.",
        ]
    nine = results["9"]
    deps = _benefit_risk_dependencies(prior_levels)
    nine["benefitRiskEvidenceAlignment"] = deps
    nine["benefitHarmContextComparison"] = align_benefit_harm(nine, evidence)
    nine["methodStatus"] = "PARTIAL_EVIDENCE_RECONCILIATION_NOT_CLINICAL_CONCLUSION"
    evidence_ready = (deps["benefitEvidenceReviewed"] and deps["harmEvidenceReviewed"]
                      and deps["indicationContextReviewed"])
    context_state = nine["benefitHarmContextComparison"]["status"]
    if not evidence_ready:
        nine["integrationStatus"] = "BLOCKED_UPSTREAM_EVIDENCE"
    elif context_state == "CONTEXT_DIFFERENCES_REQUIRE_OWNER_REVIEW":
        nine["integrationStatus"] = "CONTEXT_DIFFERENCES_REQUIRE_OWNER_REVIEW"
    elif context_state != "DESCRIPTIVE_CONTEXT_ALIGNMENT_ONLY":
        nine["integrationStatus"] = "BLOCKED_LEVEL_NINE_CONTEXT"
    elif nine["reviewReadiness"]["complete"]:
        nine["integrationStatus"] = "REVIEWED_SOURCES_REQUIRE_CLINICAL_SYNTHESIS"
    else:
        nine["integrationStatus"] = "AWAITING_OWNER_BENEFIT_RISK_JUDGMENT"
    ten = results["10"]
    ten["standardOfCareContext"] = compare_standard_care(
        ten, evidence, intake.get("assessmentCutoff"))
    ten["methodStatus"] = "PARTIAL_DATED_CONTEXT_ALIGNMENT_NOT_STANDARD_OF_CARE_VALIDATION"
    eleven = results["11"]
    eleven["therapeuticContext"] = therapeutic_context(
        eleven, evidence, intake.get("assessmentCutoff"))
    eleven["methodStatus"] = "PARTIAL_DESCRIPTIVE_BURDEN_AND_ALTERNATIVES_NOT_UNMET_NEED_VALIDATION"
    twelve = results["12"]
    twelve["replicationCandidates"] = screen_replication_candidates(
        twelve, evidence, trial_id=trial_id, cutoff=intake.get("assessmentCutoff"))
    twelve["methodStatus"] = "PARTIAL_CROSS_STUDY_IDENTITY_SCREEN_NOT_REPLICATION_VALIDATION"
    thirteen = results["13"]
    thirteen["filingContext"] = assess_filing(
        thirteen, evidence, trial_id=trial_id, cutoff=intake.get("assessmentCutoff"))
    thirteen["methodStatus"] = "PARTIAL_EXACT_APPLICATION_SOURCE_RECONCILIATION_NOT_FDA_CERTIFICATION"
    fourteen = results["14"]
    fourteen["designationContext"] = assess_designation(
        fourteen, evidence, trial_id=trial_id, cutoff=intake.get("assessmentCutoff"),
        filing_context=thirteen["filingContext"])
    fourteen["methodStatus"] = "PARTIAL_ORIGINAL_DESIGNATION_SOURCE_LEAD_NOT_FDA_VERIFICATION"
    fifteen = results["15"]
    fifteen["precedentContext"] = assess_precedent(
        fifteen, evidence, cutoff=intake.get("assessmentCutoff"), filing_context=thirteen["filingContext"])
    fifteen["methodStatus"] = "PARTIAL_HISTORICAL_PRECEDENT_SOURCE_SCREEN_NOT_TARGET_PREDICTION"
    sixteen = results["16"]
    sixteen["manufacturingContext"] = assess_manufacturing(
        sixteen, evidence, cutoff=intake.get("assessmentCutoff"), filing_context=thirteen["filingContext"])
    sixteen["methodStatus"] = "PARTIAL_CMC_PUBLIC_RECORD_UNCERTAINTY_SCREEN_NOT_INSPECTION_FINDING"
    seventeen = results["17"]
    seventeen["disclosureContext"] = assess_disclosure(
        seventeen, evidence, trial_id=trial_id, cutoff=intake.get("assessmentCutoff"))
    seventeen["methodStatus"] = "PARTIAL_DATED_DISCLOSURE_CHANGE_SCREEN_NOT_MATERIALITY_FINDING"
    eighteen = results["18"]
    eighteen["challengeContext"] = assess_challenge(
        eighteen, evidence, trial_id=trial_id)
    eighteen["methodStatus"] = "PARTIAL_COUNTERARGUMENT_RECORD_NOT_OWNER_ADJUDICATION"
    nineteen = results["19"]
    nineteen["prospectiveIntegrity"] = assess_prospective_metadata(
        nineteen, evidence, trial_id=trial_id, cutoff=intake.get("assessmentCutoff"))
    nineteen["methodStatus"] = "PARTIAL_FROZEN_FORECAST_METADATA_NOT_CALIBRATED_PREDICTION"
    twenty = results["20"]
    twenty["outcomeChronology"] = assess_outcome_chronology(
        twenty, evidence, trial_id=trial_id, cutoff=intake.get("assessmentCutoff"),
        filing_context=thirteen["filingContext"])
    twenty["methodStatus"] = "PARTIAL_POSTDECISION_ACTION_TIMELINE_NOT_VALIDATED_ACCURACY"
    return results
