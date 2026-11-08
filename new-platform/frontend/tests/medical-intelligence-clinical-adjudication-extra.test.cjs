const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const cache={};
function load(name){
 if(cache[name])return cache[name];
 const p=path.join(__dirname,"../lib/"+name+".ts");
 const js=ts.transpileModule(fs.readFileSync(p,"utf8"),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(js,{module:m,exports:m.exports,require:dep=>{
   if(!dep.startsWith("./"))throw Error("Unexpected "+dep);
   return load(dep.slice(2));
 }});
 cache[name]=m.exports;return m.exports;
}
const {APPLICATION_CYCLES}=load("medical-intelligence-applications");
const {ADJUDICATION_CASES,INVESTIGATION_PRIORITIES,adjudicationForCycle,getAdjudicationCase}=load("medical-intelligence-clinical-adjudication");
const {ADDITIONAL_ADJUDICATION_CASES}=load("medical-intelligence-clinical-adjudication-extra");
test("Second wave has eight separate verified regulatory research topics",()=>{
 assert.equal(ADDITIONAL_ADJUDICATION_CASES.length,8);
 assert.equal(ADJUDICATION_CASES.length,11);
 assert.equal(new Set(ADJUDICATION_CASES.map(x=>x.cycleId)).size,11);
 const ids=new Set();
 for(const c of ADDITIONAL_ADJUDICATION_CASES){
  assert.ok(!ids.has(c.id));ids.add(c.id);
  const app=APPLICATION_CYCLES.find(a=>a.id===c.cycleId);
  assert.ok(app);
  assert.ok(app.ncts.includes(c.nct));
  assert.equal(c.researchDate,"2026-11-07");
  assert.equal(c.verdict,"UNRESOLVED_REQUIRES_INDEPENDENT_ADJUDICATION");
  assert.equal(c.timing,"NO_NEW_TIMING_EVENT_PROVEN");
  assert.ok(c.sources.some(s=>s.role==="FAVORABLE"));
  assert.ok(c.sources.some(s=>s.role==="CHALLENGING"));
  assert.ok(c.sources.length>=3);
  assert.ok(c.whatWouldResolve.length>=4);
  assert.ok(c.clinicalSynthesis.length>100);
  for(const source of c.sources){
    assert.ok(app.ncts.includes(source.trial),"Incorrect trial: "+source.id);
    assert.match(source.url,/^https:\/\//);
    assert.match(source.date,/^20\d\d-\d\d-\d\d$/);
    assert.ok(source.date<=c.researchDate);
    assert.ok(source.limits.length>60);
  }
  assert.equal(getAdjudicationCase(c.id).cycleId,c.cycleId);
  assert.equal(adjudicationForCycle(c.cycleId).length,1);
 }
});
test("Direct FDA CRL concerns CMC and labeling, not a fabricated failed cytisinicline endpoint",()=>{
 const c=getAdjudicationCase("achv-cgmp-crl");
 assert.equal(c.category,"CMC_AND_FACILITY");
 assert.equal(c.mode,"REGULATORY_OBJECTION");
 assert.equal(c.sources.filter(s=>s.type==="FDA_ACTION_LETTER").length,2);
 assert.match(c.sources.find(s=>s.id==="achv-crl-facility").result,/Form 483/);
 assert.match(c.sources.find(s=>s.id==="achv-new-facility").limits,/not equivalent/);
 assert.equal(APPLICATION_CYCLES.find(a=>a.id===c.cycleId).reportedGoal,null);
});
test("Historical VERA FDA limitation not misrepresented as new eGFR rejection",()=>{
 const c=getAdjudicationCase("vera-egfr-confirmation");
 assert.equal(c.sources.find(s=>s.id==="vera-original-fda").type,"FDA_REVIEWER");
 assert.match(c.sources.find(s=>s.id==="vera-original-fda").result,/Week 36/);
 assert.match(c.sources.find(s=>s.id==="vera-egfr104").result,/5\.0/);
 assert.match(c.sourceInterpretation,/earlier evidence cutoff/);
 assert.equal(APPLICATION_CYCLES.find(a=>a.id===c.cycleId).reportedGoal,null);
});
test("CORT GRADIENT evidence uses linked GRADIENT NCT, not GRACE NCT",()=>{
 const c=getAdjudicationCase("cort-global-test");
 assert.equal(c.nct,"NCT03697109");
 const gradient=c.sources.find(s=>s.id==="cort-gradient");
 assert.equal(gradient.trial,"NCT04308590");
 assert.ok(APPLICATION_CYCLES.find(a=>a.id===c.cycleId).ncts.includes(gradient.trial));
 assert.match(c.sources.find(s=>s.id==="cort-global").limits,/patient-level/);
});
test("Regulatory scope and subgroup/safety contrasts remain independent by application",()=>{
 const a=getAdjudicationCase("srpt-casimersen-essence");
 const b=getAdjudicationCase("srpt-golodirsen-essence");
 assert.equal(a.nct,b.nct);
 assert.notEqual(a.cycleId,b.cycleId);
 assert.match(a.title,/exon-45/);
 assert.match(b.title,/exon-53/);
 assert.equal(a.sources[0].role,"CHALLENGING");
 assert.equal(b.sources[0].role,"CHALLENGING");
 assert.match(getAdjudicationCase("cogt-gist-liver-benefitrisk").sources.find(s=>s.id==="cogt-hepatic").result,/10\.8%/);
 assert.match(getAdjudicationCase("prax-tremor-tolerability").sources.find(s=>s.id==="prax-adverse").result,/63\/233/);
 assert.match(getAdjudicationCase("svra-dlco-function").sources.find(s=>s.id==="svra-qol48").result,/0\.1046/);
 const pending=INVESTIGATION_PRIORITIES.filter(x=>x.detailedCaseCount);
 assert.equal(pending.length,11);
 assert.equal(INVESTIGATION_PRIORITIES.length,22);
});
