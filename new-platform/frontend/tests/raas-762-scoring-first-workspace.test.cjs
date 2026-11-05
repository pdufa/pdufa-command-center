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
 assert.equal(status.uniqueNctsWithActualProvisionalMetricScores,17);
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
test("the primary scoring route and tools index put the 762 rows first",()=>{
 const page=read("app/raas-762/page.tsx"),
  client=read("app/Raas762ScoringWorkspace.tsx"),
  tools=read("app/tools/page.tsx"),
  scan=read("app/raas-scan/page.tsx");
 assert.match(page,/data-raas-primary-scoring-setup="762-nct-rows"/);
 assert.match(page,/Raas762ScoringWorkspace/);
 assert.match(tools,/data-tools-primary-raas-762="true"/);
 assert.match(tools,/href="\/raas-762"/);
 assert.match(scan,/href="\/raas-762"/);
 assert.match(client,/data-raas-762-scoring-workspace/);
 assert.match(client,/loadRegistryEvidenceIndex/);
 assert.match(client,/RaasMetricGradebook row=\{x\.trial\} bucket=\{null\} researchStageOnly=\{x\.stage\}/);
 assert.match(client,/RaasTrialHistoryButton row=\{x\.trial\} bucket=\{null\}/);
 assert.match(client,/PAGE_SIZE=50/);
 assert.match(client,/records\.length!==762/);
 assert.match(client,/const stage:\"pre\"\\|\"post\"=x\.postedResults\?"post":"pre"/);
 assert.match(client,/remaining:30-reviewed/);
 assert.match(client,/rows\.length\*30/);
 assert.match(client,/Not validated/);
 assert.match(client,/N\/A · never 0\/100/);
 for(const file of ["app/raas-762/page.tsx","app/Raas762ScoringWorkspace.tsx",
  "app/tools/page.tsx","app/raas-scan/page.tsx"]){
  const diagnostic=ts.transpileModule(read(file),{fileName:file,
   reportDiagnostics:true,compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX}});
  assert.equal(diagnostic.diagnostics?.filter(x=>
    x.category===ts.DiagnosticCategory.Error).length??0,0,file);
 }
});
