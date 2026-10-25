/** EU EudraCT KEYNOTE-024 source corroboration, NOT signed pre-interim SAP. */

export type EuProtocolCrosscheck = {
  nctId: "NCT02142738";
  schemaVersion: "historical-eu-registered-plan-crosscheck-v1";
  status: "cross_source_description_agrees_without_sap_verification";
  registry: {
    eudractNumber: "2014-000323-25";
    sponsorProtocolCode: "MK-3475-024";
    recordCountry: "Netherlands";
    sourceUrl: string;
    firstRecordEnteredDate: "2014-06-19";
    competentAuthorityDecisionDate: "2014-06-19";
    recordFirstEnteredBeforeInterim: true;
    individualEndpointFieldVersionDated: false;
    original2014FieldContentAuthenticated: false;
    signed2016SAPAvailable: false;
    authoredBySeparateOrganization: false;
    explanation: string;
  };
  identityBridge: {
    nciSourceUrl: string;
    nciTrialId: "NCT02142738";
    nciSecondaryId: "2014-000323-25";
    protocolCode: "MK-3475-024";
    separateClinicalTrial: false;
    identityCrosscheckOnly: true;
  };
  comparisons: {
    key: string;
    euSection: string;
    euReportedFinding: string;
    mappedPublishedConcept: string;
    reportedPlannedCount: number | null;
    crossSourceAgreement: true;
    euSourceUrl: string;
    revisionHistoryVerified: false;
    independentSignedSAPConfirmation: false;
  }[];
  eventTiming: {
    euPfsEventsTargetApprox: 175;
    reportedPfsEventsObserved: 189;
    euOsFirstDeathsTargetApprox: 110;
    reportedOsInterimDeathsObserved: 108;
    euOsLaterDeathsTargetApprox: 170;
    euAllowsPfsTimingDelayIfOsUnder110: true;
    euSourceSection: "E.5.1.1";
    actualDataMonitoringCommitteeTimingReconciled: false;
    eventDifferenceNotAutomaticProtocolDeviation: true;
    nextAction: string;
  };
  earlierPublicDescription: {
    sourceUrl: string;
    publicationDate: "2015-05-20";
    supportsPrimaryEndpointAndCentralReview: true;
    originalSapAuthenticated: false;
  };
  researchConclusions: {
    primaryPfsDesignCorroboratedAcrossSources: true;
    approximateEventTargetsAgreeAcrossSources: true;
    alphaSpendingInEuRegistryVerified: false;
    originalEffectiveProtocolAmendmentsVerified: false;
    preInterimSignedSapVerified: false;
    independentReplicationCompleted: false;
    safetyBenefitRiskAdjudicated: false;
    inputReadinessGradeChanged: false;
    reluctanceGradeChanged: false;
    canBeUsedToAssignClinicalSuccessGrade: false;
  };
  scientificScore: null;
  fdaApprovalProbability: null;
  readOnly: true;
  tradingActionsEnabled: false;
  fsFaModified: false;
};

const EU = "https://www.clinicaltrialsregister.eu/ctr-search/trial/2014-000323-25/NL";
const NCI = "https://www.cancer.gov/research/participate/clinical-trials-search/v?id=NCT02142738";
const ASCO = "https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103";
const MATCHES = [
  ["primary_pfs", "E.5.1", "PFS per RECIST 1.1 by blinded central review",
    "progression_free_survival", null],
  ["planned_pfs_events", "E.5.1.1", "Approximately 175 PFS events",
    "progression_free_survival", 175],
  ["planned_os_first", "E.5.2.1", "Approximately 110 deaths",
    "overall_survival", 110],
  ["planned_os_second", "E.5.2.1", "Approximately 170 deaths",
    "overall_survival", 170],
  ["secondary_os_orr", "E.5.2", "OS and centrally reviewed ORR are secondary",
    "secondary_endpoints", null],
  ["monitoring_and_design", "E.8.1 and E.8.7",
    "Open-label randomized Phase 3 with data monitoring committee",
    "trial_design", null],
] as const;

function object(x: unknown): x is Record<string, unknown> {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}
function safeText(x: unknown): x is string {
  return typeof x === "string" && x.trim().length > 0 && x.length <= 480;
}
export function validEuProtocolCrosscheck(value: unknown): value is EuProtocolCrosscheck {
  if (!object(value) || value.nctId !== "NCT02142738"
      || value.schemaVersion !== "historical-eu-registered-plan-crosscheck-v1"
      || value.status !== "cross_source_description_agrees_without_sap_verification"
      || !object(value.registry) || !object(value.identityBridge)
      || !Array.isArray(value.comparisons) || value.comparisons.length !== MATCHES.length
      || !object(value.eventTiming) || !object(value.earlierPublicDescription)
      || !object(value.researchConclusions)
      || value.scientificScore !== null || value.fdaApprovalProbability !== null
      || value.readOnly !== true || value.tradingActionsEnabled !== false
      || value.fsFaModified !== false) return false;
  const r = value.registry;
  if (r.eudractNumber !== "2014-000323-25" || r.sponsorProtocolCode !== "MK-3475-024"
      || r.recordCountry !== "Netherlands" || r.sourceUrl !== EU
      || r.firstRecordEnteredDate !== "2014-06-19"
      || r.competentAuthorityDecisionDate !== "2014-06-19"
      || r.recordFirstEnteredBeforeInterim !== true
      || r.individualEndpointFieldVersionDated !== false
      || r.original2014FieldContentAuthenticated !== false
      || r.signed2016SAPAvailable !== false
      || r.authoredBySeparateOrganization !== false
      || !safeText(r.explanation)) return false;
  const b = value.identityBridge;
  if (b.nciSourceUrl !== NCI || b.nciTrialId !== "NCT02142738"
      || b.nciSecondaryId !== "2014-000323-25"
      || b.protocolCode !== "MK-3475-024"
      || b.separateClinicalTrial !== false || b.identityCrosscheckOnly !== true) return false;
  for (let i = 0; i < MATCHES.length; i++) {
    const item = value.comparisons[i];
    const expected = MATCHES[i];
    if (!object(item) || item.key !== expected[0] || item.euSection !== expected[1]
        || item.euReportedFinding !== expected[2]
        || item.mappedPublishedConcept !== expected[3]
        || item.reportedPlannedCount !== expected[4]
        || item.crossSourceAgreement !== true
        || item.euSourceUrl !== EU
        || item.revisionHistoryVerified !== false
        || item.independentSignedSAPConfirmation !== false) return false;
  }
  const e = value.eventTiming;
  if (e.euPfsEventsTargetApprox !== 175 || e.reportedPfsEventsObserved !== 189
      || e.euOsFirstDeathsTargetApprox !== 110 || e.reportedOsInterimDeathsObserved !== 108
      || e.euOsLaterDeathsTargetApprox !== 170
      || e.euAllowsPfsTimingDelayIfOsUnder110 !== true
      || e.euSourceSection !== "E.5.1.1"
      || e.actualDataMonitoringCommitteeTimingReconciled !== false
      || e.eventDifferenceNotAutomaticProtocolDeviation !== true
      || !safeText(e.nextAction)) return false;
  const prior = value.earlierPublicDescription;
  if (prior.sourceUrl !== ASCO || prior.publicationDate !== "2015-05-20"
      || prior.supportsPrimaryEndpointAndCentralReview !== true
      || prior.originalSapAuthenticated !== false) return false;
  const c = value.researchConclusions;
  return c.primaryPfsDesignCorroboratedAcrossSources === true
    && c.approximateEventTargetsAgreeAcrossSources === true
    && c.alphaSpendingInEuRegistryVerified === false
    && c.originalEffectiveProtocolAmendmentsVerified === false
    && c.preInterimSignedSapVerified === false
    && c.independentReplicationCompleted === false
    && c.safetyBenefitRiskAdjudicated === false
    && c.inputReadinessGradeChanged === false
    && c.reluctanceGradeChanged === false
    && c.canBeUsedToAssignClinicalSuccessGrade === false;
}
