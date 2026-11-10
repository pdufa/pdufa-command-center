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

/** Dated documentary checkpoint, separate from live PostgreSQL observations.
 * Appending research evidence never advances a clinical ledger task or grade.
 */
export const MAIN_RESEARCH_CHECKPOINT = {
  revision: 36,
  observedAt: "2026-11-09T14:02:19.203666+00:00",
  baseCommit: "13b3dae5cd8bfb003430e03f56bff58caf1da70c",
  nct: "NCT06081894",
  currentTaskId: "r36.source-reconciliation",
  candidateMethodPositions: 18,
  unexaminedMethodPositions: 782,
  officialMethodGrades: 0,
  tasks: [
    {id: "r36.registry-history", title: "Recover original registry versions 26, 27, 29 and 30", status: "VERIFIED",
      acceptance: "Four exact-NCT original JSON responses passed version, submission-date, byte-count and SHA-256 checks. One primary endpoint in v26; two in v27/v29/v30. Submitted and public posting dates remain separate.",
      evidencePath: "revision36-original-history/validated_comparison.json"},
    {id: "r36.protocol-multiplicity", title: "Examine the preserved AM04 multiplicity graph", status: "VERIFIED",
      acceptance: "Original protocol page 66 was visually transcribed; the previously captured PDF hash was rechecked. This is documentary examination, not final locked SAP verification or independent statistical adjudication.",
      evidencePath: "revision36-protocol-safety/reviewer-packet.json"},
    {id: "r36.source-reconciliation", title: "Resolve the pilot's original-document and population discrepancies", status: "ACTIVE",
      acceptance: "Next: final dated locked SAP, amendment/lock chronology, original CONSORT accounting, matched HF SAE definitions/windows and treatment-interruption denominators. Estimated enrollment 420 → 500 does not resolve 516 versus 517 actual participants. HF 11/1 versus 12/3 and 14 interruptions remain unresolved.",
      evidencePath: "revision36-protocol-safety/source-avenues.json"},
    {id: "r36.independent-grading", title: "Obtain authorized independent phase and method review", status: "BLOCKED",
      acceptance: "Original evidence and qualified authorized independent review are required before official scored events. Documentary checks, source leads and provisional research panels are separate from clinical grades.",
      evidencePath: "revision36-protocol-safety/reviewer-packet.json"},
    {id: "r36.prediction-validation", title: "Validate approval, CRL and review-delay forecasts", status: "BLOCKED",
      acceptance: "Independent evidence assessment, locked historical outcomes, temporal holdout and outcome-specific calibration release gates remain unmet. Pointwise calibration-bin uncertainty code is an engineering component, not a validated FDA probability.",
      evidencePath: "revision36-protocol-safety/reviewer-packet.json"},
    {id: "r36.preview-runtime", title: "Verify this revision's preview and authenticated readback", status: "VERIFIED",
      acceptance: "Protected CI runs 42628975006 and 42630127667 passed normal login, all 40 assessments and 800 methods, unchanged history, original source receipts and zero official grades. Local browser acceptance passed at 390px and 1440px. Use the verified unique preview; the existing preview alias still targets an earlier revision.",
      evidencePath: "revision36-verification/post-rollout-authenticated-summary.json"},
    {id: "r36.backend-rollout", title: "Verify the isolated backend rollout and PostgreSQL restart", status: "VERIFIED",
      acceptance: "Render deployment dep-dbot3n8u01pc738b6bq0 is live at d580b966a4f28d64f1878a9a5e9f6f5713e181b3. Existing exact-commit release gates passed. Startup and health confirmed PostgreSQL ready, 29 source packets, 23,200 positions, preserved source history and zero clinical grades. Post-rollout 800-method readback retained the same ledger hash. Vault route remains uninstalled; no production or database-security change was performed.",
      evidencePath: "revision36-verification/release-receipt.json"},
  ],
} as const;

export function researchCheckpointEvidenceUrl(path: string): string {
  return "https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/docs/medical-review-pilot-20261108/" + path;
}
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
