"""Source-bound scientific L04–L06 review engines for opt-in SCIENTIFIC_1_6.

Distinct from the LEGACY_SOURCE_AUDIT 4–6 taxonomy. These return checkable
findings and explicit unknowns, NEVER validated clinical scores or FDA odds.
"""
from __future__ import annotations

from .scientific_trial_assessment import observed, finding

NAMES = {
    4: "Safety and benefit-risk",
    5: "Indication-specific clinical assessment",
    6: "FDA regulatory readiness",
}


def source_check(identity, value, explanation, locator, source, *, expected=True):
    check = observed(identity, value, explanation, locator, source)
    if check["state"] == "MISSING" and not expected:
        check["state"] = "NOT_YET_EXPECTED"
    return check


def level_four(doc, context, source, documents):
    """Separately retain posted harms, participant exposure and uncertainty."""
    results = doc.get("resultsSection", {})
    harms = results.get("adverseEventsModule", {})
    flow = results.get("participantFlowModule", {})
    expected = context["resultsExpected"]
    checks = [
        source_check("adverse_event_reporting", harms, "Registry-posted harms are source observations, not proof of adequate safety ascertainment.", "resultsSection.adverseEventsModule", source, expected=expected),
        source_check("serious_adverse_events", harms.get("seriousEvents"), "Serious adverse-event listings require arm-specific denominators, exposure duration and causality review.", "resultsSection.adverseEventsModule.seriousEvents", source, expected=expected),
        source_check("other_adverse_events", harms.get("otherEvents"), "Other adverse-event listings require frequency thresholds, follow-up and ascertainment context.", "resultsSection.adverseEventsModule.otherEvents", source, expected=expected),
        source_check("event_group_exposure", harms.get("eventGroups"), "Reported harm-group denominators are not exposure-adjusted rates without a supported calculation.", "resultsSection.adverseEventsModule.eventGroups", source, expected=expected),
        source_check("participant_flow", flow, "Withdrawal and participant flow inform exposure and missingness; recorded flow does not prove balanced follow-up.", "resultsSection.participantFlowModule", source, expected=expected),
        finding("benefit_risk_interpretation", "UNVERIFIED" if expected else "NOT_YET_EXPECTED",
                "No automatic favorable benefit-risk decision is possible from registry harms alone; reconcile severity, exposure, comparator and patient-relevant efficacy.", "clinical benefit-risk review"),
    ]
    return checks, [{
        "postedSafety": harms if harms else None,
        "postedParticipantFlow": flow if flow else None,
        "interpretation": "Non-public safety observations remain unknown, not zero events or evidence of safety.",
    }]


def level_five(doc, context, source, documents):
    """Indication-specific clinical questions without unsupported thresholds."""
    protocol = doc["protocolSection"]
    arms = protocol["armsInterventionsModule"].get("armGroups", [])
    eligible = protocol["eligibilityModule"]
    primary = protocol["outcomesModule"].get("primaryOutcomes", [])
    checks = [
        source_check("indication_definition", context["conditions"], "Only the exact registered conditions define this trial's indication; application labeling is separate.", "protocolSection.conditionsModule.conditions", source),
        source_check("population_eligibility", eligible, "Registered eligibility limits generalizability; enrolled baseline characteristics need separate evidence.", "protocolSection.eligibilityModule", source),
        source_check("registered_comparator", arms, "Registry arms identify intended comparators, not independently verified standard of care.", "protocolSection.armsInterventionsModule.armGroups", source),
        source_check("patient_important_endpoint", primary, "Endpoint definitions alone do not establish a clinically meaningful effect or validated surrogate.", "protocolSection.outcomesModule.primaryOutcomes", source),
        finding("standard_of_care_context", "UNVERIFIED", "Disease-, line-, setting- and date-specific standard of care is not authenticated by a trial registry arm label.", "independent indication-specific clinical evidence"),
        finding("meaningful_effect_threshold", "UNVERIFIED" if context["resultsExpected"] else "NOT_YET_EXPECTED",
                "An indication- and population-specific meaningful-benefit threshold requires sourced clinical context; no generic cutoff is assigned.", "disease-specific meaningful-benefit evidence"),
        finding("subgroup_generalizability", "UNVERIFIED" if context["resultsExpected"] else "NOT_YET_EXPECTED",
                "Subgroup effects, multiplicity and external validity need source-supported subgroup measurements and prespecification.", "enrollment and subgroup clinical evidence"),
    ]
    return checks, [{
        "indicationQuestions": context["indicationAnalysis"],
        "registeredArms": arms,
        "registeredEndpoints": primary,
        "limitation": "Neither registry comparator labels nor endpoint wording prove treatment advantage over current care.",
    }]


def level_six(doc, context, source, documents):
    """Application readiness is unknown without exact verified regulatory records."""
    protocol = doc["protocolSection"]
    phase = context["phases"]
    early = bool(phase) and all(p in {"EARLY_PHASE1", "PHASE1", "PHASE2"} for p in phase)
    state = "NOT_YET_EXPECTED" if early else "UNVERIFIED"
    checks = [
        source_check("registered_trial_identity", protocol["identificationModule"].get("nctId"),
                     "An exact NCT identifies a clinical trial, not an FDA submission or review cycle.",
                     "protocolSection.identificationModule.nctId", source),
        finding("application_identity_and_pathway", state,
                "No exact verified drug, indication, application ID and FDA review-cycle evidence is installed in this trial-only execution.", "verified FDA submission and pathway records"),
        finding("agency_interactions", state,
                "Trial registration does not prove FDA agreement, meeting outcomes, acceptance or review timing.", "original FDA correspondence and meeting records"),
        finding("application_dossier", state,
                "Do not infer an accepted application or complete dossier from Phase 3 completion, source postings or a PDUFA date on an owner roster.", "verified application dossier"),
        finding("manufacturing_and_inspection", state,
                "Non-public CMC and inspection findings are unknown, not evidence of deficiencies or clearance.", "verified CMC and inspection records"),
        finding("label_and_risk_mitigation", state,
                "No labeling, REMS or postmarketing obligations can be assumed without verified application-specific evidence.", "verified FDA labeling and risk-mitigation records"),
    ]
    return checks, [{
        "regulatoryIdentity": "UNVERIFIED_NO_APPLICATION_IDENTITY",
        "applicationOutcome": "NOT_EVALUATED",
        "reviewTiming": "NOT_EVALUATED",
        "limitation": "No FDA approval prediction or probability is derived from registry evidence alone.",
    }]


ENGINES = {4: level_four, 5: level_five, 6: level_six}
