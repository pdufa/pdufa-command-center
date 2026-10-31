"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
 ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,
 }}).outputText,file
);
const {exactProgramTimeline,pacificToday,pipelineDayCounts}=require("../lib/pipeline-timeline.ts");
const {PipelineTimelineCells,PipelineTimelineHeaders}=require("../app/PipelineTimelineColumns.tsx");
const React=require("react");
const render=(C,props)=>require("react-dom/server").renderToStaticMarkup(React.createElement(C,props));
const data={
 phase3ReadoutDate:"2026-10-01",phase3ReadoutSource:"https://example.org/press/release",phase3ReadoutVerified:true,
 pdufaDate:"2026-11-10",pdufaSource:"https://example.org/fda/target",pdufaTargetVerified:true,
};
test("days are whole Pacific-calendar days, not elapsed timestamps",()=>{
 const valid=exactProgramTimeline(data,true);
 assert.deepEqual(pipelineDayCounts(valid,"2026-10-31"),{
  daysSincePhase3Release:30,daysToPdufa:10,cutoffReached:false,
 });
 assert.deepEqual(pipelineDayCounts(valid,"2026-11-07"),{
  daysSincePhase3Release:37,daysToPdufa:3,cutoffReached:true,
 });
 assert.deepEqual(pipelineDayCounts(valid,"2026-11-11"),{
  daysSincePhase3Release:41,daysToPdufa:-1,cutoffReached:true,
 });
 assert.equal(pacificToday(new Date("2026-11-01T05:00:00Z")),"2026-10-31");
 assert.equal(pacificToday(new Date("2026-11-01T08:00:00Z")),"2026-11-01");
});
test("identity mismatches, missing provenance and registry completion hints never become date facts",()=>{
 assert.deepEqual(exactProgramTimeline(data,false),{phase3DataRelease:null,pdufaTarget:null});
 assert.deepEqual(exactProgramTimeline({phase3Date:"2026-10-01",phase3Source:"https://example.org",pdufaDate:"2026-11-10"},true),{phase3DataRelease:null,pdufaTarget:null});
 for(const invalid of ["2026-02-30","2026-13-01","2026-1-2","not-a-date"]){
  const dates=exactProgramTimeline({...data,phase3ReadoutDate:invalid,pdufaDate:invalid},true);
  assert.equal(dates.phase3DataRelease,null);
  assert.equal(dates.pdufaTarget,null);
 }
 const legacy=exactProgramTimeline({phase3Date:"2026-10-01",phase3Source:"https://example.org",
  phase3DateKind:"PUBLIC_RESULTS_RELEASE",phase3DateVerified:true},true);
 assert.equal(legacy.phase3DataRelease.date,"2026-10-01");
 assert.equal(legacy.pdufaTarget,null);
 assert.equal(exactProgramTimeline({...data,phase3ReadoutVerified:false},true).phase3DataRelease,null);
 assert.equal(exactProgramTimeline({...data,pdufaSource:"http://example.org"},true).pdufaTarget,null);
});
test("readout future dates withheld and past PDUFA dates labeled distinctly",()=>{
 const event=exactProgramTimeline(data,true);
 assert.equal(pipelineDayCounts(event,"2026-09-30").daysSincePhase3Release,null);
 const html=render(PipelineTimelineCells,{dates:event,today:"2026-11-11"});
 assert.equal((html.match(/<td/g)||[]).length,2);
 assert.ok(html.includes("41 days"));
 assert.ok(html.includes("Passed 1 days ago")||html.includes("Passed 1 day ago"));
 assert.ok(html.includes("2026-10-01"));
 assert.ok(html.includes("2026-11-10"));
 assert.ok(html.includes("reached its cutoff"));
 const unknown=render(PipelineTimelineCells,{dates:null,today:"2026-10-31"});
 assert.ok(unknown.includes("Not verified"));
 assert.ok(unknown.includes("Trial completion is not a release"));
 const headers=render(PipelineTimelineHeaders,{});
 assert.ok(headers.includes("Days since Phase 3 data release"));
 assert.ok(headers.includes("Days to PDUFA"));
});
test("new columns appear in the active post-Phase 3 PIPELINE, without modifying the POOL",()=>{
 const code=fs.readFileSync(path.join(__dirname,"../app/FunnelWorkspace.tsx"),"utf8");
 assert.ok(code.includes("<PipelineTimelineHeaders />"));
 assert.ok(code.includes("<PipelineTimelineCells dates={r.timeline} today={today}/>"));
 const funnel=fs.readFileSync(path.join(__dirname,"../lib/pool-pipeline-funnel.ts"),"utf8");
 assert.ok(funnel.includes('timeline:exactProgramTimeline(pool,poolStatus==="EXACT_MATCH")'));
});
