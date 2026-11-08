"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
 mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const {checkPhase3PublishedArithmetic}=require("../lib/phase3-published-arithmetic.ts");
const {phase3ScientificEvidenceAudit}=require("../lib/phase3-scientific-evidence-audit.ts");
const {verifiedReadoutSurveyFeed}=require("../lib/phase3-survey-source.ts");
const raw=require("../data/phase3-readout-survey-research.json");
const manifest=require("../public/phase3-public-readout-evidence-2026-11-01.json");
const file=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
const feed=verifiedReadoutSurveyFeed(raw,manifest);
const [csu1,csu2,izar]=feed.records;
const clone=x=>JSON.parse(JSON.stringify(x));
const aud=rec=>phase3ScientificEvidenceAudit(rec).checks.find(c=>c.id==="comparator");
test("primary effect uses placebo minus active, rates use active minus placebo, exact trial only",()=>{
 const one=checkPhase3PublishedArithmetic(csu1);
 const two=checkPhase3PublishedArithmetic(csu2);
 assert.deepEqual([one.uas7ExtraReduction,one.week12ExtraResponsePp,one.week24ExtraResponsePp],[9.5,33.1,33.6]);
 assert.deepEqual([two.uas7ExtraReduction,two.week12ExtraResponsePp,two.week24ExtraResponsePp],[8.8,33.1,36.4]);
 assert.equal(one.totalRandomized,963); assert.equal(two.totalRandomized,976);
 assert.equal(one.regimen,"150 mg every 4 weeks");
 assert.equal(two.regimen,"150 mg every 4 weeks");
 assert.equal(one.nctId,"NCT06445023");
 assert.equal(two.nctId,"NCT06455202");
 assert.notEqual(one.trial,two.trial);
 assert.match(one.issuerUrl,/celldex\.gcs-web\.com/);
 assert.match(one.filedCopyUrl,/www\.sec\.gov\/Archives\/edgar/);
 assert.ok(one.limitations.some(s=>s.includes("not independent clinical validation")));
 assert.ok(one.limitations.some(s=>s.includes("No NNT, CI")));
 assert.ok(one.limitations.some(s=>s.includes("separate snapshots")));
});
test("no unblinded placebo effect-size is invented for IZAR-1, missing data or unmatched products",()=>{
 assert.equal(checkPhase3PublishedArithmetic(izar),null);
 assert.equal(checkPhase3PublishedArithmetic(null),null);
 assert.equal(checkPhase3PublishedArithmetic({...csu1,ticker:"MLTX"}),null);
 assert.equal(checkPhase3PublishedArithmetic({...csu1,nctId:csu2.nctId}),null);
 assert.equal(checkPhase3PublishedArithmetic({...csu1,indication:"other indication"}),null);
 assert.equal(aud(izar).status,"NOT_ESTABLISHED");
});
test("every required fact is checked against source, date and exact-arm published number",()=>{
 for(const key of ["clinicalBenefit","magnitude","responseRemission","durability"]){
  const missing=clone(csu1);delete missing.facts[key];
  assert.equal(checkPhase3PublishedArithmetic(missing),null,key);
  const invalid=clone(csu1);invalid.facts[key].value="Unmatched primary estimate";
  assert.equal(checkPhase3PublishedArithmetic(invalid),null,key);
  const unsourced=clone(csu1);unsourced.facts[key].sourceUrl="https://other.example.org/table";
  assert.equal(checkPhase3PublishedArithmetic(unsourced),null,key);
  const wrongDate=clone(csu1);wrongDate.facts[key].sourceDate="2026-09-21";
  assert.equal(checkPhase3PublishedArithmetic(wrongDate),null,key);
  const modeled=clone(csu1);modeled.facts[key].status="MODELED";
  assert.equal(checkPhase3PublishedArithmetic(modeled),null,key);
 }
});
test("unsupported numerical comparison claims are rejected despite scientific-sounding keywords",()=>{
 const counterfeit=clone(csu1);
 counterfeit.facts.clinicalBenefit.value="vs placebo; difference statistically significant";
 counterfeit.facts.magnitude.value="placebo-adjusted claim but no source-matched numbers";
 assert.equal(aud(counterfeit).status,"NOT_ESTABLISHED");
 assert.equal(aud(csu1).status,"DOCUMENTED");
 assert.equal(aud(csu2).status,"DOCUMENTED");
});
test("recalculations do not add any new verified SURVEY questions or efficacy scores",()=>{
 const rec=clone(csu1);
 const count=Object.keys(rec.facts).length;
 const audited=checkPhase3PublishedArithmetic(rec);
 assert.ok(audited);
 assert.equal(Object.keys(rec.facts).length,count);
 assert.equal(audited.limitations.length,6);
 assert.ok(!("fdaProbability" in audited));
 assert.ok(!("numericalClinicalGrade" in audited));
 assert.ok(!("confidenceInterval" in audited));
});
test("SURVEY renders clear provenance and uncertainty inside scientific checklist",()=>{
 assert.match(file,/checkPhase3PublishedArithmetic\(record\)/);
 assert.match(file,/Exact-trial published effect-size arithmetic/);
 assert.match(file,/Week 12 UAS7 extra mean reduction versus placebo/);
 assert.match(file,/Week 24 complete-response difference/);
 assert.match(file,/SEC-filed copy of the same company release/);
 assert.match(file,/No effect-size difference, confidence interval, NNT or FDA likelihood is imputed/);
 assert.match(file,/arithmeticAudit\.limitations\.map/);
});
