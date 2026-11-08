"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const registry=require("../public/raas-registry-evidence-index.json");
const reviews=require("../data/raas-reviewed-metric-assessments.json");
const {buildTrialMetricReviewDossier}=require("../lib/raas-trial-metric-review-dossier.ts");
const {buildTrialEvidenceBacklog}=require("../lib/raas-trial-evidence-backlog.ts");
const backlog=buildTrialEvidenceBacklog(registry);
const byId=new Map(registry.records.map(r=>[r.nctId,r]));

test("762 exact NCT identities remain covered, no invented RAAS score",()=>{
 assert.equal(backlog.totalTrials,762);
 assert.equal(backlog.postedResults,337);
 assert.equal(backlog.independentReviewedMetrics,0);
 assert.equal(backlog.approvedScores,0);
 assert.equal(backlog.calibratedFdaPredictions,0);
 assert.equal(registry.summary.researchNcts,762);
});
test("every tested exact-trial research dossier presents 30 TOP plus 30 BOTTOM, all unapproved",()=>{
 const exemplars=[
  registry.records[0],
  registry.records.find(x=>x.postedResults),
  registry.records.find(x=>!x.postedResults),
  byId.get("NCT05208047"),
  byId.get(reviews.records[0].nctId),
  registry.records.find(x=>backlog.items.find(b=>b.nctId===x.nctId)?.stage==="unverified")
 ].filter(Boolean);
 assert.ok(exemplars.length>=5);
 for(const row of exemplars){
  const dossier=buildTrialMetricReviewDossier(registry,row.nctId,row.ticker);
  assert.ok(dossier,"Could not build exact NCT dossier "+row.nctId);
  assert.equal(dossier.scope,"RAAS_EXACT_NCT_60_METRIC_REVIEW_WORKSPACE_UNAPPROVED");
  assert.equal(dossier.trial.nctId,row.nctId);
  assert.equal(dossier.trial.ticker,row.ticker);
  assert.equal(dossier.trial.sourceHash,row.sourceHash);
  assert.equal(dossier.approvedScores,0);
  assert.equal(dossier.certifiedMetrics,0);
  assert.equal(dossier.fdaPassCrlExtensionProbability,null);
  for(const stage of ["pre","post"]){
   const x=dossier.perStage[stage];
   assert.equal(x.categories.length,6);
   assert.equal(x.categories.reduce((s,c)=>s+c.weight,0),100);
   const metrics=x.categories.flatMap(c=>c.metrics);
   assert.equal(metrics.length,30);
   assert.equal(new Set(metrics.map(m=>m.metricId)).size,30);
   assert.equal(x.independentlyAuthenticatedReviews,0);
   assert.equal(x.approvedFullStageScore,null);
   assert.equal(x.reviewCount,metrics.filter(m=>!!m.provisionalReview).length);
   assert.equal(x.missingMetricCount,30-x.reviewCount);
   for(const m of metrics){
    assert.ok(m.metricId.startsWith(stage+"-"));
    assert.equal(m.authenticatedHumanSignoff,false);
    assert.equal(m.approvedRaasGrade,null);
    assert.equal(m.missingRequiredIndependentEvidence,true);
    assert.ok(m.requiredEvidence.length>15);
    assert.ok(m.criticalRisk.length>15);
    assert.equal(m.registryLeadCount,m.registryLeads.length);
    for(const fact of m.registryLeads){
     assert.equal(fact.nctId,row.nctId);
     assert.equal(fact.ticker,row.ticker);
     assert.equal(fact.sourceHash,row.sourceHash);
     assert.equal(fact.candidateStage,stage);
     assert.ok(fact.metricIds.includes(m.metricId));
     assert.equal(fact.metricGrade,null);
    }
   }
  }
 }
});
test("source-linked provisional reviews exist only for exact mapped program, stage, and metric",()=>{
 const seed=reviews.records[0],dossier=
  buildTrialMetricReviewDossier(registry,seed.nctId,seed.ticker);
 assert.ok(dossier);
 if(!dossier.ambiguousProgramReviews){
  const source=dossier.perStage[seed.stage].categories.flatMap(c=>c.metrics)
   .find(m=>m.metricId===seed.metricId);
  assert.equal(source.provisionalReview.drug,seed.drug);
  assert.equal(source.provisionalReview.indication,seed.indication);
  assert.equal(source.provisionalReview.sourceUrl,seed.sourceUrl);
  assert.equal(source.provisionalReview.authenticatedHumanSignoff,undefined);
  assert.equal(source.authenticatedHumanSignoff,false);
  assert.equal(source.approvedRaasGrade,null);
 }
 const other=registry.records.find(x=>x.nctId!==seed.nctId);
 const otherDossier=buildTrialMetricReviewDossier(registry,other.nctId,other.ticker);
 assert.ok(otherDossier.perStage.pre.categories.flatMap(c=>c.metrics)
  .every(m=>!m.provisionalReview||m.provisionalReview.drug!==seed.drug||
   m.provisionalReview.indication!==seed.indication||other.nctId!==seed.nctId));
});
test("protocol-only trials cannot acquire posted BOTTOM primary or SAE research leads",()=>{
 const row=registry.records.find(x=>!x.postedResults);
 const dossier=buildTrialMetricReviewDossier(registry,row.nctId,row.ticker);
 assert.equal(dossier.perStage.post.rawSourceFactCount,0);
 assert.equal(dossier.perStage.post.withRegistryLeads,0);
 assert.equal(dossier.perStage.post.categories.flatMap(c=>c.metrics)
  .reduce((s,m)=>s+m.registryLeadCount,0),0);
});
test("wrong ticker, malformed NCT, or missing trial never substitutes another program",()=>{
 const row=registry.records[0];
 assert.equal(buildTrialMetricReviewDossier(registry,row.nctId,"WRONGTICKER"),null);
 assert.equal(buildTrialMetricReviewDossier(registry,"NCTnotvalid",row.ticker),null);
 assert.equal(buildTrialMetricReviewDossier(registry,"NCT99999999","XXXX"),null);
 const bad={...registry,records:registry.records.map((r,i)=>
  i===0?{...r,sourceHash:"wrong"}:r)};
 assert.throws(()=>buildTrialMetricReviewDossier(bad,row.nctId,row.ticker),
  /RAAS_REGISTRY_INDEX_ROW_INVALID/);
});
test("exact-trial download route is structurally guarded and preserves all 60 metrics",()=>{
 const {GET}=require("../app/api/raas-trial-review-dossier/route.ts");
 const row=registry.records[0],base="https://example.com/api/raas-trial-review-dossier";
 return Promise.all([
  GET(new Request(base+"?nctId="+row.nctId+"&ticker="+row.ticker)).text()
   .then(body=>{
    const data=JSON.parse(body);
    assert.equal(data.trial.nctId,row.nctId);
    assert.equal(data.perStage.pre.categories.flatMap(x=>x.metrics).length,30);
    assert.equal(data.perStage.post.categories.flatMap(x=>x.metrics).length,30);
    assert.equal(data.certifiedMetrics,0);
   }),
  Promise.resolve(GET(new Request(base+"?nctId="+row.nctId+"&ticker=WRONG")))
   .then(r=>assert.equal(r.status,404)),
  Promise.resolve(GET(new Request(base+"?nctId=abc&ticker="+row.ticker)))
   .then(r=>assert.equal(r.status,400))
 ]);
});
test("trial UI opens source evidence to the right, with separate stage and review filters",()=>{
 const files=[
  "app/raas-trial-review/page.tsx",
  "app/raas-trial-review/ReviewDossierClient.tsx",
  "app/raas-evidence-backlog/EvidenceBacklogClient.tsx"
 ];
 const code=files.map(f=>fs.readFileSync(path.join(root,f),"utf8"));
 assert.match(code[0],/data-raas-trial-metric-review-workspace/);
 assert.match(code[1],/data-raas-selected-metric-review/);
 assert.match(code[1],/Select TOP or BOTTOM 30-metric worklist/);
 assert.match(code[1],/Authenticated external human signoff: none/);
 assert.match(code[1],/data-raas-download-exact-review-dossier/);
 assert.match(code[2],/data-raas-open-60-metric-review/);
 assert.match(fs.readFileSync(path.join(root,
  "app/raas-trial-review/ReviewDossierClient.module.css"),"utf8"),
  /grid-template-columns:minmax\(0,1fr\) minmax\(0,1\.15fr\)/);
 for(const [i,source] of code.entries()){
  const result=ts.transpileModule(source,{
   fileName:files[i],reportDiagnostics:true,compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX
   }});
  assert.deepEqual((result.diagnostics||[]).filter(x=>
   x.category===ts.DiagnosticCategory.Error),[]);
 }
});
