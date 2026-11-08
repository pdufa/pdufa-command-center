const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const ts=require("typescript");
function load(name){
 const f=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const compiled=ts.transpileModule(f,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(compiled,{module:m,exports:m.exports});
 return m.exports;
}
const {DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS}=load("medical-intelligence-master-depth");
const {rankScientificInvestigations,PRIORITY_ORDER,PRIORITY_PHASE_GUIDANCE}=load("medical-intelligence-phase-priority");
const NCT="NCT06081894";
const stages=["EARLY_PHASE1","PHASE1","PHASE2","PHASE3","PHASE4"];
const find=(report,id)=>report.tests.find(x=>x.id===id);
test("all verified clinical phases receive 800 distinct test ranks and exactly 100 per scientific layer",()=>{
 for(const phase of stages){
  const result=rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,phase);
  assert.equal(result.total,800);
  assert.equal(result.ranked,800);
  assert.equal(new Set(result.tests.map(x=>x.id)).size,800);
  assert.equal(new Set(result.tests.map(x=>x.rank)).size,800);
  assert.equal(result.tests[0].rank,1);
  assert.equal(result.tests[799].rank,800);
  for(const layer of ["disease","molecular","translational","trial","clinical","comparative","regulatory","integration"]){
   assert.equal(result.tests.filter(x=>x.layerId===layer).length,100);
  }
  assert.equal(PRIORITY_ORDER.map(tier=>result.counts[tier]).reduce((a,b)=>a+b,0),800);
  assert.ok(result.tests.every(x=>x.grade===null));
  assert.ok(result.tests.every(x=>x.basis==="PHASE_RELEVANCE"));
  assert.equal(result.tests.every((row,i)=>row.rank===i+1),true);
  assert.ok(PRIORITY_PHASE_GUIDANCE[phase].length>35);
 }
});
test("phase-dependent priorities shift without changing the scientific test identities",()=>{
 const p1=rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,"PHASE1");
 const p3=rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,"PHASE3");
 const p4=rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,"PHASE4");
 assert.equal(find(p1,"3.3:L1").priority,"CRITICAL");
 assert.equal(find(p3,"3.3:L1").priority,"HIGH");
 assert.equal(find(p1,"5.1:L1").priority,"MODERATE");
 assert.equal(find(p3,"5.1:L1").priority,"CRITICAL");
 assert.equal(find(p1,"7.5:L1").priority,"LOW");
 assert.equal(find(p1,"7.5:L1").phaseApplicability,"FORWARD_LOOKING");
 assert.equal(find(p3,"7.5:L1").priority,"HIGH");
 assert.equal(find(p4,"8.4:L1").priority,"CRITICAL");
 assert.equal(new Set(p1.tests.map(x=>x.id)).size,new Set(p3.tests.map(x=>x.id)).size);
});
test("no verified current phase means all 800 remain unranked instead of invented urgency",()=>{
 const unknown=rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,"UNKNOWN");
 assert.equal(unknown.total,800);
 assert.equal(unknown.ranked,0);
 assert.equal(unknown.counts.VERIFY_PHASE,800);
 assert.ok(unknown.tests.every(x=>x.rank===null&&x.priority==="VERIFY_PHASE"&&x.grade===null));
 assert.throws(()=>rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,"UNKNOWN",[risk()]),/Escalation requires/);
});
function risk(overrides={}){
 return {nct:NCT,phase:"PHASE2",assessmentId:"5.3",methodLevel:7,riskId:"risk001",
  severity:"CRITICAL",finding:"Independent dated current-cycle source identifies unresolved serious safety signal",
  sourceUrls:["https://clinicaltrials.gov/study/"+NCT],verifiedOn:"2026-11-08",verified:true,...overrides};
}
test("exact-NCT sourced risks elevate only their own verified scientific test priority",()=>{
 const without=rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,"PHASE2");
 const withRisk=rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,"PHASE2",
   [risk({assessmentId:"6.5",methodLevel:7})]);
 const key="6.5:L7";
 assert.equal(find(without,key).priority,"MODERATE");
 assert.equal(find(withRisk,key).priority,"CRITICAL");
 assert.equal(find(withRisk,key).basis,"VERIFIED_RISK");
 assert.equal(find(withRisk,key).matchedRiskIds[0],"risk001");
 assert.equal(find(withRisk,"6.5:L8").priority,"MODERATE");
 assert.equal(withRisk.total,800);
 assert.ok(find(withRisk,key).rank<find(without,key).rank);
});
test("reject unsourced or mismatched risk assertions",()=>{
 const bad=[
  risk({nct:"NCT99999999"}),risk({phase:"PHASE1"}),risk({verified:false}),
  risk({sourceUrls:[]}),risk({sourceUrls:["http://test.local/study"]}),
  risk({methodLevel:21}),risk({assessmentId:"9.1"}),risk({verifiedOn:"invalid"}),
  risk({finding:""}),risk({severity:"CRITICALISH"})
 ];
 for(const entry of bad){
  assert.throws(()=>rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,NCT,"PHASE2",[entry]),/Escalation requires/);
 }
});
test("invalid, incomplete or duplicate scientific hierarchy cannot produce rankings",()=>{
 assert.throws(()=>rankScientificInvestigations(DEEP_ASSESSMENTS.slice(0,39),SCIENTIFIC_LEVELS,NCT,"PHASE3"),/exact 40/);
 assert.throws(()=>rankScientificInvestigations(DEEP_ASSESSMENTS,[...SCIENTIFIC_LEVELS.slice(0,19),SCIENTIFIC_LEVELS[0]],NCT,"PHASE3"),/exact 20/);
 assert.throws(()=>rankScientificInvestigations(DEEP_ASSESSMENTS,SCIENTIFIC_LEVELS,"bad","PHASE3"),/exact NCT/);
});
