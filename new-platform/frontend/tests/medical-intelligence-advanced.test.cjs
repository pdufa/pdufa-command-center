const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const cache={};
function load(name){
 if(cache[name])return cache[name];
 const filename=path.join(__dirname,"../lib/"+name+".ts");
 const src=fs.readFileSync(filename,"utf8");
 const js=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 vm.runInNewContext(js,{module,exports:module.exports,require:(dep)=>{
   if(dep==="../data/p3PostDataActive.json"){
     const data=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/p3PostDataActive.json"),"utf8"));
     return {default:data,...data};
   }
   assert.ok(dep.startsWith("./"),dep);
   return load(dep.slice(2));
 }});
 return cache[name]=module.exports;
}
const {APPLICATION_CYCLES}=load("medical-intelligence-applications");
const {ADVANCED_LEVELS,buildAdvancedAssessment}=load("medical-intelligence-advanced");
const {HISTORICAL_CALIBRATION,evaluateHistoricalCalibration}=load("medical-intelligence-calibration");
const page=fs.readFileSync(path.join(__dirname,"../app/medical-intelligence-preview/advanced/page.tsx"),"utf8");
const main=fs.readFileSync(path.join(__dirname,"../app/medical-intelligence-preview/page.tsx"),"utf8");
test("exactly twelve advanced failure-first levels are configured for every application",()=>{
 assert.equal(ADVANCED_LEVELS.length,12);
 assert.deepEqual(Array.from(ADVANCED_LEVELS,x=>x.number),Array.from({length:12},(_,i)=>i+1));
 assert.equal(new Set(ADVANCED_LEVELS.map(x=>x.id)).size,12);
 assert.equal(APPLICATION_CYCLES.length,23);
 for(const cycle of APPLICATION_CYCLES){
  const a=buildAdvancedAssessment(cycle.id);
  assert.ok(a,cycle.id);
  assert.equal(a.levels.length,12,cycle.id);
  assert.equal(a.predictions.length,3,cycle.id);
  assert.deepEqual(Array.from(a.predictions,p=>p.outcome),["APPROVAL","CRL","REVIEW_DELAY"]);
  assert.equal(a.certainty.status,"NOT_VALIDATED");
  assert.equal(a.certainty.rating,null);
  assert.equal(a.completedIndependentReviews,0);
  assert.ok(a.levels.every(l=>l.missing.length>=3 && l.explanation.length>20));
  assert.ok(a.predictions.every(p=>p.probability===null));
  assert.ok(a.predictions.every(p=>cycle.stage==="APPROVED_ALREADY"?
   p.status==="NOT_APPLICABLE_PREVIOUSLY_APPROVED":p.status==="ABSTAIN"));
  for(const level of a.levels)for(const src of level.sources){
   assert.match(src.url,/^https:\/\//);
   assert.ok(src.date<="2026-11-07",src.date+" in "+cycle.id);
   assert.ok(["EXACT_NCT","RELATED_EXTERNAL_TRIAL","APPLICATION_CONTEXT"].includes(src.scope));
  }
 }
});
test("trial phase and application indication are kept exact, not invented",()=>{
 const c=APPLICATION_CYCLES.find(x=>x.id==="capr-deramiocel");
 const missing=buildAdvancedAssessment(c.id);
 assert.ok(missing.phase.every(p=>p.verifiedPhase==="UNKNOWN"));
 assert.ok(missing.levels.some(x=>x.missing.some(m=>/Verify registry phase/.test(m))));
 const early=buildAdvancedAssessment(c.id,[{nct:c.ncts[0],verifiedPhase:"PHASE2",sourceUrl:"https://clinicaltrials.gov/study/"+c.ncts[0]}]);
 const stats=early.levels.find(x=>x.id==="STATISTICAL_FORENSICS");
 assert.ok(stats.missing.some(x=>/later-phase pivotal/.test(x)));
 assert.equal(early.cycle.indication,c.indication);
 assert.equal(buildAdvancedAssessment("not-a-valid-cycle"),null);
});
test("historical source findings are not mistaken for a forecast or completed analysis",()=>{
 const c=buildAdvancedAssessment("capr-deramiocel");
 assert.ok(c.sourceLeadLevelCount>0);
 assert.ok(c.levels.some(l=>l.sources.some(s=>s.sourceClass==="FDA_PRIMARY")));
 assert.ok(c.predictions.every(p=>p.status==="ABSTAIN"));
 const approved=buildAdvancedAssessment("cytk-aficamten-ohcm");
 assert.equal(approved.cycle.stage,"APPROVED_ALREADY");
 assert.equal(approved.predictions[0].status,"NOT_APPLICABLE_PREVIOUSLY_APPROVED");
});
test("historical calibration starts empty, enforces as-of and remains research-only",()=>{
 assert.equal(HISTORICAL_CALIBRATION.eligibleCount,0);
 assert.equal(HISTORICAL_CALIBRATION.releasePermitted,false);
 assert.equal(HISTORICAL_CALIBRATION.metrics.length,3);
 const good={
  cycleId:"synthetic-1",issuer:"Fixture",predictionAt:"2023-01-01",
  featureCutoff:"2022-12-31",outcomeAt:"2023-07-01",
  outcomeSourceUrl:"https://example.test/synthetic",
  probability:{APPROVAL:0.7,CRL:0.2,REVIEW_DELAY:0.3},
  observed:{APPROVAL:true,CRL:false,REVIEW_DELAY:false}
 };
 const invalid={...good,cycleId:"synthetic-2",featureCutoff:"2023-08-01"};
 const conflict={...good,cycleId:"synthetic-3",observed:{APPROVAL:true,CRL:true,REVIEW_DELAY:false}};
 const result=evaluateHistoricalCalibration([good,invalid,conflict]);
 assert.equal(result.eligibleCount,1);
 assert.equal(result.excludedCount,2);
 assert.equal(result.releasePermitted,false);
 assert.equal(result.chronologicalTrainingCount,0);
 assert.equal(result.chronologicalHoldoutCount,1);
 assert.equal(result.metrics[0].brierScore,0.09);
});
test("preview renders three outcomes, certainty, research gaps and expandable twelve levels",()=>{
 assert.match(page,/a\.predictions\.map/);
 assert.match(page,/a\.levels\.map/);
 assert.match(page,/<details/);
 assert.match(page,/not issued/);
 assert.match(page,/Independent prediction certainty/);
 assert.match(page,/HISTORICAL_CALIBRATION/);
 assert.match(page,/Automatic source watch/);
 assert.match(main,/medical-intelligence-preview\/advanced/);
 const analysis=fs.readFileSync(path.join(__dirname,"../lib/medical-intelligence-advanced.ts"),"utf8");
 assert.doesNotMatch(analysis,/\bfrom\s+["\x27][^"\x27]*(?:raas|survey)/i);
});
