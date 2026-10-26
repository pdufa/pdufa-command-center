/** Recorded required evidence gaps from the exact source-audit run shown in GOAL. */
import type { GoalScanView } from "./goal-scan-evidence";
import { goalSourceCoverage } from "./goal-source-coverage";

type Obj = Record<string, unknown>;
const object = (x: unknown): x is Obj => x !== null && typeof x === "object" && !Array.isArray(x);
const categories = new Set(["FDA", "SEC", "FINANCIAL", "MARKET", "ISSUER"]);
const statuses = new Set(["REVIEW_REQUIRED", "UNAVAILABLE", "CONFLICT", "TECHNICAL_FAILURE"]);
const text = (x: unknown, max: number): x is string =>
  typeof x === "string" && x.trim().length > 0 && x.length <= max && !/[\u0000-\u001f\u007f]/.test(x);

function recordedSource(value: unknown): string | null {
  if (typeof value !== "string" || value.length > 2000 || /\s/.test(value)) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password && !url.port &&
      /^[a-z0-9.-]+\.[a-z]{2,}$/i.test(url.hostname) &&
      !/\.(local|internal|test|example|invalid)$/i.test(url.hostname) ? value : null;
  } catch { return null; }
}

export type GoalSourceIssue = {
  id: string;
  ticker: string;
  eventKey: string;
  category: string;
  claim: string;
  status: string;
  reason: string;
  checkedAt: string;
  sourceUrl: string | null;
};
export type GoalSourceReview = { runId: number; total: number; items: GoalSourceIssue[] };

export function goalSourceReview(source: unknown, scan: GoalScanView | null): GoalSourceReview | null {
  const coverage = goalSourceCoverage(source, scan);
  if (!coverage || !object(source)) return null;
  const total = source.required_findings_unresolved;
  const rows = source.required_issue_examples;
  if (typeof total !== "number" || !Number.isSafeInteger(total) || total < 0 || total > coverage.due ||
      (coverage.fullCoverage && total !== 0) || !Array.isArray(rows) ||
      rows.length > 24 || rows.length > total) return null;
  const items: GoalSourceIssue[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    // SEC ticker/CIK conflicts are published with REGISTRY:TICKER identities,
    // not the usual TICKER|PROGRAM identity. Admit only that exact recorded
    // claim type; never silently drop a conflicted issuer source.
    const registryConflict = object(row)
      && row.category === "SEC"
      && row.claim === "FILINGS_INVENTORY"
      && row.verification_status === "CONFLICT"
      && typeof row.ticker === "string"
      && row.event_key === "REGISTRY:" + row.ticker;
    if (!object(row) || row.verification_required !== "YES" ||
        !text(row.ticker, 13) || !/^[A-Z][A-Z0-9.-]{0,12}$/.test(row.ticker) ||
        !text(row.event_key, 300) || !(registryConflict ||
          (row.event_key.startsWith(row.ticker + "|") &&
           row.event_key.length > row.ticker.length + 1)) ||
        !text(row.category, 24) || !categories.has(row.category) ||
        !text(row.claim, 80) || !/^[A-Z][A-Z0-9_]+$/.test(row.claim) ||
        !text(row.verification_status, 24) || !statuses.has(row.verification_status) ||
        !text(row.reason, 1500) || !text(row.checked_at, 40) ||
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(row.checked_at) ||
        !Number.isFinite(Date.parse(row.checked_at))) return null;
    const id = [row.event_key, row.category, row.claim].join("|");
    // Different programs for one ticker, or different claims for one program, stay separate.
    if (seen.has(id)) return null;
    seen.add(id);
    items.push({ id, ticker: row.ticker, eventKey: row.event_key, category: row.category,
      claim: row.claim, status: row.verification_status, reason: row.reason,
      checkedAt: row.checked_at, sourceUrl: recordedSource(row.source_url) });
  }
  return { runId: coverage.runId, total, items };
}

export function filterSourceIssues(items: GoalSourceIssue[], category: string, query: string): GoalSourceIssue[] {
  const needle = query.trim().toLowerCase();
  return items.filter(item => (category === "ALL" || item.category === category) &&
    (!needle || [item.ticker, item.eventKey, item.claim, item.status, item.reason]
      .some(value => value.toLowerCase().includes(needle))));
}
