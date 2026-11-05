"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const {createHash}=require("node:crypto");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const {buildRaasReviewAssignmentPlan}=
 require("../lib/raas-review-assignment-plan.ts");
const {buildRaasExactProgramReviewBundle:build}=
 require("../lib/raas-exact-program-review-bundle.ts");
const {GET}=require("../app/api/raas-exact-program-review-bundle/route.ts");

test("every expert handoff has precisely 30 TOP/BOTTOM metric requirements and exact identity",()=>{
 const groups=buildRaasReviewAssignmentPlan().groups;
 assert.equal(groups.length,17);
 for(const group of groups){
  const bundle=build(group.tasks[0].taskId);
  assert.equal(bundle.schemaVersion,1);
  assert.equal(bundle.sourceAsOf,group.sourceAsOf);
  assert.equal(bundle.program.nctId,group.nctId);
  assert.equal(bundle.program.ticker,group.ticker);
  assert.equal(bundle.program.drug,group.drug);
  assert.equal(bundle.program.indication,group.indication);
  assert.equal(bundle.program.stage,group.stage);
  assert.equal(bundle.program.applicationKey,group.applicationKey);
  assert.equal(bundle.requirements.length,30);
  assert.equal(new Set(bundle.requirements.map(r=>r.metricId)).size,30);
  assert.equal(bundle.inventory.requiredMetrics,30);
  assert.equal(bundle.inventory.sourceReviewedProvisionalMetrics,group.provisionalMetrics);
  assert.equal(bundle.inventory.missingProvisionalMetricEvidence,group.remainingStageMetrics);
  assert.equal(bundle.inventory.certifiedIndependentMetrics,0);
  assert.equal(bundle.inventory.approvedStageScore,null);
  assert.equal(bundle.inventory.calibratedFdaForecast,null);
  assert.equal(bundle.approvedOverallRaasScore,null);
  assert.equal(bundle.calibratedFdaProbabilities,null);
  const packets=bundle.requirements.filter(r=>r.priorResearchPacket!==null);
  assert.equal(packets.length,group.tasks.length);
  for(const r of bundle.requirements){
   assert.equal(r.approvedMetricGrade,null);
   assert.equal(r.certifiedIndependentReview,null);
   assert.match(r.metricId,group.stage==="pre"?/^pre-/:/^post-/);
   assert.ok(r.requiredEvidence&&r.criticalRisk&&r.independentBenchmarkRequirement);
   if(r.priorResearchPacket){
    const packet=r.priorResearchPacket;
    assert.equal(packet.sourceFingerprint,r.sourceFingerprint);
    assert.equal(packet.task.nctId,group.nctId);
    assert.equal(packet.task.ticker,group.ticker);
    assert.equal(packet.task.indication,group.indication);
    assert.equal(packet.task.drug,group.drug);
    assert.equal(packet.task.stage,group.stage);
    assert.equal(packet.approvedRaasScore,null);
    assert.equal(packet.calibratedFdaProbability,null);
   }else{
    assert.equal(r.sourceFingerprint,null);
    assert.equal(r.packetStatus,"MISSING_PROVISIONAL_EVIDENCE_NOT_ZERO");
   }
  }
  const {integrity,reviewerWorkflow,handoffState,
   approvedOverallRaasScore,calibratedFdaProbabilities,...snapshot}=bundle;
  assert.equal(integrity.canonicalPayloadHash,
   createHash("sha256").update(JSON.stringify(snapshot),"utf8").digest("hex"));
  assert.equal(integrity.digestAlgorithm,"SHA-256");
  assert.match(handoffState,/NOT_CERTIFIED/);
 }
});
test("FDA-accepted COGT Phase3 BOTTOM can be handed off in one file with 5 source packets and 25 missing",()=>{
 const group=buildRaasReviewAssignmentPlan().groups[0];
 assert.equal(group.nctId,"NCT05208047");
 assert.equal(group.ticker,"COGT");
 const bundle=build(group.tasks[0].taskId);
 assert.equal(bundle.program.stage,"post");
 assert.equal(bundle.inventory.sourceReviewedProvisionalMetrics,5);
 assert.equal(bundle.inventory.missingProvisionalMetricEvidence,25);
 assert.equal(bundle.requirements.length,30);
 assert.ok(bundle.requirements.every(r=>r.metricId.startsWith("post-")));
});
test("an unknown, wrong, or altered metric cannot silently substitute any other trial",async()=>{
 assert.equal(build("NCT00000000-not-in-roster"),null);
 for(const term of ["", "no-such-task", "\n", " ".repeat(1000)]){
  const request=new Request("https://example.test/api/raas-exact-program-review-bundle?task="+
   encodeURIComponent(term));
  const response=GET(request);
  assert.ok([400,404].includes(response.status));
  assert.equal(response.headers.get("Cache-Control"),"no-store");
 }
 const task=buildRaasReviewAssignmentPlan().groups[0].tasks[0].taskId;
 const response=GET(new Request("https://example.test/api/raas-exact-program-review-bundle?task="+
  encodeURIComponent(task)));
 assert.equal(response.status,200);
 assert.match(response.headers.get("content-disposition"),/COGT-NCT05208047-post-30-metrics/);
 assert.match(response.headers.get("content-type"),/application\/json/);
 const bundle=await response.json();
 assert.equal(bundle.requirements.length,30);
 assert.equal(bundle.program.nctId,"NCT05208047");
 assert.equal(bundle.inventory.certifiedIndependentMetrics,0);
 assert.equal(bundle.approvedOverallRaasScore,null);
 assert.equal(response.headers.get("Cache-Control"),"no-store");
});
test("mobile RAAS review board offers single file handoff for each exact stage",()=>{
 const source=fs.readFileSync(path.join(root,
  "app/raas-review-queue/RaasReviewAssignmentBoard.tsx"),"utf8");
 assert.match(source,/data-raas-complete-stage-review-handoff="30-metrics"/);
 assert.match(source,/api\/raas-exact-program-review-bundle/);
 assert.match(source,/group.tasks\[0\].taskId/);
 assert.match(source,/missing-evidence entries \(N\/A, not zero\)/);
 const parsed=ts.transpileModule(source,{fileName:"review.tsx",
  reportDiagnostics:true,compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
   jsx:ts.JsxEmit.ReactJSX
  }});
 assert.equal((parsed.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).length,0);
});

test("valid ClinicalTrials.gov NCT IDs survive both RAAS review page deep-link filters",()=>{
 const page=fs.readFileSync(path.join(root,"app/raas-review-queue/page.tsx"),"utf8");
 const terms=page.split("\n").filter(line=>line.includes("const initialNctId=")||line.includes("const existingNctId="));
 assert.equal(terms.length,2);
 for(const line of terms){
  const literal=line.slice(line.indexOf("=/")+1,line.indexOf("/.test(")+1);
  const rx=new RegExp(literal.slice(1,-1));
  assert.equal(rx.test("NCT05208047"),true);
  assert.equal(rx.test("NCT0520804"),false);
  assert.equal(rx.test("NCT052080470"),false);
  assert.equal(rx.test("nct05208047"),false);
 }
});
