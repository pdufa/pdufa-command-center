"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}
).outputText,file);
const primary=require("../data/raas-active-2024-2025-primary-source-leads.json");
const {activePdufaGoalAsOfAudit,auditGoalVersionSource,indicativeNasdaqRegularSession}=
 require("../lib/raas-pdufa-goal-asof-metric-audit.ts");
const clone=()=>structuredClone(primary);
test("All nine 2024/25 research sources have dated T-79 target inputs; none have a validated RAAS score",()=>{
 const r=activePdufaGoalAsOfAudit();
 assert.equal(r.scope,"RAAS_2024_2025_PDUFA_GOAL_VERSION_ASOF_INPUT_AUDIT");
 assert.equal(r.sourceCases,9);
 assert.deepEqual(r.reviewYears,{2024:5,2025:4});
 assert.equal(r.revisedGoalCases,2);
 assert.equal(r.unverifiedOriginalGoalSourceUrls,0);
 assert.equal(r.finalGoalPublishedBeforeFinalEntryCases,9);
 assert.equal(r.calendarWeekendEntryCases,1);
 assert.equal(r.calendarWeekendExitCases,2);
 assert.equal(r.stageMetricHistoricalApprovedCases,0);
 assert.equal(r.validatedHistoricalTradingCases,0);
 assert.equal(r.approvedOverallRaasScores,0);
 assert.deepEqual(r.assessedMetrics,["post-3-5","post-6-1","post-6-2"]);
 for(const x of r.cases){
  assert.equal(x.approvedMetricGrades,0);
  assert.equal(x.approvedRaasScore,null);
  assert.equal(x.marketSessionCalendarVerified,false);
  assert.equal(x.historicalEntryCapitalizationVerified,false);
  assert.equal(x.clinicalReadoutPublicationIndependentlyAudited,false);
  assert.equal(x.reviewState,"POINT_IN_TIME_SOURCE_LEAD_ONLY");
  assert.ok(x.current.calendarEntryDate<x.current.calendarExitDate);
  assert.ok(x.current.calendarExitDate<x.eventTargetDate);
 }
});
test("Conservative session proposals respect Nasdaq weekends, full holidays, exceptional closures and early closes",()=>{
 assert.equal(indicativeNasdaqRegularSession("2025-01-09","entry"),"2025-01-10");
 assert.equal(indicativeNasdaqRegularSession("2025-01-09","exit"),"2025-01-08");
 assert.equal(indicativeNasdaqRegularSession("2024-03-29","entry"),"2024-04-01");
 assert.equal(indicativeNasdaqRegularSession("2024-03-29","exit"),"2024-03-28");
 assert.equal(indicativeNasdaqRegularSession("2024-12-25","entry"),"2024-12-26");
 assert.equal(indicativeNasdaqRegularSession("2024-12-25","exit"),"2024-12-24");
 assert.equal(indicativeNasdaqRegularSession("2024-06-16","entry"),"2024-06-17");
 assert.equal(indicativeNasdaqRegularSession("2024-06-16","exit"),"2024-06-14");
 assert.throws(()=>indicativeNasdaqRegularSession("2026-01-01","entry"),/UNSUPPORTED/);
 const r=activePdufaGoalAsOfAudit();
 assert.equal(r.cases.length,9);
 for(const x of r.cases){
  for(const w of [x.initial,x.current]){
   assert.ok(w.indicativeEntrySessionDate>=w.calendarEntryDate);
   assert.ok(w.indicativeExitSessionDate<=w.calendarExitDate);
   assert.ok(w.indicativeEntrySessionDate<w.indicativeExitSessionDate);
   assert.ok(Number.isInteger(w.entrySessionShiftCalendarDays)&&w.entrySessionShiftCalendarDays>=0);
   assert.ok(Number.isInteger(w.exitSessionShiftCalendarDays)&&w.exitSessionShiftCalendarDays<=0);
  }
  assert.equal(x.marketSessionCalendarVerified,false);
  assert.equal(x.approvedRaasScore,null);
 }
});
test("Revised goal is NOT applied retroactively to the original T-79 calendar window",()=>{
 const r=activePdufaGoalAsOfAudit();
 const slno=r.cases.find(x=>x.ticker==="SLNO");
 assert.equal(slno.revised,true);
 assert.equal(slno.initialGoalDate,"2024-12-27");
 assert.equal(slno.eventTargetDate,"2025-03-27");
 assert.equal(slno.initialGoalAnnouncementDate,"2024-08-27");
 assert.equal(slno.revisedGoalAnnouncementDate,"2024-11-26");
 assert.equal(slno.initial.calendarEntryDate,"2024-10-09");
 assert.equal(slno.current.calendarEntryDate,"2025-01-07");
 assert.equal(slno.sourceShiftCalendarDays,90);
 assert.equal(slno.initialGoalSourceUrl,
  "https://investors.soleno.life/news-releases/news-release-details/soleno-therapeutics-announces-us-fda-acceptance-filing-and");
 assert.equal(slno.initial.targetWasPublishedByCalendarEntry,true);
 assert.equal(slno.current.targetWasPublishedByCalendarEntry,true);
 assert.equal(slno.initial.indicativeEntrySessionDate,"2024-10-09");
 assert.equal(slno.initialGoalIndependentOriginalSource,"URL_RECORDED");
 const cytk=r.cases.find(x=>x.ticker==="CYTK");
 assert.equal(cytk.initialGoalDate,"2025-09-26");
 assert.equal(cytk.eventTargetDate,"2025-12-26");
 assert.equal(cytk.initial.calendarEntryDate,"2025-07-09");
 assert.equal(cytk.current.calendarEntryDate,"2025-10-08");
 assert.equal(cytk.initialGoalAnnouncementDate,"2024-12-02");
 assert.equal(cytk.revisedGoalAnnouncementDate,"2025-05-01");
 assert.equal(cytk.sourceShiftCalendarDays,91);
 assert.ok(cytk.initialGoalSourceUrl?.startsWith("https://"));
});
test("A late FDA goal amendment is source-blocked, not marked as an eligible historical entry signal",()=>{
 const d=clone(),x=d.records.find(x=>x.ticker==="CYTK");
 x.targetAnnouncementDate="2025-11-01";
 x.fdaGoalExtensionAnnouncedDate="2025-11-01";
 const r=auditGoalVersionSource(d),c=r.cases.find(x=>x.ticker==="CYTK");
 assert.equal(c.current.targetWasPublishedByCalendarEntry,false);
 assert.equal(c.finalTargetKnownAtFinalT79Entry,false);
 assert.equal(c.reviewState,"BLOCKED_REVISED_GOAL_NOT_PUBLIC_AT_T79");
 assert.equal(c.approvedMetricGrades,0);
});
test("Later as-of FDA disclosures or a Phase3 result occurring after entry cannot become valid pre-entry inputs",()=>{
 const late=clone();late.records.find(x=>x.ticker==="ARQT").targetAnnouncementDate="2024-05-01";
 const result=auditGoalVersionSource(late);
 assert.equal(result.cases.find(x=>x.ticker==="ARQT").reviewState,"BLOCKED_FINAL_GOAL_OR_PHASE3_NOT_PUBLIC_BY_T79");
 const clinical=clone();clinical.records.find(x=>x.ticker==="ARQT").phase3ReadoutDate="2024-05-10";
 const r=auditGoalVersionSource(clinical),a=r.cases.find(x=>x.ticker==="ARQT");
 assert.equal(a.current.phase3ReadoutListedBeforeEntry,false);
 assert.equal(a.reviewState,"BLOCKED_FINAL_GOAL_OR_PHASE3_NOT_PUBLIC_BY_T79");
});
test("Outcome labels and retrospective decision dates never appear in pre-entry candidate output",()=>{
 const r=auditGoalVersionSource(clone());
 const text=JSON.stringify(r);
 assert.ok(!text.includes("actualFDAOutcome"));
 assert.ok(!text.includes("actualFDAActionDate"));
 assert.ok(!text.includes('"APPROVED"'));
 assert.ok(!text.includes('"CRL"'));
 for(const x of r.cases)assert.deepEqual(x.researchMetricSourceLeads,["post-3-5","post-6-1"]);
});
test("Reject duplicate review cases, bad sources, forged revision chain and wrong dataset scope",()=>{
 const modify=[
  d=>{d.scope="NOT_AN_ACTIVE_LEDGER"},
  d=>{d.records[1].caseId=d.records[0].caseId},
  d=>{d.records[0].targetAnnouncementSourceUrl="https://user@example.invalid/hack"},
  d=>{d.records[0].nctIds.push(d.records[0].nctIds[0])},
  d=>{d.records.find(x=>x.ticker==="CYTK").formalGoalExtensionIndependentlyVerified=false},
  d=>{d.records.find(x=>x.ticker==="CYTK").originallyAnnouncedPdufaTargetDate="2026-12-26"},
  d=>{d.records.find(x=>x.ticker==="SLNO").fdaGoalExtensionAnnouncedDate="2024-11-25"}
 ];
 for(const fn of modify){
  const d=clone();fn(d);
  assert.throws(()=>auditGoalVersionSource(d),/RAAS_GOAL_ASOF_/);
 }
});
test("The 60-metric worklist exposes historical target source audit, not a fabricated post-6-2 score",()=>{
 const root=path.join(__dirname,"..");
 const p=fs.readFileSync(path.join(root,"app/raas-worklist/page.tsx"),"utf8");
 assert.match(p,/GoalAsOfHistory/);
 assert.match(p,/raas-pdufa-asof-history/);
 assert.match(p,/data-raas-goal-asof-case/);
 assert.match(p,/sourceShiftCalendarDays/);
 assert.match(p,/indicativeEntrySessionDate/);
 assert.match(p,/indicativeExitSessionDate/);
 assert.match(p,/ETA2025-1/);
 assert.match(p,/post-3-5/);
 assert.match(p,/post-6-1/);
 assert.match(p,/post-6-2/);
 assert.match(p,/not executable|not an actionable|not executable trading|not executable trading sessions|not executable/i);
 for(const file of ["lib/raas-pdufa-goal-asof-metric-audit.ts","app/raas-worklist/page.tsx"]){
  const out=ts.transpileModule(fs.readFileSync(path.join(root,file),"utf8"),{
   fileName:file,reportDiagnostics:true,
   compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}});
  assert.deepEqual((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
   .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[],file);
 }
});

test("A later SEC filing corroborating an old goal cannot replace the original public source or create approved RAAS cases",()=>{
 const r=activePdufaGoalAsOfAudit();
 const slno=r.cases.find(x=>x.ticker==="SLNO");
 const source=primary.records.find(x=>x.ticker==="SLNO");
 assert.match(source.originalGoalSourceCorroborationUrl,/^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\/1484565\//);
 assert.ok(slno.initialGoalSourceUrl.includes("investors.soleno.life"));
 assert.notEqual(source.originalGoalSourceCorroborationUrl,slno.initialGoalSourceUrl);
 assert.equal(slno.initialGoalAnnouncementDate,"2024-08-27");
 assert.equal(slno.initial.calendarEntryDate,"2024-10-09");
 assert.equal(slno.approvedRaasScore,null);
 assert.equal(slno.approvedMetricGrades,0);
 assert.equal(slno.historicalEntryCapitalizationVerified,false);
 assert.equal(r.validatedHistoricalTradingCases,0);
});
