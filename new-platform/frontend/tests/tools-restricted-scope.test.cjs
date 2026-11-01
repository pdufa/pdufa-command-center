"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
  mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,file);
const {
 verifiedToolPool,buildToolsOpeningInventory,buildToolsResults,
 toolsContextualDesignationCounts,toolsDesignationTotals
}=require("../lib/tools-pool-inventory.ts");
const {restrictedToolsSnapshot}=require("../lib/tools-restricted-scope.ts");
const trial=(nct,stage,ticker)=>({id:"TRIAL|"+nct,ticker,stage,company:"Company",drug:"Drug",indication:"Disease"});
const pool=[
 trial("NCT00000001","Phase 1","AAA"),
 trial("NCT00000002","Phase 2","AAA"),
 trial("NCT00000003","Phase 3","AAA"),
 trial("NCT00000004","Phase 4","BBB"),
 trial("NCT00000005","Phase 2","CCC"),
 trial("NCT00000006","Phase 1","DDD"),
 trial("NCT00000007","Phase 3","EEE"),
 {id:"RESULT|a",ticker:"AAA",stage:"Phase 3 Results"}
];
const snapshot=verifiedToolPool({
 pipeline:pool,asOf:"2026-11-01T18:00:00Z",
 sourceHealth:{state:"PARTIAL",clinicalRows:7,regulatoryRows:1,pipelineSourceParity:{exactPrograms:8}}
});
const capHeader="ticker,market_cap,market_cap_source,market_cap_checked_at,market_cap_status";
const cap=(ticker,amount,status="VERIFIED",date="2026-11-01T03:21:00Z")=>
 [ticker,amount,"https://api.nasdaq.com/api/quote/"+ticker+"/summary?assetclass=stocks",date,status].join(",");
const caps=[capHeader,cap("AAA",500000000),cap("BBB",11000000000),
 cap("CCC",600000000),cap("EEE",900000000,"PENDING")].join("\n");
const registry=[
 "ticker,company,cik10,exchange,sic,sic_description,status",
 "AAA,Company,0000000001,Nasdaq,2834,Drug,OK",
 "BBB,Company,0000000002,Nasdaq,2834,Drug,OK",
 "CCC,Company,0000000003,OTC,2834,Drug,OK",
 "DDD,Company,0000000004,Nasdaq,2834,Drug,OK",
 "EEE,Company,0000000005,NYSE,2834,Drug,OK"
].join("\n");
const granted={status:"GRANTED",verification:"SOURCE_RECORDED",
 source:"https://www.fda.gov/one",designationDate:"",checkedAt:"",note:""};
const designation={
 availableKeys:{fast_track:true,orphan_drug:true},
 programs:{
  "AAA|PROGRAM":{eventKey:"AAA|PROGRAM",ticker:"AAA",drug:"Drug",indication:"Disease",
   designations:{fast_track:granted,orphan_drug:granted}},
  "BBB|PROGRAM":{eventKey:"BBB|PROGRAM",ticker:"BBB",drug:"Drug",indication:"Disease",
   designations:{fast_track:granted}}
 },
 trialEvents:{
  NCT00000001:["AAA|PROGRAM"],NCT00000002:["AAA|PROGRAM"],
  NCT00000003:["AAA|PROGRAM"],NCT00000004:["BBB|PROGRAM"]
 }
};
const now=Date.parse("2026-11-01T18:00:00Z");
test("Both independent breakdowns use the same $300M–$10B cap-restricted POOL across ALL phases",()=>{
 const {snapshot:restricted,scope}=restrictedToolsSnapshot(snapshot,caps,registry,now);
 assert.equal(scope.scope,"DATED_300M_10B_ISSUER_MARKET_CAP_SCREEN");
 assert.equal(scope.originalPoolTrials,7);
 assert.equal(scope.screenedTrials,3);
 assert.equal(scope.eligibleIssuers,1);
 assert.equal(scope.qualification,"NOT_VERIFIED");
 assert.equal(scope.outsideCapTrials,1);
 assert.equal(scope.unverifiedCapTrials,2);
 assert.equal(scope.excludedIssuerTrials,1);
 assert.deepEqual(restricted.poolRows.map(r=>r.id),
  ["TRIAL|NCT00000001","TRIAL|NCT00000002","TRIAL|NCT00000003"]);
 assert.equal(restricted.stageStats.stages["Phase 1"].trials,1);
 assert.equal(restricted.stageStats.stages["Phase 2"].trials,1);
 assert.equal(restricted.stageStats.stages["Phase 3"].trials,1);
 assert.equal(restricted.stageStats.stages["Phase 4"].trials,0);
 const opening=buildToolsOpeningInventory(restricted,0,50);
 assert.equal(opening.total,3);
 const counts=toolsContextualDesignationCounts(restricted.poolRows,designation,[],"");
 assert.equal(counts.fast_track.matchingTrials,3,"FDA counts reflect all cap-qualified phases, NOT Phase 3 only");
 assert.equal(toolsDesignationTotals(restricted.poolRows,designation).fast_track.linkedNcts,3);
 assert.equal(buildToolsResults(restricted,designation,["Phase 1"],[],"",0,50).total,1);
 assert.equal(buildToolsResults(restricted,designation,["Phase 2"],[],"",0,50).total,1);
 assert.equal(buildToolsResults(restricted,designation,["Phase 3"],[],"",0,50).total,1);
 assert.equal(buildToolsResults(restricted,designation,[],["fast_track"],"",0,50).total,3);
 assert.equal(buildToolsResults(restricted,designation,["Phase 1"],["fast_track"],"",0,50).total,1);
 assert.equal(buildToolsResults(restricted,designation,["Phase 1","Phase 2"],["orphan_drug"],"",0,50).total,2);
 assert.equal(buildToolsResults(restricted,designation,["Phase 4"],[],"",0,50).total,0,
   "An out-of-cap Phase 4 study cannot bleed into the phase breakdown");
});
test("Cap evidence incomplete, duplicate, stale, or missing fails closed for those issuers",()=>{
 assert.throws(()=>restrictedToolsSnapshot(snapshot,"",registry,now));
 assert.throws(()=>restrictedToolsSnapshot(snapshot,caps,"",now));
 const stale=[capHeader,cap("AAA",500000000,"VERIFIED","2026-09-01T03:21:00Z")].join("\n");
 assert.throws(()=>restrictedToolsSnapshot(snapshot,stale,registry,now),/RESTRICTED_MARKET_CAP_SOURCE_UNAVAILABLE/);
 const duplicated=[caps,cap("AAA",500000000)].join("\n");
 assert.throws(()=>restrictedToolsSnapshot(snapshot,duplicated,registry,now),/RESTRICTED_MARKET_CAP_NO_RECONCILED_TRIALS/);
});
test("TOOLS route applies cap restriction before Phase, FDA and CSV, never the historical Phase 3 census",()=>{
 const route=fs.readFileSync(require("node:path").join(__dirname,"../app/api/scope-funnel/route.ts"),"utf8");
 const scope=route.indexOf("restrictedToolsSnapshot(");
 const totals=route.indexOf("toolsDesignationTotals(inventory.poolRows,index)");
 const contextual=route.indexOf("toolsContextualDesignationCounts(");
 const grid=route.indexOf("buildToolsResults(inventory,index,selectedStages,selectedDesignations");
 const csv=route.indexOf("filterToolTrials(inventory.poolRows,selectedStages,matches,query)");
 assert.ok([scope,totals,contextual,grid,csv].every(n=>n>=0));
 assert.ok(scope<totals&&scope<contextual&&scope<grid&&scope<csv);
 assert.match(route,/toolsMarketCapSources\(\)/);
 assert.doesNotMatch(route,/reconcilePoolPipeline\(\{/);
});
