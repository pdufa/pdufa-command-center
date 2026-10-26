/**
 * Exact-NCT technical reviewer-pair audit, not qualified clinical adjudication.
 * Strictly revalidate the isolated backend's bounded four-gate aggregate
 * before displaying any counts. No reviewer identities or source text.
 */
const NCT = "NCT02142738";
const ORDER = [
  "protocol_sap", "published_results",
  "independent_replication", "official_regulatory",
] as const;
export type ScientificPairProgress = {
  nctId: typeof NCT;
  sourceDocumentCount: number;
  questionCount: 8;
  eligibleQuestionSourcePairs: number;
  pairingTechnicalPreflightPassedCount: number;
  disputedTechnicalPairCount: number;
  historicalAuditCorruptionPairs: number;
  gates: {
    gateId: typeof ORDER[number];
    capturedSourceCount: number;
    reconciliationQuestionCount: number;
    eligibleQuestionSourcePairs: number;
    pairingTechnicalPreflightPassed: number;
    twoAuthorizedReviewersRecorded: number;
    disputedTechnicalPairCount: number;
    historicalAuditCorruptionPairs: number;
  }[];
  independentClinicalReviewCount: 0;
  verifiedClinicalSourceCount: 0;
  qualifiedIndependenceAdjudicated: false;
  formalSecondPersonSignoffCount: 0;
  scientificAdjudicationComplete: false;
  readyForScientificConclusion: false;
  scientificScore: null;
  fdaApprovalProbability: null;
  mayPromoteScientificScore: false;
};
const blocked = (): never => { throw new Error("Technical reviewer progress contract unverified"); };
const object = (v: unknown): v is Record<string, unknown> =>
  v !== null && typeof v === "object" && !Array.isArray(v);
const bounded = (v: unknown, max: number): v is number =>
  Number.isSafeInteger(v) && typeof v === "number" && v >= 0 && v <= max;

export function validateScientificPairProgress(raw: unknown): ScientificPairProgress {
  if (!object(raw)) throw new Error("Technical reviewer progress contract unverified");
  if (raw.nctId !== NCT
      || raw.mode !== "isolated_read_only_technical_reviewer_preflight"
      || raw.capturedBytesRehashed !== true
      || raw.independentClinicalReviewCount !== 0
      || raw.verifiedClinicalSourceCount !== 0
      || raw.qualifiedIndependenceAdjudicated !== false
      || raw.formalSecondPersonSignoffCount !== 0
      || raw.scientificAdjudicationComplete !== false
      || raw.readyForScientificConclusion !== false
      || raw.scientificScore !== null
      || raw.fdaApprovalProbability !== null
      || raw.mayPromoteScientificScore !== false
      || !bounded(raw.sourceDocumentCount, 8)
      || raw.questionCount !== 8
      || !bounded(raw.eligibleQuestionSourcePairs, 64)
      || !bounded(raw.pairingTechnicalPreflightPassedCount, 64)
      || !bounded(raw.disputedTechnicalPairCount, 64)
      || !bounded(raw.historicalAuditCorruptionPairs, 64)
      || !Array.isArray(raw.gates) || raw.gates.length !== ORDER.length) blocked();
  const rows = raw.gates as unknown[];
  const gates: ScientificPairProgress["gates"] = [];
  for (let i = 0; i < ORDER.length; i++) {
    const g = rows[i];
    if (!object(g)) throw new Error("Technical reviewer progress contract unverified");
    if (g.gateId !== ORDER[i]
        || !bounded(g.capturedSourceCount, 8)
        || !bounded(g.reconciliationQuestionCount, 8)
        || !bounded(g.eligibleQuestionSourcePairs, 64)
        || !bounded(g.pairingTechnicalPreflightPassed, 64)
        || !bounded(g.twoAuthorizedReviewersRecorded, 64)
        || !bounded(g.disputedTechnicalPairCount, 64)
        || !bounded(g.historicalAuditCorruptionPairs, 64)
        || g.eligibleQuestionSourcePairs >
           g.capturedSourceCount * g.reconciliationQuestionCount
        || g.pairingTechnicalPreflightPassed > g.twoAuthorizedReviewersRecorded
        || g.twoAuthorizedReviewersRecorded > g.eligibleQuestionSourcePairs
        || g.disputedTechnicalPairCount > g.eligibleQuestionSourcePairs
        || g.historicalAuditCorruptionPairs > g.eligibleQuestionSourcePairs) blocked();
    gates.push({
      gateId: ORDER[i],
      capturedSourceCount: g.capturedSourceCount,
      reconciliationQuestionCount: g.reconciliationQuestionCount,
      eligibleQuestionSourcePairs: g.eligibleQuestionSourcePairs,
      pairingTechnicalPreflightPassed: g.pairingTechnicalPreflightPassed,
      twoAuthorizedReviewersRecorded: g.twoAuthorizedReviewersRecorded,
      disputedTechnicalPairCount: g.disputedTechnicalPairCount,
      historicalAuditCorruptionPairs: g.historicalAuditCorruptionPairs,
    });
  }
  const sum = (key: keyof typeof gates[number]) =>
    gates.reduce((n, x) => n + (typeof x[key] === "number" ? x[key] as number : 0), 0);
  if (sum("capturedSourceCount") !== raw.sourceDocumentCount
      || sum("reconciliationQuestionCount") !== 8
      || sum("eligibleQuestionSourcePairs") !== raw.eligibleQuestionSourcePairs
      || sum("pairingTechnicalPreflightPassed") !== raw.pairingTechnicalPreflightPassedCount
      || sum("disputedTechnicalPairCount") !== raw.disputedTechnicalPairCount
      || sum("historicalAuditCorruptionPairs") !== raw.historicalAuditCorruptionPairs
      || raw.pairingTechnicalPreflightPassedCount > raw.eligibleQuestionSourcePairs
      || raw.disputedTechnicalPairCount > raw.eligibleQuestionSourcePairs
      || raw.historicalAuditCorruptionPairs > raw.eligibleQuestionSourcePairs) blocked();
  return {
    nctId: NCT, sourceDocumentCount: raw.sourceDocumentCount,
    questionCount: 8, eligibleQuestionSourcePairs: raw.eligibleQuestionSourcePairs,
    pairingTechnicalPreflightPassedCount: raw.pairingTechnicalPreflightPassedCount,
    disputedTechnicalPairCount: raw.disputedTechnicalPairCount,
    historicalAuditCorruptionPairs: raw.historicalAuditCorruptionPairs,
    gates,
    independentClinicalReviewCount: 0, verifiedClinicalSourceCount: 0,
    qualifiedIndependenceAdjudicated: false, formalSecondPersonSignoffCount: 0,
    scientificAdjudicationComplete: false, readyForScientificConclusion: false,
    scientificScore: null, fdaApprovalProbability: null, mayPromoteScientificScore: false,
  };
}
