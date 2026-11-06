"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const Module=require("node:module");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
function loadTs(file,imports={}){
 const compiled=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
 }).outputText;
 const unit=new Module(file,module);unit.filename=file;unit.paths=module.paths;
 const regularRequire=unit.require.bind(unit);
 unit.require=(specifier)=>Object.prototype.hasOwnProperty.call(imports,specifier)?imports[specifier]:regularRequire(specifier);
 unit._compile(compiled,file);
 return unit.exports;
}
const policy=loadTs(path.join(root,"lib/pdufa-selected-restrictions.ts"));
const {activePhase3Cohorts:result,PROMOTED_ISSUER_NCTS,IONIS_VERIFIED_READOUTS}=loadTs(
 path.join(root,"lib/phase3-active-cohorts.ts"),{"./pdufa-selected-restrictions":policy});
const original=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-unified-classifications-2026-11-05.json"),"utf8"));
const active=new Set(["RECRUITING","NOT_YET_RECRUITING","ACTIVE_NOT_RECRUITING","ENROLLING_BY_INVITATION"]);
test("Exactly 235 Pre-Data and 23 Post-Data, all 258 unique active NCTs",()=>{
 assert.equal(result.totalPool,762);
 assert.equal(result.activeTotal,258);
 assert.deepEqual(result.counts,{PRE_DATA:235,POST_DATA:23,HISTORICAL:501,VERIFY:3});
 assert.equal(result.pre.length,235);
 assert.equal(result.post.length,23);
 const combined=[...result.pre,...result.post];
 assert.equal(new Set(combined.map(x=>x.nctId)).size,258);
 assert.ok(combined.every(x=>active.has(x.registryStatus)));
 assert.ok(combined.every(x=>/^NCT\d{8}$/.test(x.nctId)));
});
test("Move five exact-NCT issuer readouts, not unrelated company or issuer trials",()=>{
 assert.equal(PROMOTED_ISSUER_NCTS.length,5);
 assert.equal(new Set(PROMOTED_ISSUER_NCTS).size,5);
 assert.deepEqual(result.post.filter(x=>x.correctionApplied).map(x=>x.nctId).sort(),
  [...PROMOTED_ISSUER_NCTS,...IONIS_VERIFIED_READOUTS.map(x=>x.nctId)].sort());
 for(const nctId of PROMOTED_ISSUER_NCTS){
  assert.ok(!result.pre.some(x=>x.nctId===nctId));
  const x=result.post.find(x=>x.nctId===nctId);
  assert.ok(x&&x.readoutEvidenceUrl?.startsWith("https://"));
  assert.equal(x.evidenceBasis,"ISSUER_READOUT");
  assert.equal(x.originalClassificationCode,"P3_PRE_DATA_CANDIDATE");
  assert.ok(x.classificationVerified);
 }
 const mixed=result.post.find(x=>x.nctId==="NCT05031780");
 assert.equal(mixed.readoutOutcome,"MIXED_COPRIMARY_RESULTS");
});
test("Retain all 762 historic source records, unchanged exact identities and all nonpromoted classifications",()=>{
 assert.equal(result.snapshot.rows.length,762);
 assert.equal(new Set(result.snapshot.rows.map(x=>x.nctId)).size,762);
 const index=new Map(result.snapshot.rows.map(x=>[x.nctId,x]));
 const promotions=new Set([...PROMOTED_ISSUER_NCTS,...IONIS_VERIFIED_READOUTS.map(x=>x.nctId)]);
 for(const row of original.rows){
  const patched=index.get(row.nctId);
  assert.ok(patched,row.nctId);
  assert.equal(patched.registryStatus,row.registryStatus);
  assert.equal(patched.registrySourceUrl,row.registrySourceUrl);
  if(!promotions.has(row.nctId))
   assert.deepEqual(patched,row);
 }
 assert.equal(result.snapshot.counts.P3_PRE_DATA_CANDIDATE,235);
 assert.equal(result.snapshot.counts.P3_POST_DATA_ISSUER,17);
 assert.equal(result.snapshot.counts.P3_POST_DATA_REGISTRY,10);
 assert.equal(Object.values(result.snapshot.counts).reduce((a,b)=>a+b,0),762);
});
test("No completed, terminated, withdrawn or UNKNOWN NCT enters either active spreadsheet",()=>{
 const activeIds=new Set([...result.pre,...result.post].map(x=>x.nctId));
 for(const row of original.rows){
  if(!active.has(row.registryStatus))assert.ok(!activeIds.has(row.nctId));
 }
});
