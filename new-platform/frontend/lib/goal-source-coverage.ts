/** Strict read-only interpretation of the original per-run source verification ledger.
 * Coverage describes source audit findings, NOT trials, scores or trading readiness.
 * The published source audit must match the exact dated GOAL clinical run.
 */
import type { GoalScanView } from "./goal-scan-evidence";

type Obj = Record<string, unknown>;
const object = (x: unknown): x is Obj => x !== null && typeof x === "object" && !Array.isArray(x);
const count = (x: unknown): number | null =>
  typeof x === "number" && Number.isSafeInteger(x) && x >= 0 ? x : null;
const exactRunId = (x: unknown): number | null => {
  if (typeof x === "number") return count(x);
  if (typeof x !== "string" || !/^[1-9][0-9]{0,15}$/.test(x)) return null;
  const parsed = Number(x);
  return Number.isSafeInteger(parsed) ? parsed : null;
};
export type GoalSourceCoverage = {
  runId: number;
  runUrl: string;
  date: string;
  today: boolean;
  verified: number;
  due: number;
  unresolved: number;
  conflicted: number;
  unavailable: number;
  notApplicable: number;
  missingRequired: string[];
  fullCoverage: boolean;
  coveragePercent: number;
};

export function goalSourceCoverage(source: unknown, scan: GoalScanView | null): GoalSourceCoverage | null {
  if (!scan || scan.status === "RUN_FAILED" || !object(source)) return null;
  const runId = exactRunId(source.latest_run_id);
  if (!runId || runId !== scan.runId || source.latest_run_url !== scan.runUrl) return null;
  // COMPLETE here means the audit program finished, not that evidence coverage is complete.
  if (source.execution_status !== "COMPLETE" || typeof source.full_coverage_verified !== "boolean") return null;
  const values = [
    count(source.findings_due), count(source.findings_verified),
    count(source.findings_unresolved), count(source.findings_unavailable),
    count(source.findings_not_applicable),
  ];
  if (values.some(value=>value===null)) return null;
  const [due,verified,unresolved,unavailable,notApplicable] = values as number[];
  // Older ledgers had no explicit conflicts field; new ledgers must preserve
  // this independent status rather than folding it into unresolved or silently
  // hiding the whole coverage panel due to a two-record accounting mismatch.
  const conflicted = source.findings_conflicted === undefined ? 0 : count(source.findings_conflicted);
  if (conflicted === null || due === 0 || due > 10000000 ||
      verified + unresolved + conflicted + unavailable + notApplicable !== due) return null;
  if (!Array.isArray(source.missing_required_source_families) ||
      source.missing_required_source_families.length > 12 ||
      source.missing_required_source_families.some(name=>
        typeof name !== "string" || !/^[A-Z][A-Z0-9_]{1,23}$/.test(name))) return null;
  const missingRequired=source.missing_required_source_families as string[];
  if (new Set(missingRequired).size !== missingRequired.length) return null;
  if (source.full_coverage_verified === true &&
      (unresolved !== 0 || conflicted !== 0 || unavailable !== 0 || missingRequired.length !== 0)) return null;
  return {
    runId,runUrl:scan.runUrl,date:scan.date,today:scan.today,
    due,verified,unresolved,conflicted,unavailable,notApplicable,
    missingRequired,fullCoverage:source.full_coverage_verified,
    coveragePercent:Math.round((verified/due)*1000)/10,
  };
}
