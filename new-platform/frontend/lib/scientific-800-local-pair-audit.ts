/**
 * Browser-local consistency audit of two UNTRUSTED full 800-task A/B CSVs.
 * Neither a URL nor a reviewer name proves source bytes/identity/qualification.
 * No signing, submission, scientific grading or database write is possible.
 */
import { buildScientific800ReviewerHandoffCsv } from "./scientific-800-reviewer-handoff";
import type { ScientificDepthMatrix } from "./scientific-depth-review-csv";
import type { ScientificInputAudit } from "./scientific-evidence-requirements-csv";

const MAX_FILE = 3 * 1024 * 1024;
const MAX_FIELD = 5000;
const FIELDS = 29;
const EDITABLE = new Set([18, 20, 21, 22, 23, 25, 26, 27]);
const DECISIONS = new Set(["supports", "contradicts", "uncertain", "not_assessable"]);
const reject = (): never => {
  throw new Error("800-task reviewer comparison blocked: malformed source, mismatched trial, missing task or forged review status.");
};

function parseCsv(source: string): string[][] {
  if (!source || source.length > MAX_FILE || source.includes("\0")) reject();
  const text = source.charCodeAt(0) === 0xfeff ? source.slice(1) : source;
  const rows: string[][] = [];
  let row: string[] = [], value = "";
  let mode: "start" | "unquoted" | "quoted" | "after" = "start";
  const cell = () => {
    if (value.length > MAX_FIELD) reject();
    row.push(value);
    if (row.length > FIELDS) reject();
    value = "";
    mode = "start";
  };
  const line = () => {
    cell();
    if (row.length !== FIELDS || rows.length >= 801) reject();
    rows.push(row);
    row = [];
  };
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (mode === "quoted") {
      if (ch === '"') {
        if (text[i + 1] === '"') { value += '"'; i++; }
        else mode = "after";
      } else value += ch;
    } else if (ch === ",") cell();
    else if (ch === "\r" || ch === "\n") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      if (row.length || mode !== "start" || value) line();
      else if (i < text.length - 1) reject();
    } else if (mode === "start" && ch === '"') mode = "quoted";
    else if (mode === "after" || ch === '"') reject();
    else { value += ch; mode = "unquoted"; }
    if (value.length > MAX_FIELD) reject();
  }
  if (mode === "quoted") reject();
  if (row.length || mode !== "start" || value) line();
  if (rows.length !== 801) reject();
  return rows;
}

function isDate(date: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const d = new Date(date + "T00:00:00Z");
  return Number.isFinite(d.getTime())
    && d.toISOString().slice(0, 10) === date
    && d.getTime() <= Date.now();
}

function hasSource(row: string[]): boolean {
  try {
    const u = new URL(row[20]);
    if (u.protocol !== "https:" || !u.hostname || u.username || u.password
        || row[20].length > 2000) return false;
  } catch { return false; }
  return /^[a-fA-F0-9]{64}$/.test(row[21])
    && isDate(row[22]) && Boolean(row[23].trim());
}

export type Scientific800LocalPairAudit = {
  nctId: string;
  comparedTaskRows: 800;
  candidateDecisions: { A: number; B: number };
  missingOriginalSourceProvenance: { A: number; B: number };
  oneSidedDecisions: number;
  conflictingCandidateDecisions: number;
  conflictingDocumentReferences: number;
  matchingClaimedReviewerNames: number;
  conflictTaskKeys: string[];
  reviewerIdentityAuthenticated: false;
  independentQualificationVerified: false;
  sourceBytesVerified: false;
  signaturesVerified: false;
  adjudicatedTasks: 0;
  scientificScore: null;
  fdaApprovalProbability: null;
};

/**
 * Rejects edits to all immutable source-inventory fields including locked
 * NOT_VERIFIED, NOT_ASSIGNED, NOT_SUBMITTED markers. Edited A/B notes and
 * claimed identities are informational only and are NEVER authenticated.
 */
export function compareScientific800ReviewerCsvs(
  matrix: ScientificDepthMatrix,
  audit: ScientificInputAudit,
  reviewerACsv: string,
  reviewerBCsv: string,
): Scientific800LocalPairAudit {
  const templates = [
    buildScientific800ReviewerHandoffCsv(matrix, audit, "A"),
    buildScientific800ReviewerHandoffCsv(matrix, audit, "B"),
  ];
  const expected = templates.map(parseCsv);
  const [A, B] = [parseCsv(reviewerACsv), parseCsv(reviewerBCsv)];
  for (let sheet = 0; sheet < 2; sheet++) {
    const submitted = sheet === 0 ? A : B;
    for (let i = 0; i < 801; i++) {
      const reference = expected[sheet][i], candidate = submitted[i];
      if (!reference || !candidate || candidate.length !== FIELDS) reject();
      for (let j = 0; j < FIELDS; j++) {
        if (i === 0 || !EDITABLE.has(j)) {
          if (candidate[j] !== reference[j]) reject();
        } else if (candidate[j].length > MAX_FIELD) reject();
      }
      if (i > 0 && !DECISIONS.has(candidate[26]) && candidate[26] !== "NOT_SUBMITTED") reject();
    }
  }

  const candidateDecisions = { A: 0, B: 0 };
  const missingOriginalSourceProvenance = { A: 0, B: 0 };
  let oneSidedDecisions = 0, conflictingCandidateDecisions = 0;
  let conflictingDocumentReferences = 0, matchingClaimedReviewerNames = 0;
  const conflictTaskKeys: string[] = [];
  for (let i = 1; i <= 800; i++) {
    const a = A[i], b = B[i];
    const aDecision = DECISIONS.has(a[26]), bDecision = DECISIONS.has(b[26]);
    if (aDecision) {
      candidateDecisions.A++;
      if (!hasSource(a) || !a[18].trim() || !a[25].trim()) missingOriginalSourceProvenance.A++;
    }
    if (bDecision) {
      candidateDecisions.B++;
      if (!hasSource(b) || !b[18].trim() || !b[25].trim()) missingOriginalSourceProvenance.B++;
    }
    const key = a[1] + ":depth_" + a[2];
    if (aDecision !== bDecision) oneSidedDecisions++;
    if (aDecision && bDecision) {
      if (a[18].trim() && b[18].trim()
          && a[18].trim().toLocaleLowerCase() === b[18].trim().toLocaleLowerCase()) {
        matchingClaimedReviewerNames++;
      }
      if (a[26] !== b[26]) {
        conflictingCandidateDecisions++;
        if (conflictTaskKeys.length < 25) conflictTaskKeys.push(key);
      }
      if (hasSource(a) && hasSource(b)
          && (a[20] !== b[20] || a[21].toLowerCase() !== b[21].toLowerCase())) {
        conflictingDocumentReferences++;
      }
    }
  }

  return {
    nctId: matrix.nctId,
    comparedTaskRows: 800,
    candidateDecisions,
    missingOriginalSourceProvenance,
    oneSidedDecisions,
    conflictingCandidateDecisions,
    conflictingDocumentReferences,
    matchingClaimedReviewerNames,
    conflictTaskKeys,
    reviewerIdentityAuthenticated: false,
    independentQualificationVerified: false,
    sourceBytesVerified: false,
    signaturesVerified: false,
    adjudicatedTasks: 0,
    scientificScore: null,
    fdaApprovalProbability: null,
  };
}
