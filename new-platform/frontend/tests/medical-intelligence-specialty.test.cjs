const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
function load(name){
 const source=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(js,{module:m,exports:m.exports});
 return m.exports;
}
const {CLINICAL_SPECIALTY_PROFILES,CLINICAL_SPECIALTY_ASSIGNMENTS,CLINICAL_SPECIALTY_AXES,CLINICAL_SPECIALTY_STANDARDS,getSpecialtyProfile,getSpecialtyTasks}=load("medical-intelligence-specialty");
const {APPLICATION_CYCLES}=load("medical-intelligence-applications");
test("Every application cycle maps to one well-defined disease specialty without guessing",()=>{
 assert.equal(APPLICATION_CYCLES.length,23);
 assert.equal(Object.keys(CLINICAL_SPECIALTY_ASSIGNMENTS).length,APPLICATION_CYCLES.length);
 assert.equal(new Set(CLINICAL_SPECIALTY_PROFILES.map(p=>p.id)).size,CLINICAL_SPECIALTY_PROFILES.length);
 for(const a of APPLICATION_CYCLES){
  const p=getSpecialtyProfile(a.id);
  assert.ok(p,"Missing specialty mapping for "+a.id);
  assert.ok(p.specialty.length>10);
  assert.ok(p.clinicalContext.length>25);
  assert.ok(p.meaningfulOutcomes.length>25);
  assert.ok(p.seriousRisks.length>25);
  assert.ok(p.coreChallenge.length>30);
  const tasks=getSpecialtyTasks(a.id);
  assert.equal(tasks.length,10);
  assert.equal(new Set(tasks.map(t=>t.id)).size,10);
  for(const t of tasks){
   assert.equal(t.status,"NOT_CLINICALLY_ADJUDICATED");
   assert.ok(t.requiredEvidence.length>15);
   assert.ok(t.prompt.length>50);
  }
 }
 assert.equal(getSpecialtyProfile("random-id"),null);
 assert.equal(getSpecialtyTasks("random-id").length,0);
});
test("Specialty axis names reflect clinical reasoning, not survey scores or medical signoff",()=>{
 assert.equal(CLINICAL_SPECIALTY_AXES.length,10);
 const axes=CLINICAL_SPECIALTY_AXES.map(x=>x.name.toLowerCase()).join(" ");
 assert.ok(axes.includes("outcome"));
 assert.ok(axes.includes("harms"));
 assert.ok(axes.includes("fda"));
 assert.ok(CLINICAL_SPECIALTY_STANDARDS.every(s=>s.url.startsWith("https://www.fda.gov/")));
});
test("Separate indications and trial IDs receive appropriate different clinical reasoning",()=>{
 const ohcm=getSpecialtyProfile("cytk-aficamten-ohcm");
 const nonohcm=getSpecialtyProfile("cytk-aficamten-nhcm");
 assert.equal(ohcm?.id,"cardiology");
 assert.equal(nonohcm?.id,"cardiology");
 assert.equal(getSpecialtyProfile("srpt-casimersen")?.id,"neuromuscular");
 assert.equal(getSpecialtyProfile("capr-deramiocel")?.id,"neuromuscular");
 assert.notEqual(getSpecialtyProfile("phvs-ondemand")?.id,getSpecialtyProfile("cort-relacorilant")?.id);
});
