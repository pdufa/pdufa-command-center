/**
 * Independent per-test and per-assessment evidence ratings.
 * Scientific strength is NOT a calibrated FDA approval probability.
 * No source review => no score. Phase applicability must be justified.
 * This module does not read retired scoring systems or surveys.
 */
export type TrialPhase = "EARLY_PHASE1" | "PHASE1" | "PHASE2" | "PHASE3" | "PHASE4" | "UNKNOWN";
export type AssessmentDescriptor = { id: string; layerId: string; label: string };
export type TestGrade = 0 | 1 | 2 | 3 | 4 | 5;
export type AssessmentTestReview = {
  nct: string;
  phase: TrialPhase;
  assessmentId: string;
  level: number;
  disposition: "SCORED" | "NOT_APPLICABLE";
  grade?: TestGrade;
  evidenceUrls: readonly string[];
  rationale: string;
  recordedAt: string;
};
export type AssessmentRanking = AssessmentDescriptor & {
  score: number | null;
  rank: number | null;
  status: "NOT_REVIEWED" | "PROVISIONAL" | "COMPLETE" | "NOT_APPLICABLE";
  scoredTests: number;
  unreviewedTests: number;
  excludedTests: number;
  applicableTests: number;
};
export const TEST_GRADE_RUBRIC: readonly { grade: TestGrade; meaning: string }[] = [
  { grade: 0, meaning: "Verified contradictory or failed evidence" },
  { grade: 1, meaning: "Very weak or materially unfavorable evidence" },
  { grade: 2, meaning: "Mixed or materially limited evidence" },
  { grade: 3, meaning: "Promising but preliminary evidence" },
  { grade: 4, meaning: "Strong and internally consistent evidence" },
  { grade: 5, meaning: "Strong, independently replicated or rigorously validated evidence" },
];
export const PHASE_REVIEW_STANDARD: Record<TrialPhase, string> = {
  EARLY_PHASE1: "Initial tolerability, dose, drug exposure and mechanism; no Phase 3 requirement",
  PHASE1: "Safety, tolerability, PK/PD, target engagement and dose selection; no pivotal-efficacy requirement",
  PHASE2: "Preliminary efficacy, dose response, endpoint validity and Phase 3 readiness",
  PHASE3: "Trial design, prespecified efficacy/safety and results when posted; never infer unpublished results",
  PHASE4: "Postmarketing safety, effectiveness and confirmatory obligations",
  UNKNOWN: "Verify trial phase against the exact-NCT original registry before assigning any rating",
};

function validateReview(r: AssessmentTestReview, nct: string, phase: TrialPhase, ids: Set<string>) {
  if (r.nct !== nct || r.phase !== phase) throw Error("Test review does not match exact NCT and verified phase");
  if (!ids.has(r.assessmentId) || !Number.isInteger(r.level) || r.level < 1 || r.level > 20)
    throw Error("Invalid 40-assessment / 20-level position");
  if (typeof r.rationale !== "string" || r.rationale.trim().length < 20)
    throw Error("Each review or exclusion needs a specific documented rationale");
  if (!/^\d{4}-\d{2}-\d{2}/.test(r.recordedAt))
    throw Error("Test rating needs a recorded date");
  if (r.disposition === "SCORED") {
    if (typeof r.grade !== "number" || !Number.isInteger(r.grade) || r.grade < 0 || r.grade > 5)
      throw Error("A scientific test grade must be an integer from 0 to 5");
    if (!r.evidenceUrls?.length || r.evidenceUrls.some(url => !/^https:\/\//.test(url)))
      throw Error("A scored test requires original-source HTTPS evidence");
    if (phase === "UNKNOWN") throw Error("Verify the registry phase before rating");
  } else if (r.disposition === "NOT_APPLICABLE") {
    if (r.grade !== undefined) throw Error("A not-applicable test cannot receive a grade");
  } else throw Error("Unknown test disposition");
}

/** Full 40-assessment roster, a provisional test mean and a rank only for complete assessments. */
export function rankTrialAssessments(
  assessments: readonly AssessmentDescriptor[],
  nct: string,
  phase: TrialPhase,
  reviewed: readonly AssessmentTestReview[],
): AssessmentRanking[] {
  if (!/^NCT\d{8}$/.test(nct)) throw Error("Exact NCT required");
  if (!Object.hasOwn(PHASE_REVIEW_STANDARD, phase)) throw Error("Unknown trial phase label");
  const ids = new Set(assessments.map(a => a.id));
  if (ids.size !== assessments.length) throw Error("Duplicate assessment id");
  const byAssessment = new Map<string, AssessmentTestReview[]>();
  const unique = new Set<string>();
  for (const entry of reviewed) {
    validateReview(entry, nct, phase, ids);
    const key = entry.assessmentId + ":" + entry.level;
    if (unique.has(key)) throw Error("Duplicate scientific test review");
    unique.add(key);
    byAssessment.set(entry.assessmentId, [...(byAssessment.get(entry.assessmentId) || []), entry]);
  }
  const rows: AssessmentRanking[] = assessments.map(assessment => {
    const marks = byAssessment.get(assessment.id) || [];
    const scored = marks.filter(m => m.disposition === "SCORED");
    const excluded = marks.length - scored.length;
    const applicable = 20 - excluded;
    const unreviewed = applicable - scored.length;
    const score = scored.length ? Math.round((scored.reduce((sum, m) => sum + Number(m.grade), 0) / scored.length) * 200) / 10 : null;
    const status: AssessmentRanking["status"] = !applicable ? "NOT_APPLICABLE" : !scored.length ? "NOT_REVIEWED" : unreviewed ? "PROVISIONAL" : "COMPLETE";
    return { ...assessment, score, rank: null, status, scoredTests: scored.length,
      unreviewedTests: unreviewed, excludedTests: excluded, applicableTests: applicable };
  });
  // Only evidence-complete rows are comparable. Partial reviews show a visible provisional score, never a rank.
  const complete = rows.filter(r => r.status === "COMPLETE").sort((a,b) => Number(b.score) - Number(a.score) || a.id.localeCompare(b.id));
  let last: number | null = null, rank = 0;
  complete.forEach((row, i) => {
    if (row.score !== last) rank = i + 1;
    row.rank = rank;
    last = row.score;
  });
  return rows;
}
