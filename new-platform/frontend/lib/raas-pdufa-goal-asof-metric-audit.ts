/** Point-in-time, source-ledger review of the exact PDUFA target versions used
 * to anchor nine provisional 2024/2025 T-79 -> T-14 study windows.
 *
 * This is a source-availability diagnostic for post-3-5 and post-6-1,
 * NOT an independently verified FDA goal, metric grade, market-cap conclusion
 * or historical trading result. Outcome labels cannot enter this feature audit.
 */
import source from "../data/raas-active-2024-2025-primary-source-leads.json";
import {RAAS_METRIC_CATALOG} from "./raas-metric-specs";
export type GoalSourceCandidate={
 caseId:string;ticker:string;application:string;drug:string;indication:string;
 nctIds:string[];pdufaTargetDate:string;targetAnnouncementDate:string;targetAnnouncementSourceUrl:string;
 phase3ReadoutDate:string;phase3ReadoutSourceUrl:string;
 originallyAnnouncedPdufaTargetDate?:string;originalTargetAnnouncementDate?:string;
 originalTargetAnnouncementSourceUrl?:string;
 fdaGoalExtensionAnnouncedDate?:string;formalGoalExtensionIndependentlyVerified?:boolean;
 originalTargetAndRevisionSourceUrl?:string;
};
export type GoalAsOfWindow={
 targetVersion:"ORIGINAL_PUBLIC_GOAL"|"REVISED_PUBLIC_GOAL";
 calendarEntryDate:string;calendarExitDate:string;
 /** Exchange-schedule candidates only: never broker-verified trades. */
 indicativeEntrySessionDate:string;indicativeExitSessionDate:string;
 entrySessionShiftCalendarDays:number;exitSessionShiftCalendarDays:number;
 entrySessionIsEarlyClose:boolean;exitSessionIsEarlyClose:boolean;
 entryIsWeekend:boolean;exitIsWeekend:boolean;
 targetWasPublishedByCalendarEntry:boolean;phase3ReadoutListedBeforeEntry:boolean;
 goalSourceUrl:string;
};
export type GoalAsOfCase={
 caseId:string;ticker:string;application:string;reviewYear:2024|2025;
 candidateEvidenceState:"PDUFA_SOURCE_PRESENT_NOT_INDEPENDENTLY_VALIDATED";
 eventTargetDate:string;revised:boolean;
 initialGoalDate:string;initialGoalAnnouncementDate:string;
 initialGoalSourceUrl:string|null;
 phase3ReadoutListedDate:string;phase3ReadoutSourceUrl:string;
 initialGoalIndependentOriginalSource:"URL_RECORDED"|"ORIGINAL_SOURCE_URL_MISSING";
 revisedGoalSourceUrl:string|null;revisedGoalAnnouncementDate:string|null;
 sourceShiftCalendarDays:number;
 initial:GoalAsOfWindow;current:GoalAsOfWindow;
 finalTargetKnownAtFinalT79Entry:boolean;
 researchMetricSourceLeads:readonly ["post-3-5","post-6-1"];
 marketSessionCalendarVerified:false;historicalEntryCapitalizationVerified:false;
 clinicalReadoutPublicationIndependentlyAudited:false;
 approvedMetricGrades:0;approvedRaasScore:null;
 reviewState:"POINT_IN_TIME_SOURCE_LEAD_ONLY"|"BLOCKED_REVISED_GOAL_NOT_PUBLIC_AT_T79"|
 "BLOCKED_FINAL_GOAL_OR_PHASE3_NOT_PUBLIC_BY_T79";
};
export type GoalAsOfAudit={
 schemaVersion:1;scope:"RAAS_2024_2025_PDUFA_GOAL_VERSION_ASOF_INPUT_AUDIT";
 sourceAsOf:string;status:"RESEARCH_ONLY_NO_APPROVED_METRIC_SCORES";
 assessedMetrics:readonly ["post-3-5","post-6-1","post-6-2"];
 sourceCases:number;reviewYears:{2024:number;2025:number};
 revisedGoalCases:number;unverifiedOriginalGoalSourceUrls:number;
 finalGoalPublishedBeforeFinalEntryCases:number;
 calendarWeekendEntryCases:number;calendarWeekendExitCases:number;
 stageMetricHistoricalApprovedCases:0;validatedHistoricalTradingCases:0;
 approvedOverallRaasScores:0;
 cases:GoalAsOfCase[];
 warnings:readonly string[];
};
const dateOK=(d:unknown):d is string=>typeof d==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&
 !Number.isNaN(Date.parse(d+"T00:00:00Z"))&&new Date(d+"T00:00:00Z").toISOString().slice(0,10)===d;
const urlOK=(s:unknown):s is string=>typeof s==="string"&&/^https:\/\/[^\s/@:?#]+\/\S+$/.test(s)&&!s.includes("@");
const shift=(d:string,n:number)=>new Date(Date.parse(d+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
const daysBetween=(a:string,b:string)=>(Date.parse(b+"T00:00:00Z")-Date.parse(a+"T00:00:00Z"))/86400000;
const isWeekend=(d:string)=>[0,6].includes(new Date(d+"T00:00:00Z").getUTCDay());
/** Dated Nasdaq regular-session closures for the supported 2023–2025 audit
 * range. Official exchange references:
 * https://www.nasdaqtrader.com/Trader.aspx?id=Calendar
 * https://www.nasdaq.com/press-release/nyse-group-announces-2024-2025-and-2026-holiday-and-early-closings-calendar-2023-11
 * https://classic.nasdaqtrader.com/TraderNews.aspx?id=ETA2025-1
 * 2025-01-09 is the exceptional Jimmy Carter national day of mourning.
 * This calendar does NOT verify a specific security's price bar, trading
 * status, adjusted return, execution, or historical market capitalization.
 */
const usEquityFullClosureDates=new Set([
 "2023-12-25",
 "2024-01-01","2024-01-15","2024-02-19","2024-03-29","2024-05-27",
 "2024-06-19","2024-07-04","2024-09-02","2024-11-28","2024-12-25",
 "2025-01-01","2025-01-09","2025-01-20","2025-02-17","2025-04-18",
 "2025-05-26","2025-06-19","2025-07-04","2025-09-01","2025-11-27","2025-12-25"
]);
const usEquityEarlyCloses=new Set([
 "2024-07-03","2024-11-29","2024-12-24",
 "2025-07-03","2025-11-28","2025-12-24"
]);
export function indicativeNasdaqRegularSession(d:string,direction:"entry"|"exit"):string{
 if(!dateOK(d)||d<"2023-12-01"||d>"2025-12-31"||
  (direction!=="entry"&&direction!=="exit"))
  throw Error("RAAS_GOAL_ASOF_SESSION_CALENDAR_UNSUPPORTED");
 for(let n=0;n<10;n++){
  const candidate=shift(d,n*(direction==="entry"?1:-1));
  if(candidate<"2023-12-01"||candidate>"2025-12-31")
   throw Error("RAAS_GOAL_ASOF_SESSION_CALENDAR_UNSUPPORTED");
  if(!isWeekend(candidate)&&!usEquityFullClosureDates.has(candidate))return candidate;
 }
 throw Error("RAAS_GOAL_ASOF_SESSION_CALENDAR_UNRESOLVED");
}
const cap=(s:string)=>s.trim().toUpperCase();
function windowFor(goal:string,announced:string,url:string,readoutDate:string,
 version:GoalAsOfWindow["targetVersion"]):GoalAsOfWindow{
 const entry=shift(goal,-79),exit=shift(goal,-14);
 const entrySession=indicativeNasdaqRegularSession(entry,"entry");
 const exitSession=indicativeNasdaqRegularSession(exit,"exit");
 if(entrySession>=exitSession)throw Error("RAAS_GOAL_ASOF_PROPOSED_WINDOW_INVALID");
 return {targetVersion:version,calendarEntryDate:entry,calendarExitDate:exit,
  indicativeEntrySessionDate:entrySession,indicativeExitSessionDate:exitSession,
  entrySessionShiftCalendarDays:daysBetween(entry,entrySession),
  exitSessionShiftCalendarDays:daysBetween(exit,exitSession),
  entrySessionIsEarlyClose:usEquityEarlyCloses.has(entrySession),
  exitSessionIsEarlyClose:usEquityEarlyCloses.has(exitSession),
  entryIsWeekend:isWeekend(entry),exitIsWeekend:isWeekend(exit),
  targetWasPublishedByCalendarEntry:announced<=entry,
  phase3ReadoutListedBeforeEntry:readoutDate<=entry,goalSourceUrl:url};
}
export function auditGoalVersionSource(input:unknown):GoalAsOfAudit{
 if(!input||typeof input!=="object"||Array.isArray(input))
  throw Error("RAAS_GOAL_ASOF_SOURCE_INVALID");
 const d=input as {schemaVersion?:unknown;scope?:unknown;sourceAsOf?:unknown;records?:unknown};
 if(d.schemaVersion!==1||d.scope!=="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH"||
  !dateOK(d.sourceAsOf)||!Array.isArray(d.records)||d.records.length===0||d.records.length>1000)
  throw Error("RAAS_GOAL_ASOF_SOURCE_SCOPE_INVALID");
 const seen=new Set<string>(),rows:GoalAsOfCase[]=[];
 const activeMetricIds=new Set(RAAS_METRIC_CATALOG.post.flatMap(g=>g.metrics.map(m=>m.id)));
 if(["post-3-5","post-6-1","post-6-2"].some(id=>!activeMetricIds.has(id)))
  throw Error("RAAS_GOAL_ASOF_CATALOG_MISSING");
 for(const raw of d.records){
  const x=raw as GoalSourceCandidate;
  if(!x||typeof x.caseId!=="string"||!x.caseId||seen.has(x.caseId)||
   !/^[A-Z0-9.\-]{1,12}$/.test(x.ticker||"")||
   !x.application?.trim()||!x.drug?.trim()||!x.indication?.trim()||
   !Array.isArray(x.nctIds)||x.nctIds.length===0||
   x.nctIds.some(z=>!/^NCT\d{8}$/.test(z))||
   new Set(x.nctIds).size!==x.nctIds.length||
   !dateOK(x.pdufaTargetDate)||!/^202[45]-/.test(x.pdufaTargetDate)||
   !dateOK(x.targetAnnouncementDate)||x.targetAnnouncementDate>d.sourceAsOf||
   !urlOK(x.targetAnnouncementSourceUrl)||
   !dateOK(x.phase3ReadoutDate)||x.phase3ReadoutDate>d.sourceAsOf||
   !urlOK(x.phase3ReadoutSourceUrl))
   throw Error("RAAS_GOAL_ASOF_CASE_INVALID");
  seen.add(x.caseId);
  const revised=x.originallyAnnouncedPdufaTargetDate!==undefined;
  if(revised){
   if(!dateOK(x.originallyAnnouncedPdufaTargetDate)||
    !dateOK(x.originalTargetAnnouncementDate)||
    !dateOK(x.fdaGoalExtensionAnnouncedDate)||
    x.fdaGoalExtensionAnnouncedDate!==x.targetAnnouncementDate||
    x.pdufaTargetDate<=x.originallyAnnouncedPdufaTargetDate||
    x.originalTargetAnnouncementDate>=x.targetAnnouncementDate||
    x.originalTargetAnnouncementDate>x.originallyAnnouncedPdufaTargetDate||
    x.formalGoalExtensionIndependentlyVerified!==true||
    (x.originalTargetAnnouncementSourceUrl!==undefined&&!urlOK(x.originalTargetAnnouncementSourceUrl))||
    (x.originalTargetAndRevisionSourceUrl!==undefined&&!urlOK(x.originalTargetAndRevisionSourceUrl)))
    throw Error("RAAS_GOAL_ASOF_REVISION_CHAIN_INVALID");
  }else if(x.originalTargetAnnouncementDate!==undefined||
   x.fdaGoalExtensionAnnouncedDate!==undefined||
   x.originalTargetAnnouncementSourceUrl!==undefined)
    throw Error("RAAS_GOAL_ASOF_UNPAIRED_REVISION_INVALID");
  const initialGoal=revised?x.originallyAnnouncedPdufaTargetDate!:x.pdufaTargetDate;
  const firstPublic=revised?x.originalTargetAnnouncementDate!:x.targetAnnouncementDate;
  const initialSource=revised?(x.originalTargetAnnouncementSourceUrl??null):x.targetAnnouncementSourceUrl;
  const initial=windowFor(initialGoal,firstPublic,initialSource??"",x.phase3ReadoutDate,"ORIGINAL_PUBLIC_GOAL");
  const current=windowFor(x.pdufaTargetDate,x.targetAnnouncementDate,x.targetAnnouncementSourceUrl,
   x.phase3ReadoutDate,revised?"REVISED_PUBLIC_GOAL":"ORIGINAL_PUBLIC_GOAL");
  const firstKnown=initial.targetWasPublishedByCalendarEntry&&initial.phase3ReadoutListedBeforeEntry;
  const finalKnown=current.targetWasPublishedByCalendarEntry&&current.phase3ReadoutListedBeforeEntry;
  const state:GoalAsOfCase["reviewState"]=revised&&!current.targetWasPublishedByCalendarEntry?
   "BLOCKED_REVISED_GOAL_NOT_PUBLIC_AT_T79":
   !finalKnown?"BLOCKED_FINAL_GOAL_OR_PHASE3_NOT_PUBLIC_BY_T79":
   "POINT_IN_TIME_SOURCE_LEAD_ONLY";
  rows.push({
   caseId:x.caseId,ticker:cap(x.ticker),application:x.application,
   reviewYear:Number(x.pdufaTargetDate.slice(0,4)) as 2024|2025,
   candidateEvidenceState:"PDUFA_SOURCE_PRESENT_NOT_INDEPENDENTLY_VALIDATED",
   eventTargetDate:x.pdufaTargetDate,revised,
   initialGoalDate:initialGoal,initialGoalAnnouncementDate:firstPublic,
   initialGoalSourceUrl:initialSource,
   phase3ReadoutListedDate:x.phase3ReadoutDate,
   phase3ReadoutSourceUrl:x.phase3ReadoutSourceUrl,
   initialGoalIndependentOriginalSource:initialSource?"URL_RECORDED":"ORIGINAL_SOURCE_URL_MISSING",
   revisedGoalSourceUrl:revised?x.targetAnnouncementSourceUrl:null,
   revisedGoalAnnouncementDate:revised?x.targetAnnouncementDate:null,
   sourceShiftCalendarDays:daysBetween(initialGoal,x.pdufaTargetDate),
   initial,current,finalTargetKnownAtFinalT79Entry:finalKnown,
   researchMetricSourceLeads:["post-3-5","post-6-1"],
   marketSessionCalendarVerified:false,
   historicalEntryCapitalizationVerified:false,
   clinicalReadoutPublicationIndependentlyAudited:false,
   approvedMetricGrades:0,approvedRaasScore:null,reviewState:state
  });
  // Original target research windows are displayed for comparison, but they
  // cannot be promoted when an original announcement lacks a separate URL.
  if(!firstKnown&&initialGoal<current.calendarEntryDate&&
   x.pdufaTargetDate===initialGoal)
   throw Error("RAAS_GOAL_ASOF_ORIGINAL_TIMING_INVALID");
 }
 if(new Set(rows.map(r=>r.ticker+"|"+r.application)).size!==rows.length)
  throw Error("RAAS_GOAL_ASOF_DUPLICATE_APPLICATION");
 const year2024=rows.filter(r=>r.reviewYear===2024).length;
 const year2025=rows.filter(r=>r.reviewYear===2025).length;
 return {schemaVersion:1,scope:"RAAS_2024_2025_PDUFA_GOAL_VERSION_ASOF_INPUT_AUDIT",
  sourceAsOf:d.sourceAsOf,status:"RESEARCH_ONLY_NO_APPROVED_METRIC_SCORES",
  assessedMetrics:["post-3-5","post-6-1","post-6-2"],
  sourceCases:rows.length,reviewYears:{2024:year2024,2025:year2025},
  revisedGoalCases:rows.filter(r=>r.revised).length,
  unverifiedOriginalGoalSourceUrls:rows.filter(r=>r.initialGoalSourceUrl===null).length,
  finalGoalPublishedBeforeFinalEntryCases:rows.filter(r=>r.finalTargetKnownAtFinalT79Entry).length,
  calendarWeekendEntryCases:rows.filter(r=>r.current.entryIsWeekend).length,
  calendarWeekendExitCases:rows.filter(r=>r.current.exitIsWeekend).length,
  stageMetricHistoricalApprovedCases:0,validatedHistoricalTradingCases:0,
  approvedOverallRaasScores:0,cases:rows,
  warnings:[
   "PDUFA source-link presence at T-79 is not independent verification of FDA acceptance, all revisions or an actionable entry.",
   "FDA outcomes and decisions are deliberately excluded from this pre-entry metric feature audit; retrospective information must never backfill a score.",
   "The initial PDUFA goal and later revised goal create different T-79/T-14 windows. The revised window is only source-eligible when the revision was already publicly announced at its own entry.",
   "Calendar T-79/T-14 marks may fall on weekends or holidays; proposed next-entry/prior-exit regular-session dates use a dated Nasdaq closure schedule and are not verified executable prices, bars or trades.",
   "Early-close trading sessions and unscheduled closures must be checked against broker bars independently; January 9, 2025 is excluded as an exchange closure, not a valid trade date.",
   "Original-goal URLs are retained for all nine selected historical examples, but link presence is not independent evidence validation, complete FDA census coverage or approved RAAS grading.",
   "Even two FDA target and timing metric source candidates do not establish a risk score: statistical holdout, FDA census, adjusted-price checks, capitalization and source completeness remain blocked.",
   "Historical approval counts and RAAS calibrated metric grades remain zero."
  ]};
}
export const activePdufaGoalAsOfAudit=()=>auditGoalVersionSource(source);
