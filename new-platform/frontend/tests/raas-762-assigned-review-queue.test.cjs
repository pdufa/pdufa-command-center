"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(module,file)=>module._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true}}).outputText,file);
const {parseRegistryEvidenceIndex}=require("../lib/raas-registry-evidence.ts");
const {buildRaas762AssignedReviewQueue,exportRaas762AssignedReviewCsv}
 =require("../lib/raas-762-assigned-review-queue.ts");
const index=parseRegistryEvidenceIndex(JSON.parse(read("public/raas-registry-evidence-index.json")));
const queue=buildRaas762AssignedReviewQueue(index);

test("only 762 unique NCTs have one current registry stage and 30 assigned metrics each",()=>{
 assert.equal(queue.summary.exactNctCount,762);
 assert.equal(queue.summary.beforeTrials,425);
 assert.equal(queue.summary.pastTrials,337);
 assert.equal(queue.summary.assignedMetricTasks,22860);
 assert.equal(queue.items.length,22860);
 const groups=new Map();
 for(const task of queue.items){
  const items=groups.get(task.nctId)||[];
  items.push(task);groups.set(task.nctId,items);
  assert.ok(/^NCT\d{8}$/.test(task.nctId));
  assert.equal(task.metricId.startsWith(task.registryStage==="Before"?"pre-":"post-"),true);
  assert.equal(task.stageBasis,task.registryStage==="Before"?
   "REGISTRY_RESULTS_NOT_POSTED":"REGISTRY_RESULTS_POSTED");
  assert.equal(task.independentSignoffState,"NOT_CERTIFIED");
  assert.equal(task.validatedOverallRaasScore,null);
  assert.equal(task.fdaPassProbability,null);
  assert.equal(task.fdaCrlProbability,null);
  assert.equal(task.fdaExtensionProbability,null);
 }
 assert.equal(groups.size,762);
 for(const records of groups.values()){
  assert.equal(records.length,30);
  assert.equal(new Set(records.map(x=>x.metricId)).size,30);
  assert.equal(new Set(records.map(x=>x.registryStage)).size,1);
 }
});

test("source inventory and provisional reviews stay separate from FDA scores",()=>{
 assert.equal(queue.summary.sourceLeads,6767);
 assert.equal(queue.summary.metricTasksWithSourceLeads,1246);
 assert.equal(queue.summary.trialRowsWithSourceLeads,756);
 assert.ok(queue.summary.provisionalMetricTasks<=82);
 assert.equal(queue.summary.validatedOverallScores,0);
 assert.equal(queue.summary.independentCertifiedMetricTasks,0);
 assert.equal(queue.summary.calibratedFdaPredictions,0);
 const without=new Set(queue.items.filter(x=>x.sourceLeadCount>0).map(x=>x.nctId));
 assert.equal(without.size,756);
 for(const id of ["NCT00017407","NCT00033904","NCT00039000",
  "NCT00048113","NCT00048295","NCT00486980"]){
  const rows=queue.items.filter(x=>x.nctId===id);
  assert.equal(rows.length,30);
  assert.ok(rows.every(x=>x.sourceLeadCount===0));
 }
 assert.ok(queue.items.filter(x=>x.reviewState==="NO_REVIEWED_GRADE")
  .every(x=>x.preliminaryMetricScore===null));
});

test("download CSV includes 22,860 audit tasks without imputing blank grades",()=>{
 const csv=exportRaas762AssignedReviewCsv(queue);
 assert.ok(csv.startsWith("\uFEFFnctId,ticker,registryStage,stageBasis,metricId,"));
 assert.ok(csv.includes("sourceLeadCount"));
 assert.ok(csv.includes("preliminaryMetricScore"));
 assert.ok(csv.includes("independentSignoffState"));
 assert.ok(csv.includes("fdaExtensionProbability"));
 assert.equal(csv.split("\r\n").length-2,22860);
 const route=read("app/api/raas-762-review-queue/route.ts");
 const page=read("app/Raas762ScoringWorkspace.tsx");
 assert.ok(route.includes("parseRegistryEvidenceIndex(savedRegistry)"));
 assert.ok(route.includes("SOURCE_RECONCILIATION_FAILED"));
 assert.ok(route.includes('"Cache-Control":"no-store"'));
 assert.ok(page.includes('href="/api/raas-762-review-queue"'));
});
