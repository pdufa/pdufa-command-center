/** PEAK (NCT05208047) review-only register. All evidence remains unverified until adjudicated. */
import { SCIENCE_QUESTION_CATALOG } from "./science-question-catalog.proposed";
import { PEAK_REPORTED_EVIDENCE } from "./peak-reported-evidence.proposed";
export const PEAK_SCIENCE_REGISTER_VERSION = "peak-science-register-v0.1-proposed" as const;
export const PEAK_SCIENCE_REGISTER = {
  trialId: "NCT05208047",
  programId: "COGT-PEAK-GIST",
  list: "GEM",
  sourceCutoffDate: "2026-10-26",
  approvalProbability: null,
  assessments: SCIENCE_QUESTION_CATALOG.map(q => ({
    id: q.id,
    layer: q.layer,
    question: q.question,
    requiredEvidence: q.requiredEvidence,
    evidence: PEAK_REPORTED_EVIDENCE.filter(item => item.assessmentId === q.id).map(item => ({
      sourceUrl: item.sourceUrl,
      publishedAt: null as string | null,
      verifiedAt: null as string | null,
      verified: false as const,
      note: item.observation,
      status: item.status,
      requiredFollowup: item.requiredFollowup,
    })),
    missingEvidence: [q.requiredEvidence],
    score: null as number | null,
    confidence: null as number | null,
    reviewer: null as string | null,
    status: "NOT_REVIEWED" as const,
  })),
} as const;
