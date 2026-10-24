/** Date-scoped GOAL scan history from the original published daily ledger.
 * This module never recomputes counts from unrelated source snapshots.
 * Partial and failed data cannot become a verified zero.
 */
import { pacificGoalDay } from "./goal-scan-evidence";

type Obj = Record<string, unknown>;
const obj = (value: unknown): value is Obj =>
  value !== null && typeof value === "object" && !Array.isArray(value);
const amount = (value: unknown): number | null =>
  typeof value === "number" && Number.isSafeInteger(value) && value >= 0 ? value : null;
const validDay = (value: unknown): value is string => {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(value + "T12:00:00Z");
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0,10) === value;
};

export type GoalDaySection = { total: number | null; new: number | null; updated: number | null };
export type GoalDailyHistoryRow = {
  date: string;
  today: boolean;
  status: "COMPLETE" | "PARTIAL" | "RUN_FAILED";
  runId: number;
  runUrl: string;
  master: GoalDaySection;
  pipeline: GoalDaySection;
  gemJr: GoalDaySection;
  gem: GoalDaySection;
  designations: GoalDaySection;
};
function section(raw: unknown, failed: boolean): GoalDaySection {
  if (!obj(raw) || failed) return {total:null,new:null,updated:null};
  return {total:amount(raw.total),new:amount(raw.new),updated:amount(raw.updated)};
}
export function goalDailyHistory(
  daily: unknown, now = new Date(), limit = 14,
): GoalDailyHistoryRow[] {
  if (!obj(daily) || daily.schema_version !== 1 ||
      !Array.isArray(daily.days) || daily.days.length > 400 ||
      !Number.isSafeInteger(limit) || limit < 1 || limit > 400) return [];
  const today = pacificGoalDay(now);
  const groups = new Map<string, unknown[]>();
  for (const candidate of daily.days) {
    if (!obj(candidate) || !validDay(candidate.date_pacific) ||
        candidate.date_pacific > today) continue;
    groups.set(candidate.date_pacific, [...(groups.get(candidate.date_pacific) || []),candidate]);
  }
  const rows: GoalDailyHistoryRow[] = [];
  for (const [date, duplicates] of groups) {
    // Conflicting same-day publications must be reconciled upstream, not arbitrarily selected.
    if (duplicates.length !== 1 || !obj(duplicates[0])) continue;
    const day = duplicates[0];
    const runId = amount(day.run_id);
    const url = "https://github.com/pdufa/pdufa-command-center/actions/runs/" + runId;
    if (!runId || day.run_url !== url ||
        !["COMPLETE","PARTIAL","RUN_FAILED"].includes(String(day.status)) ||
        !obj(day.sections)) continue;
    const failed = day.status === "RUN_FAILED";
    rows.push({
      date, today:date === today, status:day.status as GoalDailyHistoryRow["status"],
      runId, runUrl:url,
      master:section(day.sections.master, failed),
      pipeline:section(day.sections.pipeline, failed),
      gemJr:section(day.sections.gem_jr, failed),
      gem:section(day.sections.gem, failed),
      designations:section(day.sections.designations, failed),
    });
  }
  return rows.sort((a,b)=>b.date.localeCompare(a.date)).slice(0,limit);
}
