/** Read-only CSV exports from a confirmed, source-validated GOAL calculation.
 * No APIs, credentials or speculative score fields are included.
 */
import type { GoalImpactReport, GoalExcludedProgram } from "./goal-restriction-impact";
import type { GoalRestrictionStage } from "./goal-restrictions";

function safeCell(value: string | number | null | undefined) {
  let text = String(value ?? "").replace(/\u0000/g, "").replace(/\r?\n/g, " ").trim();
  // Avoid spreadsheet formula execution when downloaded records are opened.
  if (/^[\s]*[=+\-@\t]/.test(text) || /^[\s]*[\uFF1D\uFF0B\uFF0D\uFF20]/u.test(text)) text = "'" + text;
  return '"' + text.replace(/"/g,'""') + '"';
}
function csv(rows: (string | number | null | undefined)[][]) {
  return "\uFEFF" + rows.map(row=>row.map(safeCell).join(",")).join("\r\n") + "\r\n";
}
const stageNames:GoalRestrictionStage[]=["PIPELINE","GEM_JR","GEM"];
export function impactSummaryCsv(report:GoalImpactReport):string {
  const data:(string | number | null | undefined)[][] = [[
    "Stage","Rule","Saved rule ID","Baseline before","Newly excluded","Remaining after",
    "Pending evidence after","Unknown when tested alone","Saved source as of","Restriction evidence as of",
    "Report type",
  ]];
  for(const stage of stageNames) {
    const part=report.stages[stage];
    for(const step of part.steps) data.push([
      stage,step.title,step.id,step.before,step.excluded,step.after,
      step.pending,step.unknownAlone,report.asOf,report.evidenceFetchedAt,
      "READ_ONLY_SAVED_SCREENING",
    ]);
  }
  return csv(data);
}
export function impactProgramCsv(
  report:GoalImpactReport, stage:GoalRestrictionStage, ruleId:string,
  kind:"EXCLUDED"|"PENDING",
):string{
  const rule=report.stages[stage].steps.find(s=>s.id===ruleId);
  if(!rule) throw new Error("Source restriction step is not in the calculated report");
  const found:GoalExcludedProgram[]=kind==="EXCLUDED" ? rule.excludedPrograms : rule.pendingPrograms;
  if(found.length !== (kind==="EXCLUDED"?rule.excluded:rule.pending))
    throw new Error("Source program identity count does not match summary");
  return csv([
    ["Stage","Saved rule ID","Rule","Evidence status","Ticker","Permanent Program ID",
      "Saved row ID","NCT","Drug","Indication","Saved source as of","Restriction evidence as of"],
    ...found.map(p=>[stage,rule.id,rule.title,kind,p.ticker,p.programId,p.id,p.nctId,
      p.drug,p.indication,report.asOf,report.evidenceFetchedAt]),
  ]);
}
