/**
 * Offline comparison of two UNSIGNED, exact-NCT four-gate source handoffs.
 * Both files may be forged or stale: this is inventory drift detection only,
 * not proof of archival immutability, original publisher, independent review,
 * trial efficacy, or FDA approval.
 */
import { buildScientificSourceReviewHandoff } from "./scientific-captured-archive-check";

const NCT = "NCT02142738";
const MAX_JSON_LENGTH = 256 * 1024;
const BLOCKED = "Source handoff comparison blocked: malformed, wrong-trial, or falsely verified inventory.";

type RawDocument = {
  documentId: string;
  gateId: string;
  sourceType: string;
  sha256: string;
  byteLength: number;
  capturedByteIntegrity: "REHASHED_AT_AUTHENTICATED_ARCHIVE_READ";
  originalPublisherAuthenticated: false;
  sourceContentClinicallyAdjudicated: false;
};

type ValidHandoff = {
  sourceDocumentCount: number;
  capturedEvidenceCategories: number;
  capturedPdfFingerprints: RawDocument[];
  gateCoverage: { gateId: string; capturedPdfCount: number }[];
};

const fail = (): never => { throw new Error(BLOCKED); };

function isRecord(x: unknown): x is Record<string, unknown> {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

/** Re-run the original handoff builder against a strictly reconstructed
 * source manifest, then demand the exact canonical packet fields and values.
 * This independently rechecks all safety flags, gate counts, immutable byte
 * digest identifiers, missing actions, and forbidden sensitive extra fields.
 */
function validate(raw: string): ValidHandoff {
  if (typeof raw !== "string" || raw.length === 0
      || raw.length > MAX_JSON_LENGTH || raw.includes("\0")) fail();
  let value: unknown;
  try { value = JSON.parse(raw); }
  catch { return fail(); }
  if (!isRecord(value)) fail();
  const fingerprintRows = value.capturedPdfFingerprints;
  if (value.nctId !== NCT
      || value.schemaVersion !== "isolated-science-source-review-handoff-v1"
      || value.classification !== "UNSIGNED_UNVERIFIED_SOURCE_INVENTORY"
      || !Array.isArray(fingerprintRows)
      || fingerprintRows.length > 8) fail();

  const docs: RawDocument[] = [];
  for (const item of fingerprintRows as unknown[]) {
    if (!isRecord(item)) fail();
    const { documentId, gateId, sourceType, sha256, byteLength } = item;
    if (typeof documentId !== "string" || !/^[a-f0-9]{32}$/.test(documentId)
        || typeof gateId !== "string" || !/^[a-z_]{3,32}$/.test(gateId)
        || typeof sourceType !== "string" || !/^[a-z_]{3,64}$/.test(sourceType)
        || typeof sha256 !== "string" || !/^[a-f0-9]{64}$/.test(sha256)
        || !Number.isSafeInteger(byteLength) || (byteLength as number) < 32
        || (byteLength as number) > 5 * 1024 * 1024) fail();
    docs.push({
      documentId, gateId, sourceType, sha256, byteLength,
      capturedByteIntegrity: "REHASHED_AT_AUTHENTICATED_ARCHIVE_READ",
      originalPublisherAuthenticated: false,
      sourceContentClinicallyAdjudicated: false,
    } as RawDocument);
  }
  const rebuilt = {
    nctId: NCT, sourceDocumentCount: docs.length,
    allCapturedBytesRehashed: true, independentSourceVerificationCompleted: false,
    scientificScore: null, fdaApprovalProbability: null,
    documents: docs.map(doc => ({
      documentId: doc.documentId, gateId: doc.gateId,
      sourceType: doc.sourceType, sha256: doc.sha256, byteLength: doc.byteLength,
      captureStatus: "byte_integrity_checked_unverified",
      scientificVerificationComplete: false,
    })),
  };
  try {
    const expected = JSON.parse(buildScientificSourceReviewHandoff(NCT, rebuilt));
    // All allowed fields and fixed non-verification statuses must match EXACTLY.
    // JSON whitespace may differ, but field additions, edits or reordered IDs fail.
    if (JSON.stringify(value) !== JSON.stringify(expected)) fail();
  } catch { fail(); }

  return value as unknown as ValidHandoff;
}

export type HandoffDrift = {
  nctId: "NCT02142738";
  priorDocumentCount: number;
  laterDocumentCount: number;
  addedDocumentIds: string[];
  removedDocumentIds: string[];
  changedDocumentIds: string[];
  unchangedDocumentCount: number;
  gates: {
    gateId: string;
    priorCapturedPdfCount: number;
    laterCapturedPdfCount: number;
  }[];
  comparisonResult: "NO_REPORTED_CHANGE" | "CAPTURED_INVENTORY_CHANGED";
  sourcesAuthenticated: false;
  snapshotsCryptographicallySigned: false;
  reviewerCredentialsVerified: false;
  clinicalAdjudicationComplete: false;
  scientificScore: null;
  fdaApprovalProbability: null;
  promotionAllowed: false;
};

/** Earlier/later are selected by the operator: ordering cannot be proven from
 * unsigned packets; this comparison never claims trustworthy provenance.
 */
export function compareFourGateSourceHandoffs(priorJson: string, laterJson: string): HandoffDrift {
  const prior = validate(priorJson);
  const later = validate(laterJson);
  const oldDocs = new Map(prior.capturedPdfFingerprints.map(x => [x.documentId, x]));
  const newDocs = new Map(later.capturedPdfFingerprints.map(x => [x.documentId, x]));
  const added: string[] = [];
  const removed: string[] = [];
  const changed: string[] = [];
  let unchanged = 0;
  for (const [id, doc] of oldDocs) {
    const now = newDocs.get(id);
    if (!now) removed.push(id);
    else if (doc.sha256 !== now.sha256 || doc.byteLength !== now.byteLength
        || doc.gateId !== now.gateId || doc.sourceType !== now.sourceType) changed.push(id);
    else unchanged++;
  }
  for (const id of newDocs.keys()) if (!oldDocs.has(id)) added.push(id);
  added.sort();
  removed.sort();
  changed.sort();
  const gates = prior.gateCoverage.map((old, i) => ({
    gateId: old.gateId,
    priorCapturedPdfCount: old.capturedPdfCount,
    laterCapturedPdfCount: later.gateCoverage[i].capturedPdfCount,
  }));
  const drift = added.length > 0 || removed.length > 0 || changed.length > 0;
  return {
    nctId: NCT,
    priorDocumentCount: prior.sourceDocumentCount,
    laterDocumentCount: later.sourceDocumentCount,
    addedDocumentIds: added,
    removedDocumentIds: removed,
    changedDocumentIds: changed,
    unchangedDocumentCount: unchanged,
    gates,
    comparisonResult: drift ? "CAPTURED_INVENTORY_CHANGED" : "NO_REPORTED_CHANGE",
    sourcesAuthenticated: false,
    snapshotsCryptographicallySigned: false,
    reviewerCredentialsVerified: false,
    clinicalAdjudicationComplete: false,
    scientificScore: null,
    fdaApprovalProbability: null,
    promotionAllowed: false,
  };
}
