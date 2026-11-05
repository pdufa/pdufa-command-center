"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true,
  jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const index=require("../public/raas-registry-evidence-index.json");
const reviewed=require("../data/raas-reviewed-metric-assessments.json");
const {buildTrialEvidenceBacklog}=
 require("../lib/raas-trial-evidence-backlog.ts");
const report=buildTrialEvidenceBacklog(index);

test("All 762 exact registry trials are represented once, without score promotion",()=>{
 assert.equal(report.scope,"RAAS_762_REGISTRY_RESEARCH_TRIAGE_NOT_APPROVED_SCORES");
 assert.equal(report.totalTrials,762);
 assert.equal(report.items.length,762);
 assert.equal(new Set(report.items.map(x=>x.nctId)).size,762);
 assert.equal(report.postedResults,337);
 assert.equal(report.protocolOnly,425);
 assert.equal(report.currentFdaPhase3,1);
 assert.equal(report.currentPhase3Top,6);
 assert.equal(report.independentReviewedMetrics,0);
 assert.equal(report.approvedScores,0);
 assert.equal(report.calibratedFdaPredictions,0);
 assert.ok(report.items.every(x=>x.approvedRaasScore===null&&
  x.calibratedFdaProbability===null));
});
test("Every review is counted only for the exact NCT+issuer and separately in TOP/BOTTOM",()=>{
 assert.equal(report.provisionalMetricReviews,96);
 assert.equal(report.trialsWithAnyProvisionalMetrics,21);
 assert.equal(report.provisionalMetricReviews,
  report.items.reduce((n,x)=>n+x.reviewedTop+x.reviewedBottom,0));
 for(const item of report.items){
  assert.ok(item.reviewedTop>=0&&item.reviewedTop<=30);
  assert.ok(item.reviewedBottom>=0&&item.reviewedBottom<=30);
  assert.equal(item.missingTopMetricIds.length,30-item.reviewedTop);
  assert.equal(item.missingBottomMetricIds.length,30-item.reviewedBottom);
  assert.ok(item.missingTopMetricIds.every(x=>x.startsWith("pre-")));
  assert.ok(item.missingBottomMetricIds.every(x=>x.startsWith("post-")));
  assert.match(item.sourceUrl,new RegExp("^https://clinicaltrials\\.gov/study/"+item.nctId+"$"));
 }
 assert.ok(reviewed.records.every(r=>{
  const found=report.items.find(x=>x.nctId===r.nctId&&x.ticker===r.ticker);
  return found&&(
   r.stage==="pre"?!found.missingTopMetricIds.includes(r.metricId):
    !found.missingBottomMetricIds.includes(r.metricId)
  );
 }));
});
test("FDA priority includes ONLY PEAK Phase 3 COGT, never unrelated accepted Phase2 NDAs",()=>{
 const one=report.items.filter(x=>x.priority==="FDA_ACCEPTED_PHASE3");
 assert.equal(one.length,1);
 assert.equal(one[0].nctId,"NCT05208047");
 assert.equal(one[0].ticker,"COGT");
 assert.equal(one[0].stage,"post");
 assert.equal(one[0].acceptedPdufaGoal,"2026-11-30");
 assert.ok(one[0].reviewedBottom>0);
 for(const id of ["NCT05186753","NCT04996875"])
  assert.ok(!report.items.some(x=>x.nctId===id&&x.priority==="FDA_ACCEPTED_PHASE3"));
});
test("The six current TOP Phase3 trials are separately prioritized, never inferred as FDA pending",()=>{
 const top=report.items.filter(x=>x.priority==="CURRENT_PHASE3_TOP");
 assert.equal(top.length,6);
 assert.deepEqual(top.map(x=>x.nctId).sort(),
  ["NCT06641089","NCT06736574","NCT07363577",
   "NCT07369154","NCT07671911","NCT07868419"]);
 assert.ok(top.every(x=>x.stage==="pre"&&x.acceptedPdufaGoal===null&&
  x.reviewedBottom===0&&x.reviewedTop>=3));
});
test("Unknown registry stage is not made BOTTOM by posted results or TOP by protocol-only",()=>{
 assert.ok(report.unverifiedStages>500);
 for(const item of report.items.filter(x=>x.stage==="unverified")){
  assert.equal(item.stageSourceUrl,null);
  assert.equal(item.stageEvidenceDate,null);
  assert.match(item.nextEvidenceAction,/First verify whether an exact Phase 3 public readout occurred|Resolve the trial-to-therapy/);
 }
 const comparison=report.items.filter(x=>x.priority==="REGISTRY_COMPARATIVE_RESULTS");
 assert.ok(comparison.length>100);
 assert.ok(comparison.every(x=>x.hasPrimaryComparisons&&x.postedResults&&
  x.stage==="unverified"));
 assert.ok(report.items.filter(x=>x.priority==="REGISTRY_PROTOCOL_ONLY").every(
  x=>!x.postedResults&&x.stage==="unverified"));
});
test("Source coverage is separate from independent review and every row retains date and source hash",()=>{
 assert.equal(report.trialsWithComparativeRegistryEvidence,170);
 assert.equal(report.trialsWithConfidenceIntervals,149);
 for(const x of report.items){
  assert.match(x.sourceHash,/^[0-9a-f]{64}$/);
  assert.match(x.sourceDate,/^\d{4}-\d{2}-\d{2}$/);
  assert.ok(x.registeredPhases.length>0||x.registeredStatus);
 }
});
test("The new route and mobile filters link to existing RAAS workflows",async()=>{
 const client=read("app/raas-evidence-backlog/EvidenceBacklogClient.tsx");
 const page=read("app/raas-evidence-backlog/page.tsx");
 const scan=read("app/raas-scan/page.tsx");
 const reviewQueue=read("app/raas-review-queue/page.tsx");
 for(const s of [scan,reviewQueue])assert.match(s,/raas-evidence-backlog/);
 for(const x of ["data-raas-research-backlog","Source availability","Provisional reviews",
  "Export 762-trial evidence gaps","Previous 25","Next 25",
  "data-raas-evidence-backlog-nct"])assert.ok(client.includes(x),x);
 assert.match(page,/762 saved Phase 3 research trial identifiers/);
 for(const [name,source] of [["page.tsx",page],["EvidenceBacklogClient.tsx",client]]){
  const r=ts.transpileModule(source,{fileName:name,reportDiagnostics:true,
   compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX}});
  assert.deepEqual((r.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error),[]);
 }
 const {GET}=require("../app/api/raas-evidence-backlog/route.ts");
 const res=GET();
 assert.equal(res.status,200);
 assert.match(res.headers.get("Content-Type"),/text\/csv/);
 const csv=await res.text();
 assert.match(csv,/NCT05208047/);
 assert.match(csv,/NCT07671911/);
 assert.equal(csv.split("\r\n").length-2,762);
});
