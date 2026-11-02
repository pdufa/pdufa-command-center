"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(module,file)=>{
 const src=fs.readFileSync(file,"utf8");
 const js=ts.transpileModule(src,{fileName:file,compilerOptions:{
   module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022
 }}).outputText;
 module._compile(js,file);
};
const thresholds=require("../lib/raas-threshold-profiles.ts");
const ledgers=require("../lib/raas-reviewed-score-ledger.ts");
const engine=require("../lib/raas-score-engine.ts");
const clinical=require("../lib/raas-clinical-benchmarks.ts");
const observations=engine.parseRaasPilotFeed(require("../data/raas-pilot-observations.json"));
const rawLedger=require("../data/raas-reviewed-snapshots.json");
const rawCalibrations=require("../data/raas-approved-calibrations.json");
test("sixty metric-specific threshold profiles require validation before composite scoring",()=>{
 assert.equal(thresholds.RAAS_THRESHOLD_PROFILES.length,60);
 const ids=new Set(thresholds.RAAS_THRESHOLD_PROFILES.map(p=>p.stage+"|"+p.metricId));
 assert.equal(ids.size,60);
 for(const p of thresholds.RAAS_THRESHOLD_PROFILES){
   assert.ok(p.minimumInputs&&p.benchmarkRequired&&p.category);
   assert.equal(p.approvedForComposite,false);
 }
 assert.equal(thresholds.RAAS_THRESHOLD_PROFILES.filter(p=>p.status==="PROVISIONAL_NOT_CALIBRATED").length,1);
});
test("dated LBRX H1 2027 guidance produces a transparent exploratory 50/100 not RAAS",()=>{
 const trial={nctId:"NCT07363577",ticker:"LBRX",
  drug:"LB-102 (100 mg tablet) | LB-102 (50 mg tablet)",indication:"Schizophrenia"};
 const result=thresholds.provisionalGradesForTrial(observations,trial,"pre","CURRENT","2026-11-02");
 assert.equal(result.length,1);
 assert.equal(result[0].score,50);
 assert.equal(result[0].ruleId,"timing-specificity-exploratory-2026-11-02-v1");
 assert.equal(result[0].kind,"RESEARCH_ONLY_NOT_VALIDATED");
 assert.match(result[0].limitations,/Never contributes/);
 assert.deepEqual(thresholds.provisionalGradesForTrial(observations,trial,"pre","ENTRY","2026-11-02"),[]);
 assert.deepEqual(thresholds.provisionalGradesForTrial(observations,trial,"pre","CURRENT","2026-10-01"),[]);
 assert.deepEqual(thresholds.provisionalGradesForTrial(observations,{...trial,drug:"not LB-102"},"pre","CURRENT","2026-11-02"),[]);
});
test("all audited grade registers start empty and cannot create investment scores",()=>{
 const calibrations=ledgers.parseRaasCalibrations(rawCalibrations);
 const ledger=ledgers.parseRaasReviewedLedger(rawLedger);
 assert.equal(calibrations.entries.length,0);
 assert.equal(ledger.records.length,0);
 assert.equal(ledgers.reviewedScoreForTrial(ledger,calibrations,{
  nctId:"NCT07363577",ticker:"LBRX",
  drug:"LB-102 (100 mg tablet) | LB-102 (50 mg tablet)",indication:"Schizophrenia"
 },"pre","CURRENT","2026-11-02"),null);
});
test("unreviewed or insufficiently tested calibration rules are blocked",()=>{
 assert.throws(()=>ledgers.parseRaasCalibrations({...rawCalibrations,entries:[{
  metricId:"pre-4-1",stage:"pre",benchmarkId:"source-timing-rule",ruleVersion:"1",
  validatedAt:"2026-10-31",validationSourceUrl:"https://example.org/test",
  outOfSampleTrials:2,benchmarkDescription:"Unvalidated demonstration",status:"APPROVED_FOR_COMPOSITE",
  scoreThresholds:[0,25,50,75,100].map(grade=>({grade,rule:"demo"}))
 }]}),/RAAS_CALIBRATION_NOT_VALIDATED/);
});
test("reviewed snapshots cannot silently change trial identity",()=>{
 const record={nctId:"NCT07363577",ticker:"LBRX",drug:"LB-102",indication:"Schizophrenia",
 stage:"pre",snapshot:"CURRENT",asOf:"2026-11-02",reviewedAt:"2026-11-02",
 reviewer:"test-only",note:"Test no identity substitution",ratings:[{
 nctId:"NCT99999999",ticker:"LBRX",stage:"pre",snapshot:"CURRENT",metricId:"pre-4-1",
 score:50,assessedAt:"2026-11-02",sourceDate:"2026-10-27",status:"VERIFIED",
 benchmarkId:"test",method:"demo",evidenceId:"demo",sourceUrl:"https://example.org/test"}],
 gates:[]};
 assert.throws(()=>ledgers.parseRaasReviewedLedger({...rawLedger,records:[record]}),/RAAS_SNAPSHOT_INVALID/);
});
test("published CSU UAS7 reference is within-patient, never placebo-adjusted threshold",()=>{
 const b=clinical.contextualClinicalBenchmark("barzolvolimab","chronic spontaneous urticaria","UAS7 points");
 assert.equal(b.min,9.5);assert.equal(b.max,10.5);
 assert.equal(b.interpretation,"WITHIN_PATIENT_CHANGE");
 assert.match(b.notApplicableTo,/between-group/);
 assert.equal(clinical.contextualClinicalBenchmark("sonelokimab","psoriatic arthritis","UAS7 points"),null);
});

test("Even manually approved labels cannot bypass missing same-metric historical evidence",()=>{
 const benchmarkId="synthetic-calibration-only";
 const cal=ledgers.parseRaasCalibrations({...rawCalibrations,entries:[{
  metricId:"pre-4-1",stage:"pre",benchmarkId,ruleVersion:"synthetic-v1",
  validatedAt:"2026-10-01",validationSourceUrl:"https://example.org/synthetic-calibration",
  outOfSampleTrials:30,benchmarkDescription:"Synthetic only, never save to production",status:"APPROVED_FOR_COMPOSITE",
  scoreThresholds:[0,25,50,75,100].map(grade=>({grade,rule:"synthetic scoring rule"}))
 }]});
 const record={nctId:"NCT07363577",ticker:"LBRX",drug:"LB-102",indication:"Schizophrenia",
  stage:"pre",snapshot:"CURRENT",asOf:"2026-11-02",reviewedAt:"2026-11-02",
  reviewer:"synthetic-test",note:"Test historical gates only",ratings:[{
   nctId:"NCT07363577",ticker:"LBRX",stage:"pre",snapshot:"CURRENT",
   metricId:"pre-4-1",score:50,assessedAt:"2026-11-02",sourceDate:"2026-10-27",
   sourceUrl:"https://example.org/synthetic-score",benchmarkId,
   method:"synthetic test",evidenceId:"synthetic-only",status:"VERIFIED"
  }],gates:[{name:"Eligibility",status:"PASSED"}]};
 const ledger=ledgers.parseRaasReviewedLedger({...rawLedger,records:[record]});
 const args=[ledger,cal,{nctId:record.nctId,ticker:record.ticker,drug:record.drug,indication:record.indication},
   "pre","CURRENT","2026-11-02"];
 const without=ledgers.reviewedScoreForTrial(...args,[]);
 assert.equal(without.acceptedRatings.length,0);
 assert.equal(without.score.score,null);
 const diagnostic={metricId:"pre-4-1",stage:"pre",independentPrograms:30,
   spearmanScoreToReturn:.2,status:"REVIEW_ELIGIBLE_NOT_APPROVED"};
 const withHistory=ledgers.reviewedScoreForTrial(...args,[diagnostic]);
 assert.equal(withHistory.acceptedRatings.length,1);
 assert.equal(withHistory.score.score,null);
 assert.equal(withHistory.score.graded,1);
});

test("new grading TS modules and UI parse without diagnostics",()=>{
 const files=["lib/raas-threshold-profiles.ts","lib/raas-reviewed-score-ledger.ts","lib/raas-clinical-benchmarks.ts","app/TrialRaasDisclosure.tsx"];
 for(const file of files){
  const text=fs.readFileSync(path.join(root,file),"utf8");
  const result=ts.transpileModule(text,{fileName:file,reportDiagnostics:true,
   compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,jsx:ts.JsxEmit.ReactJSX}});
  const errors=(result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error);
  assert.deepEqual(errors.map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[],file);
 }
});
