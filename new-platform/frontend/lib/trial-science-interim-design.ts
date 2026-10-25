/** Published 2016 KEYNOTE-024 interim plan is not authenticated prospective SAP. */
export type PublishedInterimDesign = {
  nctId: "NCT02142738";
  status: "published_design_not_authenticated_original_sap";
  sourceDateContext: {
    originalInterimDataCutoff: "2016-05-09";
    journalSourceUrl: string;
    journalLocator: string;
    fdaStaffSourceUrl: string;
    fdaStaffLocator: string;
    originalSupplementSourceUrl: string;
    originalSupplementFilename: "nejmoa1606774_protocol.pdf";
    originalSupplementRead: false;
    contemporaneousSapAuthenticated: false;
  };
  reportedDesign: {
    overallOneSidedAlphaPercent: 2.5;
    firstInterim: {
      plannedMinimumRandomized: 191;
      plannedMinimumFollowupMonths: 6;
      testingEndpoint: "objective_response_rate";
      reportedAllocatedOneSidedAlphaPercent: 0.5;
      sourceUrl: string;
      sourceLocator: string;
      prespecificationIndependentlyConfirmed: false;
    };
    secondInterim: {
      plannedApproximatePfsEvents: 175;
      testingEndpoint: "progression_free_survival";
      reportedAllocatedOneSidedAlphaPercent: 2.0;
      sourceUrl: string;
      sourceLocator: string;
      prespecificationIndependentlyConfirmed: false;
    };
    osGroupSequential: {
      plannedApproximateDeaths: [number, number];
      sourceUrl: string;
      sourceLocator: string;
      prespecificationIndependentlyConfirmed: false;
    };
    descriptionPublishedAfterCutoff: true;
    signedOriginalPlanAuthenticated: false;
  };
  observedInterim: {
    reportedPfsEvents: 189;
    reportedDeaths: 108;
    pfsHR: 0.50;
    pfsCi95: [number, number];
    reportedPfsPValue: "<0.001";
    osHR: 0.60;
    osCi95: [number, number];
    reportedOsPValue: 0.005;
    fdaStaffReportedOsAllocatedAlpha: 0.0118;
    comparisonStatus: "source_reported_not_recalculated";
    fdaStaffArticleIsNotFullAgencyClinicalReview: true;
  };
  reconciliation: {
    historicalResultsSourceChecked: true;
    independentOriginalSAPReviewComplete: false;
    alphaSpendingRecomputedFromSignedSAP: false;
    patientLevelReanalysisComplete: false;
    scientificConclusionAuthorized: false;
    inputReadinessGradeChanged: false;
    reluctanceGradeChanged: false;
    missingCriticalSources: string[];
    nextAction: string;
  };
  scientificScore: null;
  fdaApprovalProbability: null;
  readOnly: true;
  tradingActionsEnabled: false;
  fsFaModified: false;
};

const JOURNAL = "https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774";
const FULL = "https://www.nejm.org/doi/full/10.1056/nejmoa1606774";
const FDA = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/";

function obj(x: unknown): x is Record<string, unknown> {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}
function text(x: unknown): x is string {
  return typeof x === "string" && x.length > 0 && x.length < 500;
}
function exactNumbers(x: unknown, numbers: readonly number[]): boolean {
  return Array.isArray(x) && x.length === numbers.length &&
    numbers.every((expected, index) => x[index] === expected);
}

export function validPublishedInterimDesign(x: unknown): x is PublishedInterimDesign {
  if (!obj(x) || x.nctId !== "NCT02142738"
      || x.status !== "published_design_not_authenticated_original_sap"
      || !obj(x.sourceDateContext) || !obj(x.reportedDesign)
      || !obj(x.observedInterim) || !obj(x.reconciliation)
      || x.scientificScore !== null || x.fdaApprovalProbability !== null
      || x.readOnly !== true || x.tradingActionsEnabled !== false
      || x.fsFaModified !== false) return false;

  const source = x.sourceDateContext;
  if (source.originalInterimDataCutoff !== "2016-05-09"
      || source.journalSourceUrl !== JOURNAL
      || source.fdaStaffSourceUrl !== FDA
      || source.originalSupplementSourceUrl !== FULL
      || source.originalSupplementFilename !== "nejmoa1606774_protocol.pdf"
      || !text(source.journalLocator) || !text(source.fdaStaffLocator)
      || source.originalSupplementRead !== false
      || source.contemporaneousSapAuthenticated !== false) return false;

  const design = x.reportedDesign;
  if (design.overallOneSidedAlphaPercent !== 2.5
      || !obj(design.firstInterim) || !obj(design.secondInterim)
      || !obj(design.osGroupSequential)
      || design.descriptionPublishedAfterCutoff !== true
      || design.signedOriginalPlanAuthenticated !== false) return false;
  const first = design.firstInterim, second = design.secondInterim, os = design.osGroupSequential;
  if (first.plannedMinimumRandomized !== 191
      || first.plannedMinimumFollowupMonths !== 6
      || first.testingEndpoint !== "objective_response_rate"
      || first.reportedAllocatedOneSidedAlphaPercent !== 0.5
      || first.sourceUrl !== JOURNAL
      || first.prespecificationIndependentlyConfirmed !== false
      || !text(first.sourceLocator)
      || second.plannedApproximatePfsEvents !== 175
      || second.testingEndpoint !== "progression_free_survival"
      || second.reportedAllocatedOneSidedAlphaPercent !== 2.0
      || second.sourceUrl !== JOURNAL
      || second.prespecificationIndependentlyConfirmed !== false
      || !text(second.sourceLocator)
      || !exactNumbers(os.plannedApproximateDeaths, [110,170])
      || os.sourceUrl !== JOURNAL
      || os.prespecificationIndependentlyConfirmed !== false
      || !text(os.sourceLocator)) return false;

  const observed = x.observedInterim;
  if (observed.reportedPfsEvents !== 189
      || observed.reportedDeaths !== 108
      || observed.pfsHR !== 0.50
      || !exactNumbers(observed.pfsCi95, [0.37,0.68])
      || observed.reportedPfsPValue !== "<0.001"
      || observed.osHR !== 0.60
      || !exactNumbers(observed.osCi95, [0.41,0.89])
      || observed.reportedOsPValue !== 0.005
      || observed.fdaStaffReportedOsAllocatedAlpha !== 0.0118
      || observed.comparisonStatus !== "source_reported_not_recalculated"
      || observed.fdaStaffArticleIsNotFullAgencyClinicalReview !== true) return false;

  const review = x.reconciliation;
  return review.historicalResultsSourceChecked === true
    && review.independentOriginalSAPReviewComplete === false
    && review.alphaSpendingRecomputedFromSignedSAP === false
    && review.patientLevelReanalysisComplete === false
    && review.scientificConclusionAuthorized === false
    && review.inputReadinessGradeChanged === false
    && review.reluctanceGradeChanged === false
    && Array.isArray(review.missingCriticalSources)
    && review.missingCriticalSources.length === 3
    && review.missingCriticalSources.every(text)
    && text(review.nextAction);
}
