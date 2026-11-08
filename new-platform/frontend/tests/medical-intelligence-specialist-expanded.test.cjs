const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const dir=path.join(__dirname,"../lib");
const cache={};
function load(name){
 if(cache[name])return cache[name];
 const source=fs.readFileSync(path.join(dir,name+".ts"),"utf8");
 const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 vm.runInNewContext(js,{module,exports:module.exports,require:(request)=>{
  if(!request.startsWith("./"))throw Error("Unknown import "+request);
  return load(request.slice(2));
 }});
 cache[name]=module.exports;
 return module.exports;
}
const base=load("medical-intelligence-specialist-casebook");
const {EXPANDED_SPECIALIST_CASES,expandedSpecialistCaseForCycle}=load("medical-intelligence-specialist-expanded");
const {APPLICATION_CYCLES}=load("medical-intelligence-applications");
const {CLINICAL_SPECIALTY_ASSIGNMENTS}=load("medical-intelligence-specialty");

test("Eight expanded disease-specific cases with seven sourced clinical interpretations each",()=>{
 assert.equal(EXPANDED_SPECIALIST_CASES.length,8);
 assert.equal(new Set(EXPANDED_SPECIALIST_CASES.map(c=>c.cycleId)).size,8);
 assert.equal(new Set([...base.SPECIALIST_CASES,...EXPANDED_SPECIALIST_CASES].map(c=>c.cycleId)).size,11);
 const cycleIds=new Set(APPLICATION_CYCLES.map(x=>x.id));
 for(const c of EXPANDED_SPECIALIST_CASES){
  assert.ok(cycleIds.has(c.cycleId),"Not an active FOCUS application: "+c.cycleId);
  assert.ok(CLINICAL_SPECIALTY_ASSIGNMENTS[c.cycleId],"Missing specialty");
  assert.equal(c.completedSpecialistSignoff,false);
  assert.equal(c.conclusion,"PARTIAL_SOURCED_RESEARCH");
  assert.equal(c.dimensions.length,7);
  for(const d of c.dimensions){
   assert.ok(d.topic.length>=10);
   assert.ok(d.observedClinicalEvidence.length>70);
   assert.ok(d.specialistInterpretation.length>75);
   assert.ok(d.neededToResolve.length>65);
   assert.match(d.sourceUrl,/^https:\/\//);
   assert.match(d.sourceDate,/^20\d\d-\d\d-\d\d$/);
   assert.ok(d.sourceDate<="2026-11-07","Future-dated "+c.cycleId);
  }
  assert.equal(expandedSpecialistCaseForCycle(c.cycleId).medicalQuestion,c.medicalQuestion);
 }
 assert.equal(expandedSpecialistCaseForCycle("not-a-case"),null);
});
test("Distinct supplements and negative endpoint findings cannot be silently merged",()=>{
 const a=expandedSpecialistCaseForCycle("srpt-casimersen");
 const b=expandedSpecialistCaseForCycle("srpt-golodirsen");
 assert.notEqual(a.cycleId,b.cycleId);
 assert.match(JSON.stringify(a),/exon 45|exon-45/i);
 assert.match(JSON.stringify(b),/exon 53|exon-53/i);
 assert.match(JSON.stringify(a),/did not meet statistical significance/);
 assert.match(JSON.stringify(b),/did not meet statistical significance/);
 assert.match(JSON.stringify(expandedSpecialistCaseForCycle("mltx-sonelokimab")),/0.053/);
 assert.match(JSON.stringify(expandedSpecialistCaseForCycle("abvx-uc")),/0.1034/);
});
test("FDA accelerated approval vs follow-up full approval kept distinct",()=>{
 const v=expandedSpecialistCaseForCycle("vera-trutakna");
 const text=JSON.stringify(v);
 assert.match(text,/Week 36/);
 assert.match(text,/5.6/);
 assert.match(text,/104/);
 assert.match(text,/supplemental BLA/);
 assert.equal(v.completedSpecialistSignoff,false);
});

test("Retinal lesion surrogate and aldosterone-mediated safety questions stay separate from FDA-verified deficiencies",()=>{
 const retina=JSON.stringify(expandedSpecialistCaseForCycle("blte-stargardt"));
 assert.match(retina,/35.7%/);
 assert.match(retina,/post-hoc/);
 assert.match(retina,/visual function/);
 const bp=JSON.stringify(expandedSpecialistCaseForCycle("mlys-lorundrostat"));
 assert.match(bp,/hyperkalemia/i);
 assert.match(bp,/does not establish excess serious hyperkalemia/);
 assert.match(bp,/46%/);
});
