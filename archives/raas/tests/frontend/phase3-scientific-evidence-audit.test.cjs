"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
 mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
 esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}
 }).outputText,file);
const {verifiedReadoutSurveyFeed}=require("../lib/phase3-survey-source.ts");
const {phase3ScientificEvidenceAudit}=require("../lib/phase3-scientific-evidence-audit.ts");
const {readoutResearchCoverage}=require("../lib/phase3-readout-sort.ts");
const data=require("../data/phase3-readout-survey-research.json");
const manifest=require("../public/phase3-public-readout-evidence-2026-11-01.json");
const source=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
const feed=verifiedReadoutSurveyFeed(data,manifest);
const [csu1,csu2,izar]=feed.records;
function byId(r,id){return phase3ScientificEvidenceAudit(r).checks.find(x=>x.id===id);}
test("each CSU trial adds precisely one non-longitudinal Week 24 response field",()=>{
 const trials=[
  [csu1,"49.0%","15.4%","42.4%","9.3%"],
  [csu2,"54.0%","17.6%","45.7%","12.6%"]
 ];
 for(const [r,active24,placebo24,active12,placebo12] of trials){
  const field=r.facts.durability;
  assert.ok(field);
  assert.equal(field.status,"VERIFIED");
  assert.equal(field.sourceDate,"2026-09-22");
  for(const v of [active24,placebo24,active12,placebo12])
   assert.ok(field.value.includes(v),r.nctId+" needs "+v);
  assert.match(field.value,/separate timepoint proportions/);
  assert.match(field.value,/does not establish individual uninterrupted response persistence/);
  assert.match(field.method,/Not an independent patient-level longitudinal dataset audit/);
  assert.equal(field.sourceUrl,manifest.entries.find(e=>e.nctId===r.nctId).evidenceUrl);
  assert.deepEqual(Object.keys(r.facts).sort(),[
    "clinicalBenefit","durability","magnitude","responseRemission","treatmentResistantBenefit"
  ]);
 }
});
test("documented comparative response and timepoints do not make a trial's full SURVEY ready",()=>{
 for(const r of [csu1,csu2]){
  const evidence=manifest.entries.find(e=>e.nctId===r.nctId);
  const coverage=readoutResearchCoverage({nctId:r.nctId,ticker:r.ticker,
   company:r.ticker,status:"COMPLETED",evidence,sourceUrl:"https://clinicaltrials.gov/study/"+r.nctId},
   "post",feed);
  assert.equal(coverage.verified,5);
  assert.equal(coverage.ready,false);
  assert.equal(coverage.groupsVerified<5,true);
 }
 const audit=phase3ScientificEvidenceAudit(izar);
 assert.equal(Object.keys(izar.facts).length,2);
 assert.equal(byId(izar,"comparator").status,"NOT_ESTABLISHED");
 assert.equal(byId(izar,"later").status,"NOT_ESTABLISHED");
 assert.equal(byId(izar,"safety").status,"NOT_ESTABLISHED");
 assert.equal(byId(izar,"independent").status,"NOT_ESTABLISHED");
 assert.equal(byId(izar,"fda").status,"NOT_ESTABLISHED");
 assert.equal(audit.documented,1);
});
test("scientific validation gate distinguishes reported comparison from independent adjudication",()=>{
 const record=phase3ScientificEvidenceAudit(csu1);
 assert.equal(record.checks.length,6);
 assert.equal(record.documented,3);
 assert.equal(record.gaps,3);
 for(const key of ["issuer","comparator","later"])
  assert.equal(byId(csu1,key).status,"DOCUMENTED");
 for(const key of ["safety","independent","fda"])
  assert.equal(byId(csu1,key).status,"NOT_ESTABLISHED");
 assert.match(byId(csu1,"later").detail,/Different timepoint proportions/);
 assert.match(byId(csu1,"safety").detail,/qualitative/);
 assert.match(byId(csu1,"fda").detail,/not a filed\/accepted application/);
});
test("absent or unrecognized trial evidence fails closed",()=>{
 const empty=phase3ScientificEvidenceAudit(null);
 assert.equal(empty.documented,0);
 assert.equal(empty.gaps,6);
 const noPlacebo=JSON.parse(JSON.stringify(csu1));
 noPlacebo.facts.clinicalBenefit.value="150mg response rate only; no comparator";
 assert.equal(byId(noPlacebo,"comparator").status,"NOT_ESTABLISHED");
 const noFollowup=JSON.parse(JSON.stringify(csu1));
 delete noFollowup.facts.durability;
 assert.equal(byId(noFollowup,"later").status,"NOT_ESTABLISHED");
});
test("final SURVEY exposes scientific audit separately from readiness and forecast",()=>{
 assert.match(source,/phase3ScientificEvidenceAudit\(record\)/);
 assert.match(source,/Phase 3 scientific evidence verification checklist/);
 assert.match(source,/Scientific validation checkpoints/);
 assert.match(source,/independent adjudication/);
 assert.match(source,/Do not promote this checklist into the numerical medical grade/);
 assert.match(source,/FDA decision forecast:\s*<\/strong> ABSTAIN/);
});
