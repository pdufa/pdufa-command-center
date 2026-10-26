/**
 * Historical FDA source-search preparation only — pinned October 25 research.
 *
 * This is NOT the live HOP readiness API, an FDA decision cohort, or a
 * prediction-training dataset. Do not update these numbers without a new
 * independently checked source audit and an explicit snapshot date.
 */
export type FDAReviewWorklistSnapshot = Readonly<{
  asOf: string;
  sourceState: "QUARANTINED_RESEARCH_ONLY";
  publishedLetterReferences: number;
  matchedOriginalApplicationReferences: number;
  missingFromApprovalCentricRosterReferences: number;
  ambiguousApplicationReferences: number;
  distinctMissingApplicationCandidates: number;
  independentlyVerifiedReviewCycles: 0;
  modelEligibleReviewCycles: 0;
  completeOriginalDecisionDenominatorVerified: false;
  predictionProbability: null;
  researchWorkflowUrl: string;
  reviewIssueUrl: string;
}>;

export const FDA_REVIEW_WORKLIST_SNAPSHOT: FDAReviewWorklistSnapshot = {
  asOf: "2026-10-25",
  sourceState: "QUARANTINED_RESEARCH_ONLY",
  publishedLetterReferences: 458,
  matchedOriginalApplicationReferences: 334,
  missingFromApprovalCentricRosterReferences: 107,
  ambiguousApplicationReferences: 17,
  distinctMissingApplicationCandidates: 84,
  independentlyVerifiedReviewCycles: 0,
  modelEligibleReviewCycles: 0,
  completeOriginalDecisionDenominatorVerified: false,
  predictionProbability: null,
  researchWorkflowUrl: "https://github.com/pdufa/pdufa-command-center/actions/runs/40255670202",
  reviewIssueUrl: "https://github.com/pdufa/pdufa-command-center/issues/360",
};

/** A source-reference queue is categorically distinct from FDA decision labels. */
export function auditFDAReviewWorklist(snapshot: FDAReviewWorklistSnapshot) {
  const nums = [
    snapshot.publishedLetterReferences,
    snapshot.matchedOriginalApplicationReferences,
    snapshot.missingFromApprovalCentricRosterReferences,
    snapshot.ambiguousApplicationReferences,
    snapshot.distinctMissingApplicationCandidates,
  ];
  if (snapshot.asOf !== "2026-10-25" ||
      snapshot.sourceState !== "QUARANTINED_RESEARCH_ONLY" ||
      !nums.every(x => Number.isSafeInteger(x) && x >= 0) ||
      snapshot.publishedLetterReferences !==
        snapshot.matchedOriginalApplicationReferences +
        snapshot.missingFromApprovalCentricRosterReferences +
        snapshot.ambiguousApplicationReferences ||
      snapshot.distinctMissingApplicationCandidates >
        snapshot.missingFromApprovalCentricRosterReferences ||
      snapshot.independentlyVerifiedReviewCycles !== 0 ||
      snapshot.modelEligibleReviewCycles !== 0 ||
      snapshot.completeOriginalDecisionDenominatorVerified !== false ||
      snapshot.predictionProbability !== null ||
      snapshot.researchWorkflowUrl !==
        "https://github.com/pdufa/pdufa-command-center/actions/runs/40255670202" ||
      snapshot.reviewIssueUrl !==
        "https://github.com/pdufa/pdufa-command-center/issues/360") {
    throw new Error("FDA research worklist snapshot cannot be accepted");
  }
  return {
    pendingLetterReferences:
      snapshot.missingFromApprovalCentricRosterReferences +
      snapshot.ambiguousApplicationReferences,
    searchPackets:
      snapshot.distinctMissingApplicationCandidates +
      snapshot.ambiguousApplicationReferences,
    independentlyVerifiedReviewCycles: 0,
    modelEligibleReviewCycles: 0,
    certifiedProbability: null,
  } as const;
}
