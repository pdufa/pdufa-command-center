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
const snapshot=comparisonSnapshot(row(),null);assert.equal(snapshot.groups.length,0);assert.equal(snapshot.required,0);assert.equal(snapshot.verified,0);assert.equal(snapshot.readiness,'NOT_ASSESSED');
});
test("source-verified versus modeled assessment fields are counted separately",()=>{
const result=comparisonSnapshot(row(),null);assert.equal(result.verified,0);assert.equal(result.modeled,0);assert.equal(result.groups.length,0);
});
test("research comparison never treats shared disease as proof of superiority",()=>{
  assert.match(comparisonCaveat([row(),row({nctId:"NCT87654321"})]),/does not prove/);
  assert.match(comparisonCaveat([row(),row({nctId:"NCT87654321",indication:"Disease B"})]),/Different indications/);
  assert.match(comparisonCaveat([row()]),/at least two/);
});
