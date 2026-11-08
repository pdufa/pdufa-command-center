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
 const code=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 vm.runInNewContext(code,{module,exports:module.exports,require:spec=>{
  if(!spec.startsWith("./"))throw Error("Unexpected dependency "+spec);
  return load(spec.slice(2));
 }});
 cache[name]=module.exports;
 return module.exports;
}
const {APPLICATION_CYCLES}=load("medical-intelligence-applications");
const {buildSpecialtyEvidenceAudit,allSpecialtyEvidenceAudits}=load("medical-intelligence-specialty-evidence");
const {findingsForNct}=load("medical-intelligence-reviewed-findings");

test("Every source-reconstructed FOCUS application has 10 clinical axes and is not falsely marked adjudicated",()=>{
 const audits=allSpecialtyEvidenceAudits();
 assert.equal(audits.length,23);
 assert.equal(new Set(audits.map(a=>a.cycleId)).size,23);
 for(const a of audits){
  const cycle=APPLICATION_CYCLES.find(c=>c.id===a.cycleId);
  assert.ok(cycle);
  assert.equal(a.axes.length,10);
  assert.equal(a.clinicalEvaluationStatus,"INCOMPLETE_NOT_PHYSICIAN_REVIEWED");
  assert.equal(a.sourceBackedAxes+a.uncoveredAxes,10);
  assert.equal(new Set(a.axes.map(x=>x.axis)).size,10);
  const exactUnique=new Set(cycle.ncts.flatMap(n=>findingsForNct(n).map(f=>f.id)));
  assert.equal(a.uniqueSourceFindings,exactUnique.size);
  for(const axis of a.axes){
   assert.ok(["RELEVANT_SOURCE_FOUND_REVIEW_PENDING","NO_CURATED_SOURCE_YET"].includes(axis.status));
   assert.equal(axis.researchTask.status,"NOT_CLINICALLY_ADJUDICATED");
   assert.equal(axis.sourceCount,axis.supportingSourceFindings.length);
   assert.equal(axis.status,axis.sourceCount?"RELEVANT_SOURCE_FOUND_REVIEW_PENDING":"NO_CURATED_SOURCE_YET");
   for(const f of axis.supportingSourceFindings)assert.ok(exactUnique.has(f.id),"Leaked source across FDA applications");
  }
 }
 assert.equal(buildSpecialtyEvidenceAudit("unknown"),null);
});
test("No assumed clean slate: a gap is not absence of FDA risk",()=>{
 const a=buildSpecialtyEvidenceAudit("vera-trutakna");
 assert.ok(a.axes.some(x=>x.sourceCount===0));
 for(const axis of a.axes.filter(x=>x.sourceCount===0))
   assert.ok(axis.notes.some(note=>note.includes("research-coverage gap")));
});
test("Historical CRLs and confirmed review-clock extensions explicitly distinguished from forecasts",()=>{
 const capr=buildSpecialtyEvidenceAudit("capr-deramiocel");
 assert.ok(capr.axes.some(axis=>axis.notes.some(n=>n.includes("Historical FDA actions"))));
 assert.equal(capr.clinicalEvaluationStatus,"INCOMPLETE_NOT_PHYSICIAN_REVIEWED");
});
