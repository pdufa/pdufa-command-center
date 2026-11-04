"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}).outputText,file);
const root=path.resolve(__dirname,".."),repo=path.resolve(root,"../..");
const {RAAS_PROVISIONAL_RULES,provisionalRule,screenProvisionalAnchor}=
 require("../lib/raas-provisional-policy.ts");
const {provisionalScoresForTrial}=require("../lib/raas-provisional-trial-scores.ts");
const capture=require(path.join(repo,"scripts/raas_trial_clinical_metric_capture.cjs"));
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data/raas-pilot-observations.json")));
const readout=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-public-readout-evidence-2026-11-01.json")));
const trial=(nct,ticker,drug,indication)=>({nctId:nct,ticker,drug,indication});
const get=(nct,ticker,stage,drug,indication)=>provisionalScoresForTrial(
 trial(nct,ticker,drug,indication),stage);
test("all sixty metrics have 0/25/50/75/100 rubrics; none is called approved",()=>{
 assert.equal(RAAS_PROVISIONAL_RULES.length,60);
 assert.equal(new Set(RAAS_PROVISIONAL_RULES.map(x=>x.metricId)).size,60);
 assert.equal(RAAS_PROVISIONAL_RULES.filter(x=>x.stage==="pre").length,30);
 assert.equal(RAAS_PROVISIONAL_RULES.filter(x=>x.stage==="post").length,30);
 assert.equal(RAAS_PROVISIONAL_RULES.filter(x=>x.method==="AUTOMATED_NARROW_PILOT").length,3);
 for(const r of RAAS_PROVISIONAL_RULES){
  assert.deepEqual(Object.keys(r.anchors).map(Number),[0,25,50,75,100]);
  assert.ok(r.requiredEvidence&&r.benchmarkRequired&&r.criticalRisk);
  assert.equal(r.approvedForComposite,false);
  assert.equal(r.accuracyValidated,false);
  assert.match(r.version,/provisional/);
 }
 assert.equal(provisionalRule("post","post-3-5").method,"EVIDENCE_REVIEW_REQUIRED");
});
test("BOTTOM CSU documented arm-level results yield only narrow experimental component proxies",()=>{
 const c1=get("NCT06445023","CLDX","post","barzolvolimab","chronic spontaneous urticaria");
 const c2=get("NCT06455202","CLDX","post","barzolvolimab","chronic spontaneous urticaria");
 const m=get("NCT06641076","MLTX","post","sonelokimab","psoriatic arthritis");
 assert.deepEqual(c1.scoredMetrics.map(g=>[g.metricId,g.score]),[
  ["post-1-1",100],["post-1-2",100]
 ]);
 assert.deepEqual(c2.scoredMetrics.map(g=>[g.metricId,g.score]),[
  ["post-1-1",75],["post-1-2",100]
 ]);
 for(const result of [c1,c2,m]){
  assert.equal(result.overallScore,null);
  assert.equal(result.scoredOf30+result.unscoredOf30,30);
  assert.ok(result.scoredMetrics.every(g=>g.kind==="RESEARCH_ONLY_NOT_VALIDATED"));
 }
 assert.equal(m.scoredOf30,0); // unadjusted ACR50 and cash NOT efficacy scoring
 assert.equal(get("NCT06445023","CLDX","post","different molecule","chronic spontaneous urticaria").scoredOf30,0);
 assert.equal(get("NCT06445023","WRONG","post").scoredOf30,0);
});
test("historical SOURCE capture script and browser agree on BOTTOM component math",()=>{
 const scored=capture.deriveClinicalCandidates(pilot,readout);
 assert.equal(scored.length,2);
 assert.deepEqual(scored.map(x=>[x.nctId,x.grades.map(g=>[g.metricId,g.score])]),[
  ["NCT06445023",[["post-1-1",100],["post-1-2",100]]],
  ["NCT06455202",[["post-1-1",75],["post-1-2",100]]]
 ]);
 const empty={schemaVersion:1,scope:"RAAS_TRIAL_SCORE_HISTORY",note:"test",records:[]};
 const recordedAt="2026-11-04T15:35:05.000Z";
 const a=capture.appendClinicalEvents(empty,scored,recordedAt,pilot.sourceAsOf);
 assert.equal(a.added,2);
 assert.equal(a.ledger.records[0].metricCoverage,2);
 assert.ok(a.ledger.records.every(x=>x.score===null&&x.scoreKind==="UNSCORED"));
 const b=capture.appendClinicalEvents(a.ledger,scored,"2026-11-04T15:35:06.000Z",pilot.sourceAsOf);
 assert.equal(b.added,0);
 assert.deepEqual(b.ledger.records,a.ledger.records);
 assert.throws(()=>capture.appendClinicalEvents(a.ledger,scored,"2026-11-04T15:35:04.000Z",pilot.sourceAsOf),/BACKDATING/);
 const forged=structuredClone(pilot);
 forged.records.find(r=>r.nctId==="NCT06445023").observations[0].controlChange=undefined;
 const revised=capture.deriveClinicalCandidates(forged,readout);
 assert.equal(revised.find(r=>r.nctId==="NCT06445023").grades.length,1);
});
test("human review requires exact identity, dated reference benchmark, recorded counterevidence and genuine signoff",()=>{
 const identity=trial("NCT06445023","CLDX","barzolvolimab","chronic spontaneous urticaria");
 const input={...identity,stage:"post",metricId:"post-1-3",band:75,
  assessmentAsOf:"2026-11-04",sourceDate:"2026-09-22",
  sourceUrl:"https://ir.example.com/signed-results",
  benchmarkSourceDate:"2026-05-01",
  benchmarkSourceUrl:"https://clinicaltrials.gov/study/NCT06445023",
  reviewer:"Research reviewer, primary evidence checked",
  rationale:"Explicitly reviewed the endpoint, multiplicity and missingness requirements against published findings and the planned reference comparison; this is synthetic test data only.",
  counterEvidence:"Residual safety and missing data risk not independently resolved."};
 const accepted=screenProvisionalAnchor(input,identity,"2026-11-04");
 assert.equal(accepted.accepted,true);
 assert.equal(accepted.score,75);
 assert.equal(screenProvisionalAnchor({...input,band:35},identity,"2026-11-04").accepted,false);
 assert.equal(screenProvisionalAnchor({...input,sourceDate:"2026-12-31"},identity,"2026-11-04").accepted,false);
 assert.equal(screenProvisionalAnchor({...input,rationale:"fine"},identity,"2026-11-04").accepted,false);
 assert.equal(screenProvisionalAnchor({...input,nctId:"NCT12345678"},identity,"2026-11-04").accepted,false);
 assert.equal(screenProvisionalAnchor({...input,sourceDate:"2026-99-99"},identity,"2026-11-04").accepted,false);
});
