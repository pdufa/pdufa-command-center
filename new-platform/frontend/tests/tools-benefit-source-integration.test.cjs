"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
    jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file
);
const {benefitsFromPipeline}=require("../lib/benefit-research-source.ts");
const {parseBenefitFeed}=require("../lib/benefit-assessments.ts");
const empty={schemaVersion:1,sourceAsOf:null,records:[]};
const core={nctId:"NCT12345678",ticker:"EXM",company:"Example",
 drug:"Example Therapy",indication:"Example indication",
 sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",poolStatus:"EXACT_MATCH",
 postPhase3Evidence:"REGISTRY_COMPLETED",qualification:"NEEDS_REVIEW",
 reasons:[],censusStatus:"COMPLETED",capUsd:400000000,capAsOf:"2026-10-20"};
const primary={
 value:12000,status:"VERIFIED",sourceUrl:"https://example.org/primary",
 sourceDate:"2026-10-20",method:"Explicit, sourced U.S. population estimate",
 reason:"Documented exact-indication population",confidence:"HIGH"};
const withFact=(update={})=>({...core,commercialAssessment:{
 nctId:core.nctId,ticker:core.ticker,indication:core.indication,
 fields:{eligibleUsPatients:{...primary,...update}}}});
const advantage={id:"reviewed-a",assessment:1,rank:1,title:"Verified comparative result",
 comparator:"Relevant standard of care",comparison:"Prespecified endpoint +4 pp",
 sourceUrl:"https://example.org/comparator",sourceDate:"2026-10-20",
 method:"Direct randomized comparator",confidence:"MODERATE",status:"VERIFIED"};
test("canonical source VERIFIED evidence automatically fills original #1 benefit field",()=>{
 const out=benefitsFromPipeline([withFact()],"2026-10-31",empty);
 assert.equal(out.records.length,1);
 const fact=out.records[0].facts.eligibleUsPatients;
 assert.equal(fact.status,"VERIFIED");
 assert.equal(fact.value,"12,000");
 assert.equal(fact.sourceUrl,primary.sourceUrl);
 assert.equal(fact.sourceDate,"2026-10-20");
 assert.deepEqual(out.records[0].advantages,[]);
});
test("MODELED evidence remains clearly marked as model, never verified",()=>{
 const out=benefitsFromPipeline([withFact({status:"MODELED"})],"2026-10-31",empty);
 assert.equal(out.records[0].facts.eligibleUsPatients.status,"MODELED");
});
test("unknown, unsupported, stale, identity-mismatched evidence never gets published",()=>{
 const invalidCases=[
  {...core,poolStatus:"REVIEW_REQUIRED",commercialAssessment:withFact().commercialAssessment},
  {...core,postPhase3Evidence:"NOT_VERIFIED",commercialAssessment:withFact().commercialAssessment},
  withFact({sourceUrl:"http://insecure.example/estimate"}),
  withFact({sourceDate:"2026-12-01"}),
  withFact({method:""}),
  withFact({confidence:"UNKNOWN"}),
  {...core,commercialAssessment:{...withFact().commercialAssessment,nctId:"NCT87654321"}},
 ];
 for(const row of invalidCases){
  const out=benefitsFromPipeline([row],"2026-10-31",empty);
  assert.equal(out.records.length,0,JSON.stringify(row).slice(0,180));
 }
});
test("reviewed advantages are never manufactured by inferred competitors",()=>{
 const out=benefitsFromPipeline([withFact()],"2026-10-31",empty);
 assert.equal(out.records[0].advantages.length,0);
 assert.deepEqual(out.records[0].overallAdvantages,[]);
});
test("independent reviewed rankings preserve their rank and source",()=>{
 const reviewed=parseBenefitFeed({schemaVersion:1,sourceAsOf:"2026-10-20",
  records:[{nctId:core.nctId,ticker:core.ticker,drug:core.drug,indication:core.indication,
   facts:{},advantages:[advantage],overallAdvantages:[advantage]}]});
 const out=benefitsFromPipeline([withFact()],"2026-10-31",reviewed);
 assert.equal(out.records.length,1);
 assert.equal(out.records[0].advantages.length,1);
 assert.equal(out.records[0].overallAdvantages[0].id,advantage.id);
});
test("duplicate exact-program identities fail rather than double-count",()=>{
 assert.throws(()=>benefitsFromPipeline([withFact(),withFact()],"2026-10-31",empty),
  /BENEFIT_PIPELINE_DUPLICATE_IDENTITY/);
});
test("TOOLS benefit API fetches complete, version-consistent canonical Pipeline source, not static-only",()=>{
 const route=fs.readFileSync(path.join(__dirname,"../app/api/benefit-assessments/route.ts"),"utf8");
 assert.match(route,/loadCompleteResearch/);
 assert.match(route,/url\.searchParams\.set\("view","pipeline"\)/);
 assert.match(route,/benefitsFromPipeline\(complete\.rows/);
 assert.match(route,/return response\.json\(\)/);
 assert.match(route,/status:503/);
 assert.doesNotMatch(route,/sourceAsOf:null,records:\[\]/);
});
