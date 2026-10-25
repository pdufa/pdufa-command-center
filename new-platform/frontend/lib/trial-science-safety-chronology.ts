/** Historical KEYNOTE-024 as-treated AE counts and 2019 follow-up provenance.
 * Every numerical statement below is checked against an exact known source
 * before it can reach the UI. This is not an independent safety assessment.
 */
export type TreatedSafetyRow = {
  classification: string;
  pembrolizumab: { affected: number; atRisk: number; reportedPercent: number };
  chemotherapy: { affected: number; atRisk: number; reportedPercent: number };
  sourceUrl: string;
  sourceLocator: string;
  treatmentRelated: true;
  sourceReportedNotIndependentlyVerified: true;
};

export type SafetyChronology = {
  nctId: "NCT02142738";
  status: "published_safety_source_reconciliation_only";
  original2016: {
    analysisId: "keynote024_initial_2016";
    publicationDate: "2016-10-08";
    dataCutoffDate: "2016-05-09";
    sourceUrl: string;
    sourcePubMed: string;
    randomized: { pembrolizumab: number; chemotherapy: number };
    asTreated: { pembrolizumab: number; chemotherapy: number };
    unexposedChemotherapyRandomized: 1;
    reportedTreatRelatedSafety: TreatedSafetyRow[];
    roundingArithmeticChecked: true;
    patientLevelVerified: false;
    clinicalSafetyAppraisalComplete: false;
  };
  immuneMediated2016: {
    sourceUrl: string;
    sourceLocator: string;
    causalityDefinition: "regardless_of_investigator_treatment_attribution";
    anyGradePercent: { pembrolizumab: number; chemotherapy: number };
    grade3to4Percent: { pembrolizumab: number; chemotherapy: number };
    noGrade5ImmuneMediatedEventsReported: true;
    notEquivalentToTreatmentRelatedAE: true;
  };
  updated2019: {
    sourceId: "30620668";
    sourceUrl: string;
    publicationDate: "2019-01-08";
    analysisDataCutoff: "2017-07-10";
    randomized: { pembrolizumab: number; chemotherapy: number };
    reportedGrade3to5TreatmentRelatedPercent: {
      pembrolizumab: number; chemotherapy: number;
    };
    reportedOnStudyCrossoverPatients: 82;
    intentionToTreatOS: { hazardRatio: number; ci95: number[] };
    twoStageCrossoverAdjustedOS: { hazardRatio: number; ci95: number[] };
    crossoverAdjustedInterpretation: "model_based_sensitivity_not_randomized_estimate";
    publishedAEAffectedCountsExtracted: false;
    mustNotOverwriteOriginal2016: true;
  };
  registryReconciliation: {
    archivedGroupsObserved: number;
    sourceUrl: string;
    countsPooledAcrossTreatmentCourses: false;
    registryAEGroupMatchesJournalTRAE: false;
    registryUsesDistinctCategoriesAndPossibleCrossover: true;
    publishedSafetyDenominatorsIdentified: true;
    crossSystemAEReconciliationCompleted: false;
    missingOriginalSapStillBlocking: true;
    nextAction: string;
  };
  scientificScore: null;
  fdaApprovalProbability: null;
  inputReadinessGradeChanged: false;
  reluctanceGradeChanged: false;
  readOnly: true;
  tradingActionsEnabled: false;
};

const ORIGINAL = "https://www.nejm.org/doi/full/10.1056/nejmoa1606774";
const PUBMED = "https://pubmed.ncbi.nlm.nih.gov/27718847/";
const FOLLOWUP = "https://pubmed.ncbi.nlm.nih.gov/30620668/";
const REGISTRY = "https://clinicaltrials.gov/study/NCT02142738";

// Source-attributed category identities and exact original 2016 table cells.
// Intentionally NOT computed by pooling ClinicalTrials.gov event groups.
const EXPECTED: readonly [string, number, number, number, number][] = [
  ["treatment_related_any_grade", 113, 135, 73.4, 90.0],
  ["treatment_related_grade_3_to_5", 41, 80, 26.6, 53.3],
  ["serious_treatment_related_any_grade", 33, 31, 21.4, 20.7],
  ["treatment_related_discontinuation_any_grade", 11, 16, 7.1, 10.7],
  ["treatment_related_death", 1, 3, 0.6, 2.0],
];

const obj = (x: unknown): x is Record<string, unknown> =>
  x !== null && typeof x === "object" && !Array.isArray(x);
const literalPair = (x: unknown, p: number, c: number): boolean =>
  obj(x) && x.pembrolizumab === p && x.chemotherapy === c;
function exactRate(x: unknown, affected: number, risk: number, reported: number): boolean {
  return obj(x) && x.affected === affected && x.atRisk === risk &&
    x.reportedPercent === reported &&
    Math.abs(100 * affected / risk - reported) < 0.051;
}

export function validSafetyChronology(x: unknown): x is SafetyChronology {
  if (!obj(x) || x.nctId !== "NCT02142738"
      || x.status !== "published_safety_source_reconciliation_only"
      || x.readOnly !== true || x.tradingActionsEnabled !== false
      || x.scientificScore !== null || x.fdaApprovalProbability !== null
      || x.inputReadinessGradeChanged !== false
      || x.reluctanceGradeChanged !== false
      || !obj(x.original2016) || !obj(x.updated2019)
      || !obj(x.immuneMediated2016) || !obj(x.registryReconciliation)) return false;
  const first = x.original2016;
  if (first.analysisId !== "keynote024_initial_2016"
      || first.publicationDate !== "2016-10-08"
      || first.dataCutoffDate !== "2016-05-09"
      || first.sourceUrl !== ORIGINAL || first.sourcePubMed !== PUBMED
      || !literalPair(first.randomized, 154, 151)
      || !literalPair(first.asTreated, 154, 150)
      || first.unexposedChemotherapyRandomized !== 1
      || first.roundingArithmeticChecked !== true
      || first.patientLevelVerified !== false
      || first.clinicalSafetyAppraisalComplete !== false
      || !Array.isArray(first.reportedTreatRelatedSafety)
      || first.reportedTreatRelatedSafety.length !== EXPECTED.length) return false;
  for (let i = 0; i < EXPECTED.length; i++) {
    const row = first.reportedTreatRelatedSafety[i];
    const [label, p, c, percentP, percentC] = EXPECTED[i];
    if (!obj(row) || row.classification !== label
        || !exactRate(row.pembrolizumab, p, 154, percentP)
        || !exactRate(row.chemotherapy, c, 150, percentC)
        || row.sourceUrl !== ORIGINAL
        || row.sourceLocator !== "Table 3: Adverse Events in the As-Treated Population"
        || row.treatmentRelated !== true
        || row.sourceReportedNotIndependentlyVerified !== true) return false;
  }
  const immune = x.immuneMediated2016;
  if (immune.sourceUrl !== ORIGINAL
      || immune.sourceLocator !== "Original manuscript Table 3 and Adverse Events narrative"
      || immune.causalityDefinition !== "regardless_of_investigator_treatment_attribution"
      || !literalPair(immune.anyGradePercent, 29.2, 4.7)
      || !literalPair(immune.grade3to4Percent, 9.7, 0.7)
      || immune.noGrade5ImmuneMediatedEventsReported !== true
      || immune.notEquivalentToTreatmentRelatedAE !== true) return false;
  const followup = x.updated2019;
  if (followup.sourceId !== "30620668"
      || followup.sourceUrl !== FOLLOWUP
      || followup.publicationDate !== "2019-01-08"
      || followup.analysisDataCutoff !== "2017-07-10"
      || !literalPair(followup.randomized, 154, 151)
      || !literalPair(followup.reportedGrade3to5TreatmentRelatedPercent, 31.2, 53.3)
      || followup.reportedOnStudyCrossoverPatients !== 82
      || !obj(followup.intentionToTreatOS)
      || followup.intentionToTreatOS.hazardRatio !== 0.63
      || JSON.stringify(followup.intentionToTreatOS.ci95) !== JSON.stringify([0.47, 0.86])
      || !obj(followup.twoStageCrossoverAdjustedOS)
      || followup.twoStageCrossoverAdjustedOS.hazardRatio !== 0.49
      || JSON.stringify(followup.twoStageCrossoverAdjustedOS.ci95) !== JSON.stringify([0.34, 0.69])
      || followup.crossoverAdjustedInterpretation !== "model_based_sensitivity_not_randomized_estimate"
      || followup.publishedAEAffectedCountsExtracted !== false
      || followup.mustNotOverwriteOriginal2016 !== true) return false;
  const reg = x.registryReconciliation;
  return reg.sourceUrl === REGISTRY
    && typeof reg.archivedGroupsObserved === "number"
    && Number.isInteger(reg.archivedGroupsObserved)
    && reg.archivedGroupsObserved >= 0 && reg.archivedGroupsObserved <= 24
    && reg.countsPooledAcrossTreatmentCourses === false
    && reg.registryAEGroupMatchesJournalTRAE === false
    && reg.registryUsesDistinctCategoriesAndPossibleCrossover === true
    && reg.publishedSafetyDenominatorsIdentified === true
    && reg.crossSystemAEReconciliationCompleted === false
    && reg.missingOriginalSapStillBlocking === true
    && typeof reg.nextAction === "string"
    && reg.nextAction.length >= 15 && reg.nextAction.length <= 400;
}
