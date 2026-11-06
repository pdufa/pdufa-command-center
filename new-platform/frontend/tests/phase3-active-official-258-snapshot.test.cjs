"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true
 }}).outputText,file);
const {activePhase3Cohorts}=require("../lib/phase3-active-cohorts.ts");
const {activeOfficialRegistryRecords,activeOfficialRegistryIntegrity,activeOfficialRegistryRecord}
 =require("../lib/phase3-active-official-registry.ts");
const {GET:coverage}=require("../app/api/phase3-active-190-coverage/route.ts");
const source=fs.readFileSync(require.resolve("../app/api/phase3-unified-190-columns/route.ts"),"utf8");
const audit=fs.readFileSync(require.resolve("../app/api/phase3-missing-data-audit/route.ts"),"utf8");

test("persisted official registry snapshot has every one of 258 unique active NCTs",()=>{
 const allowed=new Set([...activePhase3Cohorts.pre,...activePhase3Cohorts.post].map(x=>x.nctId));
 assert.equal(activeOfficialRegistryRecords.length,258);
 assert.equal(allowed.size,258);
 assert.ok(activeOfficialRegistryIntegrity(allowed));
 assert.equal(new Set(activeOfficialRegistryRecords.map(x=>x.nctId)).size,258);
 assert.ok(activeOfficialRegistryRecords.every(x=>x.sourceState==="FETCHED"&&x.registryUrl.includes(x.nctId)));
 for(const id of allowed)assert.ok(activeOfficialRegistryRecord(id));
 assert.equal(activeOfficialRegistryRecords.filter(x=>x.registryResultsPosted).length,10);
 assert.equal(activeOfficialRegistryRecords.filter(x=>x.hasPublicSAP).length,10);
});
test("default 258x190 evidence export uses saved official source; audits agree on precedence",()=>{
 assert.match(source,/activeOfficialRegistryRecord\(r\.nctId\)/);
 assert.match(source,/activeOfficialRegistryIntegrity\(/);
 assert.match(audit,/activeOfficialRegistryRecord\(r\.nctId\)/);
 assert.match(audit,/activeOfficialRegistryIntegrity\(/);
});
test("normal 190-field coverage gets saved official facts even without a live request",async()=>{
 const res=await coverage(new Request("http://localhost/api/phase3-active-190-coverage"));
 assert.equal(res.status,200,await res.clone().text());
 const obj=await res.json();
 assert.equal(obj.liveOfficialRegistry,false);
 assert.equal(obj.totals.trials,258);
 assert.equal(obj.totals.expectedCells,258*190);
 assert.ok(obj.totals.documentedQuestions>=2790);
 assert.ok(obj.totals.unscoredQuestions<=4889);
 assert.equal(obj.totals.documentedQuestions+obj.totals.predictedQuestions+obj.totals.unscoredQuestions,258*30);
 assert.equal(obj.totals.raasScoredTrials,0);
 assert.equal(obj.totals.clinicalRatedTrials,6);
});
