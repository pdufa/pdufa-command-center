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
const {verifiedReadoutSurveyFeed}=require("../lib/phase3-survey-source.ts");
const {benefitForTrial}=require("../lib/benefit-assessments.ts");
const {readoutResearchCoverage}=require("../lib/phase3-readout-sort.ts");
const manifest=require("../public/phase3-public-readout-evidence-2026-11-01.json");
const reviewed=require("../data/phase3-readout-survey-research.json");
const source=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
const route=fs.readFileSync(require.resolve("../app/api/phase3-readout-survey/route.ts"),"utf8");
const clone=obj=>JSON.parse(JSON.stringify(obj));
const row=entry=>({nctId:entry.nctId,ticker:entry.ticker,company:entry.ticker,
 evidence:entry,sourceUrl:"https://clinicaltrials.gov/study/"+entry.nctId,status:"COMPLETED"});
test("readout feed has three exact documented issuer trials, not pre-release or unscreened pool records",()=>{
 const feed=verifiedReadoutSurveyFeed(reviewed,manifest);
 assert.deepEqual(feed.records.map(r=>r.nctId),
  ["NCT06445023","NCT06455202","NCT06641076"]);
 assert.ok(feed.records.every(x=>x.advantages.length===0));
 for(const rec of feed.records){
  const entry=manifest.entries.find(x=>x.nctId===rec.nctId);
  assert.equal(entry.kind,"POST_PUBLIC_READOUT");
  const found=benefitForTrial(feed,{nctId:rec.nctId,ticker:rec.ticker,
   drug:entry.drug,indication:entry.indication});
  assert.equal(found,rec);
  for(const f of Object.values(rec.facts)){
   assert.equal(f.status,"VERIFIED");
   assert.equal(f.sourceUrl,entry.evidenceUrl);
   assert.equal(f.sourceDate,entry.evidenceDate);
   assert.match(f.method,/Sponsor-reported/);
  }
 }
});
test("CSU1 versus CSU2 endpoints and subgroup values stay separate by NCT",()=>{
 const feed=verifiedReadoutSurveyFeed(reviewed,manifest);
 const first=feed.records[0],second=feed.records[1];
 assert.match(first.facts.magnitude.value,/9\.5/);
 assert.match(second.facts.magnitude.value,/8\.8/);
 assert.match(first.facts.responseRemission.value,/42\.4%/);
 assert.match(second.facts.responseRemission.value,/45\.7%/);
 assert.match(first.facts.treatmentResistantBenefit.value,/55\.3%/);
 assert.match(second.facts.treatmentResistantBenefit.value,/41\.7%/);
});
test("IZAR-1 keeps blinded placebo comparison unavailable and no efficacy effect size fabricated",()=>{
 const record=verifiedReadoutSurveyFeed(reviewed,manifest).records[2];
 assert.deepEqual(Object.keys(record.facts).sort(),["qualityOfLife","responseRemission"]);
 assert.match(record.facts.responseRemission.value,/42\.1%/);
 assert.match(record.facts.responseRemission.value,/Placebo comparative data remained blinded/);
 assert.equal(record.facts.clinicalBenefit,undefined);
 assert.equal(record.facts.magnitude,undefined);
 assert.equal(record.facts.safetyAdvantage,undefined);
});
test("source-matched issuer data populates survey coverage, but not validated final readiness",()=>{
 const feed=verifiedReadoutSurveyFeed(reviewed,manifest);
 for(const item of manifest.entries.filter(x=>x.kind==="POST_PUBLIC_READOUT")){
  const c=readoutResearchCoverage(row(item),"post",feed);
  assert.ok(c.verified>=2);
  assert.equal(c.ready,false);
  assert.ok(c.groupsVerified<5);
 }
 for(const item of manifest.entries.filter(x=>x.kind==="PRE_AS_OF_CHECK"))
  assert.equal(readoutResearchCoverage(row(item),"pre",feed),null);
});
test("false identity, source URLs, dates and duplicated programs all fail closed",()=>{
 const base=clone(reviewed);
 const variants=[
  d=>{d.records[0].ticker="MLTX";},
  d=>{d.records[0].drug="different drug";},
  d=>{d.records[0].indication="another condition";},
  d=>{d.records[0].facts.magnitude.sourceUrl="https://example.com/not-pinned";},
  d=>{d.records[0].facts.magnitude.sourceDate="2026-09-21";},
  d=>{d.records[0].facts.magnitude.status="MODELED";},
  d=>{d.records[0].facts.magnitude.method="Independent random clinical score";},
  d=>{d.records.push(clone(d.records[0]));},
  d=>{d.records.push({...clone(d.records[0]),nctId:"NCT07363577",ticker:"LBRX",drug:"LB-102 (100 mg tablet) | LB-102 (50 mg tablet)",indication:"Schizophrenia"});},
  d=>{d.sourceAsOf="2026-10-31";}
 ];
 for(const edit of variants){
  const v=clone(base);edit(v);
  assert.throws(()=>verifiedReadoutSurveyFeed(v,manifest));
 }
});
test("a matching registry trial ID with a wrong product name can never join by ticker alone",()=>{
 const feed=verifiedReadoutSurveyFeed(reviewed,manifest);
 assert.equal(benefitForTrial(feed,{nctId:"NCT06445023",ticker:"CLDX",
  drug:"another barzolvolimab product",indication:"chronic spontaneous urticaria"}),null);
 assert.equal(benefitForTrial(feed,{nctId:"NCT00000000",ticker:"CLDX",
  drug:"barzolvolimab",indication:"chronic spontaneous urticaria"}),null);
});
test("Phase 3 source endpoint is authenticated, independent from Pipeline and used by both survey dialogs",()=>{
 assert.match(route,/authConfigured\(\)/);
 assert.match(route,/hasSession\(req\.cookies\.get\(COOKIE_NAME\)/);
 assert.match(route,/verifiedReadoutSurveyFeed\(research,manifest\)/);
 assert.match(route,/status:401/);
 assert.match(route,/status:503/);
 assert.match(route,/private, no-store/);
 assert.match(source,/fetch\("\/api\/phase3-readout-survey"/);
 assert.match(source,/Issuer-disclosed topline observations are source-matched/);
 assert.match(source,/not independent adjudication of efficacy or safety/);
 assert.doesNotMatch(route,/benefitsFromPipeline/);
});
