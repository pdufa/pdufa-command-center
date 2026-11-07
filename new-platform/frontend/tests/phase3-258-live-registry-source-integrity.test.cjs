"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true
 }}).outputText,file);
const {activePhase3Cohorts}=require("../lib/phase3-active-cohorts.ts");
const {loadLivePhase3Registry}=require("../app/api/phase3-live-registry-backfill/route.ts");
const exportSource=fs.readFileSync(path.join(root,"app/api/phase3-unified-190-columns/route.ts"),"utf8");

test("258 active NCTs are unique, independently identifiable, and exclude the historic archive",()=>{
 const rows=[...activePhase3Cohorts.pre,...activePhase3Cohorts.post];
 assert.equal(rows.length,258);
 assert.equal(new Set(rows.map(r=>r.nctId)).size,258);
 assert.equal(activePhase3Cohorts.pre.length,229);
 assert.equal(activePhase3Cohorts.post.length,29);
});
test("live registry selection is exact-NCT scoped, with sourced eligibility, PRO, subgroup and site metadata",async()=>{
 const active=[...activePhase3Cohorts.pre,...activePhase3Cohorts.post];
 const nct=active[0].nctId,original=global.fetch;
 const calls=[];
 global.fetch=async (address)=>{
  const u=new URL(address);
  assert.equal(u.hostname,"clinicaltrials.gov");
  assert.equal(u.pathname,"/api/v2/studies");
  assert.equal(u.searchParams.get("filter.ids"),nct);
  calls.push(address);
  return new Response(JSON.stringify({studies:[{
   protocolSection:{
    identificationModule:{nctId:nct},
    statusModule:{overallStatus:"RECRUITING",studyLastPostDateStruct:{date:"2026-11-05"}},
    designModule:{phases:["PHASE3"],enrollmentInfo:{count:100,type:"ESTIMATED"},
     designInfo:{allocation:"RANDOMIZED",maskingInfo:{masking:"DOUBLE"}}},
    armsInterventionsModule:{interventions:[{name:"Study drug",type:"DRUG"},{name:"Placebo",type:"DRUG"}],
     armGroups:[{type:"PLACEBO_COMPARATOR",label:"Placebo arm"}]},
    outcomesModule:{primaryOutcomes:[{measure:"Change from baseline",timeFrame:"Week 16"}],
     secondaryOutcomes:[{measure:"Patient reported quality of life"},{measure:"Response by age subgroup"}]},
    eligibilityModule:{eligibilityCriteria:"Inclusion: age 18+; exclusion: active infection",
     minimumAge:"18 Years",maximumAge:"80 Years",sex:"ALL"},
    contactsLocationsModule:{locations:[
     {country:"United States"},{country:"Canada"},{country:"United States"}]}
   },hasResults:false
  }]}),{status:200,headers:{"Content-Type":"application/json"}});
 };
 try{
  const a=await loadLivePhase3Registry([nct]);
  assert.equal(a.failedBatches,0);
  assert.equal(a.rows.length,1);
  assert.equal(calls.length,1);
  assert.equal(a.rows[0].original.nctId,nct);
  const x=a.rows[0].registry;
  assert.equal(x.nctId,nct);
  assert.match(x.eligibilityCriteria,/active infection/);
  assert.equal(x.eligibilityAges,"18 Years–80 Years");
  assert.equal(x.siteCount,3);
  assert.equal(x.countries,"Canada | United States");
  assert.match(x.patientReportedOutcomeTitles,/quality of life/);
  assert.match(x.subgroupOutcomeTitles,/age subgroup/);
  assert.equal(x.registryResultsPosted,false);
  assert.equal(x.postedPrimaryOutcomeCount,0);
  await assert.rejects(loadLivePhase3Registry([nct,nct]),/integrity/);
  await assert.rejects(loadLivePhase3Registry(["NCT00000000"]),/integrity/);
 }finally{global.fetch=original;}
});
test("190-field export reuses exact subset and labels protocol observations without inferred scores",()=>{
 assert.match(exportSource,/const needed=ledger\.rows\.filter\(included\)\.map\(r=>r\.nctId\)/);
 assert.match(exportSource,/loadLivePhase3Registry\(needed\)/);
 for(const question of [6,18,19,26]){
  assert.match(exportSource,new RegExp("q\\.number==="+question+"&&\\(?liveRegistry\\."));
 }
 assert.match(exportSource,/const fact=\(description:string\)=>\["SOURCE_FACT_ONLY","","",description,url\]/);
 assert.match(exportSource,/HEADERS\.length!==190/);
});

test("dated official SAP files and subgroup outcome labels increase documentary coverage, not clinical scores",()=>{
 const {phase3OnlineSourceFact}=require("../lib/phase3-online-source-evidence.ts");
 const {sourceObservation}=require("../lib/phase3-universal-questions.ts");
 const activeIds=[...activePhase3Cohorts.pre,...activePhase3Cohorts.post].map(r=>r.nctId);
 const sap=activeIds.filter(id=>phase3OnlineSourceFact(id,13)!==null);
 assert.equal(sap.length,10);
 for(const id of sap){
  for(const q of [13,14,15]){
   const observed=phase3OnlineSourceFact(id,q);
   assert.equal(observed.status,"SOURCE_FACT_ONLY");
   assert.match(observed.sourceUrl,new RegExp(id+"$"));
   assert.match(observed.description,/NOT been critically reviewed/);
  }
 }
 const subgroup=activeIds.filter(id=>sourceObservation(id,19)!==null);
 assert.equal(subgroup.length,2);
 for(const id of subgroup){
  const observed=sourceObservation(id,19);
  assert.match(observed.description,/no claim of subgroup effect/);
  assert.equal(observed.documentationScore,100);
  assert.match(observed.sourceUrl,new RegExp(id+"$"));
 }
});
