/** Read-only, fail-closed reconciliation of GOAL's daily scan preview.
 * Never turn a partial source run, another day's record, or a null count into
 * a current-day new trial, FDA designation, or qualified GEM admission.
 */
import type { NewFromScanSummary, NewFromScanRow } from "./scan-new-results";

type Obj = Record<string, unknown>;
const object = (v: unknown): v is Obj => v !== null && typeof v === "object" && !Array.isArray(v);
const count = (v: unknown): number | null =>
  typeof v === "number" && Number.isSafeInteger(v) && v >= 0 ? v : null;
const day = (v: unknown): v is string => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)
  && Number.isFinite(Date.parse(v + "T12:00:00Z"))
  && new Date(v + "T12:00:00Z").toISOString().slice(0, 10) === v;
const trustedRun = (id: number | null, url: unknown): string | null =>
  id !== null && typeof url === "string" &&
  url === "https://github.com/pdufa/pdufa-command-center/actions/runs/" + id ? url : null;
const validClinicalLink = (url: unknown, nct: unknown) =>
  typeof nct === "string" && /^NCT\d{8}$/.test(nct) &&
  url === "https://clinicaltrials.gov/study/" + nct ? url as string : null;

export function pacificGoalDay(now: Date): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now);
  const field = (name: string) => parts.find(item => item.type === name)?.value || "";
  return [field("year"), field("month"), field("day")].join("-");
}
export type GoalScanRow = {
  kind: "NEW_PROGRAM" | "NEW_PHASE3_RESULT" | "NEW_STAGE_MEMBER";
  stage: "PIPELINE" | "GEM JR" | "GEM";
  ticker: string | null;
  drug: string | null;
  trialId: string | null;
  label: string;
  link: string | null;
  exactRun: boolean;
};
export type GoalScanView = {
  date: string;
  today: boolean;
  status: "COMPLETE" | "PARTIAL" | "RUN_FAILED";
  runId: number;
  runUrl: string;
  masterNew: number | null;
  masterUpdated: number | null;
  designationTotal: number | null;
  newPrograms: number | null;
  changedPrograms: number | null;
  rows: GoalScanRow[];
  note: string;
};

export function goalScanView(data: unknown, now = new Date()): GoalScanView | null {
  if (!object(data) || !object(data.daily) || data.daily.schema_version !== 1 ||
      !Array.isArray(data.daily.days) || data.daily.days.length > 400) return null;
  const dailyRows = data.daily.days.filter(object).filter(x => day(x.date_pacific))
    .sort((a,b) => String(b.date_pacific).localeCompare(String(a.date_pacific)));
  const today = pacificGoalDay(now);
  const recorded = dailyRows.find(x => x.date_pacific === today) || dailyRows.find(x => x.date_pacific <= today);
  if (!recorded || !["COMPLETE","PARTIAL","RUN_FAILED"].includes(String(recorded.status))) return null;
  const runId = count(recorded.run_id);
  const runUrl = trustedRun(runId, recorded.run_url);
  if (runId === null || runId === 0 || !runUrl || !object(recorded.sections)) return null;
  const master = object(recorded.sections.master) ? recorded.sections.master : null;
  const designations = object(recorded.sections.designations) ? recorded.sections.designations : null;
  const masterNew = count(master?.new), masterUpdated = count(master?.updated);
  const designationTotal = count(designations?.total);
  const source = object(data.newFromScan) ? data.newFromScan : null;
  const sameRun = source && count(source.runId) === runId && source.scanPacificDate === recorded.date_pacific;
  const sourceUpdates = sameRun ? count(source.pipelineChangedTrials) : null;
  const contradictoryUpdates = sourceUpdates !== null && masterUpdated !== null && sourceUpdates !== masterUpdated;
  const rows: GoalScanRow[] = [];
  if (sameRun && !contradictoryUpdates && Array.isArray(source.rows) && source.rows.length <= 100) {
    const seen = new Set<string>();
    for (const candidate of source.rows) {
      if (!object(candidate) ||
          !["PIPELINE","GEM JR","GEM"].includes(String(candidate.stage)) ||
          !["NEW_PROGRAM","NEW_PHASE3_RESULT","NEW_STAGE_MEMBER"].includes(String(candidate.kind)) ||
          typeof candidate.label !== "string" || candidate.label.length > 300 ||
          typeof candidate.exactRun !== "boolean" ||
          (candidate.ticker != null && (typeof candidate.ticker !== "string" ||
            !/^[A-Z][A-Z0-9.-]{0,12}$/.test(candidate.ticker))) ||
          (candidate.drug != null && (typeof candidate.drug !== "string" || candidate.drug.length > 200)) ||
          (candidate.trialId != null && (typeof candidate.trialId !== "string" ||
            !/^NCT\d{8}$/.test(candidate.trialId)))) continue;
      const kind = candidate.kind as GoalScanRow["kind"];
      const stage = candidate.stage as GoalScanRow["stage"];
      const key = stage + "|" + kind + "|" + candidate.trialId + "|" + candidate.ticker;
      if (seen.has(key)) continue;
      seen.add(key);
      rows.push({
        kind, stage,
        ticker: candidate.ticker as string | null,
        drug: candidate.drug as string | null,
        trialId: candidate.trialId as string | null,
        label: candidate.label,
        link: validClinicalLink(candidate.sourceUrl, candidate.trialId),
        exactRun: candidate.exactRun,
      });
    }
  }
  const verifiedNewPrograms = sameRun && !contradictoryUpdates ? count(source?.pipelineNewPrograms) : null;
  return {
    date: recorded.date_pacific as string, today: recorded.date_pacific === today,
    status: recorded.status as GoalScanView["status"], runId, runUrl,
    masterNew: recorded.status === "RUN_FAILED" ? null : masterNew,
    masterUpdated: recorded.status === "RUN_FAILED" ? null : masterUpdated,
    designationTotal: recorded.status === "RUN_FAILED" ? null : designationTotal,
    newPrograms: recorded.status === "RUN_FAILED" ? null : verifiedNewPrograms,
    changedPrograms: recorded.status === "RUN_FAILED" ? null :
      contradictoryUpdates ? null : sourceUpdates,
    rows: recorded.status === "RUN_FAILED" ? [] : rows.slice(0,20),
    note: contradictoryUpdates
      ? "The nightly source report and daily ledger disagree on updated trials; per-run detail is withheld."
      : recorded.status === "PARTIAL"
      ? "Partial published evidence. A completed collector is not a complete FDA/SEC or Pipeline verification."
      : recorded.status === "RUN_FAILED"
      ? "The registered nightly run failed; numbers are not treated as verified scan results."
      : "Published dated scan counts. Individual clinical/FDA/financing evidence still needs verification.",
  };
}
