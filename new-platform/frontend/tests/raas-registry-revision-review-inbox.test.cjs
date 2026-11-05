"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const registry=require("../public/raas-registry-evidence-index.json");
const status=require("../data/raas-registry-evidence-change-status.json");
const history=require("../data/raas-registry-evidence-change-history.json");
const {buildRaasRegistryRevisionReviewInbox:build}=
 require("../lib/raas-registry-revision-review-inbox.ts");
const {buildRaasIndependentReviewQueue}=
 require("../lib/raas-independent-review-queue.ts");
const queue=buildRaasIndependentReviewQueue();
const external=queue.items.find(x=>x.metricId==="post-1-1");
assert.ok(external,"Expected an exact-NCT provisional post-1-1 source review for fixture");
const trial=registry.records.find(x=>x.nctId===external.nctId&&x.ticker===external.ticker);
assert.ok(trial,"Existing provisional source review must match exact registry ticker");
const t1="2027-01-02T01:00:00+00:00",t2="2027-01-03T01:00:00+00:00";
const alternate=(h)=>h[0]==="a"?"b".repeat(64):"a".repeat(64);
const fakeStatus=(events)=>({...status,sourceFetchFailed:0,
 auditState:"COMPLETE",recordedAt:"2027-01-04T01:00:00+00:00",
 latestSourceAsOf:registry.sourceAsOf,totalRetainedHistoricalEvents:events.length});
const makeEvent=(id,observedAt,newHash=trial.sourceHash,previousHash=alternate(newHash))=>({
 eventId:id.repeat(64),observedAt,nctId:trial.nctId,
 ticker:trial.ticker,sourceUrl:trial.sourceUrl,
 previousSourceHash:previousHash,newSourceHash:newHash,
 changeCategories:["PRIMARY_OUTCOME_RESULTS_CHANGED"],
 candidateResearchMetricIds:["post-1-1","post-1-3"],
 reviewFlag:"CLINICAL_OR_DESIGN_REVIEW_REQUIRED",
 approvedRaasScore:null,calibratedFdaProbability:null
});
const fresh=(events)=>({...history,schemaVersion:1,
 scope:"RAAS_EXACT_NCT_REGISTRY_SOURCE_CHANGE_HISTORY_UNGRADED",events});

test("current published history is auditable without claiming zero means no collection",()=>{
 const inbox=build(history,status,registry,queue);
 assert.equal(inbox.auditState,status.auditState);
 assert.equal(inbox.historyEvents,history.events.length);
 assert.equal(inbox.independentlyApprovedMetrics,0);
 assert.equal(inbox.approvedRaasScores,0);
 assert.equal(inbox.calibratedFdaForecasts,0);
 assert.equal(inbox.tasks.length,inbox.uniqueTrialMetricTasks);
 assert.equal(inbox.registryAsOf,registry.sourceAsOf);
});

test("source revision becomes two specific candidate research metrics, not another grade",()=>{
 const events=[makeEvent("d",t1)];
 const inbox=build(fresh(events),fakeStatus(events),registry,queue);
 assert.equal(inbox.historyEvents,1);
 assert.equal(inbox.revisionReviewEvents,1);
 assert.equal(inbox.candidateMetricAssignments,2);
 assert.equal(inbox.uniqueTrialMetricTasks,2);
 assert.equal(inbox.uniqueNcts,1);
 assert.equal(inbox.existingProvisionalReviewPairs,1);
 assert.equal(inbox.supersededOrUnsyncedTasks,0);
 const metric=inbox.tasks.find(x=>x.metricId==="post-1-1");
 assert.equal(metric.nctId,trial.nctId);
 assert.equal(metric.ticker,trial.ticker);
 assert.equal(metric.currentRegistryHash,trial.sourceHash);
 assert.equal(metric.newSourceHash,trial.sourceHash);
 assert.equal(metric.revisionCountForMetric,1);
 assert.equal(metric.provisionalResearchIdentity,"EXACT_NCT_METRIC_REVIEW_EXISTS");
 assert.equal(metric.matchingExistingProvisionalResearchReviews,1);
 assert.equal(metric.metricStage,"post");
 assert.equal(metric.state,"REQUIRES_INDEPENDENT_EVIDENCE_REASSESSMENT");
 assert.equal(metric.approvedRaasMetricGrade,null);
 assert.equal(metric.approvedRaasScore,null);
 assert.equal(metric.calibratedFdaForecast,null);
});

test("two sequential revisions remain in history, one actionable latest task per exact metric",()=>{
 const prior=alternate(trial.sourceHash),first=["a","b","c"].find(x=>!([prior[0],trial.sourceHash[0]].includes(x))).repeat(64);
 const events=[
  makeEvent("d",t1,first,prior),
  makeEvent("e",t2,trial.sourceHash,first)
 ];
 const inbox=build(fresh(events),fakeStatus(events),registry,queue);
 assert.equal(inbox.historyEvents,2);
 assert.equal(inbox.revisionReviewEvents,2);
 assert.equal(inbox.candidateMetricAssignments,4);
 assert.equal(inbox.uniqueTrialMetricTasks,2);
 assert.equal(inbox.supersededOrUnsyncedTasks,0);
 for(const task of inbox.tasks){
  assert.equal(task.revisionCountForMetric,2);
  assert.equal(task.firstObservedAt,t1);
  assert.equal(task.observedAt,t2);
  assert.equal(task.newSourceHash,trial.sourceHash);
  assert.equal(task.previousSourceHash,first);
 }
 const versionMismatch=build(fresh(events.slice(0,1)),
  fakeStatus(events.slice(0,1)),registry,queue);
 assert.equal(versionMismatch.supersededOrUnsyncedTasks,2);
 assert.equal(versionMismatch.tasks[0].sourceMatch,
  "SOURCE_VERSION_SUPERSEDED_OR_UNSYNCED");
});

test("invalid metrics, stale identities, forged approval or duplicate event IDs fail closed",()=>{
 const base=makeEvent("d",t1);
 const patches=[
  {ticker:"WRONG"},
  {sourceUrl:"https://clinicaltrials.gov/study/NCT99999999"},
  {approvedRaasScore:75},
  {candidateResearchMetricIds:["post-1-1","pre-1-2"]},
  {candidateResearchMetricIds:["post-1-1","post-1-1"]},
  {reviewFlag:"OTHER_OFFICIAL_REGISTRY_UPDATE"},
  {previousSourceHash:trial.sourceHash}
 ];
 for(const patch of patches){
  const list=[{...base,...patch}];
  assert.throws(()=>build(fresh(list),fakeStatus(list),registry,queue),
   /RAAS_REVISION_INBOX_/);
 }
 const double=[base,{...base}];
 assert.throws(()=>build(fresh(double),fakeStatus(double),registry,queue),
  /RAAS_REVISION_INBOX_/);
 const reverse=[makeEvent("d",t2),makeEvent("e",t1)];
 assert.throws(()=>build(fresh(reverse),fakeStatus(reverse),registry,queue),
  /RAAS_REVISION_INBOX_NONMONOTONIC_HISTORY/);
});

test("administrative-only update never manufactures metric alerts",()=>{
 const e=makeEvent("d",t1);
 e.changeCategories=["REGISTRY_LAST_UPDATED_DATE_CHANGED"];
 e.candidateResearchMetricIds=[];
 e.reviewFlag="OTHER_OFFICIAL_REGISTRY_UPDATE";
 const xs=[e],inbox=build(fresh(xs),fakeStatus(xs),registry,queue);
 assert.equal(inbox.historyEvents,1);
 assert.equal(inbox.revisionReviewEvents,0);
 assert.equal(inbox.candidateMetricAssignments,0);
 assert.equal(inbox.uniqueTrialMetricTasks,0);
});

test("CSV exports research assignments without score columns interpreted as grades",async()=>{
 const {GET}=require("../app/api/raas-registry-revision-review-tasks/route.ts");
 const r=GET();
 assert.equal(r.status,200);
 assert.match(r.headers.get("Cache-Control"),/no-store/);
 const csv=await r.text();
 assert.ok(csv.includes("nctId,ticker,metricId,metricName,metricStage"));
 assert.ok(csv.includes("approvedRaasMetricGrade,approvedRaasScore,calibratedFdaForecast"));
 const route=fs.readFileSync(path.join(root,
  "app/api/raas-registry-revision-review-tasks/route.ts"),"utf8");
 assert.match(route,/\^\\s\*\[=\+@-\]/);
 assert.match(route,/"N\/A","N\/A","N\/A"/);
});

test("review queue, source history and trial workbench provide two-way exact metric links",()=>{
 const paths=[
  "app/raas-review-queue/page.tsx",
  "app/raas-review-queue/RegistryRevisionInboxClient.tsx",
  "app/raas-review-queue/ReviewQueueClient.tsx",
  "app/raas-evidence-changes/page.tsx",
  "app/raas-trial-review/page.tsx",
  "app/raas-trial-review/ReviewDossierClient.tsx"
 ];
 const sources=paths.map(p=>fs.readFileSync(path.join(root,p),"utf8"));
 assert.match(sources[0],/data-raas-review-state="NOT_VALIDATED"/);
 assert.match(sources[0],/RegistryRevisionInboxClient/);
 assert.match(sources[1],/data-raas-registry-metric-review-inbox/);
 assert.match(sources[1],/data-raas-open-exact-alert-metric/);
 assert.match(sources[1],/metricId:task.metricId/);
 assert.match(sources[1],/sourceMatch/);
 assert.match(sources[2],/initialMetricId/);
 assert.match(sources[3],/Open all this NCT/);
 assert.match(sources[4],/initialMetricId=\{initialMetricId\}/);
 assert.match(sources[5],/initialMetricId.startsWith\("post-"\)/);
 assert.match(sources[5],/category.metrics.some/);
 for(const [i,src] of sources.entries()){
  const compiled=ts.transpileModule(src,{
   fileName:paths[i],reportDiagnostics:true,compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX
   }});
  assert.equal((compiled.diagnostics||[]).filter(x=>
   x.category===ts.DiagnosticCategory.Error).length,0);
 }
});
