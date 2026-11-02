"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText,file);
const raw=require("../data/raas-prospective-source-baselines.json");
const pilot=require("../data/raas-pilot-observations.json");
const tradingHistory=require("../data/raas-historical-cases.json");
const metricHistory=require("../data/raas-historical-metric-snapshots.json");
const calibration=require("../data/raas-approved-calibrations.json");
const reviewed=require("../data/raas-reviewed-snapshots.json");
const mod=require("../lib/raas-prospective-source-baselines.ts");
const clone=()=>JSON.parse(JSON.stringify(raw));
test("Two source-dated pre-readout TOP baselines have exact prior pilot trial identities",()=>{
 const feed=mod.parseProspectiveSourceBaselines(raw);
 assert.equal(feed.records.length,2);
 const x=feed.records[0];
 assert.equal(x.ticker,"LBRX");
 assert.equal(x.nctId,"NCT07363577");
 assert.equal(x.stage,"pre");
 assert.equal(x.capturedOn,"2026-11-02");
 assert.equal(x.marketCap.usdMillions,1280);
 assert.equal(x.marketCap.observedAsOf,"2026-10-30");
 assert.equal(x.marketCap.verification,"VENDOR_REPORTED_NOT_INDEPENDENTLY_AUDITED");
 const original=pilot.records.find(p=>p.nctId===x.nctId);
 assert.ok(original);
 assert.equal(x.ticker,original.ticker);
 assert.equal(x.drug,original.drug);
 assert.equal(x.indication.toLowerCase(),original.indication.toLowerCase());
 assert.equal(x.observations.length,4);
 assert.ok(x.observations.every(o=>o.sourcePublishedAt<=x.capturedOn));
 assert.deepEqual(mod.prospectiveSourceSummary(feed),{
  baselines:2,distinctPrograms:2,distinctIssuers:2,recordedSourceFacts:9,
  numericRaasScores:0,validatedHistoricalOutcomes:0
 });
});
test("TRVI NAL ER OCEAN-1 has source-backed prior efficacy and H1 2028 guidance, with no Phase 3 result",()=>{
 const feed=mod.parseProspectiveSourceBaselines(raw);
 const trial=feed.records.find(r=>r.nctId==="NCT07671911");
 assert.ok(trial);
 assert.equal(trial.ticker,"TRVI");
 assert.equal(trial.drug,"NAL ER");
 assert.equal(trial.indication,"Idiopathic Pulmonary Fibrosis");
 assert.equal(trial.stage,"pre");
 assert.equal(trial.marketCap.usdMillions,1932);
 assert.equal(trial.marketCap.observedAsOf,"2026-10-30");
 assert.equal(trial.marketCap.verification,"VENDOR_REPORTED_NOT_INDEPENDENTLY_AUDITED");
 assert.equal(trial.observations.length,5);
 assert.ok(trial.observations.every(o=>o.sourcePublishedAt<=trial.capturedOn));
 assert.ok(trial.observations.every(o=>o.sourceUrl.startsWith("https://")));
 const prior=trial.observations.find(o=>o.id==="trvi-coral-prior-phase2b");
 assert.equal(prior.kind,"PRIOR_PHASE2B_EFFICACY");
 assert.equal(prior.sourcePublishedAt,"2025-06-02");
 assert.match(prior.limitation,/Not the OCEAN-1 Phase 3 result/);
 const timing=trial.observations.find(o=>o.id==="trvi-ocean1-readout-guidance");
 assert.match(timing.valueText,/first half of 2028/);
 assert.match(timing.valueText,/NOT an OCEAN-1 readout/);
 const finance=trial.observations.find(o=>o.id==="trvi-q2-finance-2026");
 assert.match(finance.valueText,/318.9 million/);
 assert.match(finance.limitation,/Never add both cash numbers/);
 const original=pilot.records.find(p=>p.nctId===trial.nctId);
 assert.ok(original);
 assert.equal(original.ticker,trial.ticker);
 assert.equal(original.drug,trial.drug);
 assert.equal(original.stage,trial.stage);
});
test("Related NCTs of one issuer and the same therapy are not double-counted as independent programs",()=>{
 const draft=clone();
 draft.records.push({...draft.records[1],nctId:"NCT98765432",id:"separate-trial-same-therapy"});
 const summary=mod.prospectiveSourceSummary(mod.parseProspectiveSourceBaselines(draft));
 assert.equal(summary.baselines,3);
 assert.equal(summary.distinctPrograms,2);
 assert.equal(summary.distinctIssuers,2);
 assert.equal(summary.numericRaasScores,0);
});
test("An issuer's published facts never masquerade as a recorded RAAS numeric forecast",()=>{
 const x=mod.parseProspectiveSourceBaselines(raw).records[0];
 assert.equal(x.archivedRaasPrediction,false);
 assert.equal(x.predictedRaas,null);
 assert.equal(x.predictedReturnPercent,null);
 assert.equal(x.entryExecutionPrice,null);
 assert.equal(x.readoutAtCapture,"NOT_YET_REPORTED");
 assert.equal(tradingHistory.cases.length,0);
 assert.equal(metricHistory.records.length,0);
 assert.equal(calibration.entries.length,0);
 assert.equal(reviewed.records.length,0);
});
test("Reject backdated releases, future observations, duplicate facts and missing sources",()=>{
 for(const edit of [
  {sourcePublishedAt:"2026-11-03"},
  {observedAsOf:"2026-11-04"},
  {sourceUrl:"http://unsecure.example/x"},
  {sourceUrl:"https://attacker@trusted.example/x"},
  {metricIds:["pre-999"]},
  {metricIds:["pre-1-2","pre-1-2"]},
  {sourcePublishedAt:"2026-01-01",observedAsOf:"2026-03-25"},
  {valueText:""},
  {kind:"POST_READOUT_RESULT"}
 ]){
  const draft=clone();draft.records[0].observations[0]={...draft.records[0].observations[0],...edit};
  assert.throws(()=>mod.parseProspectiveSourceBaselines(draft),/RAAS_PROSPECTIVE_FACT_INVALID/);
 }
 const duplicate=clone();duplicate.records[0].observations.push({...duplicate.records[0].observations[0]});
 assert.throws(()=>mod.parseProspectiveSourceBaselines(duplicate),/RAAS_PROSPECTIVE_FACT_INVALID/);
});
test("Reject fabricated score, resolved outcome, mislabeled provenance, out-of-scope cap and wrong analysis stage metrics",()=>{
 for(const edit of [
  {predictedRaas:75},{predictedReturnPercent:20},{archivedRaasPrediction:true},
  {readoutAtCapture:"SUCCESS"},{entryExecutionPrice:39.7},
  {capturedOn:"2026-01-01"},
  {marketCap:{...raw.records[0].marketCap,usdMillions:200}},
  {marketCap:{...raw.records[0].marketCap,verification:"AUDITED"}},
  {stage:"post"}
 ]){
  const draft=clone();draft.records[0]={...draft.records[0],...edit};
  assert.throws(()=>mod.parseProspectiveSourceBaselines(draft),
   /RAAS_PROSPECTIVE_BASELINE_INVALID|RAAS_PROSPECTIVE_FACT_INVALID/);
 }
 const duplicate=clone();duplicate.records.push({...duplicate.records[0],id:"second"});
 assert.throws(()=>mod.parseProspectiveSourceBaselines(duplicate),/RAAS_PROSPECTIVE_DUPLICATE_SNAPSHOT/);
});
test("Audit page displays separate prospective source record, not a backfilled retrospective forecast",()=>{
 const root=path.resolve(__dirname,"..");
 const page=fs.readFileSync(path.join(root,"app/raas-history/page.tsx"),"utf8");
 for(const signal of ["data-prospective-baseline","data-prospective-facts",
   "prospective.records.map","0 predictions","No original 0–100 RAAS grade",
   "Git commit history","raas-history-top","retrospective"]){
  assert.ok(page.includes(signal),signal);
 }
 for(const rel of ["lib/raas-prospective-source-baselines.ts","app/raas-history/page.tsx"]){
  const output=ts.transpileModule(fs.readFileSync(path.join(root,rel),"utf8"),{
   fileName:rel,reportDiagnostics:true,compilerOptions:{
    module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX
   }
  });
  assert.deepEqual((output.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error)
   .map(d=>ts.flattenDiagnosticMessageText(d.messageText," ")),[],rel);
 }
});
