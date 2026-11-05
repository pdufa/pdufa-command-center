"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const registry=require("../public/raas-registry-evidence-index.json");
const status=require("../data/raas-registry-evidence-change-status.json");
const history=require("../data/raas-registry-evidence-change-history.json");
const {buildRaasIndependentReviewQueue}=require("../lib/raas-independent-review-queue.ts");
const {buildRaasReviewAssignmentPlan}=require("../lib/raas-review-assignment-plan.ts");
const {buildRaasRegistryRevisionReviewInbox}=require("../lib/raas-registry-revision-review-inbox.ts");
const {auditRaasReviewProgramSourceGates:audit}=require("../lib/raas-review-source-alert-gate.ts");
const {buildRaasExactProgramReviewBundle}=require("../lib/raas-exact-program-review-bundle.ts");
const queue=buildRaasIndependentReviewQueue();
const plan=buildRaasReviewAssignmentPlan(queue);
const inbox=buildRaasRegistryRevisionReviewInbox(history,status,registry,queue);

test("saved registry source audit maps exactly to all 18 program-stage review handoffs",()=>{
 const gates=audit(plan,inbox,registry);
 assert.equal(gates.totalPrograms,20);
 assert.equal(gates.gates.length,plan.groups.length);
 assert.equal(new Set(gates.gates.map(g=>g.programId)).size,20);
 assert.equal(gates.approvedRaasScores,0);
 assert.equal(gates.calibratedFdaForecasts,0);
 for(const g of gates.gates){
  const original=plan.groups.find(x=>x.id===g.programId);
  assert.ok(original);
  assert.equal(g.nctId,original.nctId);
  assert.equal(g.ticker,original.ticker);
  assert.equal(g.stage,original.stage);
  assert.equal(g.reviewFeedAsOf,original.sourceAsOf);
  assert.equal(g.registryAsOf,registry.sourceAsOf);
  assert.match(g.registrySourceHash,/^[a-f0-9]{64}$/);
  assert.equal(g.approvedRaasScore,null);
  assert.equal(g.calibratedFdaProbability,null);
  assert.ok(["NO_RECORDED_METRIC_REVISIONS","RECHECK_SOURCE_REVISIONS",
   "SOURCE_AUDIT_INCOMPLETE_OR_UNSYNCED"].includes(g.status));
  assert.match(g.explanation,/source|registry|comparison/i);
 }
 assert.equal(gates.needRevisionRecheck+gates.sourceAuditUnconfirmed+
  gates.noRecordedMetricRevisions,20);
});
test("a newly flagged clinical revision stops a clean source assertion for only its exact stage",()=>{
 const co=plan.groups.find(x=>x.nctId==="NCT05208047");
 assert.ok(co);
 const alerted={...inbox,tasks:[{
  nctId:co.nctId,ticker:co.ticker,metricStage:co.stage,metricId:"post-1-1",
  sourceMatch:"MATCHES_SAVED_REGISTRY",observedAt:"2026-11-06T01:00:00Z"
 }]};
 const gates=audit(plan,alerted,registry);
 const flagged=gates.gates.find(x=>x.programId===co.id);
 assert.equal(flagged.status,"RECHECK_SOURCE_REVISIONS");
 assert.deepEqual(flagged.sourceChangedMetricIds,["post-1-1"]);
 assert.equal(flagged.relevantRevisionAlertCount,1);
 assert.equal(flagged.supersededOrUnsyncedAlertCount,0);
 assert.equal(flagged.approvedRaasScore,null);
 assert.ok(gates.gates.filter(x=>x.status==="RECHECK_SOURCE_REVISIONS").length>=1);
});
test("incomplete, stale or mismatched saved registry audit never appears clean",()=>{
 const badStates=[{...inbox,auditState:"COMPLETED_WITH_SOURCE_ERRORS"},
  {...inbox,registryAsOf:"2020-01-01T00:00:00Z"}];
 for(const bad of badStates){
  const auditResult=audit(plan,bad,registry);
  assert.equal(auditResult.sourceAuditUnconfirmed,plan.groups.length);
  assert.ok(auditResult.gates.every(x=>
   x.status==="SOURCE_AUDIT_INCOMPLETE_OR_UNSYNCED"));
  assert.equal(auditResult.approvedRaasScores,0);
 }
 const edited={...plan,groups:plan.groups.map((x,i)=>i===0?
  {...x,ticker:"INCORRECT"}:x)};
 assert.equal(audit(edited,inbox,registry).gates[0].status,
  "SOURCE_AUDIT_INCOMPLETE_OR_UNSYNCED");
});
test("the source-change gate is checksummed inside the downloadable 30-metric handoff",()=>{
 const first=plan.groups[0];
 const bundle=buildRaasExactProgramReviewBundle(first.tasks[0].taskId);
 assert.ok(bundle);
 assert.equal(bundle.sourceChangeReview.programId,first.id);
 assert.equal(bundle.sourceChangeReview.nctId,first.nctId);
 assert.equal(bundle.sourceChangeReview.approvedRaasScore,null);
 assert.equal(bundle.sourceChangeReview.calibratedFdaProbability,null);
 assert.match(bundle.handoffState,/NOT_CERTIFIED/);
 assert.equal(bundle.requirements.length,30);
 assert.equal(bundle.inventory.certifiedIndependentMetrics,0);
 assert.equal(bundle.approvedOverallRaasScore,null);
});
test("reviewer cards display exact source-change alert and link to dated registry history",()=>{
 const board=fs.readFileSync(path.join(root,
  "app/raas-review-queue/RaasReviewAssignmentBoard.tsx"),"utf8");
 const page=fs.readFileSync(path.join(root,"app/raas-review-queue/page.tsx"),"utf8");
 assert.match(page,/auditRaasReviewProgramSourceGates/);
 assert.match(page,/sourceGates=\{sourceGates\}/);
 assert.match(board,/data-raas-exact-program-source-gate/);
 assert.match(board,/sourceGateById\.get\(group\.id\)/);
 assert.match(board,/raas-evidence-changes/);
 assert.match(board,/No recorded metric revision/);
 const checked=ts.transpileModule(board,{fileName:"source-board.tsx",
  reportDiagnostics:true,compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
   jsx:ts.JsxEmit.ReactJSX
  }});
 assert.equal((checked.diagnostics||[]).filter(x=>
  x.category===ts.DiagnosticCategory.Error).length,0);
});
