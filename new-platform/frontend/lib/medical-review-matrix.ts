/** Read-only scientific evidence projection. No forecast or score is inferred here. */
export type Evidence = {sourceUrl: string; stageDocumentSha256?: string};
export type Revision = {review_event_id: string; verified_phase: string; phase_event_id: string;
  revision: number; disposition: string; grade: number | null; reviewer_id: string;
  evidence_reviewed_at: string; rationale: string; evidence: Evidence[]};
export type Gap = {gap_code: string; evidence_note: string; recorded_at: string};
export type MethodReview = {methodIndex: number; status: string; grade: number | null;
  reviewEventId: string | null; revision: number | null; reviewedAt: string | null; reviewerId: string | null;
  rationale: string | null; sourceEvidence: Evidence[]; history: Revision[]; evidenceGaps: Gap[]};
export type AssessmentReview = {assessmentIndex: number; status: string; scoreOutOf100: number | null;
  reviewedMethods: number; excludedMethods: number; pendingMethods: number; applicableMethods: number;
  methods?: MethodReview[]};
export type ReviewMatrix = {nct: string; verifiedPhase: string | null; phaseEventId: string | null;
  totalPositions: number; counts: Record<string, number>; assessments: AssessmentReview[];
  selectedAssessment: AssessmentReview | null; historicalReviewEvents: number; recordedGapEvents: number;
  phaseHistory: {phase_event_id: string; verified_phase: string; reviewer_id: string; verified_at: string}[];
  gradingPolicy?: {version: string; status: string; anchors: {grade: number; meaning: string}[];
    normalization: {formula: string}; historicalEventsCertifiedAgainstPolicy: boolean}};
export type CatalogMethod = {methodIndex: number; method: string; methodDescription: string;
  priorityTier: string; priorityRank: number | null; phaseApplicability: string; requiredSources: string};
export type CatalogAssessment = {assessmentIndex: number; assessmentId: string; layerId: string;
  label: string; objective: string; methods: CatalogMethod[]};
export type CatalogMatrix = {nct: string; phase: string; phaseBasis: string;
  phaseEvents: {phase_event_id: string; verified_phase: string}[];
  registry: {reportedPhases: string[]; phaseStatus: string; sourceUrl: string};
  assessments: CatalogAssessment[]};

export function isolatedMedicalBackend(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password || url.pathname !== "/" || url.search || url.hash)
      return null;
    return url.origin;
  } catch { return null; }
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw Error("INVALID_MATRIX");
  return value as Record<string, unknown>;
}
function guarded(value: Record<string, unknown>, nct: string) {
  const forecast = object(value.fdaPredictions);
  if (value.nct !== nct || value.certainty !== "NOT_VALIDATED" ||
      Object.keys(forecast).length !== 3 || Object.values(forecast).some(x => x !== "ABSTAIN"))
    throw Error("UNVERIFIED_MATRIX");
}
const statuses = new Set(["SCORED", "NOT_APPLICABLE", "RETRACTED", "STALE_PHASE", "UNREVIEWED", "VERIFY_PHASE"]);
function grade(value: unknown): boolean {return typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 5;}
function strings(value: Record<string, unknown>, keys: string[]): boolean {return keys.every(k => typeof value[k] === "string");}
const phases = new Set(["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"]);
const dispositions = new Set(["SCORED", "NOT_APPLICABLE", "RETRACTED"]);
function nonempty(value: unknown): value is string {return typeof value === "string" && value.trim().length > 0;}
function integer(value: unknown): value is number {return typeof value === "number" && Number.isInteger(value) && value >= 0;}
function sources(value: unknown): value is Evidence[] {
  return Array.isArray(value) && value.every(raw => {
    const source = object(raw);
    if (typeof source.sourceUrl !== "string" || typeof source.stageDocumentSha256 !== "string" || !/^[a-f0-9]{64}$/.test(source.stageDocumentSha256)) return false;
    try {
      const url = new URL(source.sourceUrl);
      return url.protocol === "https:" && !url.username && !url.password;
    } catch {return false;}
  });
}
function summaryStatus(phase: unknown, a: Record<string, unknown>): string {
  return !phase ? "VERIFY_PHASE" : !a.applicableMethods ? "NOT_APPLICABLE" : !a.reviewedMethods ? "NOT_REVIEWED" : a.pendingMethods ? "PROVISIONAL" : "COMPLETE";
}
const summaryFields = ["assessmentIndex", "status", "scoreOutOf100", "reviewedMethods", "excludedMethods", "pendingMethods", "applicableMethods"];
export function validateReviewMatrix(value: unknown, nct: string, assessmentIndex?: number): ReviewMatrix {
  const v = object(value); guarded(v, nct);
  const counts = object(v.counts);
  if (v.totalPositions !== 800 || Object.keys(counts).length !== statuses.size ||
      Object.entries(counts).some(([k, n]) => !statuses.has(k) || !integer(n)) ||
      Object.values(counts).reduce<number>((sum, n) => sum + (n as number), 0) !== 800 ||
      !Array.isArray(v.phaseHistory) || !integer(v.recordedGapEvents) || !integer(v.historicalReviewEvents) ||
      v.phaseHistory.some(p => !strings(object(p), ["verified_phase", "reviewer_id", "verified_at"]) ||
        !nonempty(object(p).phase_event_id) || !phases.has(String(object(p).verified_phase))) ||
      !Array.isArray(v.assessments) || v.assessments.length !== 40 ||
      v.assessments.some((a, i) => object(a).assessmentIndex !== i + 1)) throw Error("INVALID_MATRIX_COUNTS");
  const phase = v.verifiedPhase, phaseId = v.phaseEventId;
  const phaseEvents = new Map(v.phaseHistory.map(raw => {const p = object(raw); return [p.phase_event_id, p.verified_phase];}));
  const current = v.phaseHistory.at(-1);
  if (phase === null ? phaseId !== null || current !== undefined || counts.VERIFY_PHASE !== 800 :
      !phases.has(String(phase)) || !nonempty(phaseId) || !current || object(current).phase_event_id !== phaseId ||
      object(current).verified_phase !== phase || counts.VERIFY_PHASE !== 0) throw Error("INVALID_CURRENT_PHASE");
  if (v.gradingPolicy !== undefined) {
    const policy = object(v.gradingPolicy);
    if (!strings(policy, ["version", "status"]) || !Array.isArray(policy.anchors) ||
        policy.anchors.some(raw => !grade(object(raw).grade) || !strings(object(raw), ["meaning"])) ||
        !strings(object(policy.normalization), ["formula"]) ||
        typeof policy.historicalEventsCertifiedAgainstPolicy !== "boolean") throw Error("INVALID_GRADING_POLICY");
  }
  let scoredTotal = 0, excludedTotal = 0;
  for (const raw of v.assessments) {
    const a = object(raw);
    if (!integer(a.pendingMethods) || !integer(a.reviewedMethods) || !integer(a.excludedMethods) ||
        a.pendingMethods + a.reviewedMethods + a.excludedMethods !== 20 ||
        a.applicableMethods !== 20 - a.excludedMethods || a.status !== summaryStatus(phase, a) ||
        (a.reviewedMethods ? !phase || typeof a.scoreOutOf100 !== "number" || !Number.isFinite(a.scoreOutOf100) || a.scoreOutOf100 < 0 || a.scoreOutOf100 > 100 : a.scoreOutOf100 !== null))
      throw Error("INVALID_ASSESSMENT_GRADE");
    scoredTotal += a.reviewedMethods; excludedTotal += a.excludedMethods;
  }
  if (scoredTotal !== counts.SCORED || excludedTotal !== counts.NOT_APPLICABLE) throw Error("INCONSISTENT_MATRIX_COUNTS");
  if (assessmentIndex !== undefined) {
    const selected = object(v.selectedAssessment), summary = object(v.assessments[assessmentIndex - 1]);
    if (summaryFields.some(key => selected[key] !== summary[key]) ||
        !Array.isArray(selected.methods) || selected.methods.length !== 20) throw Error("INVALID_METHOD_DETAILS");
    const methodCounts: Record<string, number> = Object.fromEntries([...statuses].map(status => [status, 0]));
    const eventIds = new Set<string>(); let gradeSum = 0, historicalCount = 0;
    selected.methods.forEach((raw, i) => {
      const m = object(raw);
      if (m.methodIndex !== i + 1 || !statuses.has(String(m.status)) ||
          (m.status === "SCORED" ? !grade(m.grade) || !phase : m.grade !== null) ||
          !sources(m.sourceEvidence) || !Array.isArray(m.history) || !Array.isArray(m.evidenceGaps) ||
          m.evidenceGaps.some(g => !strings(object(g), ["gap_code", "evidence_note", "recorded_at"]))) throw Error("INVALID_METHOD_GRADE");
      const revisionIds = new Set<string>();
      const history = m.history.map(rawRevision => {
        const r = object(rawRevision), key = r.verified_phase + ":" + r.revision;
        if (!["review_event_id", "phase_event_id", "reviewer_id", "evidence_reviewed_at", "rationale"].every(k => nonempty(r[k])) ||
            r.assessment_index !== assessmentIndex || r.method_index !== i + 1 ||
            !phases.has(String(r.verified_phase)) || phaseEvents.get(r.phase_event_id) !== r.verified_phase ||
            !integer(r.revision) || r.revision < 1 || !dispositions.has(String(r.disposition)) ||
            (r.disposition === "SCORED" ? !grade(r.grade) : r.grade !== null) ||
            !sources(r.evidence) || (r.disposition === "SCORED" && !r.evidence.length) ||
            eventIds.has(String(r.review_event_id)) || revisionIds.has(key)) throw Error("INVALID_REVIEW_HISTORY");
        eventIds.add(String(r.review_event_id)); revisionIds.add(key); historicalCount++;
        return r;
      });
      const matched = history.filter(r => r.phase_event_id === phaseId && r.verified_phase === phase);
      const latest = matched.reduce<Record<string, unknown> | null>((before, r) => !before || Number(r.revision) > Number(before.revision) ? r : before, null);
      const expectedStatus = !phase ? "VERIFY_PHASE" : latest ? latest.disposition : history.length ? "STALE_PHASE" : "UNREVIEWED";
      if (m.status !== expectedStatus) throw Error("INCONSISTENT_METHOD_PHASE");
      if (latest) {
        if (m.reviewEventId !== latest.review_event_id || m.revision !== latest.revision || m.grade !== latest.grade ||
            m.reviewerId !== latest.reviewer_id || m.reviewedAt !== latest.evidence_reviewed_at || m.rationale !== latest.rationale ||
            JSON.stringify(m.sourceEvidence) !== JSON.stringify(latest.evidence)) throw Error("INCONSISTENT_CURRENT_REVIEW");
      } else if (m.reviewEventId !== null || m.revision !== null || m.reviewerId !== null || m.reviewedAt !== null || m.rationale !== null || m.sourceEvidence.length)
        throw Error("UNREVIEWED_METHOD_HAS_REVIEW");
      methodCounts[String(m.status)]++;
      if (m.status === "SCORED") gradeSum += Number(m.grade);
    });
    if (historicalCount > v.historicalReviewEvents || methodCounts.SCORED !== selected.reviewedMethods ||
        methodCounts.NOT_APPLICABLE !== selected.excludedMethods ||
        Object.entries(methodCounts).some(([status, count]) => count > Number(counts[status])) ||
        (methodCounts.SCORED && Math.abs(Number(selected.scoreOutOf100) - gradeSum / methodCounts.SCORED * 20) > 0.051))
      throw Error("INCONSISTENT_METHOD_COUNTS");
  } else if (v.selectedAssessment !== null) throw Error("UNEXPECTED_METHOD_SELECTION");
  return v as unknown as ReviewMatrix;
}

export function validateCatalogMatrix(value: unknown, nct: string): CatalogMatrix {
  const v = object(value); guarded(v, nct);
  const registry = object(v.registry);
  if (!Array.isArray(registry.reportedPhases) || registry.reportedPhases.some(p => typeof p !== "string"))
    throw Error("INVALID_REGISTRY_PHASES");
  if (!Array.isArray(v.assessments) || v.assessments.length !== 40 ||
      v.assessments.some((raw, i) => {
        const a = object(raw);
        return a.assessmentIndex !== i + 1 || !strings(a, ["assessmentId", "layerId", "label", "objective"]) || !Array.isArray(a.methods) || a.methods.length !== 20 ||
          a.methods.some((rawMethod, j) => {
            const m = object(rawMethod);
            return m.methodIndex !== j + 1 || !strings(m, ["method", "methodDescription", "requiredSources", "priorityTier", "phaseApplicability"]);
          });
      })) throw Error("INVALID_SCIENTIFIC_CATALOG");
  return v as unknown as CatalogMatrix;
}

/** Parallel source reads must describe the same verified phase-event snapshot. */
export function assertMatrixPhaseSnapshot(catalog: CatalogMatrix, review: ReviewMatrix): void {
  if (!Array.isArray(catalog.phaseEvents)) throw Error("INVALID_CATALOG_PHASE_HISTORY");
  const latest = catalog.phaseEvents.at(-1);
  if ((latest?.phase_event_id ?? null) !== review.phaseEventId || (latest?.verified_phase ?? null) !== review.verifiedPhase)
    throw Error("MEDICAL_PHASE_CHANGED_RETRY");
}
