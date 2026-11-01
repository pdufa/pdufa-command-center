"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
  mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,file);
const {
 verifiedToolPool,buildToolsOpeningInventory,buildToolsResults,
 toolsContextualDesignationCounts,toolsDesignationTotals
}=require("../lib/tools-pool-inventory.ts");
const {restrictedToolsSnapshot}=require("../lib/tools-restricted-scope.ts");
const trial=(nct,stage,ticker="AAA")=>({id:"TRIAL|"+nct,ticker,stage,company:"Company",drug:"Drug",indication:"Disease"});
const pool=[
 trial("NCT00000001","Phase 3"),
 trial("NCT00000002","Phase 3"),
 trial("NCT00000003","Phase 2"),
 trial("NCT00000004","Phase 3 Results"),
 trial("NCT00000005","Phase 3","OTHER"),
 {id:"RESULT|a",ticker:"AAA",stage:"Phase 3 Results"}
];
const snapshot=verifiedToolPool({
 pipeline:pool,asOf:"2026-11-01T10:00:00Z",
 sourceHealth:{state:"PARTIAL",clinicalRows:5,regulatoryRows:1,pipelineSourceParity:{exactPrograms:6}}
});
const review=(nct,ticker="AAA",status="REGISTRY_COMPLETED",cap=500000000)=>({
 nctId:nct,ticker,company:"Company",drug:"Drug",indication:"Disease",
 sourceUrl:"https://clinicaltrials.gov/study/"+nct,censusStatus:"COMPLETED",
 capUsd:cap,capAsOf:"2026-10-26T00:00:00Z",
 poolStatus:"EXACT_MATCH",postPhase3Evidence:status,
 qualification:"NEEDS_REVIEW",reasons:[],timeline:{}
});
const reviews=[
 review("NCT00000001"),
 review("NCT00000002","AAA","REGISTRY_COMPLETED",11000000000),
 review("NCT00000003"), // Phase 2 in POOL: never pass post-Phase-3 scope
 review("NCT00000004"),
 review("NCT00000005","OTHER","FINAL_READOUT_NEEDS_PROOF"),
 review("NCT00000006") // not in POOL
];
const granted={status:"GRANTED",verification:"SOURCE_RECORDED",source:"https://www.fda.gov/one",designationDate:"",checkedAt:"",note:""};
const designation={
 availableKeys:{fast_track:true,orphan_drug:true},
 programs:{
  "AAA|PROGRAM":{eventKey:"AAA|PROGRAM",ticker:"AAA",drug:"Drug",indication:"Disease",
   designations:{fast_track:granted,orphan_drug:granted}}
 },
 trialEvents:{
  NCT00000001:["AAA|PROGRAM"],NCT00000002:["AAA|PROGRAM"],
  NCT00000004:["AAA|PROGRAM"],NCT00000005:["AAA|PROGRAM"]
 }
};
test("Phase and FDA share ONE $300M–$10B completed Phase 3 research subset",()=>{
 const {snapshot:restricted,scope}=restrictedToolsSnapshot(snapshot,reviews,"2026-10-26T12:21:15.972309+00:00");
 assert.equal(scope.originalPoolTrials,5);
 assert.equal(scope.screenedTrials,2);
 assert.equal(scope.qualification,"NOT_VERIFIED");
 assert.deepEqual(restricted.poolRows.map(r=>r.id),["TRIAL|NCT00000001","TRIAL|NCT00000004"]);
 assert.equal(restricted.stageStats.stages["Phase 3"].trials,1);
 assert.equal(restricted.stageStats.stages["Phase 3 Results"].trials,1);
 assert.equal(restricted.stageStats.stages["Phase 2"].trials,0);
 const opening=buildToolsOpeningInventory(restricted,0,50);
 assert.equal(opening.total,2);
 const counts=toolsContextualDesignationCounts(restricted.poolRows,designation,[],"");
 assert.equal(counts.fast_track.matchingTrials,2,"Designation cannot see the excluded Phase 3 or Phase 2 NCTs");
 const totals=toolsDesignationTotals(restricted.poolRows,designation);
 assert.equal(totals.fast_track.linkedNcts,2);
 const phase=buildToolsResults(restricted,designation,["Phase 3"],[],"",0,50);
 assert.equal(phase.total,1);
 const fda=buildToolsResults(restricted,designation,[],["fast_track"],"",0,50);
 assert.equal(fda.total,2);
 const both=buildToolsResults(restricted,designation,["Phase 3"],["fast_track"],"",0,50);
 assert.equal(both.total,1);
 assert.deepEqual(both.rows.map(r=>r.id),["TRIAL|NCT00000001"]);
 const phase2=buildToolsResults(restricted,designation,["Phase 2"],[],"",0,50);
 assert.equal(phase2.total,0,"No unrestricted Phase 2 leakage into restricted counts");
});
test("Missing or invalid restriction census fails closed, not unrestricted fallback",()=>{
 assert.throws(()=>restrictedToolsSnapshot(snapshot,[],"2026-10-26"),/RESTRICTED_PIPELINE_CENSUS_UNAVAILABLE/);
 assert.throws(()=>restrictedToolsSnapshot(snapshot,reviews,"invalid"),/RESTRICTED_PIPELINE_CENSUS_UNAVAILABLE/);
});
test("Production TOOLS route builds restricted snapshot before every Phase/FDA facet and CSV",()=>{
 const route=fs.readFileSync(require("node:path").join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
 const scope=route.indexOf("restrictedToolsSnapshot(");
 const designation=route.indexOf("toolsDesignationTotals(inventory.poolRows,index)");
 const contextual=route.indexOf("toolsContextualDesignationCounts(");
 const rows=route.indexOf("buildToolsResults(inventory,index,selectedStages,selectedDesignations");
 const csv=route.indexOf("filterToolTrials(inventory.poolRows,selectedStages,matches,query)");
 assert.ok([scope,designation,contextual,rows,csv].every(v=>v>=0));
 assert.ok(scope<designation&&scope<contextual&&scope<rows&&scope<csv,"One restricted inventory must gate all facets and exports");
 assert.doesNotMatch(route,/if this independent census cannot be validated, withhold ONLY its count/i);
});
