export type HealthState = "good" | "warning" | "failed" | "unknown";
export type HealthCheck = {
  id: string; label: string; state: HealthState; summary: string;
  detail: string; checkedAt: string | null;
};
export type SiteHealthReport = { checkedAt: string; checks: HealthCheck[] };
type RecordData = Record<string, unknown>;
export function record(value: unknown): RecordData | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? value as RecordData : null;
}
export function count(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) >= 0;
}
export function timestamp(value: unknown): string | null {
  return typeof value === "string" && Number.isFinite(Date.parse(value)) ? value : null;
}
export function current(value: unknown, now: number, hours = 36): boolean {
  const time = timestamp(value);
  return !!time && now - Date.parse(time) >= -300000 && now - Date.parse(time) <= hours * 3600000;
}
export function overallHealth(checks: HealthCheck[]): HealthState {
  // Combining colors must never average a failure or missing check into green.
  if (checks.some(check => check.state === "failed")) return "failed";
  if (!checks.length || checks.every(check => check.state === "unknown")) return "unknown";
  return checks.every(check => check.state === "good") ? "good" : "warning";
}
export const HEALTH_LABELS: Record<HealthState, string> = {
  good: "All checks passed", warning: "Needs attention", failed: "Problem detected", unknown: "Unverified",
};

export function savedCheck(
  id: string, label: string, data: RecordData | null, now: number,
  evaluate: (data: RecordData) => Pick<HealthCheck, "state" | "summary" | "detail">,
): HealthCheck {
  const checkedAt = timestamp(data?.updated_at_utc ?? data?.generated_at_utc ?? data?.checked_at_utc);
  if (!data || !checkedAt) return { id, label, state: "unknown", summary: "Unverified",
    detail: "A dated report is not available. Missing results are not counted as a pass.", checkedAt };
  const result = evaluate(data);
  if (!current(checkedAt, now)) return { id, label, ...result, state: result.state === "failed" ? "failed" : "warning",
    summary: "Out of date · " + result.summary, detail: result.detail + " This saved check is over 36 hours old or its timestamp is invalid.", checkedAt };
  return { id, label, ...result, checkedAt };
}

export function clinicalHealth(data: RecordData) {
  const scans = Array.isArray(data.scans) ? data.scans.map(record).filter(x => x !== null) : [];
  const statuses = scans.map(scan => String(scan.collector_status || "").toUpperCase());
  const failed = statuses.some(state => ["FAILED", "ERROR", "FAILURE"].includes(state));
  const complete = scans.length >= 3 && statuses.every(state => state === "COMPLETE");
  return { state: (failed ? "failed" : complete ? "good" : "warning") as HealthState,
    summary: failed ? "Collector failed" : complete ? "Clinical collectors complete" : "Partial / unverified",
    detail: "Clinical collection only. FDA, SEC, financing and other source verification are checked separately." };
}
export function sourceHealth(data: RecordData) {
  const unresolved = data.required_findings_unresolved;
  const complete = data.full_coverage_verified === true && data.status === "COMPLETE" && unresolved === 0;
  const failed = ["FAILED", "ERROR"].includes(String(data.status));
  return { state: (failed ? "failed" : complete ? "good" : "warning") as HealthState,
    summary: count(unresolved) ? `${unresolved.toLocaleString("en-US")} unresolved findings` : String(data.status || "Unverified"),
    detail: "Combined source verification: " + (Array.isArray(data.missing_required_source_families)
      ? data.missing_required_source_families.filter(x => typeof x === "string").join(", ") || "No missing families reported."
      : "Required source-family coverage is unverified.") };
}
export function scoringHealth(data: RecordData) {
  const counts = record(data.counts);
  const gaps = counts?.data_gaps;
  const passed = ["PASS", "COMPLETE", "CHECKED"].includes(String(data.status)) && gaps === 0;
  return { state: (data.status === "FAILED" ? "failed" : passed ? "good" : "warning") as HealthState,
    summary: count(gaps) ? `${gaps} scoring data gaps` : String(data.status || "Unverified"),
    detail: "Saved scoring-input audit. It does not certify that all trials have fresh scores or independently verified evidence." };
}
export function emailHealth(data: RecordData) {
  const safeScope = data.scope === "PDUFA_ONLY_EXCLUDING_INBOX_TRASH_SPAM";
  const valid = safeScope && data.status === "CHECKED" && count(data.total_count) &&
    count(data.unread_count) && data.unread_count <= data.total_count;
  return { state: (valid ? "good" : "unknown") as HealthState,
    summary: valid ? `${(data.total_count as number).toLocaleString("en-US")} emails · ${(data.unread_count as number).toLocaleString("en-US")} unread` : "Count unavailable",
    detail: "PDUFA and its sublabels, deduplicated. Inbox, Trash and Spam excluded. Read-only count; no messages changed." };
}
