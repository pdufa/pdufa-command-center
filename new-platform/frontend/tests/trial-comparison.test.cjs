"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>mod._compile(
  ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
    module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true
  }}).outputText,file
);
const {screenComparisonCandidates,comparisonSnapshot,comparisonCaveat,trialComparisonKey}=require("../lib/trial-comparison.ts");
const row=(patch={})=>({nctId:"NCT12345678",ticker:"EXAM",company:"Example",drug:"Therapy A",
  indication:"Disease A",sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",
  censusStatus:"COMPLETED",capUsd:500000000,capAsOf:"2026-10-31",
  poolStatus:"EXACT_MATCH",postPhase3Evidence:"REGISTRY_COMPLETED",
  qualification:"NEEDS_REVIEW",reasons:[],...patch});
test("candidate screening keeps exact $300M-$10B post-Phase 3 research boundary",()=>{
  const a=row();
  const filtered=screenComparisonCandidates([a,a,row({nctId:"NCT87654321",capUsd:299999999}),
    row({nctId:"NCT23456789",capUsd:10000000001}),
    row({nctId:"NCT34567890",poolStatus:"NO_MATCH"}),
    row({nctId:"NCT45678901",postPhase3Evidence:"UNKNOWN"}),
    row({nctId:"NCT56789012",qualification:"REJECTED"}),
    row({nctId:"NCT67890123",drug:null})]);
  assert.equal(filtered.length,1);
  assert.equal(trialComparisonKey(filtered[0]),trialComparisonKey(a));
});
test("all 20 groups stay visible; missing evidence is not fabricated into a score",()=>{
  const summary=comparisonSnapshot(row(),null);
  assert.equal(summary.groups.length,20);
  assert.ok(summary.required>=20);
  assert.equal(summary.verified,0);
  assert.equal(summary.modeled,0);
  assert.equal(summary.readiness,"NOT_ASSESSED");
  assert.ok(summary.groups.every(g=>g.fields.length>0&&g.verified===0));
});
test("source-verified versus modeled assessment fields are counted separately",()=>{
  const fact={value:"12%",status:"VERIFIED",sourceUrl:"https://example.org/study",
    sourceDate:"2026-10-31",method:"endpoint check",confidence:"HIGH"};
  const feed={schemaVersion:1,sourceAsOf:"2026-10-31",records:[{
    nctId:"NCT12345678",ticker:"EXAM",drug:"Therapy A",indication:"Disease A",
    facts:{clinicalBenefit:fact,peakAnnualSales:{...fact,status:"MODELED",value:"$400M"}},advantages:[]
  }]};
  const result=comparisonSnapshot(row(),feed);
  assert.equal(result.verified,1);
  assert.equal(result.modeled,1);
  assert.equal(result.groups[2].verified,1);
  assert.equal(result.groups[14].modeled,1);
});
test("research comparison never treats shared disease as proof of superiority",()=>{
  assert.match(comparisonCaveat([row(),row({nctId:"NCT87654321"})]),/does not prove/);
  assert.match(comparisonCaveat([row(),row({nctId:"NCT87654321",indication:"Disease B"})]),/Different indications/);
  assert.match(comparisonCaveat([row()]),/at least two/);
});
