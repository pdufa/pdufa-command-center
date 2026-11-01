"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
 }}).outputText,file);
const {timelineDisplay}=require("../app/TrialTimelineSummary.tsx");
const read=name=>fs.readFileSync(path.join(__dirname,"../app",name),"utf8");
const timeline={phase3DataRelease:{date:"2026-10-01",sourceUrl:"https://example.org/readout",status:"VERIFIED"},
  pdufaTarget:{date:"2026-11-10",sourceUrl:"https://example.org/target",status:"VERIFIED"}};
test("trial timing uses two independently sourced dates",()=>{
 const v=timelineDisplay(timeline,"2026-11-01");
 assert.equal(v.since,"31 days");
 assert.equal(v.until,"9 days");
 assert.equal(v.release.date,"2026-10-01");
});
test("passed FDA target displays as passed rather than implying a negative countdown",()=>{
 const v=timelineDisplay(timeline,"2026-11-12");
 assert.equal(v.until,"Passed 2 days ago");
 assert.equal(v.since,"42 days");
});
test("missing and future readout are not invented",()=>{
 const a=timelineDisplay(null,"2026-11-01");
 assert.equal(a.since,"Not verified");
 assert.equal(a.until,"Not verified");
 const b=timelineDisplay({...timeline,phase3DataRelease:{...timeline.phase3DataRelease,date:"2026-11-10"}},"2026-11-01");
 assert.equal(b.since,"Not verified");
});
test("trial detail and comparison headers show date counters before assessment fields",()=>{
 const full=read("trial/[nctId]/page.tsx"),compare=read("TrialComparison.tsx");
 const dossier=read("PipelineFourViews.tsx");
 assert.ok(full.indexOf("<FullTrialTimeline")<full.indexOf("<TrialWorkflowCounts"));
 assert.ok(compare.includes("<TrialTimelineSummary timeline={t.row.timeline}"));
 assert.ok(dossier.includes("<TrialTimelineSummary timeline={row.timeline} today={today}"));
});

test("green-bordered date boxes are visible directly next to tickers across trial views",()=>{
 const metric=read("TrialTimelineSummary.tsx");
 const full=read("FullTrialTimeline.tsx");
 const page=read("trial/[nctId]/page.tsx");
 const dossier=read("PipelineFourViews.tsx");
 const comparison=read("TrialComparison.tsx");
 assert.match(metric,/border:"3px solid #0b9348"/);
 assert.match(metric,/DAYS SINCE PHASE 3/);
 assert.match(metric,/DAYS TO PDUFA/);
 assert.ok(full.includes("Ticker: {ticker||"));
 assert.ok(full.indexOf("Ticker: {ticker||")<full.indexOf("<TrialTimelineSummary timeline={timeline} compact"));
 assert.ok(page.indexOf("<FullTrialTimeline")<page.indexOf("<TrialWorkflowCounts"));
 assert.ok(dossier.indexOf("<h3 style={{margin:0}}>{row.nctId} · {row.ticker}</h3>")<
           dossier.indexOf("<TrialTimelineSummary timeline={row.timeline} today={today} compact"));
 assert.ok(comparison.indexOf("<h3 style={{fontSize:18,margin:0}}>{t.row.ticker}</h3>")<
           comparison.indexOf("<TrialTimelineSummary timeline={t.row.timeline} compact"));
});

test("TOOLS trial listing and 20-assessment table show the green counters after ticker",()=>{
 const sheet=read("ToolsResultsSpreadsheet.tsx");
 const matrix=read("ToolsBenefitMatrix.tsx");
 const route=read("api/scope-funnel/route.ts");
 assert.ok(sheet.includes("<strong>{display(row.ticker)}</strong>"));
 assert.ok(sheet.includes("<TrialTimelineSummary timeline={row.timeline} today={today} compact/>"));
 assert.ok(matrix.includes("<strong>{short(row.ticker)}</strong><TrialTimelineSummary timeline={row.timeline} today={today} compact/>"));
 assert.ok(matrix.includes("<TrialTimelineSummary timeline={selected.timeline} today={today} compact/>"));
 assert.ok(route.includes("trialTimelines=new Map<string,TimelineDates>"));
 assert.ok(route.includes("timeline:trialTimelines.get(row.nctId+"));
});

test("A and P labels distinguish the two green bordered date counters",()=>{
 const metric=read("TrialTimelineSummary.tsx");
 assert.match(metric,/<span style={letter}>A<\/span><span>DAYS SINCE PHASE 3<\/span>/);
 assert.match(metric,/<span style={letter}>P<\/span><span>DAYS TO PDUFA<\/span>/);
 assert.match(metric,/background:"#08763f"/);
});
