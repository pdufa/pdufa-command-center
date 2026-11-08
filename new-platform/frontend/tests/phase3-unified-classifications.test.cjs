const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const json=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-unified-classifications-2026-11-05.json"),"utf8"));
test("Every unique NCT in the full 762-trial census has a source-qualified classification",()=>{
 assert.equal(json.total,762);
 assert.equal(json.rows.length,762);
 assert.equal(new Set(json.rows.map(x=>x.nctId)).size,762);
 assert.equal(Object.values(json.counts).reduce((a,b)=>a+b,0),762);
 assert.equal(json.counts.P3_POST_DATA_ISSUER,9);
 assert.equal(json.counts.P3_POST_DATA_REGISTRY,10);
 for(const row of json.rows){
  assert.match(row.nctId,/^NCT\d{8}$/);
  assert.ok(row.classificationCode && row.classification && row.registryStatus);
  assert.match(row.registrySourceUrl,/^https:\/\/clinicaltrials\.gov\/study\/NCT\d{8}$/);
  if(row.classificationVerified)assert.ok(row.readoutEvidenceUrl&&row.readoutSourceDate);
  if(row.classificationCode==="P3_PRE_DATA_CANDIDATE")
   assert.equal(row.classificationVerified,false);
  assert.equal(row.fdaApplicationStatus,"NOT_VERIFIED");
  assert.equal(row.pdufaGoalDate,null);
 }
});
test("Unified classifications appear above legacy Phase 3 panels without removing historical records",()=>{
const ui=require('node:fs').readFileSync(require('node:path').join(__dirname,'../app/Phase3ReadoutSheets.tsx'),'utf8');assert.match(ui,/classifyPhase3Readouts/);assert.match(ui,/Not verified/);assert.doesNotMatch(ui,/Phase3PreDataBatch|Survey|RAAS.*Score/);
});
