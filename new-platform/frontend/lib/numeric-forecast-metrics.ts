import type { AssessmentDetail, AssessmentStage } from "./candidate-assessments";

/**
 * Read-only numeric presentation of EXISTING seven-category research scores.
 * This is NOT an FDA approval forecast, scientific-40 investigation, or
 * historical-comparables model. Null is missing evidence; zero is scored zero.
 */
export const HISTORICAL_SIMILARITY_DIMENSIONS = [
  "Disease / indication similarity",
  "Drug mechanism and target",
  "Patient population / eligibility",
  "Trial design / phase",
  "Primary endpoints / statistical plan",
  "Observed efficacy and effect sizes",
  "Safety / tolerability",
  "FDA pathway and regulatory precedent",
] as const;

export type NumericMetric = {
  id: string;
  label: string;
  ratingOutOf100: number | null;
  points: number;
  maximum: number;
  evidencePoints: number;
  reviewedMeasurements: number;
  totalMeasurements: number;
  complete: boolean;
  status: string;
};
export type NumericForecastDisplay = {
  sourceModel: AssessmentStage;
  modelVersion: string;
  asOf: string;
  researchModelScore: number | null;
  observedResearchPoints: number;
  evidenceCoverageOutOf100: number;
  completeCategories: number;
  categoryTotal: 7;
  metrics: NumericMetric[];
  // No source-linked, independently reviewed historical comparisons were returned
  // by the candidate-assessments service. Do not infer analogs from other trials.
  comparableTrialCount: null;
  historicalApprovalCount: null;
  historicalDecisionDenominator: null;
  scientificAssessmentCount: null;
  scientificAssessmentDenominator: 40;
  readinessGradeOutOf100: null;
  reluctanceGradeOutOf100: null;
  preliminaryHistoricalForecast: null;
  calibratedFdaApprovalProbability: null;
};
const almost = 0.02;
const bounded = (n: number, max: number) =>
  Number.isFinite(n) && n >= 0 && n <= max + almost;

export function createNumericForecastDisplay(detail: AssessmentDetail, stage: AssessmentStage): NumericForecastDisplay {
  const model = detail?.models?.[stage];
  if (!model || !Array.isArray(model.categories) || model.categories.length !== 7
      || typeof detail.modelVersion !== "string" || !detail.modelVersion
      || typeof detail.asOf !== "string" || !/^\\d{4}-\\d{2}-\\d{2}$/.test(detail.asOf)
      || !bounded(model.coverage, 100) || !bounded(model.observedPoints, 100)
      || (model.score !== null && !bounded(model.score, 100))) {
    throw new Error("A reliable seven-category research scoring display is unavailable");
  }
  const seen = new Set<string>();
  const metrics = model.categories.map(category => {
    if (!category || !category.id || seen.has(category.id) || !category.label
        || !Number.isFinite(category.maximum) || category.maximum <= 0 || category.maximum > 100
        || !bounded(category.coverage, category.maximum)
        || !bounded(category.observedPoints, category.maximum)
        || category.observedPoints > category.coverage + almost
        || !Array.isArray(category.metrics)
        || (category.score !== null && !bounded(category.score, category.maximum))) {
      throw new Error("Research metric rating and its evidence denominator do not reconcile");
    }
    seen.add(category.id);
    const complete = category.status === "COMPLETE"
      && category.coverage >= category.maximum - almost
      && category.score !== null;
    const reviewedMeasurements = category.metrics.filter(m =>
      m && Number.isFinite(m.coverage) && m.coverage > 0
      && m.points !== null && Number.isFinite(m.points)
    ).length;
    return {
      id:category.id,
      label:category.label,
      ratingOutOf100:complete ? Number((category.score! / category.maximum * 100).toFixed(1)) : null,
      points:category.observedPoints,
      maximum:category.maximum,
      evidencePoints:category.coverage,
      reviewedMeasurements,
      totalMeasurements:category.metrics.length,
      complete,
      status:category.status,
    };
  });
  const maximumTotal = metrics.reduce((n,metric)=>n+metric.maximum,0);
  const pointsTotal = metrics.reduce((n,metric)=>n+metric.points,0);
  const evidenceTotal = metrics.reduce((n,metric)=>n+metric.evidencePoints,0);
  if (Math.abs(maximumTotal - 100) > almost
      || Math.abs(pointsTotal - model.observedPoints) > almost
      || Math.abs(evidenceTotal - model.coverage) > almost
      || (model.score !== null && (model.coverage < 99.99
        || metrics.some(m=>!m.complete)
        || Math.abs(model.score-model.observedPoints)>almost))) {
    throw new Error("Numerical metric totals do not reconcile to the saved research score");
  }
  return {
    sourceModel:stage,
    modelVersion:detail.modelVersion,
    asOf:detail.asOf,
    researchModelScore:model.score,
    observedResearchPoints:model.observedPoints,
    evidenceCoverageOutOf100:model.coverage,
    completeCategories:metrics.filter(x=>x.complete).length,
    categoryTotal:7,
    metrics,
    comparableTrialCount:null,
    historicalApprovalCount:null,
    historicalDecisionDenominator:null,
    scientificAssessmentCount:null,
    scientificAssessmentDenominator:40,
    readinessGradeOutOf100:null,
    reluctanceGradeOutOf100:null,
    preliminaryHistoricalForecast:null,
    calibratedFdaApprovalProbability:null,
  };
}
