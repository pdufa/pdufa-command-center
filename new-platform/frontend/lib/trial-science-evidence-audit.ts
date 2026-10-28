/** Historical trial evidence crosswalk, independent of scores and efficacy. */

export type SourceMilestone = {
  date: string;
  id: string;
  title: string;
  sourceUrl: string;
  sourceLocator: string;
  evidenceStatus: string;
  finding: string;
  limitation: string;
  proofOfOriginalSap: false;
};

export type SourceSafetyGroup = {
  groupId: string;
  title: string;
  sourceLocator: string;
  counts: Record<"seriousEvents" | "otherEvents" | "deaths", {
    numAffected: number | null;
    numAtRisk: number | null;
    population: "registry_event_group_as_reported";
    sourceFields: string[];
  }>;
  independentlyVerified: false;
};

export type SourceEvidenceAudit = {
  nctId: "NCT02142738";
  assessmentStatus: "historical_evidence_crosswalk_only";
  timeline: SourceMilestone[];
  earlyDesignEvidence: {
    status: "public_trial_design_reported_pre_cutoff";
    sourceUrl: string;
    publicationDate: "2015-05-20";
    primaryEndpoint: string;
    secondaryEndpoints: string[];
    preinterimDocumentVerified: false;
    signedSapVerified: false;
    originalMultiplicityVerified: false;
  };
  registrySafety: {
    sourceUrl: string;
    sourceType: "checksum_verified_archive_registry_posting";
    status: "groups_reported" | "no_groups_documented_in_snapshot";
    groups: SourceSafetyGroup[];
    groupCount: number;
    treatmentSwitchGroupsMayExist: true;
    randomizedArmComparisonValidated: false;
    publishedTreatmentRelatedAeRatesReconciled: false;
    missingGroupsDoNotImplyZeroEvents: true;
    note: string;
  };
  readOnly: true;
  scientificScore: null;
  fdaApprovalProbability: null;
  inputReadinessGradeChanged: false;
  reluctanceGradeChanged: false;
  independentProtocolSapReviewComplete: false;
  tradingActionsEnabled: false;
};

const NCT = "NCT02142738";
const ASCO = "https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103";
const LATER = "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf";
const REGISTRY = "https://clinicaltrials.gov/study/NCT02142738";
const EXPECTED_MILESTONES = [
  ["2015-05-20", "contemporaneous_trial_design", ASCO,
   "public_description_before_cutoff"],
  ["2016-05-09", "primary_analysis_cutoff",
   "https://pubmed.ncbi.nlm.nih.gov/27718847/",
   "cutoff_reported_retrospectively"],
  ["2016-10-08", "original_results_published",
   "https://pubmed.ncbi.nlm.nih.gov/27718847/",
   "published_results"],
  ["2016-10-08", "supplementary_protocol_listed",
   "https://doi.org/10.1056/NEJMoa1606774",
   "linked_document_not_content_reviewed"],
  ["2017-12-20", "later_protocol_date", LATER,
   "document_date_reported"],
  ["2020-06-01", "long_term_followup_cutoff",
   "https://pubmed.ncbi.nlm.nih.gov/33872070/",
   "cutoff_reported_retrospectively"],
  ["2021-04-19", "long_term_analysis_published",
   "https://pubmed.ncbi.nlm.nih.gov/33872070/",
   "published_results"],
] as const;

function obj(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}
function str(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 1600;
}
function count(value: unknown): boolean {
  return value === null || (typeof value === "number" &&
    Number.isInteger(value) && value >= 0 && value <= 100000);
}

export function validSourceEvidenceAudit(input: unknown): input is SourceEvidenceAudit {
  if (!obj(input) || input.nctId !== NCT
      || input.assessmentStatus !== "historical_evidence_crosswalk_only"
      || !Array.isArray(input.timeline) || input.timeline.length !== 7
      || !obj(input.earlyDesignEvidence) || !obj(input.registrySafety)
      || input.readOnly !== true || input.scientificScore !== null
      || input.fdaApprovalProbability !== null
      || input.inputReadinessGradeChanged !== false
      || input.reluctanceGradeChanged !== false
      || input.independentProtocolSapReviewComplete !== false
      || input.tradingActionsEnabled !== false) return false;

  for (let i = 0; i < EXPECTED_MILESTONES.length; i++) {
    const row = input.timeline[i];
    const [date, id, url, status] = EXPECTED_MILESTONES[i];
    if (!obj(row) || row.date !== date || row.id !== id
        || row.sourceUrl !== url || row.evidenceStatus !== status
        || row.proofOfOriginalSap !== false
        || !str(row.title) || !str(row.finding)
        || !str(row.sourceLocator) || !str(row.limitation)) return false;
  }
  const early = input.earlyDesignEvidence;
  if (early.status !== "public_trial_design_reported_pre_cutoff"
      || early.sourceUrl !== ASCO || early.publicationDate !== "2015-05-20"
      || early.primaryEndpoint !== "progression_free_survival_by_central_RECIST1_1"
      || !Array.isArray(early.secondaryEndpoints)
      || early.secondaryEndpoints.join("|") !==
         "objective_response_rate|overall_survival|safety"
      || early.preinterimDocumentVerified !== false
      || early.signedSapVerified !== false
      || early.originalMultiplicityVerified !== false) return false;

  const safety = input.registrySafety;
  if (safety.sourceUrl !== REGISTRY
      || safety.sourceType !== "checksum_verified_archive_registry_posting"
      || !Array.isArray(safety.groups) || safety.groups.length > 24
      || safety.groupCount !== safety.groups.length
      || safety.status !== (safety.groups.length ?
          "groups_reported" : "no_groups_documented_in_snapshot")
      || safety.treatmentSwitchGroupsMayExist !== true
      || safety.randomizedArmComparisonValidated !== false
      || safety.publishedTreatmentRelatedAeRatesReconciled !== false
      || safety.missingGroupsDoNotImplyZeroEvents !== true
      || !str(safety.note)) return false;

  const ids = new Set<string>();
  for (let i = 0; i < safety.groups.length; i++) {
    const group = safety.groups[i];
    if (!obj(group) || !str(group.groupId) || !str(group.title)
        || ids.has(group.groupId) || group.independentlyVerified !== false
        || group.sourceLocator !==
          `resultsSection.adverseEventsModule.eventGroups[${i}]`
        || !obj(group.counts)) return false;
    ids.add(group.groupId);
    for (const [category, affectedKey, atRiskKey] of [
      ["seriousEvents", "seriousNumAffected", "seriousNumAtRisk"],
      ["otherEvents", "otherNumAffected", "otherNumAtRisk"],
      ["deaths", "deathsNumAffected", "deathsNumAtRisk"],
    ]) {
      const item = group.counts[category];
      if (!obj(item) || !count(item.numAffected) || !count(item.numAtRisk)
          || item.population !== "registry_event_group_as_reported"
          || !Array.isArray(item.sourceFields)
          || item.sourceFields.length !== 2
          || item.sourceFields[0] !== `${group.sourceLocator}.${affectedKey}`
          || item.sourceFields[1] !== `${group.sourceLocator}.${atRiskKey}`
          || (typeof item.numAffected === "number" &&
              typeof item.numAtRisk === "number" &&
              item.numAffected > item.numAtRisk)) return false;
    }
  }
  return true;
}
