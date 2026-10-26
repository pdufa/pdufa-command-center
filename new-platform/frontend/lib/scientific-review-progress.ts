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

export type ScientificQuestionWork = {
  questionId: string;
  gateId: typeof ORDER[number];
  title: string;
  priority: "critical" | "high" | "medium";
  nextScientificCheck: string;
  capturedSourceCount: number;
  eligibleSourcePairs: number;
  technicallyPairedSources: number;
  unpairedSources: number;
  disputedSourcePairs: number;
  invalidAuditHistoryPairs: number;
  technicalWorkStatus:
    | "CAPTURE_ORIGINAL_SOURCE_REQUIRED"
    | "AUDIT_HISTORY_REQUIRES_REPAIR"
    | "RECORDED_DECISION_CONFLICT"
    | "TWO_REVIEWER_TECHNICAL_PAIR_REQUIRED"
    | "PARTIAL_TECHNICAL_PAIR_COVERAGE"
    | "TECHNICAL_PAIR_ONLY_UNADJUDICATED";
  qualifiedIndependentReviewCompleted: false;
  scientificQuestionResolved: false;
};

const QUESTION_SEQUENCE = [
  ["protocol_amendment_chronology", "protocol_sap"],
  ["baseline_population_indication", "published_results"],
  ["pfs_initial_vs_followup", "published_results"],
  ["crossover_adjustment", "published_results"],
  ["safety_endpoint_taxonomy", "published_results"],
  ["exploratory_qol_multiplicity", "published_results"],
  ["2015_vs_2016_fda_actions", "official_regulatory"],
  ["independent_corroboration", "independent_replication"],
] as const;

function safeLabel(x: unknown, max: number): x is string {
  return typeof x === "string" && x.length >= 3 && x.length <= max
    && !/[\u0000-\u001F\u007F]/.test(x);
}

function classifyQuestion(q: Record<string, unknown>): ScientificQuestionWork["technicalWorkStatus"] {
  if ((q.invalidAuditHistoryPairs as number) > 0) return "AUDIT_HISTORY_REQUIRES_REPAIR";
  if ((q.disputedSourcePairs as number) > 0) return "RECORDED_DECISION_CONFLICT";
  if ((q.capturedSourceCount as number) === 0) return "CAPTURE_ORIGINAL_SOURCE_REQUIRED";
  if ((q.technicallyPairedSources as number) === 0) return "TWO_REVIEWER_TECHNICAL_PAIR_REQUIRED";
  if ((q.unpairedSources as number) > 0) return "PARTIAL_TECHNICAL_PAIR_COVERAGE";
  return "TECHNICAL_PAIR_ONLY_UNADJUDICATED";
}

export type ScientificPairProgress = {
  nctId: typeof NCT;
  sourceDocumentCount: number;
  questionCount: 8;
  eligibleQuestionSourcePairs: number;
  pairingTechnicalPreflightPassedCount: number;
  disputedTechnicalPairCount: number;
  historicalAuditCorruptionPairs: number;
  openUnadjudicatedQuestionCount: 8;
  questions: ScientificQuestionWork[];
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
      || raw.openUnadjudicatedQuestionCount !== 8
      || !Array.isArray(raw.questions) || raw.questions.length !== 8
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
      capturedSourceCount: g.capturedSourceCount as number,
      reconciliationQuestionCount: g.reconciliationQuestionCount as number,
      eligibleQuestionSourcePairs: g.eligibleQuestionSourcePairs as number,
      pairingTechnicalPreflightPassed: g.pairingTechnicalPreflightPassed as number,
      twoAuthorizedReviewersRecorded: g.twoAuthorizedReviewersRecorded as number,
      disputedTechnicalPairCount: g.disputedTechnicalPairCount as number,
      historicalAuditCorruptionPairs: g.historicalAuditCorruptionPairs as number,
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
  const questions: ScientificQuestionWork[] = [];
  for (let i = 0; i < QUESTION_SEQUENCE.length; i++) {
    const question = (raw.questions as unknown[])[i];
    if (!object(question)) throw Error("Technical reviewer question contract unverified");
    const [expectedId, expectedGate] = QUESTION_SEQUENCE[i];
    if (question.questionId !== expectedId || question.gateId !== expectedGate
        || !safeLabel(question.title, 200)
        || !safeLabel(question.nextScientificCheck, 700)
        || !["critical", "high", "medium"].includes(question.priority as string)
        || question.qualifiedIndependentReviewCompleted !== false
        || question.scientificQuestionResolved !== false
        || !bounded(question.capturedSourceCount, 8)
        || !bounded(question.eligibleSourcePairs, 8)
        || !bounded(question.technicallyPairedSources, 8)
        || !bounded(question.unpairedSources, 8)
        || !bounded(question.disputedSourcePairs, 8)
        || !bounded(question.invalidAuditHistoryPairs, 8)
        || question.capturedSourceCount !== question.eligibleSourcePairs
        || (question.technicallyPairedSources as number) +
           (question.unpairedSources as number) !== question.eligibleSourcePairs
        || (question.disputedSourcePairs as number) > question.eligibleSourcePairs
        || (question.invalidAuditHistoryPairs as number) > question.eligibleSourcePairs
        || question.technicalWorkStatus !== classifyQuestion(question)
        || question.capturedSourceCount !==
           gates.find(g => g.gateId === expectedGate)?.capturedSourceCount
    ) blocked();
    questions.push({
      questionId: expectedId, gateId: expectedGate,
      title: question.title as string,
      priority: question.priority as ScientificQuestionWork["priority"],
      nextScientificCheck: question.nextScientificCheck as string,
      capturedSourceCount: question.capturedSourceCount as number,
      eligibleSourcePairs: question.eligibleSourcePairs as number,
      technicallyPairedSources: question.technicallyPairedSources as number,
      unpairedSources: question.unpairedSources as number,
      disputedSourcePairs: question.disputedSourcePairs as number,
      invalidAuditHistoryPairs: question.invalidAuditHistoryPairs as number,
      technicalWorkStatus: classifyQuestion(question),
      qualifiedIndependentReviewCompleted: false,
      scientificQuestionResolved: false,
    });
  }
  const questionsSum = (key: "eligibleSourcePairs"|"technicallyPairedSources"
      |"disputedSourcePairs"|"invalidAuditHistoryPairs") =>
    questions.reduce((sum, q) => sum + q[key], 0);
  if (questionsSum("eligibleSourcePairs") !== raw.eligibleQuestionSourcePairs
      || questionsSum("technicallyPairedSources") !== raw.pairingTechnicalPreflightPassedCount
      || questionsSum("disputedSourcePairs") !== raw.disputedTechnicalPairCount
      || questionsSum("invalidAuditHistoryPairs") !== raw.historicalAuditCorruptionPairs
      || gates.some(g => questions.filter(q => q.gateId === g.gateId).length
         !== g.reconciliationQuestionCount)) blocked();

  return {
    nctId: NCT, sourceDocumentCount: raw.sourceDocumentCount as number,
    questionCount: 8, eligibleQuestionSourcePairs: raw.eligibleQuestionSourcePairs as number,
    pairingTechnicalPreflightPassedCount: raw.pairingTechnicalPreflightPassedCount as number,
    disputedTechnicalPairCount: raw.disputedTechnicalPairCount as number,
    historicalAuditCorruptionPairs: raw.historicalAuditCorruptionPairs as number,
    gates, questions, openUnadjudicatedQuestionCount: 8,
    independentClinicalReviewCount: 0, verifiedClinicalSourceCount: 0,
    qualifiedIndependenceAdjudicated: false, formalSecondPersonSignoffCount: 0,
    scientificAdjudicationComplete: false, readyForScientificConclusion: false,
    scientificScore: null, fdaApprovalProbability: null, mayPromoteScientificScore: false,
  };
}
