const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
function load(name,deps={}){
 const code=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const js=ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(js,{module:m,exports:m.exports,require:key=>{
  if(!Object.hasOwn(deps,key))throw Error("Unexpected dependency: "+key);
  return deps[key];
 }});
 return m.exports;
}
const specialty=load("medical-intelligence-specialty");
const assessment=load("medical-intelligence-assessment-rankings");
const snapshot=load("medical-intelligence-phase-snapshot",{
 "./medical-intelligence-assessment-rankings":assessment
});
const {buildAllPhaseSubspecialtyReview}=load("medical-intelligence-specialty-all-phases",{
 "./medical-intelligence-specialty":specialty,
 "./medical-intelligence-assessment-rankings":assessment,
 "./medical-intelligence-phase-snapshot":snapshot
});
const nct="NCT06081894";
const stages=["EARLY_PHASE1","PHASE1","PHASE2","PHASE3","PHASE4","UNKNOWN"];
const profiles=specialty.CLINICAL_SPECIALTY_PROFILES;
function grade(phase,axis,grade=4){
 return {nct,phase,profileId:"cardiology",axis,status:"REVIEWED",grade,
  finding:"Original-source clinical interpretation with specific observed disease finding",
  counterEvidence:"Documented critical alternative and limitations for this observed finding",
  unresolvedRisk:"Durability of observed improvement and relevant long-term uncertainty",
  verifiedSourceUrls:["https://clinicaltrials.gov/study/"+nct],
  reviewedOn:"2026-11-08"};
}
test("every phase retains identical ten disease-specialty reasoning axes for every existing specialty profile",()=>{
 assert.ok(profiles.length>=16);
 for(const profile of profiles){
  const canonical=specialty.CLINICAL_SPECIALTY_AXES.map(x=>x.id).join(",");
  for(const stage of stages){
   const r=buildAllPhaseSubspecialtyReview(nct,stage,profile.id);
   assert.equal(r.axes.length,10);
   assert.equal(r.axes.map(x=>x.axis).join(","),canonical);
   assert.ok(r.axes.every(x=>x.phaseQuestion.length>20&&x.conditionSpecificChallenge.length>20));
   assert.ok(r.axes.every(x=>x.status==="NOT_CLINICALLY_ADJUDICATED"));
   assert.equal(r.score.provisionalScore,null);
   assert.equal(r.score.finalizedScore,null);
   assert.equal(r.clinicalSignoff,false);
   assert.equal(r.outcomeProbability,null);
  }
 }
});
test("Phase 1 keeps the same domains, but does not demand pivotal efficacy or a filing score",()=>{
 const r=buildAllPhaseSubspecialtyReview(nct,"PHASE1","cardiology");
 assert.equal(r.profile.id,"cardiology");
 assert.equal(r.score.requiredAxes,8);
 assert.equal(r.axes.filter(x=>x.expectation==="FORWARD_LOOKING").length,2);
 assert.match(r.axes[5].phaseQuestion,/no Phase 3 efficacy requirement/);
 assert.ok(r.riskQuestions.some(q=>q.domain==="SAFETY"));
 assert.ok(r.axes.every(x=>x.evidenceStandard.length>15));
});
test("phase-appropriate clinical grades are provisional until all required domains have source adjudication",()=>{
 const r=buildAllPhaseSubspecialtyReview(nct,"PHASE2","cardiology",[grade("PHASE2",1,4)]);
 assert.equal(r.score.status,"PARTIAL");
 assert.equal(r.score.provisionalScore,80);
 assert.equal(r.score.finalizedScore,null);
 assert.equal(r.score.reviewedRequiredAxes,1);
 assert.equal(r.score.unratedRequiredAxes,r.score.requiredAxes-1);
});
test("completed review averages only same-phase evidence-backed required axes, not future axes",()=>{
 const reviews=Array.from({length:8},(_,i)=>grade("PHASE1",i+1,4));
 reviews.splice(5,1);
 reviews.push(grade("PHASE1",9,5));
 const r=buildAllPhaseSubspecialtyReview(nct,"PHASE1","cardiology",reviews);
 assert.equal(r.score.status,"COMPLETE");
 assert.equal(r.score.finalizedScore,82.5);
 assert.equal(r.score.reviewedRequiredAxes,8);
});
test("future clinical outcome axes cannot falsely score, and unknown specialties are not guessed",()=>{
 assert.throws(()=>buildAllPhaseSubspecialtyReview(nct,"PHASE1","cardiology",[grade("PHASE1",6)]),/Forward-looking/);
 assert.throws(()=>buildAllPhaseSubspecialtyReview(nct,"UNKNOWN","cardiology",[grade("UNKNOWN",7)]),/Verified phase/);
 assert.equal(buildAllPhaseSubspecialtyReview(nct,"PHASE1","unlisted-specialty"),null);
 assert.throws(()=>buildAllPhaseSubspecialtyReview(nct,"PHASE2","cardiology",[{...grade("PHASE2",1),phase:"PHASE1"}]),/identity/);
 assert.throws(()=>buildAllPhaseSubspecialtyReview(nct,"PHASE2","cardiology",[{...grade("PHASE2",1),verifiedSourceUrls:[]}]),/original source citations/);
 assert.throws(()=>buildAllPhaseSubspecialtyReview(nct,"PHASE2","cardiology",[grade("PHASE2",1),grade("PHASE2",1)]),/uniqueness/);
});
