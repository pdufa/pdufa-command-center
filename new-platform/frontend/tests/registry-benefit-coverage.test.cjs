"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),
 {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const {registryCoverageFromSnapshot,sourceReviewHint}=require("../lib/registry-benefit-coverage.ts");
const now=Date.parse("2026-11-01T04:57:00.000Z");
const sample=()=>({schemaVersion:1,censusAsOf:"2026-10-26",scanStartedAt:"2026-11-01T04:55:22.000Z",
 scanned:375,successful:1,failed:374,reusedWithin72Hours:0,records:[{
  nctId:"NCT12345678",sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",
  retrievedAt:"2026-11-01T04:55:23.000Z",sourceUpdated:"2026-10-20",
  resultsPosted:true,primary:[{measurements:[{group:"Study arm",value:"53"}]}],
  seriousAdverseEvents:[{groups:[{group:"Study arm",affected:1,atRisk:100}]}],
  truncatedEvidence:{outcomes:false,seriousEvents:false},
  comparisonVerified:false,benefitRank:null,fdaDecisionVerified:false
 }]});
test("official source snapshot shows exact-NCT data availability but never benefit superiority",()=>{
 const x=registryCoverageFromSnapshot(sample(),now);
 assert.equal(x.scanned,375);
 assert.equal(x.postedResults,1);
 assert.equal(x.withPrimaryMeasurements,1);
 assert.equal(x.withSeriousEventCounts,1);
 assert.equal(x.records.length,1);
 assert.match(sourceReviewHint(x.records[0],3),/review required/i);
 assert.match(sourceReviewHint(x.records[0],8),/review required/i);
 assert.equal(sourceReviewHint(x.records[0],19),null);
 assert.equal(sourceReviewHint(undefined,3),null);
});
test("old, future, cross-NCT, fake approval and duplicate records fail closed",()=>{
 const stale=sample();
 assert.throws(()=>registryCoverageFromSnapshot(stale,now+49*3600000),/STALE_REGISTRY_SOURCE_ARCHIVE/);
 const future=sample();future.scanStartedAt="2026-11-03T00:00:00.000Z";
 assert.throws(()=>registryCoverageFromSnapshot(future,now),/STALE_REGISTRY_SOURCE_ARCHIVE/);
 const mismatch=sample();mismatch.records[0].sourceUrl="https://example.org/mismatch";
 assert.throws(()=>registryCoverageFromSnapshot(mismatch,now),/INVALID_REGISTRY_SOURCE_IDENTITY/);
 const promoted=sample();promoted.records[0].comparisonVerified=true;
 assert.throws(()=>registryCoverageFromSnapshot(promoted,now),/INVALID_REGISTRY_SOURCE_IDENTITY/);
 const dup=sample();dup.records.push({...dup.records[0]});dup.successful=2;dup.failed=373;
 assert.throws(()=>registryCoverageFromSnapshot(dup,now),/INVALID_REGISTRY_SOURCE_IDENTITY/);
 const impossible=sample();impossible.records[0].resultsPosted=false;
 assert.throws(()=>registryCoverageFromSnapshot(impossible,now),/INCONSISTENT_REGISTRY_POSTING_STATE/);
});
test("archive read is signed-in and UI presents source-only status separately from rankings",()=>{
 const route=fs.readFileSync(path.join(__dirname,"../app/api/registry-benefit-coverage/route.ts"),"utf8");
 const ui=fs.readFileSync(path.join(__dirname,"../app/ToolsBenefitMatrix.tsx"),"utf8");
 assert.match(route,/hasSession/);
 assert.match(route,/registryCoverageFromSnapshot/);
 assert.match(route,/private, no-store/);
 assert.match(route,/status:503/);
 assert.match(ui,/\/api\/registry-benefit-coverage/);
 assert.match(ui,/sourceReviewHint\(sourceIndex.get\(row.nctId\),g.number\)/);
 assert.match(ui,/Official registry research archive/);
 assert.match(ui,/Assessment conclusions remain Not assessed until reviewed/);
 assert.match(ui,/Registry data · review required/);
});
test("published research archive has the expected census and valid provenance without assuming benefit",()=>{
 const raw=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/registry-benefit-research-snapshot.json"),"utf8"));
 // The archive date can age; validate at its own recorded collection time, not wall-clock.
 if(raw.scanStartedAt!==null){
  const x=registryCoverageFromSnapshot(raw,Date.parse(raw.scanStartedAt)+300000);
  assert.equal(x.scanned,375);
  assert.ok(x.postedResults<=x.records.length);
  assert.ok(x.withSeriousEventCounts<=x.records.length);
  assert.ok(x.withPrimaryMeasurements<=x.records.length);
  assert.ok(x.records.every(row=>/^NCT\d{8}$/.test(row.nctId)));
 }
});
