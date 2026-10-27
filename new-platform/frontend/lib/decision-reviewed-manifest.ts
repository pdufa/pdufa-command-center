import type {DecisionIdentity, ReviewedDecisionEvidence} from "./decision-workstream";
import {parseScienceInvestigation} from "./decision-science-investigation";
import {validatePrimaryTrialSourceIdentity} from "./decision-trial-source-identity";

/** Validation checks transport shape and identity, never the truth of review assertions. */
export const MAX_REVIEWED_MANIFEST_BYTES = 2 * 1024 * 1024;
type Check = (value: unknown) => void;
const invalid = (): never => { throw new Error("Reviewed decision evidence has an invalid schema or identity"); };
const record = (v: unknown): Record<string, unknown> => {
  if (!v || typeof v !== "object" || Array.isArray(v)
      || ![Object.prototype, null].includes(Object.getPrototypeOf(v))) return invalid();
  return v as Record<string, unknown>;
};
const text: Check = v => { if (typeof v !== "string" || v.length > 2048 || /[\u0000-\u001f]/.test(v)) invalid(); };
const bool: Check = v => { if (typeof v !== "boolean") invalid(); };
const number: Check = v => { if (typeof v !== "number" || !Number.isFinite(v)) invalid(); };
const count: Check = v => { number(v); if (!Number.isSafeInteger(v) || (v as number) < 0) invalid(); };
const probability: Check = v => { number(v); if ((v as number) < 0 || (v as number) > 1) invalid(); };
const choices = (...values: unknown[]): Check => v => { if (!values.includes(v)) invalid(); };
const nullable = (check: Check): Check => v => { if (v !== null) check(v); };
const list = (check: Check, maximum = 2000): Check => v => {
  if (!Array.isArray(v) || v.length > maximum) return invalid();
  v.forEach(check);
};
const object = (schema: Record<string, Check>, optional: string[] = []): Check => v => {
  const r = record(v);
  if (Object.keys(r).some(k => !Object.hasOwn(schema, k))) invalid();
  for (const [key, check] of Object.entries(schema)) {
    if (!Object.hasOwn(r, key)) { if (!optional.includes(key)) invalid(); }
    else check(r[key]);
  }
};
const sourceUrl: Check = v => {
  text(v);
  // Explicit missing sources remain missing. The readiness gates reject them.
  if (v === "") return;
  try { const u = new URL(v as string); if (u.protocol !== "https:" || !u.hostname || u.username || u.password) invalid(); }
  catch { invalid(); }
};
const identitySchema = object({exactKey:text, programId:text, trialId:text, ticker:text,
  stage:choices("PIPELINE", "GEM_JR", "GEM")});

export function validateDecisionIdentity(value: unknown): DecisionIdentity {
  identitySchema(value);
  const r = value as DecisionIdentity;
  if (!r.exactKey.trim() || r.exactKey.length > 512 || !/^PDUFA-\d{6,12}$/.test(r.programId)
      || !/^NCT\d{8}$/.test(r.trialId) || !/^[A-Z][A-Z0-9.-]{0,9}$/.test(r.ticker)) invalid();
  return {...r};
}

const review = nullable(object({programId:text, trialId:text, asOf:text,
  status:choices("COMPLETE", "PARTIAL", "MISSING"), sourceStatus:choices("VERIFIED", "UNVERIFIED", "CONFLICT"),
  reviewedLevels:count, requiredLevels:count, criticalFindingsResolved:bool,
  calibrationStatus:choices("VALIDATED", "UNVALIDATED")}, ["calibrationStatus"]));
const target = object({programId:text, asOf:text, diseaseSubtype:text, indication:text, mechanism:text, primaryEndpoint:text});
const analogue = object({programId:text, decisionAt:text, diseaseSubtype:text, indication:text, mechanism:text,
  primaryEndpoint:text, trialPhase:count, outcome:choices("APPROVED", "CRL", "WITHDRAWN"), sourceUrl, independentlyReviewed:bool});
const coverage = object({asOf:text, windowStart:text, windowEnd:text, eligibleApplications:count, reviewedDecisions:count,
  approved:count, crl:count, withdrawn:count, unresolved:count, sourceCoverageConfirmed:bool, includesNonApprovals:bool});
const chronologyRow = object({sourceUrl, publishedAt:text, observedAt:text, decisionAt:text, predictionCutoff:text, independentlyReviewed:bool});
const chronology: Check = v => {
  const r = record(v), keys = Object.keys(r);
  if (keys.length > 2000 || keys.some(k => !/^PDUFA-\d{6,12}$/.test(k))) invalid();
  Object.values(r).forEach(list(chronologyRow, 10));
};
const market = nullable(object({programId:text, ticker:text, observedAt:text, capturedAt:text, adjustedClose:number,
  currency:text, priceSource:sourceUrl, adjustmentMethod:choices("SPLIT_AND_DIVIDEND_ADJUSTED", "SPLIT_ADJUSTED", "RAW"),
  corporateActionsReviewed:bool, verifiedBy:text}));
const main = nullable(object({programId:text, ticker:text, asOf:text, restrictionsReviewed:bool,
  unresolvedCriticalRisks:count, marketEntry:market, marketExit:market}));
const predictionFields = {programId:text, predictedAt:text, decisionAt:text, predictionSource:sourceUrl,
  decisionSource:sourceUrl, predictionCapturedAt:text, decisionObservedAt:text, probability, approved:bool,
  reviewStatus:choices("INDEPENDENTLY_VERIFIED", "PENDING", "CONFLICT")};
const prediction = object(predictionFields);
const holdoutRow = object({...predictionFields, applicationNumber:text, modelVersion:text, subgroup:text});
const plan = object({modelVersion:text, planSource:sourceUrl, frozenAt:text, holdoutStart:text, holdoutEnd:text,
  evaluatedAt:text, trainingProgramIds:list(text), holdoutProgramIds:list(text)});
const longText: Check = v => { if (typeof v !== "string" || v.length > 20000 || /\u0000/.test(v)) invalid(); };
const dossierShape = object({identity:identitySchema, asOf:text, drug:text, indication:text, companyCik:text,
  fdaApplication:nullable(text), layers:list(object({id:text, label:text}), 8),
  levels:list(object({id:text, label:text, layerId:text, assessments:list(object({id:text,
    status:choices("COMPLETE", "PARTIAL", "MISSING", "CONFLICT"), reviewer:text,
    criticalEvaluation:longText, uncertainty:longText, unresolvedCriticalFindings:count,
    sources:list(object({url:sourceUrl, publishedAt:text, observedAt:text, independentlyReviewed:bool, primaryTrial:object({trialId:text, protocolId:text})}, ["primaryTrial"]), 20)}), 2)}), 20)});
const scienceDossier: Check = nullable(v => {
  dossierShape(v);
  const d = parseScienceInvestigation(v);
  for (const level of d.levels) for (const assessment of level.assessments) for (const source of assessment.sources) {
    const primary = (source as typeof source & {primaryTrial?:{trialId:string;protocolId:string}}).primaryTrial;
    if (primary) validatePrimaryTrialSourceIdentity({trialId:d.identity.trialId, protocolId:primary.protocolId}, primary);
  }
});
const evidenceSchema = object({identity:identitySchema, science:review, outcome:review, target, history:list(analogue),
  coverage, chronology, main, calibrationRows:list(prediction), scienceDossier,
  outcomeApplicationNumber:nullable(text), mainCompanyCik:nullable(text),
  holdout:nullable(object({training:list(holdoutRow), rows:list(holdoutRow), plan}))}, ["scienceDossier", "outcomeApplicationNumber", "mainCompanyCik"]);
const digest: Check = v => { if (typeof v !== "string" || !/^[a-f0-9]{64}$/.test(v)) invalid(); };
const envelopeSchema = object({schemaVersion:choices(1), identity:identitySchema, evidence:evidenceSchema,
  researchOnly:choices(true), modelValidated:choices(false), probability:choices(null), tradeAuthorized:choices(false),
  manifestSha256:digest}, ["manifestSha256"]);
const sameIdentity = (a: DecisionIdentity, b: DecisionIdentity) =>
  a.exactKey === b.exactKey && a.programId === b.programId && a.trialId === b.trialId && a.ticker === b.ticker && a.stage === b.stage;

/** No model inference, write, independent verification, or trading permission occurs here.
 * Partial manifests are valid transport; the composer still checks all evidence gates. */
export function parseReviewedDecisionManifest(value: unknown, expected: DecisionIdentity): ReviewedDecisionEvidence {
  validateDecisionIdentity(expected);
  const serialized = JSON.stringify(value);
  if (!serialized || new TextEncoder().encode(serialized).byteLength > MAX_REVIEWED_MANIFEST_BYTES) invalid();
  envelopeSchema(value);
  const r = value as {identity:DecisionIdentity; evidence:ReviewedDecisionEvidence};
  if (!sameIdentity(validateDecisionIdentity(r.identity), expected)
      || !sameIdentity(validateDecisionIdentity(r.evidence.identity), expected)
      || r.evidence.target.programId !== expected.programId
      || [r.evidence.science, r.evidence.outcome].some(s => s && (s.programId !== expected.programId || s.trialId !== expected.trialId))
      || r.evidence.scienceDossier && !sameIdentity(validateDecisionIdentity(r.evidence.scienceDossier.identity), expected)
      || r.evidence.main && (r.evidence.main.programId !== expected.programId || r.evidence.main.ticker !== expected.ticker)) invalid();
  // Clone only after bounded validation, so callers cannot mutate the parsed source object.
  return JSON.parse(serialized).evidence as ReviewedDecisionEvidence;
}
