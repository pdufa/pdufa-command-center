/** Read-only, evidence-gated SYSTEM STATUS summaries.
 * Existing P/J/G scores (3x7) are NOT the requested 40 scientific investigations.
 * Never infer clinical success, predict approval, or grant a trading permission.
 */
import { ASSESSMENT_STAGES, validateAssessmentIndex } from "./candidate-assessments";
import type { AssessmentIndex } from "./candidate-assessments";
import type { HopSourceReadiness } from "./hop-readiness";

export type ModelCoverage = {
  complete: number; partial: number; missing: number;
};
export type ScienceStatus = {
  asOf: string;
  computedAt: string;
  total: number;
  registryLinked: number;
  registryMissing: number;
  reviewSource: string;
  modelVersion: string;
  scores: Record<"PIPELINE" | "GEM_JR" | "GEM", ModelCoverage>;
  scientific40Verified: false;
  clinicalOutcomeCertified: false;
};

/** Validate actual candidate counts, not only the label 'COMPLETE'. */
export function auditScienceIndex(value: unknown): ScienceStatus {
  const raw = value as { status?: string } | null;
  if (!raw || raw.status !== "COMPLETE") throw new Error("Candidate evidence index is not complete");
  const data: AssessmentIndex = validateAssessmentIndex(value);
  if (!Number.isSafeInteger(data.total) || data.total < 1
      || !Number.isSafeInteger(data.registryLinked) || data.registryLinked < 0
      || !Number.isSafeInteger(data.registryMissing) || data.registryMissing < 0
      || data.registryLinked + data.registryMissing !== data.total
      || !Number.isFinite(Date.parse(data.computedAt)) || !/^\\d{4}-\\d{2}-\\d{2}$/.test(data.asOf)
      || typeof data.modelVersion !== "string" || !data.modelVersion
      || typeof data.reviewSource !== "string") {
    throw new Error("Candidate index source and registry totals do not reconcile");
  }
  const scores = {} as ScienceStatus["scores"];
  for (const [offset, stage] of ASSESSMENT_STAGES.entries()) {
    const counts = { complete: 0, partial: 0, missing: 0 };
    for (const record of data.records) {
      const tuple = record[offset + 1];
      if (!Array.isArray(tuple)) throw new Error("Missing model evidence tuple");
      if (tuple[0] !== null) counts.complete++;
      else if (tuple[2] > 0) counts.partial++;
      else counts.missing++;
    }
    const reported = data.totals?.[stage];
    if (!reported || Object.keys(counts).some(k => reported[k as keyof ModelCoverage] !== counts[k as keyof ModelCoverage])) {
      throw new Error("Candidate score coverage totals do not reconcile");
    }
    scores[stage] = counts;
  }
  return {
    asOf: data.asOf, computedAt: data.computedAt, modelVersion: data.modelVersion,
    total: data.total, registryLinked: data.registryLinked,
    registryMissing: data.registryMissing, reviewSource: data.reviewSource, scores,
    scientific40Verified: false, clinicalOutcomeCertified: false,
  };
}

export type OutcomeStatus = {
  checkedAt: string;
  publishedLetters: number | null;
  approvedApplications: number | null;
  sourcePageReviewRows: number | null;
  independentlyVerifiedReviewCycles: number;
  modelEligibleReviewCycles: 0;
  modelValidated: false;
  predictionAvailable: false;
};

/** Requires the already-authenticated, fail-closed HOP read-only API response. */
export function auditOutcomeStatus(value: unknown): OutcomeStatus {
  const r = value as HopSourceReadiness | null;
  if (!r || r.status !== "RESEARCH_ONLY" || r.modelValidated !== false
      || r.predictionAvailable !== false || r.probability !== null
      || r.denominatorComplete !== false || r.modelEligibleReviewCycles !== 0
      || r.independentlyVerifiedReviewCycles == null
      || !Number.isSafeInteger(r.independentlyVerifiedReviewCycles)
      || r.independentlyVerifiedReviewCycles < 0
      || !Number.isFinite(Date.parse(r.checkedAt))) {
    throw new Error("Historical outcome evidence cannot be certified");
  }
  for (const count of [r.publishedLetters, r.approvedApplications, r.sourcePageReviewRows]) {
    if (count != null && (!Number.isSafeInteger(count) || count < 0)) throw new Error("Invalid source audit count");
  }
  return {
    checkedAt: r.checkedAt,
    publishedLetters: r.publishedLetters,
    approvedApplications: r.approvedApplications,
    sourcePageReviewRows: r.sourcePageReviewRows,
    independentlyVerifiedReviewCycles: r.independentlyVerifiedReviewCycles,
    modelEligibleReviewCycles: 0,
    modelValidated: false, predictionAvailable: false,
  };
}
