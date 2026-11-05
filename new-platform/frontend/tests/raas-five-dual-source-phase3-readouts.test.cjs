"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
 esModuleInterop:true}}).outputText,file);
const {parsePhase3CensusCsv}=require("../lib/phase3-census-rows.ts");
const {classifyPhase3Readouts}=require("../lib/phase3-public-readout.ts");
const {buildTopBottomRaasMetricWorklist}=require("../lib/raas-top-bottom-spreadsheet-worklist.ts");
const {buildRaasReadoutStageReviewQueue}=require("../lib/raas-readout-stage-review-queue.ts");
const manifest=JSON.parse(fs.readFileSync(path.join(root,"public/phase3-public-readout-evidence-2026-11-01.json"),"utf8"));
const recovered=require("../data/phase3_issuer_readout_additions_2026-11-05.json");
const census=parsePhase3CensusCsv(fs.readFileSync(path.join(root,"public/phase3-census-2026-10-26.csv"),"utf8")).rows;

test("five separately sourced exact NCT Phase 3 issuer results expand only BOTTOM; no pool rating",()=>{
 const c=classifyPhase3Readouts(manifest,census);
 assert.equal(c.total,741);
 assert.equal(c.pre.length,2);
 assert.equal(c.post.length,8);
 assert.equal(c.unverified.length,731);
 assert.equal(recovered.records.length,5);
 assert.equal(manifest.entries.length,10);
 assert.equal(recovered.counts.verifiedFdaRegulatoryOutcomes,0);
 assert.equal(recovered.counts.validatedOverallRaasScores,0);
 const proof=new Map(recovered.records.map(x=>[x.nctId,x]));
 const expected=new Map([
  ["NCT05186818",["CYTK","SEQUOIA-HCM","2023-12-27"]],
  ["NCT05767346",["CYTK","MAPLE-HCM","2025-05-13"]],
  ["NCT06081894",["CYTK","ACACIA-HCM","2026-05-05"]],
  ["NCT03697109",["CORT","GRACE","2024-05-28"]],
  ["NCT04308590",["CORT","GRADIENT","2024-10-30"]],
 ]);
 assert.equal(proof.size,5);
 for(const [nct,[ticker,acronym,date]] of expected){
  const p=proof.get(nct),matched=c.post.find(r=>r.nctId===nct);
  assert.ok(p&&matched,nct);
  assert.equal(matched.ticker,ticker);
  assert.equal(matched.evidence.issuerTrialName,acronym);
  assert.equal(matched.evidence.evidenceDate,date);
  assert.equal(matched.evidence.registryTrialUrl,"https://clinicaltrials.gov/study/"+nct);
  assert.equal(matched.evidence.kind,"POST_PUBLIC_READOUT");
  assert.match(matched.evidence.evidenceUrl,/^https:\/\/ir\.(cytokinetics|corcept)\.com\//);
 }
 const top=buildTopBottomRaasMetricWorklist("pre",c.pre);
 const bottom=buildTopBottomRaasMetricWorklist("post",c.post);
 assert.equal(top.summary.metricRequirementRows,60);
 assert.equal(bottom.summary.metricRequirementRows,240);
 assert.equal(top.summary.approvedOverallRaasScores,0);
 assert.equal(bottom.summary.approvedOverallRaasScores,0);
 assert.equal(bottom.summary.calibratedFdaForecasts,0);
 const research=buildRaasReadoutStageReviewQueue(c);
 assert.equal(research.summary.awaitingStageVerification,731);
 assert.equal(research.summary.raasRatingsAssignedByQueue,0);
});
test("different indications and same-ticker different NCTs are kept separate",()=>{
 const c=classifyPhase3Readouts(manifest,census);
 const acacia=c.post.find(x=>x.nctId==="NCT06081894");
 const maple=c.post.find(x=>x.nctId==="NCT05767346");
 assert.ok(acacia&&maple);
 assert.notEqual(acacia.evidence.issuerTrialName,maple.evidence.issuerTrialName);
 assert.notEqual(acacia.evidence.indication,maple.evidence.indication);
 const grace=c.post.find(x=>x.nctId==="NCT03697109");
 const gradient=c.post.find(x=>x.nctId==="NCT04308590");
 assert.notEqual(grace.evidence.issuerTrialName,gradient.evidence.issuerTrialName);
 assert.match(proofNote("NCT04308590"),/not statistically significant/i);
 function proofNote(nct){return recovered.records.find(x=>x.nctId===nct).reviewNote;}
});
test("source-manifest tampering or removing evidence crosswalk cannot promote incorrect trial",()=>{
 const mutate=fn=>{
  const a=structuredClone(manifest);
  fn(a);
  return ()=>classifyPhase3Readouts(a,census);
 };
 for(const mutateOne of [
  x=>x.entries.find(z=>z.nctId==="NCT05767346").ticker="CORT",
  x=>x.entries.find(z=>z.nctId==="NCT05767346").issuerTrialName="SEQUOIA-HCM",
  x=>x.entries.find(z=>z.nctId==="NCT05767346").registryTrialUrl=
    "https://clinicaltrials.gov/study/NCT05186818",
  x=>x.entries.find(z=>z.nctId==="NCT05767346").evidenceDate="2026-11-02",
  x=>x.entries.find(z=>z.nctId==="NCT05767346").drug="other",
  x=>x.entries.pop(),
  x=>x.sourceFiles.pop(),
  x=>x.entries.push({...x.entries[0]}),
 ]){
  const action=mutate(mutateOne);
  assert.throws(action,/Dated Phase 3 readout evidence did not pass identity/);
 }
});
test("the mobile TOP/BOTTOM table displays named issuer readout and registry link, not approved grade",()=>{
 const s=fs.readFileSync(path.join(root,"app/Phase3ReadoutSheets.tsx"),"utf8");
 assert.match(s,/data-raas-dual-source-acronym/);
 assert.match(s,/row\.evidence\.registryTrialUrl/);
 assert.match(s,/row\.evidence\.issuerTrialName/);
 assert.match(s,/downloadTopBottomRaasWorklist\(bucket,matched\)/);
 assert.doesNotMatch(s,/downloadTopBottomRaasWorklist\("unverified"/);
});
