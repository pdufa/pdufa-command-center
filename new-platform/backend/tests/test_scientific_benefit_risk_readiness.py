"""Level 9 evidence readiness must not be satisfied by unrelated reviewed topics."""
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_levels_nine_to_twenty import NCT, intake, reviewed_record


def context(endpoint, **changes):
    return {
        "endpoint": endpoint, "population": "ITT",
        "treatmentArm": "Drug", "comparatorArm": "Placebo",
        "timeOrigin": "Randomization", "followupDays": 90, **changes,
    }


def review(data=None):
    value = reviewed_record()
    if data is not None:
        value["measurements"] = data
    return value


def prior(efficacy="statisticalAnalysisPlan", harm="exposureAndFollowup",
          indication="unmetNeedContext"):
    def level(criterion):
        return {
            "score": None, "scientificValidation": "NOT_VERIFIED",
            "fdaPrediction": "ABSTAIN",
            "acceptedEvidence": {criterion: {
                "sourceVerified": True, "retrievalProvenance": "RECORDED"
            }},
        }
    return {
        "3": level(efficacy), "4": level(harm),
        "5": level(indication),
    }


def assess(upstream, benefit=None, harm=None):
    return assess_levels_nine_to_twenty(
        intake(), trial_id=NCT,
        evidence={
            "9.benefitEvidence": review(benefit) if benefit is not None else review(),
            "9.harmEvidence": review(harm) if harm is not None else review(),
        },
        prior_levels=upstream,
    )["9"]


def test_unrelated_review_counts_do_not_establish_benefit_harm_ready():
    result = assess(prior())
    flags = result["benefitRiskEvidenceAlignment"]
    assert flags["benefitEvidenceReviewed"] is False
    assert flags["harmEvidenceReviewed"] is False
    assert flags["indicationContextReviewed"] is False
    assert result["integrationStatus"] == "BLOCKED_UPSTREAM_EVIDENCE"
    assert result["score"] is None


def test_on_topic_upstream_review_is_still_not_enough_without_level9_measurements():
    result = assess(prior("primaryEndpointResults", "seriousAdverseEvents", "indicationDefinition"))
    flags = result["benefitRiskEvidenceAlignment"]
    assert flags["benefitEvidenceReviewed"] is True
    assert flags["harmEvidenceReviewed"] is True
    assert flags["indicationContextReviewed"] is True
    assert result["benefitHarmContextComparison"]["status"] == "REJECTED_MEASUREMENTS"
    assert result["integrationStatus"] == "BLOCKED_LEVEL_NINE_CONTEXT"
    assert result["fdaPrediction"] == "ABSTAIN"


def test_different_population_does_not_create_reconciled_benefit_risk():
    result = assess(
        prior("effectSizeAndPrecision", "adverseEvents", "clinicalMeaningfulness"),
        context("Benefit"), context("Serious harms", population="SAFETY"))
    assert result["integrationStatus"] == "CONTEXT_DIFFERENCES_REQUIRE_OWNER_REVIEW"
    assert result["benefitHarmContextComparison"]["comparability"] == "NOT_ESTABLISHED"
    assert result["score"] is None


def test_matching_metadata_remains_unvalidated_owner_review_question():
    result = assess(
        prior("primaryEndpointResults", "seriousAdverseEvents", "indicationDefinition"),
        context("Response"), context("Harm"))
    assert result["integrationStatus"] == "AWAITING_OWNER_BENEFIT_RISK_JUDGMENT"
    assert result["benefitHarmContextComparison"]["status"] == "DESCRIPTIVE_CONTEXT_ALIGNMENT_ONLY"
    assert result["score"] is None
    assert result["fdaPrediction"] == "ABSTAIN"


def test_reviewed_statistical_plan_alone_is_not_efficacy_review():
    upstream = prior("statisticalAnalysisPlan", "adverseEvents", "indicationDefinition")
    result = assess(upstream, context("Benefit"), context("Harm"))
    assert result["integrationStatus"] == "BLOCKED_UPSTREAM_EVIDENCE"
