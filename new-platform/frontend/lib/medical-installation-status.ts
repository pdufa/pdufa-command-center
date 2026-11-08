/** Exact ledger observations, separate from the historical MAIN checkpoint tracker. */
export type InstallationTask = {
  id: string; title: string; status: "VERIFIED" | "ACTIVE" | "BLOCKED" | "UNKNOWN";
  completed: number | null; remaining: number | null; dependency: string | null; evidence: string;
};
export type MedicalInstallation = {
  state: "OBSERVED" | "BLOCKED" | "UNKNOWN"; reason?: string;
  counts: null | {canonicalTrials: number; observedTrialLedgers: number;
    sourceCompleteTrials: number; sourceStages: number; phaseVerifiedTrials: number;
    potentialMethodPositions: number; recordedCurrentPhaseGrades: number; excludedMethods: number;
    pendingObservedMethods: number; unobservedMethodPositions: number; completedAssessments: number;
    historicalReviewEvents: number; recordedGapEvents: number; independentlySignedClinicalReviews: null;
    methodStates: Record<string, number>};
  tasks: InstallationTask[]; currentTaskId: string | null;
  definitions: Record<string, string>; clinicalSignoff: "NOT_VERIFIED";
  sourceCollectionDates?: {oldest: string | null; newest: string | null; freshnessValidation: "NOT_ADJUDICATED"};
};
export type MedicalInstallationSnapshot = {observedAt: string; installation: MedicalInstallation};
const states = ["VERIFIED", "ACTIVE", "BLOCKED", "UNKNOWN"] as const;
function rec(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw Error("INVALID_INSTALLATION_OBSERVATION");
  return value as Record<string, unknown>;
}
function count(value: unknown): value is number {return typeof value === "number" && Number.isSafeInteger(value) && value >= 0;}
function nullableCount(value: unknown): boolean {return value === null || count(value);}
export function validateMedicalInstallation(value: unknown): MedicalInstallationSnapshot {
  const root = rec(value), item = rec(root.medicalInstallation), predictions = rec(item.fdaPredictions);
  if (root.schemaVersion !== 1 || typeof root.observedAt !== "string" || !Number.isFinite(Date.parse(root.observedAt)) ||
      !["OBSERVED", "UNKNOWN", "BLOCKED"].includes(String(item.state)) || item.clinicalSignoff !== "NOT_VERIFIED" ||
      predictions.APPROVAL !== "ABSTAIN" || predictions.CRL !== "ABSTAIN" || predictions.REVIEW_DELAY !== "ABSTAIN" ||
      Object.keys(predictions).length !== 3 || item.certainty !== "NOT_VALIDATED" || !Array.isArray(item.tasks) ||
      (item.currentTaskId !== null && typeof item.currentTaskId !== "string") ||
      Object.values(rec(item.definitions)).some(v => typeof v !== "string")) throw Error("INVALID_INSTALLATION_OBSERVATION");
  if (item.reason !== undefined && typeof item.reason !== "string") throw Error("INVALID_INSTALLATION_REASON");
  const ids = new Set<string>();
  for (const raw of item.tasks) {
    const task = rec(raw);
    if (typeof task.id !== "string" || !/^medical\.[a-z-]+$/.test(task.id) || ids.has(task.id) ||
        typeof task.title !== "string" || !states.includes(task.status as typeof states[number]) ||
        !nullableCount(task.completed) || !nullableCount(task.remaining) ||
        (task.dependency !== null && typeof task.dependency !== "string") || typeof task.evidence !== "string")
      throw Error("INVALID_INSTALLATION_TASK");
    ids.add(task.id);
  }
  if (item.currentTaskId !== null && !ids.has(item.currentTaskId as string)) throw Error("INVALID_CURRENT_TASK");
  if (item.state === "OBSERVED") {
    const storage = rec(root.storage), counts = rec(item.counts), methods = rec(counts.methodStates), tasks = rec(item.taskCounts);
    const numeric = ["canonicalTrials", "observedTrialLedgers", "sourceCompleteTrials", "sourceStages", "phaseVerifiedTrials",
      "potentialMethodPositions", "recordedCurrentPhaseGrades", "excludedMethods", "pendingObservedMethods",
      "unobservedMethodPositions", "completedAssessments", "historicalReviewEvents", "recordedGapEvents"];
    const methodKeys = ["SCORED", "NOT_APPLICABLE", "RETRACTED", "STALE_PHASE", "UNREVIEWED", "VERIFY_PHASE"];
    if (storage.state !== "READY" || storage.kind !== "postgresql" || numeric.some(k => !count(counts[k])) ||
        counts.independentlySignedClinicalReviews !== null || methodKeys.some(k => !count(methods[k])) ||
        Object.keys(methods).length !== methodKeys.length ||
        (counts.canonicalTrials as number) * 800 !== counts.potentialMethodPositions ||
        (counts.observedTrialLedgers as number) > (counts.canonicalTrials as number) ||
        (counts.phaseVerifiedTrials as number) > (counts.observedTrialLedgers as number) ||
        (counts.sourceCompleteTrials as number) > (counts.observedTrialLedgers as number) ||
        methods.SCORED !== counts.recordedCurrentPhaseGrades || methods.NOT_APPLICABLE !== counts.excludedMethods ||
        ["RETRACTED", "STALE_PHASE", "UNREVIEWED", "VERIFY_PHASE"].reduce((sum, k) => sum + (methods[k] as number), 0) !== counts.pendingObservedMethods ||
        methodKeys.reduce((sum, k) => sum + (methods[k] as number), 0) + (counts.unobservedMethodPositions as number) !== counts.potentialMethodPositions ||
        states.some(state => tasks[state] !== (item.tasks as InstallationTask[]).filter(t => t.status === state).length))
      throw Error("INVALID_INSTALLATION_COUNTS");
    const dates = rec(item.sourceCollectionDates);
    if (dates.freshnessValidation !== "NOT_ADJUDICATED" || [dates.oldest, dates.newest].some(d => d !== null && typeof d !== "string"))
      throw Error("INVALID_SOURCE_FRESHNESS");
  } else if (item.counts !== null || item.tasks.length || item.currentTaskId !== null) throw Error("UNKNOWN_INSTALLATION_COUNTS");
  return {observedAt: root.observedAt as string, installation: item as unknown as MedicalInstallation};
}
