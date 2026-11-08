const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const cache={};
function load(name){
 if(cache[name])return cache[name];
 const source=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(compiled,{module:m,exports:m.exports,require:dependency=>{
  if(!dependency.startsWith("./"))throw Error("Unexpected dependency "+dependency);
  return load(dependency.slice(2));
 }});
 cache[name]=m.exports;
 return m.exports;
}
const apps=load("medical-intelligence-applications");
const all=load("medical-intelligence-specialist-all");
const original=load("medical-intelligence-specialist-casebook");
const expanded=load("medical-intelligence-specialist-expanded");
const w1=load("medical-intelligence-specialist-wave-one");
const w2=load("medical-intelligence-specialist-wave-two");
test("All 23 distinct FDA application cycles have a partial seven-dimension specialty case, not a completed MD review",()=>{
 assert.equal(apps.APPLICATION_CYCLES.length,23);
 assert.equal(original.SPECIALIST_CASES.length,3);
 assert.equal(expanded.EXPANDED_SPECIALIST_CASES.length,8);
 assert.equal(w1.SPECIALIST_WAVE_ONE.length,6);
 assert.equal(w2.SPECIALIST_WAVE_TWO.length,6);
 assert.equal(all.ALL_SPECIALIST_CASES.length,23);
 assert.equal(new Set(all.ALL_SPECIALIST_CASES.map(c=>c.cycleId)).size,23);
 const expected=new Set(apps.APPLICATION_CYCLES.map(a=>a.id));
 for(const c of all.ALL_SPECIALIST_CASES){
  assert.ok(expected.has(c.cycleId),"Unknown FDA cycle "+c.cycleId);
  assert.equal(c.dimensions.length,7,c.cycleId);
  assert.equal(c.conclusion,"PARTIAL_SOURCED_RESEARCH");
  assert.equal(c.completedSpecialistSignoff,false);
  assert.match(c.source,/^https:\/\//);
  assert.ok(c.medicalQuestion.length>65);
  assert.equal(all.getFullSpecialistCase(c.cycleId).cycleId,c.cycleId);
 }
 for(const id of expected)assert.ok(all.getFullSpecialistCase(id),"Missing "+id);
 assert.equal(all.getFullSpecialistCase("NONSENSE"),null);
});
test("All newly researched clinical interpretations have an individual date and source, not simulated medical signoff",()=>{
 const coverage=all.getSpecialistDepthCoverage();
 assert.equal(coverage.length,23);
 assert.equal(coverage.reduce((n,x)=>n+x.clinicalDimensions,0),161);
 assert.equal(coverage.reduce((n,x)=>n+x.sourceLinkedDimensions,0),140);
 for(const c of [...expanded.EXPANDED_SPECIALIST_CASES,...w1.SPECIALIST_WAVE_ONE,...w2.SPECIALIST_WAVE_TWO]){
  for(const d of c.dimensions){
   assert.match(d.sourceDate,/^20\d\d-\d\d-\d\d$/);
   assert.ok(d.sourceDate<="2026-11-07","Future source "+c.cycleId+": "+d.sourceDate);
   assert.match(d.sourceUrl,/^https:\/\//);
   assert.ok(d.topic.length>=10,c.cycleId+" missing topic");
   for(const prop of ["observedClinicalEvidence","specialistInterpretation","neededToResolve"])
    assert.ok(d[prop].length>35,c.cycleId+" missing "+prop);
  }
 }
 for(const c of coverage){
  assert.equal(c.completedClinicalAdjudication,false);
  assert.equal(c.completedPhysicianSignoff,false);
  assert.equal(c.clinicalStatus,"PARTIAL_SOURCED_RESEARCH");
 }
});
test("No conflation of separate disease indications and pending versus prior approval",()=>{
 const ohcm=all.getFullSpecialistCase("cytk-aficamten-ohcm");
 const nhcm=all.getFullSpecialistCase("cytk-aficamten-nhcm");
 assert.match(JSON.stringify(ohcm),/already-approved|already approved|approved indication/i);
 assert.match(JSON.stringify(nhcm),/10%/);
 assert.notEqual(ohcm.cycleId,nhcm.cycleId);
 const ir=all.getFullSpecialistCase("phvs-ondemand");
 const xr=all.getFullSpecialistCase("phvs-prophylaxis");
 assert.match(JSON.stringify(ir),/1.28 hours/);
 assert.match(JSON.stringify(xr),/83%/);
 assert.match(JSON.stringify(xr),/planned/);
 assert.notEqual(ir.cycleId,xr.cycleId);
});
test("Real tradeoffs remain visible instead of being hidden behind positive primary p-values",()=>{
 const p=all.getFullSpecialistCase("prax-ulixacaltamide");
 assert.match(JSON.stringify(p),/27.0%/);
 assert.match(JSON.stringify(p),/1.7%/);
 const ad=all.getFullSpecialistCase("apmd-ad109");
 assert.match(JSON.stringify(ad),/21.2%/);
 assert.match(JSON.stringify(ad),/3.1%/);
 const ach=all.getFullSpecialistCase("achv-cytisinicline");
 assert.match(JSON.stringify(ach),/manufactur/i);
 assert.match(JSON.stringify(ach),/not clinical efficacy\/safety/i);
 const z=all.getFullSpecialistCase("zbio-obexelimab");
 assert.match(JSON.stringify(z),/0.44/);
});
