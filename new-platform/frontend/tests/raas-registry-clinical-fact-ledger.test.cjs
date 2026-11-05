"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const registry=require("../public/raas-registry-evidence-index.json");
const {buildRaasRegistryClinicalFactLedger}=
 require("../lib/raas-registry-clinical-fact-ledger.ts");
const facts=buildRaasRegistryClinicalFactLedger(registry);

test("entire ClinicalTrials.gov research index maps to research-only raw source facts",()=>{
 assert.equal(facts.scope,"RAAS_EXACT_NCT_REGISTRY_SOURCE_FACTS_UNGRADED");
 assert.equal(facts.registryNcts,762);
 assert.equal(facts.registryPostedResults,337);
 assert.ok(facts.trialsWithLeads>300);
 assert.equal(facts.totalSourceFacts,facts.facts.length);
 assert.ok(facts.rawNumericFacts>150,"Expected raw numeric source measurements");
 assert.ok(facts.rawContrastFacts>0,"Expected primary outcome contrasts");
 assert.ok(facts.rawConfidenceIntervalFacts>0,"Expected primary confidence intervals");
 assert.ok(facts.rawSeriousEventAffectedRates>0,"Expected reported safety denominator rates");
 assert.equal(facts.independentlyValidatedMetricGrades,0);
 assert.equal(facts.approvedOverallRaasScores,0);
 assert.equal(facts.calibratedFdaPredictions,0);
});
test("each source clinical fact is attached only to the matching registry NCT/ticker and ungraded",()=>{
 const source=new Map(registry.records.map(x=>[x.nctId,x]));
 const ids=new Set();
 for(const fact of facts.facts){
  const original=source.get(fact.nctId);
  assert.ok(original,"No unknown NCT");
  assert.equal(fact.ticker,original.ticker);
  assert.equal(fact.sourceUrl,original.sourceUrl);
  assert.equal(fact.sourceHash,original.sourceHash);
  assert.equal(fact.sourceAsOf,registry.sourceAsOf);
  assert.match(fact.sourceDate,/^\d{4}-\d{2}-\d{2}$/);
  assert.ok(!ids.has(fact.id),"A fact was duplicated across the registry");
  ids.add(fact.id);
  assert.ok(fact.metricIds.length>0&&fact.metricIds.every(id=>
   id.startsWith(fact.candidateStage+"-")));
  assert.equal(fact.metricGrade,null);
  assert.equal(fact.approvedOverallRaasScore,null);
  assert.equal(fact.fdaProbability,null);
  if(fact.candidateStage==="post")assert.equal(original.postedResults,true);
  if(fact.measurementValue!==null)assert.ok(Number.isFinite(fact.measurementValue));
  if(fact.kind==="POSTED_SAE_AFFECTED_RATE_RAW_MEASUREMENT"){
   assert.ok(fact.measurementValue>=0&&fact.measurementValue<=100);
   assert.equal(fact.measurementUnit,"%");
  }
 }
 assert.equal(ids.size,facts.totalSourceFacts);
});
test("protocol-only entries never leak posted outcome effect observations",()=>{
 const byNct=new Map();
 for(const fact of facts.facts){
  const grouped=byNct.get(fact.nctId)??[];grouped.push(fact);
  byNct.set(fact.nctId,grouped);
 }
 for(const r of registry.records.filter(x=>!x.postedResults)){
  assert.ok((byNct.get(r.nctId)??[]).every(f=>
   f.candidateStage==="pre"&&f.kind==="REGISTERED_PHASE3_PROTOCOL"),
   "Protocol-only NCT cannot receive post-result evidence "+r.nctId);
 }
});
test("malformed source checksums and cross-NCT identity cannot be accepted",()=>{
 const bad={...registry,records:registry.records.map((r,i)=>
  i===0?{...r,sourceHash:"not-a-valid-source-hash"}:r)};
 assert.throws(()=>buildRaasRegistryClinicalFactLedger(bad),
  /RAAS_REGISTRY_INDEX_ROW_INVALID/);
 const duplicate={...registry,records:[...registry.records]};
 duplicate.records[1]={...duplicate.records[1],nctId:duplicate.records[0].nctId};
 assert.throws(()=>buildRaasRegistryClinicalFactLedger(duplicate),
  /RAAS_REGISTRY_INDEX_ROW_INVALID/);
});
test("original numerical source observations export with no fabricated metric-grade columns",async()=>{
 const {GET}=require("../app/api/raas-registry-clinical-facts/route.ts");
 const response=GET();
 assert.equal(response.status,200);
 assert.match(response.headers.get("content-type"),/text\/csv/);
 const csv=await response.text();
 assert.match(csv,/nctId,ticker,candidateStage,metricIds,kind/);
 assert.match(csv,/NCT\d{8}/);
 assert.equal(csv.split("\r\n").length-2,facts.totalSourceFacts);
 assert.doesNotMatch(csv,/metricGrade,approvedOverallRaasScore,fdaProbability/);
});
test("iPhone evidence backlog renders exact source facts and distinct filters without approvals",()=>{
 const page=read("app/raas-evidence-backlog/EvidenceBacklogClient.tsx");
 const factsUI=read("app/raas-evidence-backlog/TrialClinicalEvidenceFacts.tsx");
 for(const fragment of ["buildRaasRegistryClinicalFactLedger","TrialClinicalEvidenceFacts",
  "Filter extracted primary and safety observations","Export original clinical source facts"])
  assert.ok(page.includes(fragment),"Missing source facts linkage "+fragment);
 for(const fragment of ["data-raas-clinical-source-facts","data-raas-source-fact",
   "Source-reported numeric observation","Registry-posted results may appear after",
   "not independently confirmed readout stage"])
  assert.ok(factsUI.includes(fragment),"Missing raw fact content "+fragment);
 for(const [fileName,code] of [["EvidenceBacklogClient.tsx",page],
   ["TrialClinicalEvidenceFacts.tsx",factsUI]]){
  const transpiled=ts.transpileModule(code,{fileName,reportDiagnostics:true,
   compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
    jsx:ts.JsxEmit.ReactJSX}});
  assert.deepEqual((transpiled.diagnostics||[]).filter(x=>
   x.category===ts.DiagnosticCategory.Error),[]);
 }
});
