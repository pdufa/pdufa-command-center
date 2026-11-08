"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,".."),repo=path.resolve(root,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {provisionalScoresForTrial}=require("../lib/raas-provisional-trial-scores.ts");
const capture=require(path.join(repo,"scripts/raas_post_clinical_provisional_capture.cjs"));
const pilot=JSON.parse(read("data/raas-pilot-observations.json"));
const readout=JSON.parse(read("public/phase3-public-readout-evidence-2026-11-01.json"));
const candidates=()=>capture.derivePostCandidates(pilot,readout);
const empty=()=>({schemaVersion:1,scope:"RAAS_TRIAL_SCORE_HISTORY",note:"isolated",records:[]});
const recordedAt="2026-11-04T18:00:00.000Z";
test("two exact placebo-controlled Phase 3 studies yield four experimental component grades",()=>{
 const result=candidates();
 assert.equal(result.length,4);
 assert.deepEqual(result.map(x=>[x.nctId,x.metricId,x.score]),[
  ["NCT06445023","post-1-1",75],["NCT06445023","post-1-2",100],
  ["NCT06455202","post-1-1",75],["NCT06455202","post-1-2",100]
 ]);
 for(const c of result){
  assert.equal(c.sourceUrl,"https://ir.celldex.com/node/16781/ixbrl-viewer");
  assert.equal(c.stage,"post");
  assert.ok(c.sourceDate<=pilot.sourceAsOf);
  const api=provisionalScoresForTrial(c,"post");
  assert.equal(api.scoredMetrics.find(x=>x.metricId===c.metricId)?.score,c.score);
  assert.equal(api.overallScore,null);
  assert.equal(api.scoredOf30,2);
 }
});
test("single-arm study, forged source, wrong ticker and wrong study do not receive numeric pilot grades",()=>{
 const m=provisionalScoresForTrial({nctId:"NCT06641076",ticker:"MLTX",
  drug:"sonelokimab",indication:"psoriatic arthritis"},"post");
 assert.equal(m.scoredOf30,0);
 assert.equal(provisionalScoresForTrial({nctId:"NCT06445023",ticker:"CLDX",
  drug:"unrelated",indication:"chronic spontaneous urticaria"},"post").scoredOf30,0);
 assert.deepEqual(capture.derivePostCandidates(
  {...pilot,records:pilot.records.map(r=>r.nctId==="NCT06445023"?
   {...r,observations:r.observations.map(o=>({...o,sourceUrl:"https://fake.example.org/source"}))}:r)},
   readout).map(x=>x.nctId).includes("NCT06445023"),false);
 assert.deepEqual(capture.derivePostCandidates(pilot,
  {...readout,entries:readout.entries.filter(x=>x.nctId!=="NCT06445023")})
  .map(x=>x.nctId).includes("NCT06445023"),false);
});
test("historical score events append as unscored overall, are reproducible and idempotent",()=>{
 const c=candidates();
 const first=capture.appendPostMetricEvents(empty(),c,recordedAt,pilot.sourceAsOf);
 assert.equal(first.added,4);
 assert.ok(first.ledger.records.every(x=>
  x.kind==="METRIC_SCORE_UPDATED"&&x.score===null&&x.scoreKind==="UNSCORED"));
 assert.deepEqual(first.ledger.records.flatMap(x=>x.metricGrades.map(g=>g.metricId))
  .sort(),["post-1-1","post-1-1","post-1-2","post-1-2"]);
 const retry=capture.appendPostMetricEvents(first.ledger,c,
  "2026-11-04T18:01:00.000Z",pilot.sourceAsOf);
 assert.equal(retry.added,0);
 assert.deepEqual(retry.ledger.records,first.ledger.records);
 assert.throws(()=>capture.appendPostMetricEvents(empty(),c,
  "2026-11-01T12:00:00.000Z",pilot.sourceAsOf),/INVALID/);
});
test("clinical pilot thresholds are predeclared and do not equate missing to zero",()=>{
 assert.equal(capture.bands(-1,[2,5,10]),0);
 assert.equal(capture.bands(1,[2,5,10]),25);
 assert.equal(capture.bands(3,[2,5,10]),50);
 assert.equal(capture.bands(9,[2,5,10]),75);
 assert.equal(capture.bands(12,[2,5,10]),100);
 assert.ok(!candidates().some(x=>x.score===0));
});
