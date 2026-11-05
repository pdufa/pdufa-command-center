"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true,
  jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const {buildRaasIndependentReviewQueue}=
 require("../lib/raas-independent-review-queue.ts");
const {buildRaasReviewAssignmentPlan:build}=
 require("../lib/raas-review-assignment-plan.ts");
const {frozenReviewPacket}=require("../lib/raas-external-review-intake.ts");
const queue=buildRaasIndependentReviewQueue();

test("every provisional metric has one exact-trial source-frozen unsigned assignment packet",()=>{
 const plan=build(queue);
 assert.equal(plan.totalPackets,96);
 assert.equal(plan.distinctPrograms,21);
 assert.equal(plan.fdaAcceptedPhase3Packets,5);
 assert.equal(plan.currentPhase3TopPackets,27);
 assert.equal(plan.otherResearchPackets,64);
 assert.equal(plan.groups.reduce((total,g)=>total+g.provisionalMetrics,0),96);
 assert.equal(new Set(plan.groups.map(g=>g.id)).size,plan.groups.length);
 const tasks=plan.groups.flatMap(group=>group.tasks);
 assert.equal(new Set(tasks.map(t=>t.taskId)).size,96);
 const originals=new Map(queue.items.map(t=>[t.id,t]));
 for(const group of plan.groups){
  assert.ok(group.provisionalMetrics>0&&group.provisionalMetrics<=30);
  assert.equal(group.remainingStageMetrics+group.provisionalMetrics,30);
  assert.equal(group.approvedStageScore,null);
  assert.equal(group.externalReviewerAssigned,false);
  assert.equal(new Set(group.tasks.map(t=>t.metricId)).size,group.tasks.length);
  for(const task of group.tasks){
   const original=originals.get(task.taskId);
   assert.ok(original,"Exact original metric packet must exist");
   assert.equal(original.nctId,group.nctId);
   assert.equal(original.ticker,group.ticker);
   assert.equal(original.drug,group.drug);
   assert.equal(original.indication,group.indication);
   assert.equal(original.stage,group.stage);
   assert.equal(task.sourceFingerprint,frozenReviewPacket(task.taskId).sourceFingerprint);
   assert.match(task.sourceFingerprint,/^[a-f0-9]{64}$/);
   assert.equal(task.receiptState,"NO_RECEIPT");
   assert.equal(task.approvedMetricGrade,null);
   assert.equal(task.calibratedFdaProbability,null);
  }
 }
 assert.equal(plan.submittedReceiptReferences,0);
 assert.equal(plan.pendingReceiptAuthentication,0);
 assert.equal(plan.certifiedIndependentMetricSignoffs,0);
 assert.equal(plan.approvedStageScores,0);
 assert.equal(plan.calibratedFdaForecasts,0);
});
test("exact FDA-accepted Phase 3 program is first and Phase 2 events are excluded",()=>{
 const plan=build(queue);
 const high=plan.groups.filter(g=>g.priority==="FDA_ACCEPTED_PHASE3");
 assert.equal(high.length,1);
 assert.equal(high[0].nctId,"NCT05208047");
 assert.equal(high[0].ticker,"COGT");
 assert.equal(high[0].stage,"post");
 assert.equal(high[0].provisionalMetrics,5);
 assert.equal(plan.groups[0].id,high[0].id);
 assert.equal(plan.groups.filter(g=>g.priority==="CURRENT_PHASE3_TOP").length,6);
 assert.equal(plan.groups.filter(g=>g.priority==="OTHER_RESEARCH").length,14);
 for(const wrongNct of ["NCT05186753","NCT04996875"]){
  assert.ok(!high.some(g=>g.nctId===wrongNct));
 }
});
test("source frozen packet identity, per-program stage and duplicate task safety",()=>{
 const duplicate={...queue,items:[...queue.items,queue.items[0]],total:97};
 assert.throws(()=>build(duplicate),/RAAS_ASSIGNMENT_DUPLICATE_EXACT_TASK/);
 const altered={...queue,items:queue.items.map((x,i)=>i===1?
  {...x,id:x.id+"-changed",metricId:queue.items[0].metricId,
   nctId:queue.items[0].nctId,ticker:queue.items[0].ticker,
   drug:queue.items[0].drug,indication:queue.items[0].indication,
   stage:queue.items[0].stage,priority:queue.items[0].priority,
   applicationKey:queue.items[0].applicationKey}:x)};
 assert.throws(()=>build(altered),/RAAS_ASSIGNMENT_DUPLICATE_PROGRAM_METRIC/);
});
test("CSV manifest exports 96 checksum-linked, unsigned assignments with no raw signed documents",async()=>{
 const {GET}=require("../app/api/raas-review-assignment-manifest/route.ts");
 const response=GET();
 assert.equal(response.status,200);
 assert.match(response.headers.get("Cache-Control"),/no-store/);
 const csv=await response.text();
 const lines=csv.trim().split("\r\n");
 assert.equal(lines.length,97);
 assert.match(lines[0],/sourceFingerprint/);
 assert.match(lines[0],/exactPacketDownloadPath/);
 assert.match(csv,/NCT05208047/);
 assert.match(csv,/UNASSIGNED/);
 assert.doesNotMatch(csv,/CERTIFIED_INDEPENDENT_APPROVED/);
 const fingerprints=build(queue).groups.flatMap(g=>g.tasks.map(t=>t.sourceFingerprint));
 assert.ok(fingerprints.every(h=>csv.includes(h)));
 const route=fs.readFileSync(path.join(root,
  "app/api/raas-review-assignment-manifest/route.ts"),"utf8");
 assert.match(route,/\[=\+@-\]/);
 assert.match(route,/"N\/A","N\/A","N\/A"/);
});
test("iPhone review queue includes accessible grouped assignment and no auto approval action",()=>{
 const page=fs.readFileSync(path.join(root,"app/raas-review-queue/page.tsx"),"utf8");
 const component=fs.readFileSync(path.join(root,
  "app/raas-review-queue/RaasReviewAssignmentBoard.tsx"),"utf8");
 assert.match(page,/buildRaasReviewAssignmentPlan\(queue\)/);
 assert.match(page,/<RaasReviewAssignmentBoard plan=\{assignmentPlan\} sourceGates=\{sourceGates\}\/>/);
 assert.match(component,/data-raas-review-assignment-board/);
 assert.match(component,/Download all/);
 assert.match(component,/Filter RAAS external review assignments by priority/);
 assert.match(component,/sourceFingerprint/);
 assert.match(component,/no certified scores or FDA predictions/);
 assert.doesNotMatch(component,/onClick=\{[^}]*approve/);
 for(const [file,source] of [["page.tsx",page],["RaasReviewAssignmentBoard.tsx",component]]){
  const parsed=ts.transpileModule(source,{
   fileName:file,reportDiagnostics:true,compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX
   }
  });
  assert.equal((parsed.diagnostics||[]).filter(d=>
   d.category===ts.DiagnosticCategory.Error).length,0);
 }
});
