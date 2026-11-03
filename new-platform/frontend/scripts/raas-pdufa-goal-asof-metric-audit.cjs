#!/usr/bin/env node
"use strict";
/** Publish source-time research only. No retrospective FDA action, investment
 * score, trading signal, inferred market session or historical return.
 */
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
 esModuleInterop:true}}
).outputText,file);
const {activePdufaGoalAsOfAudit}=require("../lib/raas-pdufa-goal-asof-metric-audit.ts");
const outputPath=(env,name)=>process.env[env]||path.resolve(__dirname,"..",name);
const fields=["ticker","application","reviewYear","eventTargetDate",
 "initialGoalDate","initialGoalAnnouncementDate","initialGoalSourceUrl",
 "initialCalendarEntryT79","initialCalendarExitT14",
 "revised","revisedGoalAnnouncementDate","revisedGoalSourceUrl",
 "currentCalendarEntryT79","currentCalendarExitT14",
 "proposedConservativeEntrySession","proposedConservativeExitSession",
 "entrySessionShiftCalendarDays","exitSessionShiftCalendarDays",
 "entrySessionIsEarlyClose","exitSessionIsEarlyClose",
 "finalTargetKnownAtFinalT79Entry","sourceShiftCalendarDays",
 "currentEntryIsWeekend","currentExitIsWeekend",
 "researchMetricIds","reviewState","approvedMetricGrades"];
const row=(x)=>({
 ticker:x.ticker,application:x.application,reviewYear:x.reviewYear,
 eventTargetDate:x.eventTargetDate,initialGoalDate:x.initialGoalDate,
 initialGoalAnnouncementDate:x.initialGoalAnnouncementDate,
 initialGoalSourceUrl:x.initialGoalSourceUrl,
 initialCalendarEntryT79:x.initial.calendarEntryDate,
 initialCalendarExitT14:x.initial.calendarExitDate,
 revised:x.revised,revisedGoalAnnouncementDate:x.revisedGoalAnnouncementDate,
 revisedGoalSourceUrl:x.revisedGoalSourceUrl,
 currentCalendarEntryT79:x.current.calendarEntryDate,
 currentCalendarExitT14:x.current.calendarExitDate,
 proposedConservativeEntrySession:x.current.indicativeEntrySessionDate,
 proposedConservativeExitSession:x.current.indicativeExitSessionDate,
 entrySessionShiftCalendarDays:x.current.entrySessionShiftCalendarDays,
 exitSessionShiftCalendarDays:x.current.exitSessionShiftCalendarDays,
 entrySessionIsEarlyClose:x.current.entrySessionIsEarlyClose,
 exitSessionIsEarlyClose:x.current.exitSessionIsEarlyClose,
 finalTargetKnownAtFinalT79Entry:x.finalTargetKnownAtFinalT79Entry,
 sourceShiftCalendarDays:x.sourceShiftCalendarDays,
 currentEntryIsWeekend:x.current.entryIsWeekend,
 currentExitIsWeekend:x.current.exitIsWeekend,
 researchMetricIds:x.researchMetricSourceLeads.join(" | "),
 reviewState:x.reviewState,approvedMetricGrades:x.approvedMetricGrades
});
function csv(report){
 if(report?.scope!=="RAAS_2024_2025_PDUFA_GOAL_VERSION_ASOF_INPUT_AUDIT"||
  !Array.isArray(report.cases))throw Error("RAAS_GOAL_ASOF_EXPORT_INVALID");
 const esc=v=>{const s=String(v??"");
  const safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(s)?"'"+s:s;
  return '"'+safe.replaceAll('"','""')+'"';};
 return fields.join(",")+"\n"+report.cases.map(x=>{
  const v=row(x);return fields.map(k=>esc(v[k])).join(",");
 }).join("\n")+"\n";
}
function main(){
 try{
  const report=activePdufaGoalAsOfAudit();
  if(report.stageMetricHistoricalApprovedCases!==0||
   report.validatedHistoricalTradingCases!==0||report.approvedOverallRaasScores!==0||
   report.cases.some(x=>x.approvedMetricGrades!==0||x.approvedRaasScore!==null))
   throw Error("RAAS_GOAL_ASOF_NO_UNAPPROVED_SCORE_PROMOTION");
  const j=outputPath("RAAS_GOAL_ASOF_OUTPUT_JSON","raas-2024-2025-pdufa-goal-version-asof.json"),
   c=outputPath("RAAS_GOAL_ASOF_OUTPUT_CSV","raas-2024-2025-pdufa-goal-version-asof.csv");
  for(const f of [j,c])fs.mkdirSync(path.dirname(f),{recursive:true});
  fs.writeFileSync(j,JSON.stringify(report,null,2)+"\n");
  fs.writeFileSync(c,csv(report));
  const summary={status:report.status,cases:report.sourceCases,reviewYears:report.reviewYears,
   formalRevisedGoalCases:report.revisedGoalCases,
   finalSourceAtT79:report.finalGoalPublishedBeforeFinalEntryCases,
   originalSourceUrlMissing:report.unverifiedOriginalGoalSourceUrls,
   calendarWeekendEntries:report.calendarWeekendEntryCases,
   calendarWeekendExits:report.calendarWeekendExitCases,
   proposedSessionAdjustedEntries:report.cases.filter(x=>x.current.entrySessionShiftCalendarDays!==0).length,
   proposedSessionAdjustedExits:report.cases.filter(x=>x.current.exitSessionShiftCalendarDays!==0).length,
   independentlyApprovedMetricGrades:0,validatedTrades:0};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### PDUFA original / revised FDA target point-in-time research audit\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNot historical market-session, cap, FDA census or RAAS metric validation.\n");
 }catch(e){console.error("RAAS_GOAL_ASOF_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;}
}
if(require.main===module)main();
module.exports={csv};
