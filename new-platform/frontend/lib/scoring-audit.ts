/** Conservative parser for the saved post-scan scoring input audit.
 * Reporting stale or incomplete evidence is not a calculation or score.
 */
export type ScoreAuditCheck = {
  Test: string;
  Status: "DATA GAP" | "REVIEW" | "SHARED INPUT" | "OBSERVED";
  Result: string;
  "Why it matters": string;
};
export type ScoreAudit = {
  generated_at_utc: string;
  status: "REVIEW_REQUIRED" | "NO_INPUT_GAPS_FOUND" | "SCAN_FAILURE" | "INPUTS_UNAVAILABLE";
  source_scan: { workflow: string; run_id: number; conclusion: string };
  counts: { input_tests: number; data_gaps: number; reviews: number; models_mapped: number; overlaps: number };
  checks: ScoreAuditCheck[];
  provenance_note: string;
};
export type ScoreAuditView = { audit: ScoreAudit; freshness: "CURRENT" | "STALE" | "CLOCK_UNVERIFIED" };
const STATUSES = new Set(["REVIEW_REQUIRED", "NO_INPUT_GAPS_FOUND", "SCAN_FAILURE", "INPUTS_UNAVAILABLE"]);
const CHECKS = new Set(["DATA GAP", "REVIEW", "SHARED INPUT", "OBSERVED"]);
const isCount = (x: unknown) => typeof x === "number" && Number.isSafeInteger(x) && x >= 0;
const object = (x: unknown): x is Record<string, unknown> => !!x && typeof x === "object" && !Array.isArray(x);

export function scoreAuditView(value: unknown, now = Date.now()): ScoreAuditView | null {
  if (!object(value) || !object(value.source_scan) || !object(value.counts) || !Array.isArray(value.checks)
      || !STATUSES.has(String(value.status)) || typeof value.generated_at_utc !== "string"
      || typeof value.provenance_note !== "string"
      || typeof value.source_scan.workflow !== "string"
      || !isCount(value.source_scan.run_id) || value.source_scan.run_id === 0
      || typeof value.source_scan.conclusion !== "string") return null;
  const counts = value.counts;
  if (["input_tests","data_gaps","reviews","models_mapped","overlaps"].some(k => !isCount(counts[k]))
      || value.checks.length > 100 || value.checks.length !== counts.input_tests) return null;
  for (const item of value.checks) {
    if (!object(item) || !CHECKS.has(String(item.Status))
        || ["Test","Result","Why it matters"].some(k => typeof item[k] !== "string")) return null;
  }
  const gaps = value.checks.filter((x: ScoreAuditCheck) => x.Status === "DATA GAP").length;
  const reviews = value.checks.filter((x: ScoreAuditCheck) => x.Status === "REVIEW").length;
  if (counts.data_gaps !== gaps || counts.reviews !== reviews
      || (value.status === "NO_INPUT_GAPS_FOUND" && (gaps || reviews))
      || (value.status === "REVIEW_REQUIRED" && !gaps && !reviews)) return null;
  const stamp = Date.parse(value.generated_at_utc);
  const freshness = !Number.isFinite(stamp) || !Number.isFinite(now) || stamp > now + 5 * 60_000
    ? "CLOCK_UNVERIFIED"
    : now - stamp > 48 * 60 * 60_000 ? "STALE" : "CURRENT";
  return {audit: value as ScoreAudit, freshness};
}
