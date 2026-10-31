"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {normalizeRegistryStudy}=require("../lib/pipeline-live-registry.ts");
const id="NCT12345678",asOf="2026-10-31T21:00:00.000Z";
const sample={
 protocolSection:{
  identificationModule:{nctId:id,briefTitle:"Randomized Investigational Therapy"},
  statusModule:{overallStatus:"COMPLETED",primaryCompletionDateStruct:{date:"2024-02-19"},lastUpdatePostDateStruct:{date:"2026-09-01"}},
  designModule:{phases:["PHASE2","PHASE3"],enrollmentInfo:{count:419}},
  sponsorCollaboratorsModule:{leadSponsor:{name:"Example Trial Sponsor"}},
  conditionsModule:{conditions:["Disease X","Disease Y"]},
  armsInterventionsModule:{interventions:[{name:"Example Investigational Drug"},{name:"Active comparator"}]},
 },hasResults:true,
};
test("current registry info is source dated, exact-NCT and NEVER a qualified Pipeline candidate",()=>{
 const out=normalizeRegistryStudy(sample,id,asOf);
 assert.equal(out.nctId,id);assert.equal(out.phase3Registered,true);
 assert.equal(out.registryAssessment,"PHASE3_COMPLETED_REGISTRY_ONLY");
 assert.equal(out.qualification,"NEEDS_REVIEW");assert.equal(out.enrollment,419);
 assert.equal(out.resultsPosted,true);assert.equal(out.sourceUrl,"https://clinicaltrials.gov/study/"+id);
 assert.deepEqual(out.phases,["PHASE2","PHASE3"]);assert.equal(out.lastUpdatePosted,"2026-09-01");
 assert.ok(out.remainingChecks.some(x=>x.includes("market cap")));
});
test("registration status and phase never imply pivotal results or approval",()=>{
 for(const [phases,status,expected] of [
   [["PHASE3"],"RECRUITING","PHASE3_OTHER_STATUS"],
   [["PHASE2"],"COMPLETED","PHASE3_NOT_ESTABLISHED"],
   [undefined,"COMPLETED","PHASE3_NOT_ESTABLISHED"],
   [["PHASE3"],"TERMINATED","PHASE3_OTHER_STATUS"]
 ]){
  const result=normalizeRegistryStudy({...sample,protocolSection:{...sample.protocolSection,
   designModule:{phases},statusModule:{overallStatus:status}}},id,asOf);
  assert.equal(result.registryAssessment,expected);
  assert.equal(result.qualification,"NEEDS_REVIEW");
 }
});
test("mismatched NCT, malformed dates, false source results and poisoned arrays fail closed",()=>{
 assert.throws(()=>normalizeRegistryStudy(sample,"NCT99999999",asOf),/mismatch/);
 assert.throws(()=>normalizeRegistryStudy(sample,id,"not-a-timestamp"),/timestamp/);
 const res=normalizeRegistryStudy({...sample,hasResults:false,protocolSection:{...sample.protocolSection,
  statusModule:{overallStatus:"COMPLETED",lastUpdatePostDateStruct:{date:"2026-02-31"}},
  conditionsModule:{conditions:["Disease X","Disease X",false,null]},
  designModule:{phases:["PHASE3"],enrollmentInfo:{count:-1}}
 }},id,asOf);
 assert.equal(res.resultsPosted,false);assert.equal(res.lastUpdatePosted,null);
 assert.equal(res.enrollment,null);assert.deepEqual(res.conditions,["Disease X"]);
});
test("authenticated per-NCT API only looks up pinned census and does not proxy untrusted URLs",()=>{
 const source=fs.readFileSync(path.join(__dirname,"../app/api/phase3-trial/route.ts"),"utf8");
 const ui=fs.readFileSync(path.join(__dirname,"../app/PipelineFourViews.tsx"),"utf8");
 assert.ok(source.includes("hasSession(req.cookies.get(COOKIE_NAME)?.value)"));
 assert.ok(source.includes('parsePhase3CensusCsv(csv)'));
 assert.ok(source.includes('corpus.rows.some(r=>r.nctId===nct)'));
 assert.ok(source.includes('redirect:"manual"'));
 assert.ok(source.includes('AbortSignal.timeout(13000)'));
 assert.ok(source.includes('Cache-Control":"private, no-store"'));
 assert.ok(ui.includes("<LiveRegistryReview nctId={row.nctId}/>"));
});
