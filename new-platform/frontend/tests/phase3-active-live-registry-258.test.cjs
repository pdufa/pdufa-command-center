"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}}
).outputText,file);
const {loadLivePhase3Registry}=require("../app/api/phase3-live-registry-backfill/route.ts");
const {activePhase3Cohorts}=require("../lib/phase3-active-cohorts.ts");
const active=[...activePhase3Cohorts.pre,...activePhase3Cohorts.post].map(r=>r.nctId);
const study=(id)=>({
 protocolSection:{
  identificationModule:{nctId:id},
  statusModule:{overallStatus:"RECRUITING",studyLastPostDateStruct:{date:"2026-11-06"}},
  designModule:{phases:["PHASE3"],enrollmentInfo:{count:220,type:"ESTIMATED"},
   designInfo:{allocation:"RANDOMIZED",maskingInfo:{masking:"DOUBLE"}}},
  armsInterventionsModule:{interventions:[{type:"DRUG",name:"Active compound"},{type:"DRUG",name:"Placebo"}],
   armGroups:[{type:"PLACEBO_COMPARATOR",label:"Placebo"}]},
  outcomesModule:{primaryOutcomes:[{measure:"Treatment endpoint",timeFrame:"Week 12"}],
   secondaryOutcomes:[{measure:"Patient reported quality of life",timeFrame:"Week 12"}]},
  eligibilityModule:{eligibilityCriteria:"Inclusion: diagnosis confirmed; exclusion: unstable serious illness.",
   minimumAge:"18 Years",maximumAge:"80 Years",sex:"ALL"},
  contactsLocationsModule:{locations:[{country:"United States",city:"Boston"}]}
 }
});
test("official registry collection requests exactly 258 active NCTs and enriches eligibility and PRO facts",async()=>{
 const orig=global.fetch,seen=new Set(),calls=[];
 global.fetch=async url=>{
  const parsed=new URL(String(url)),ids=parsed.searchParams.get("filter.ids").split(",");
  calls.push(ids.length);
  ids.forEach(id=>{assert.ok(active.includes(id));assert.ok(!seen.has(id));seen.add(id);});
  return new Response(JSON.stringify({studies:ids.map(study)}),{status:200});
 };
 try{
  const data=await loadLivePhase3Registry(active);
  assert.equal(calls.length,11);
  assert.equal(seen.size,258);
  assert.equal(data.rows.length,258);
  assert.equal(data.failedBatches,0);
  assert.ok(data.rows.every(x=>x.registry!==null));
  assert.ok(data.rows.every(x=>x.registry.eligibilityAges==="18 Years–80 Years"));
  assert.ok(data.rows.every(x=>x.registry.siteCount===1));
  assert.ok(data.rows.every(x=>x.registry.patientReportedOutcomeTitles.includes("quality of life")));
 }finally{global.fetch=orig;}
});
test("duplicate and non-source NCTs are rejected before contacting external registry",async()=>{
 await assert.rejects(loadLivePhase3Registry([active[0],active[0]]),/integrity/);
 await assert.rejects(loadLivePhase3Registry(["NCT00000000"]),/integrity/);
});
test("both all-active 190 column export and coverage audit support opt-in source refresh",()=>{
 const exportSource=fs.readFileSync(require.resolve("../app/api/phase3-unified-190-columns/route.ts"),"utf8");
 const coverage=fs.readFileSync(require.resolve("../app/api/phase3-active-190-coverage/route.ts"),"utf8");
 const sheet=fs.readFileSync(require.resolve("../app/Phase3SourceOnlySheets.tsx"),"utf8");
 assert.match(exportSource,/loadLivePhase3Registry\(needed\)/);
 assert.match(exportSource,/live\.rows\.length!==needed\.length/);
 assert.match(exportSource,/liveRegistry\.eligibilityCriteria/);
 assert.match(exportSource,/liveRegistry\.patientReportedOutcomeTitles/);
 assert.match(exportSource,/liveRegistry\.participantFlowDiscontinuations/);
 assert.match(coverage,/live\?"&live=1":""/);
 assert.match(sheet,/phase3-unified-190-columns\?cohort=active&amp;live=1/);
});
