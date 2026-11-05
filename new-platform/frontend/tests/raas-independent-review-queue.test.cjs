"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const {buildRaasIndependentReviewQueue}=require("../lib/raas-independent-review-queue.ts");

test("queue captures all actual reviewed source metrics and never invents signed independent ratings",()=>{
 const q=buildRaasIndependentReviewQueue();
 assert.equal(q.total,82);
 assert.equal(q.items.length,82);
 assert.equal(q.uniqueNcts,17);
 assert.equal(q.currentFdaPhase3Metrics,5);
 assert.equal(q.currentTopPhase3Metrics,27);
 assert.equal(q.otherResearchMetrics,50);
 assert.equal(q.aiPending,82);
 assert.equal(q.markedIndependentWithoutAuditedReceipt,0);
 assert.equal(q.independentlyVerifiedSignoffs,0);
 assert.equal(q.approvedRaasScores,0);
 assert.equal(q.calibratedFdaForecasts,0);
 assert.equal(new Set(q.items.map(x=>x.id)).size,82);
 assert.ok(q.items.every(x=>x.approvedOverallRaasScore===null&&
  x.calibratedFdaProbability===null));
});
test("current FDA case remains exact approved Phase3 Cogent GIST NCT; Phase2 NDAs cannot enter queue",()=>{
 const q=buildRaasIndependentReviewQueue();
 const fda=q.items.filter(x=>x.priority==="FDA_ACCEPTED_PHASE3");
 assert.equal(fda.length,5);
 assert.ok(fda.every(x=>x.nctId==="NCT05208047"&&x.ticker==="COGT"&&
  x.applicationKey==="COGT-BEZUCLASTINIB-GIST-2026"&&x.stage==="post"));
 for(const id of ["NCT05186753","NCT04996875"])
  assert.ok(!q.items.some(x=>x.nctId===id&&x.priority==="FDA_ACCEPTED_PHASE3"));
});
test("current TOP priority is restricted to six exact registry Phase3 NCTs and does not conflate issuer duplicates",()=>{
 const q=buildRaasIndependentReviewQueue();
 const top=q.items.filter(x=>x.priority==="CURRENT_PHASE3_TOP");
 const intended=["NCT06641089","NCT06736574","NCT07363577",
  "NCT07369154","NCT07671911","NCT07868419"];
 assert.deepEqual([...new Set(top.map(x=>x.nctId))].sort(),intended);
 assert.ok(top.every(x=>x.stage==="pre"&&x.applicationKey===null));
 assert.equal(new Set(top.map(x=>x.ticker)).size,4);
 for(const item of q.items){
  assert.match(item.sourceUrl,/^https:\/\//);
  assert.match(item.benchmarkSourceUrl,/^https:\/\//);
  assert.ok(item.sourceDate<=item.assessedAt&&item.assessedAt<=q.asOf);
  assert.ok(item.criticalRiskReview&&item.uncertaintyReview&&item.benchmarkContext);
  assert.ok(item.metricWeightPercent>0&&item.metricWeightPercent<=100);
  assert.equal(item.reviewState,"AI_ASSISTED_AWAITING_HUMAN_REVIEW");
 }
});
test("queue route, filters, secure source URLs, and CSV handoff remain available on iPhone without rating approval",()=>{
 const page=read("app/raas-review-queue/page.tsx");
 const client=read("app/raas-review-queue/ReviewQueueClient.tsx");
 const scan=read("app/raas-scan/page.tsx");
 const worklist=read("app/raas-worklist/page.tsx");
 for(const s of [scan,worklist])assert.match(s,/raas-review-queue/);
 for(const fragment of ["data-raas-independent-review-queue","ReviewQueueClient","independentlyVerifiedSignoffs"])
  assert.ok(page.includes(fragment));
 for(const fragment of ["data-raas-review-item","sourceUrl","benchmarkSourceUrl",
   "Clear filters","Export review tasks","Previous 20","Next 20","aria-label","attributable independent reviewer identity"])
  assert.ok(client.includes(fragment),fragment);
 for(const [source,name] of [[page,"page.tsx"],[client,"ReviewQueueClient.tsx"]]){
  const output=ts.transpileModule(source,{fileName:name,reportDiagnostics:true,
   compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
  assert.deepEqual((output.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).map(d=>d.code),[]);
 }
});
test("CSV exports exact research rows and never treats signed reviews as complete",async()=>{
 const {GET}=require("../app/api/raas-independent-review-queue/route.ts");
 const res=GET();
 assert.equal(res.status,200);
 assert.match(res.headers.get("content-type"),/text\/csv/);
 assert.match(res.headers.get("content-disposition"),/raas-independent-metric-review-queue.csv/);
 const csv=await res.text();
 assert.match(csv,/metricWeightPercent/);
 assert.match(csv,/NCT05208047/);
 assert.match(csv,/NCT07671911/);
 assert.match(csv,/AI_ASSISTED_AWAITING_HUMAN_REVIEW/);
 assert.doesNotMatch(csv,/CERTIFIED_INDEPENDENT_APPROVED/);
});
