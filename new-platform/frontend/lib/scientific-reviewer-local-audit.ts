/**
 * Browser-local read-only reconciliation of three exported 320-task worksheets.
 * CSV input is UNTRUSTED. This is never evidence submission, independent
 * reviewer authentication, document byte verification, or scientific scoring.
 */
import {
  buildScientificDepthReviewCsv, buildScientificReviewerHandoffCsv,
  type ScientificDepthMatrix,
} from "./scientific-depth-review-csv";

const MAX_CHARS = 1024 * 1024;
const DECISIONS = new Set(["supports", "contradicts", "uncertain", "not_assessable"]);
const problem = (): never => {
  throw new Error("Reviewer worksheet comparison blocked: invalid trial, matrix, CSV or unverified review claim.");
};

/** Quote-aware bounded CSV reader. Allows quoted reviewer notes containing newlines. */
function readCsv(text: string): string[][] {
  if (!text || text.length > MAX_CHARS || text.includes("\0")) problem();
  const source = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  const result: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let mode: "start" | "quoted" | "unquoted" | "after_quote" = "start";
  const field = () => {
    if (cell.length > 5000) problem();
    row.push(cell);
    cell = "";
    mode = "start";
    if (row.length > 21) problem();
  };
  const record = () => {
    field();
    if (result.length >= 321) problem();
    result.push(row);
    row = [];
  };
  for (let i = 0; i < source.length; i++) {
    const c = source[i];
    if (mode === "quoted") {
      if (c === '"') {
        if (source[i + 1] === '"') { cell += '"'; i++; }
        else mode = "after_quote";
      } else cell += c;
    } else if (c === ",") {
      recordField();
    } else if (c === "\r" || c === "\n") {
      if (c === "\r" && source[i + 1] === "\n") i++;
      record();
    } else if (mode === "start" && c === '"') mode = "quoted";
    else if (mode === "after_quote" || c === '"') problem();
    else { mode = "unquoted"; cell += c; }
    if (cell.length > 5000) problem();
  }
  function recordField() {
    field();
  }
  if (mode === "quoted") problem();
  if (mode !== "start" || cell !== "" || row.length) record();
  if (result.length !== 321) problem();
  return result;
}

function same(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((cell, i) => cell === b[i]);
}

function eligibleProvenance(row: string[]): boolean {
  const url = row[13];
  if (!url || url.length > 2000) return false;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:" || !parsed.hostname || parsed.username || parsed.password) return false;
  } catch { return false; }
  if (!/^[a-fA-F0-9]{64}$/.test(row[14])) return false;
  const date = row[15];
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const parsedDate = new Date(date + "T00:00:00Z");
  if (Number.isNaN(parsedDate.getTime()) || parsedDate.toISOString().slice(0, 10) !== date
      || parsedDate.getTime() > Date.now()) return false;
  return Boolean(row[16].trim());
}

export type LocalReviewerAuditReport = {
  nctId: string;
  validatedTaskRows: 320;
  candidateObservations: { A: number; B: number };
  missingProvenance: { A: number; B: number };
  incompleteObservations: { A: number; B: number };
  oneSidedObservations: number;
  conflictingCandidateDecisions: number;
  conflictTaskKeys: string[];
  reviewerIdentitiesVerified: false;
  sourceBytesVerified: false;
  signaturesVerified: false;
  independentlyAdjudicatedTasks: 0;
  scientificScore: null;
  fdaApprovalProbability: null;
  promotionAllowed: false;
};

/** No file upload, storage, network call or promotion—even identical A/B rows are NOT adjudication. */
export function auditScientificReviewerCsvs(
  matrix: ScientificDepthMatrix, inventoryCsv: string, reviewerACsv: string, reviewerBCsv: string,
): LocalReviewerAuditReport {
  const expectedInventory = readCsv(buildScientificDepthReviewCsv(matrix));
  const expectedReviewer = readCsv(buildScientificReviewerHandoffCsv(matrix, "A"));
  const inventory = readCsv(inventoryCsv);
  const reviewers = { A: readCsv(reviewerACsv), B: readCsv(reviewerBCsv) };
  for (let i = 0; i < expectedInventory.length; i++) {
    if (!same(inventory[i], expectedInventory[i])) problem();
  }
  const observations = { A: 0, B: 0 };
  const missingProvenance = { A: 0, B: 0 };
  const incomplete = { A: 0, B: 0 };
  const complete = { A: [] as boolean[], B: [] as boolean[] };
  for (const slot of ["A", "B"] as const) {
    const rows = reviewers[slot];
    if (!same(rows[0], expectedReviewer[0])) problem();
    for (let i = 1; i <= 320; i++) {
      const row = rows[i];
      if (row.length !== 21 || !same(row.slice(0, 10), expectedInventory[i])
          || row[10] !== slot || row[12] !== "NOT_VERIFIED"
          || row[20] !== "NOT_SUBMITTED"
          || !DECISIONS.has(row[18]) && row[18] !== "NOT_SUBMITTED") problem();
      const entered = row[18] !== "NOT_SUBMITTED";
      const goodSource = eligibleProvenance(row);
      const namesNotes = Boolean(row[11].trim() && row[17].trim());
      const good = entered && goodSource && namesNotes;
      if (entered && !goodSource) missingProvenance[slot]++;
      if (entered && !namesNotes) incomplete[slot]++;
      if (good) observations[slot]++;
      complete[slot].push(good);
    }
  }
  let oneSided = 0;
  const conflicts: string[] = [];
  for (let i = 1; i <= 320; i++) {
    const a = complete.A[i - 1], b = complete.B[i - 1];
    if (a !== b) oneSided++;
    if (a && b && reviewers.A[i][18] !== reviewers.B[i][18]) {
      conflicts.push(expectedInventory[i][2] + ":" + expectedInventory[i][3]);
    }
  }
  return {
    nctId: matrix.nctId,
    validatedTaskRows: 320,
    candidateObservations: observations,
    missingProvenance,
    incompleteObservations: incomplete,
    oneSidedObservations: oneSided,
    conflictingCandidateDecisions: conflicts.length,
    conflictTaskKeys: conflicts,
    reviewerIdentitiesVerified: false,
    sourceBytesVerified: false,
    signaturesVerified: false,
    independentlyAdjudicatedTasks: 0,
    scientificScore: null,
    fdaApprovalProbability: null,
    promotionAllowed: false,
  };
}
