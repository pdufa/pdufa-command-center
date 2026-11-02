"use strict";
const {test}=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const ts=require("typescript");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>
 mod._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
 esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX}}).outputText,file);
const {phase3RegistryConcordance}=require("../lib/phase3-registry-concordance.ts");
const {verifiedReadoutSurveyFeed}=require("../lib/phase3-survey-source.ts");
const ledger=require("../data/phase3-protocol-registry-checks.json");
const readout=require("../data/phase3-readout-survey-research.json");
const manifest=require("../public/phase3-public-readout-evidence-2026-11-01.json");
const source=fs.readFileSync(require.resolve("../app/Phase3ReadoutSheets.tsx"),"utf8");
const records=verifiedReadoutSurveyFeed(readout,manifest).records;
const clone=x=>JSON.parse(JSON.stringify(x));
test("all three exact NCTs have an aligned, source-linked registered primary outcome",()=>{
 assert.deepEqual(ledger.records.map(x=>x.nctId),records.map(x=>x.nctId));
 for(const record of records){
  const audit=phase3RegistryConcordance(record,ledger.records);
  assert.equal(audit.status,"PROTOCOL_ALIGNED",record.nctId);
  assert.match(audit.design,/randomized · blinded · placebo-controlled/);
  assert.equal(audit.registryUrl,"https://clinicaltrials.gov/study/"+record.nctId);
  assert.equal(audit.registryMirrorUrl,"https://ichgcp.net/clinical-trials-registry/"+record.nctId);
  assert.match(audit.uncertainty,/not independently|not independent|not an independently|independent/i);
  assert.ok(!("fdaProbability" in audit));
  assert.ok(!("scientificGrade" in audit));
 }
});
test("CSU records match Week 12 UAS7 primary, and 2026-03-25 registration update predates sponsor readout",()=>{
 for(const rec of records.slice(0,2)){
  const a=phase3RegistryConcordance(rec,ledger.records);
  assert.equal(a.primaryOutcome,"Mean change from baseline in UAS7 · Week 12");
  assert.equal(a.snapshotDate,"2026-03-25");
  assert.equal(a.snapshotPredatesDisclosure,true);
 }
});
test("IZAR-1 matches Week 16 ACR50 without inventing unblinded placebo results or historical preregistration",()=>{
 const a=phase3RegistryConcordance(records[2],ledger.records);
 assert.equal(a.primaryOutcome,"Proportion achieving ACR50 response · Week 16");
 assert.equal(a.snapshotPredatesDisclosure,false);
 assert.match(a.uncertainty,/Historical prespecification requires version-history inspection/);
 assert.equal(records[2].facts.magnitude,undefined);
 assert.equal(records[2].facts.clinicalBenefit,undefined);
});
test("missing source, duplicates, wrong trial, false timepoint and alternate therapy fail closed",()=>{
 assert.equal(phase3RegistryConcordance(null,ledger.records).status,"NOT_ESTABLISHED");
 const original=records[0];
 const noSource=clone(original);delete noSource.facts.clinicalBenefit;
 const altered=clone(original);altered.facts.clinicalBenefit.value="Week 16 ACR50 response";
 for(const record of [noSource,altered,{...original,nctId:"NCT00000000"},
  {...original,drug:"different"},{...original,ticker:"MLTX"},{...original,indication:"different"}])
  assert.equal(phase3RegistryConcordance(record,ledger.records).status,"NOT_ESTABLISHED");
 assert.equal(phase3RegistryConcordance(original,[...ledger.records,ledger.records[0]]).status,"NOT_ESTABLISHED");
 const wrong=clone(ledger.records);wrong[0].primaryWeek=24;
 assert.equal(phase3RegistryConcordance(original,wrong).status,"NOT_ESTABLISHED");
 const noPlacebo=clone(ledger.records);noPlacebo[0].placeboControlled=false;
 assert.equal(phase3RegistryConcordance(original,noPlacebo).status,"NOT_ESTABLISHED");
});
test("registered endpoint concordance is not counted as verified clinical outcomes or survey evidence",()=>{
 const rec=clone(records[0]);
 const before=Object.keys(rec.facts).length;
 const a=phase3RegistryConcordance(rec,ledger.records);
 assert.equal(a.status,"PROTOCOL_ALIGNED");
 assert.equal(Object.keys(rec.facts).length,before);
 assert.match(a.uncertainty,/not an independently verified treatment effect/);
});
test("final SURVEY displays registry and issuer links and clear limitations",()=>{
 assert.match(source,/phase3RegistryConcordance\(record,protocolRegistry\.records\)/);
 assert.match(source,/Cross-source Phase 3 registered protocol alignment/);
 assert.match(source,/ClinicalTrials.gov protocol cross-check/);
 assert.match(source,/Public registry-text mirror/);
 assert.match(source,/Original issuer result/);
 assert.match(source,/does not increase any of the 38 SURVEY evidence counts/);
});
