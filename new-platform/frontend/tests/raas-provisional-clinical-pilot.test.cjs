"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
 fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,".."),repo=path.resolve(root,"../..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,file);
const {provisionalScoresForTrial}=require("../lib/raas-provisional-trial-scores.ts");
const {RAAS_PROVISIONAL_RUBRICS,provisionalStageCoverage}=
 require("../lib/raas-provisional-rubric-engine.ts");
const {parseRaasTrialHistory}=require("../lib/raas-trial-score-history.ts");
const capture=require(path.join(repo,"scripts/raas_trial_clinical_metric_capture.cjs"));
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data/raas-pilot-observations.json"),"utf8"));
const readout=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
const get=(nct,ticker,drug,indication)=>provisionalScoresForTrial({
 nctId:nct,ticker,drug,indication},"post");
test("60 rubric definitions remain intact; three narrow pilot metric IDs have actual calculators",()=>{
 assert.equal(RAAS_PROVISIONAL_RUBRICS.length,60);
 const top=provisionalScoresForTrial({nctId:"NCT07363577",ticker:"LBRX"},"pre");
 assert.deepEqual(top.scoredMetrics.map(x=>[x.metricId,x.score]),[["pre-4-1",50]]);
 const c1=get("NCT06445023","CLDX","barzolvolimab","chronic spontaneous urticaria");
 const c2=get("NCT06455202","CLDX","barzolvolimab","chronic spontaneous urticaria");
 assert.deepEqual(c1.scoredMetrics.map(x=>[x.metricId,x.score]),[
  ["post-1-1",100],["post-1-2",100]
 ]);
 assert.deepEqual(c2.scoredMetrics.map(x=>[x.metricId,x.score]),[
  ["post-1-1",75],["post-1-2",100]
 ]);
 for(const c of [c1,c2]){
  assert.equal(c.overallScore,null);assert.equal(c.scoredOf30,2);
  assert.ok(c.scoredMetrics.every(g=>g.kind==="RESEARCH_ONLY_NOT_VALIDATED"));
  const coverage=provisionalStageCoverage("post",c.scoredMetrics);
  assert.equal(coverage.weightCoveredPercent,10);
  assert.equal(coverage.fullyCoveredProvisionalScore,null);
 }
 assert.equal(get("NCT06641076","MLTX","sonelokimab","psoriatic arthritis").scoredOf30,0);
 assert.equal(get("NCT06445023","CLDX","different therapy","chronic spontaneous urticaria").scoredOf30,0);
 assert.equal(get("NCT06445023","FAKE","barzolvolimab","chronic spontaneous urticaria").scoredOf30,0);
});
test("clinical nightly source capture has same trial identity, score math and genuine timestamps",()=>{
 const c=capture.deriveClinicalCandidates(pilot,readout);
 assert.deepEqual(c.map(x=>[x.nctId,x.grades.map(g=>[g.metricId,g.score])]),[
  ["NCT06445023",[["post-1-1",100],["post-1-2",100]]],
  ["NCT06455202",[["post-1-1",75],["post-1-2",100]]]
 ]);
 const d={schemaVersion:1,scope:"RAAS_TRIAL_SCORE_HISTORY",note:"test",records:[]};
 const time="2026-11-04T19:00:00.000Z";
 const a=capture.appendClinicalEvents(d,c,time,pilot.sourceAsOf);
 assert.equal(a.added,2);
 assert.equal(a.ledger.records[0].metricCoverage,2);
 assert.ok(a.ledger.records.every(x=>x.score===null&&x.scoreKind==="UNSCORED"));
 assert.equal(parseRaasTrialHistory(a.ledger).records.length,2);
 const replay=capture.appendClinicalEvents(a.ledger,c,"2026-11-04T19:01:00.000Z",pilot.sourceAsOf);
 assert.equal(replay.added,0);
 assert.deepEqual(replay.ledger.records,a.ledger.records);
 assert.throws(()=>capture.appendClinicalEvents(a.ledger,c,"2026-11-04T18:59:59.000Z",pilot.sourceAsOf),/BACKDATING/);
 const manipulated=structuredClone(pilot);
 manipulated.records.find(x=>x.nctId==="NCT06445023").observations[0].controlChange=null;
 const after=capture.deriveClinicalCandidates(manipulated,readout);
 assert.equal(after.find(x=>x.nctId==="NCT06445023").grades.length,1);
});
test("a published result without exact matched study cannot enter BOTTOM score history",()=>{
 const fake=structuredClone(readout);
 fake.entries=fake.entries.filter(x=>x.nctId!=="NCT06445023");
 assert.deepEqual(capture.deriveClinicalCandidates(pilot,fake).map(x=>x.nctId),["NCT06455202"]);
 const issue=structuredClone(readout);
 issue.entries.find(x=>x.nctId==="NCT06445023").drug="wrong molecule";
 assert.equal(capture.deriveClinicalCandidates(pilot,issue).length,1);
});
