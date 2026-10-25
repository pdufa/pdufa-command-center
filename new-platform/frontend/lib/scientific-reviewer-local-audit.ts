/**
 * Browser-only audit of two UNTRUSTED human-entered reviewer worksheets.
 * This never sends a request, saves a review or certifies source/identity.
 */
import {
  buildScientificReviewerHandoffCsv, type ScientificDepthMatrix,
} from "./scientific-depth-review-csv";

const BASE_COLUMNS = [
  "nct_id", "layer", "assessment", "depth_level", "depth", "review_objective",
  "review_status", "independently_verified", "scientific_score",
  "fda_approval_probability",
] as const;
const REVIEW_COLUMNS = [
  "reviewer_slot", "reviewer_name", "qualification_verification",
  "primary_document_url", "document_sha256", "public_document_date",
  "evidence_section_or_table", "finding_notes", "reviewer_decision",
  "reviewer_signature", "submission_status",
] as const;
const HEADER = [...BASE_COLUMNS, ...REVIEW_COLUMNS];
const TYPES = new Set(["supports", "contradicts", "uncertain", "not_assessable"]);
const MAX_BYTES = 1024 * 1024;
const MAX_CELL = 5000;
type Parsed = string[][];
type Slot = "A" | "B";

export type LocalReviewAudit = {
  exactNctId: string;
  candidateA: number;
  candidateB: number;
  missingProvenanceA: number;
  missingProvenanceB: number;
  incompleteNotesA: number;
  incompleteNotesB: number;
  oneSidedObservations: number;
  disagreementTaskIds: string[];
  candidateDisagreementCount: number;
  tasksIndependentlyAdjudicated: 0;
  sourceDocumentsAuthenticated: false;
  reviewersAuthenticated: false;
  signaturesVerified: false;
  promotionAllowed: false;
  scientificScore: null;
  fdaApprovalProbability: null;
  status: "BLOCKED_REQUIRES_INDEPENDENT_REVIEW";
};

function reject(): never {
  throw new Error("Local reviewer audit blocked: invalid, altered or untrusted worksheet.");
}

/** Strict bounded RFC-style CSV parser, including quoted commas/newlines. */
function parseCsv(source: string): Parsed {
  if (typeof source !== "string" || source.length > MAX_BYTES || !source || source.includes("\0")) reject();
  const rows: Parsed = [];
  let row: string[] = [], cell = "", quoted = false, afterQuote = false, fieldStarted = false;
  function finishCell() {
    if (cell.length > MAX_CELL) reject();
    row.push(cell);
    cell = "";
    afterQuote = false;
    fieldStarted = false;
  }
  function finishRow() {
    finishCell();
    rows.push(row);
    row = [];
    if (rows.length > 321) reject();
  }
  const csv = source.charCodeAt(0) === 0xFEFF ? source.slice(1) : source;
  for (let i = 0; i < csv.length; i++) {
    const ch = csv[i];
    if (quoted) {
      if (ch === '"') {
        if (csv[i + 1] === '"') { cell += '"'; i++; }
        else { quoted = false; afterQuote = true; }
      } else cell += ch;
    } else if (afterQuote) {
      if (ch === ",") finishCell();
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && csv[i + 1] === "\n") i++;
        finishRow();
      } else reject();
    } else if (ch === '"' && !fieldStarted) {
      quoted = true; fieldStarted = true;
    } else if (ch === ",") finishCell();
    else if (ch === "\r" || ch === "\n") {
      if (ch === "\r" && csv[i + 1] === "\n") i++;
      finishRow();
    } else {
      if (ch === '"') reject();
      cell += ch; fieldStarted = true;
    }
    if (cell.length > MAX_CELL) reject();
  }
  if (quoted) reject();
  // A single terminal newline is not another empty row.
  if (row.length || cell.length || fieldStarted || afterQuote) finishRow();
  return rows;
}

function validDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(value + "T00:00:00.000Z");
  return Number.isFinite(date.valueOf())
    && date.toISOString().slice(0, 10) === value
    && date.valueOf() <= Date.now();
}

/** A URL/hash/date here are UNVERIFIED strings, not authenticated provenance. */
function syntacticProvenance(row: string[]): boolean {
  const url = row[13], digest = row[14], published = row[15], section = row[16];
  if (url.length > 2000 || /[\r\n\t]/.test(url) || !/^https:\/\//i.test(url)) return false;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || !parsed.hostname || parsed.username || parsed.password) return false;
  } catch { return false; }
  return /^[a-fA-F0-9]{64}$/.test(digest) && validDate(published) && !!section.trim();
}

function validateSheet(
  source: string,
  slot: Slot,
  expected: Parsed,
): Parsed {
  const rows = parseCsv(source);
  if (rows.length !== 321 || rows[0].length !== HEADER.length
      || rows[0].some((value, idx) => value !== HEADER[idx])) reject();
  for (let i = 1; i <= 320; i++) {
    const row = rows[i], baseline = expected[i];
    if (!row || row.length !== HEADER.length || !baseline
        || row.slice(0, BASE_COLUMNS.length).some((cell, col) => cell !== baseline[col])
        || row[10] !== slot || row[12] !== "NOT_VERIFIED"
        || row[20] !== "NOT_SUBMITTED"
        || (row[18] !== "NOT_SUBMITTED" && !TYPES.has(row[18]))) reject();
  }
  return rows;
}

export function reconcileLocalReviewerWorksheets(
  matrix: ScientificDepthMatrix, csvA: string, csvB: string,
): LocalReviewAudit {
  // Reuse the same full 320-task fail-closed contract as the download controls.
  const expectedA = parseCsv(buildScientificReviewerHandoffCsv(matrix, "A"));
  const expectedB = parseCsv(buildScientificReviewerHandoffCsv(matrix, "B"));
  const a = validateSheet(csvA, "A", expectedA);
  const b = validateSheet(csvB, "B", expectedB);
  let candidateA = 0, candidateB = 0;
  let missingProvenanceA = 0, missingProvenanceB = 0;
  let incompleteNotesA = 0, incompleteNotesB = 0;
  let oneSidedObservations = 0;
  const disagreementTaskIds: string[] = [];

  for (let i = 1; i <= 320; i++) {
    const x = a[i], y = b[i];
    const observedA = x[18] !== "NOT_SUBMITTED";
    const observedB = y[18] !== "NOT_SUBMITTED";
    const provenanceA = observedA && syntacticProvenance(x);
    const provenanceB = observedB && syntacticProvenance(y);
    const completeA = provenanceA && !!x[11].trim() && !!x[17].trim();
    const completeB = provenanceB && !!y[11].trim() && !!y[17].trim();
    if (observedA && !provenanceA) missingProvenanceA++;
    if (observedB && !provenanceB) missingProvenanceB++;
    if (provenanceA && !completeA) incompleteNotesA++;
    if (provenanceB && !completeB) incompleteNotesB++;
    if (completeA) candidateA++;
    if (completeB) candidateB++;
    if (completeA !== completeB) oneSidedObservations++;
    if (completeA && completeB && x[18] !== y[18]) {
      // Only trusted canonical task keys are displayed. Never show reviewer notes.
      disagreementTaskIds.push(x[2] + ":" + x[3]);
    }
  }

  return {
    exactNctId: matrix.nctId,
    candidateA, candidateB, missingProvenanceA, missingProvenanceB,
    incompleteNotesA, incompleteNotesB, oneSidedObservations,
    disagreementTaskIds, candidateDisagreementCount: disagreementTaskIds.length,
    tasksIndependentlyAdjudicated: 0,
    sourceDocumentsAuthenticated: false, reviewersAuthenticated: false,
    signaturesVerified: false, promotionAllowed: false,
    scientificScore: null, fdaApprovalProbability: null,
    status: "BLOCKED_REQUIRES_INDEPENDENT_REVIEW",
  };
}
