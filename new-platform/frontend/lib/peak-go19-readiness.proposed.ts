/** Reconcile PEAK source-review queue to SCIENCE-40 without promoting observations into scores. */
import { PEAK_SCIENCE_REGISTER } from "./peak-evidence-register.proposed";
import { PEAK_GO18_REVIEW } from "./peak-go18-review-queue.proposed";

export const PEAK_GO19_READINESS = (() => {
  const reviews = new Map<string, (typeof PEAK_GO18_REVIEW.observations)[number]>(
    PEAK_GO18_REVIEW.observations.map(row => [row.assessmentId, row]),
  );
  const records = PEAK_SCIENCE_REGISTER.assessments.map(row => {
    const review = reviews.get(row.id);
    return {
      assessmentId: row.id,
      layer: row.layer,
      publishedLinks: row.evidence.length,
      reviewState: review?.evidenceState ?? "NOT_IN_GO18_QUEUE",
      outstanding: [
        ...row.missingEvidence,
        ...(review ? [review.gap] : []),
      ],
      independentlyVerified: false,
      score: null,
    };
  });
  return {
    trialId: PEAK_SCIENCE_REGISTER.trialId,
    questionCount: records.length,
    go18ReviewCount: reviews.size,
    go18PartialCount: records.filter(r => r.reviewState === "PARTIAL_SOURCE").length,
    go18MissingCount: records.filter(r => r.reviewState === "MISSING").length,
    mappedPublishedQuestions: records.filter(r => r.publishedLinks > 0).length,
    verifiedQuestionCount: 0,
    scientificReadiness: "INSUFFICIENT_EVIDENCE",
    approvalProbability: null,
    records,
  } as const;
})();
