"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const nctLines=p=>read(p).split(/\r?\n/).filter(x=>/^NCT\d{8},/.test(x));
const status=require("../data/raas-all-trials-partial-metric-ratings-status.json");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
 esModuleInterop:true}}).outputText,file);
const {RAAS_METRIC_CATALOG}=require("../lib/raas-metric-specs.ts");

test("the one-row-per-trial RAAS setup has exactly 762 uniquely identified NCTs",()=>{
 const lines=nctLines("public/raas-trial-score-ledger.csv");
 const ncts=lines.map(x=>x.split(",")[0]);
 assert.equal(lines.length,762);
 assert.equal(new Set(ncts).size,762);
 assert.equal(status.researchTrials,762);
 assert.equal(status.fullValidatedRaasScores,0);
 assert.equal(status.uniqueNctsWithActualProvisionalMetricScores,21);
 for(const line of lines){
  assert.ok(/NCT\d{8}/.test(line.split(",")[0]));
  assert.ok(line.includes("INCOMPLETE_30_METRIC_INDEPENDENT_REVIEW"));
 }
});
test("every NCT has separate TOP and BOTTOM 30-metric stage setup rows",()=>{
 const trialRows=nctLines("public/raas-trial-score-ledger.csv");
 const stageRows=nctLines("public/raas-all-trials-partial-metric-ratings.csv");
 assert.equal(stageRows.length,1524);
 assert.equal(status.trialStageRows,1524);
 const count=new Map();
 for(const line of stageRows){
  const cols=line.split(",",6);
  const key=cols[0],stage=cols[5];
  assert.ok(stage==="PRE_RESEARCH_ONLY"||stage==="POST_RESEARCH_ONLY");
  const tracked=count.get(key)||new Set();
  assert.ok(!tracked.has(stage));
  tracked.add(stage);count.set(key,tracked);
 }
 assert.equal(count.size,762);
 for(const line of trialRows){
  assert.deepEqual([...count.get(line.split(",")[0])].sort(),
   ["POST_RESEARCH_ONLY","PRE_RESEARCH_ONLY"]);
 }
});
test("the underlying RAAS catalog defines 30 TOP and 30 BOTTOM metric IDs",()=>{
 const ids=new Set();
 for(const stage of ["pre","post"]){
  const names=RAAS_METRIC_CATALOG[stage].flatMap(c=>c.metrics.map(x=>x.id));
  assert.equal(names.length,30);
  assert.equal(new Set(names).size,30);
  assert.ok(names.every(x=>x.startsWith(stage+"-")));
  for(const id of names)ids.add(id);
 }
 assert.equal(ids.size,60);
});
test("primary 762 research route exposes five active clinical factors and cross-stage history",()=>{
 const page=read("app/raas-762/page.tsx"),ui=read("app/Raas762ScoringWorkspace.tsx");
 assert.match(page,/Raas762ScoringWorkspace/);
 assert.match(ui,/RaasClinicalFiveCell row=\{x\.trial\} bucket=\{null\} researchStageOnly=\{x\.stage\}/);
 assert.match(ui,/RaasTrialHistoryButton/);
 assert.match(ui,/rows\.length\*5/);
 assert.match(ui,/remaining:5-reviewed/);
 assert.match(ui,/PAGE_SIZE=50/);
 assert.match(ui,/x\.postedResults\?"post":"pre"/);
 assert.match(ui,/records\.length!==762/);
 assert.doesNotMatch(ui,/RaasMetricGradebook row=\{x\.trial\}/);
});
