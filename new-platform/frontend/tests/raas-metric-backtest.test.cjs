"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);
const engine=require("../lib/raas-historical-backtest.ts");
const metric=require("../lib/raas-metric-backtest.ts");
const productionEvents=require("../data/raas-historical-cases.json");
const productionScores=require("../data/raas-historical-metric-snapshots.json");
// All following examples are entirely synthetic and never saved to production evidence files.
const sourceDate="2025-05-05";
const price=(date,adjustedClose)=>({date,adjustedClose,currency:"USD",
 sourceUrl:"https://example.org/synthetic-price",sourcePublishedAt:sourceDate});
const caseA={
 caseId:"synthetic-a",nctIds:["NCT12345678"],ticker:"TEST",drug:"LAB-1",indication:"Test disorder",
 stage:"pre",marketCapUsdMillions:600,marketCapSourceUrl:"https://example.org/cap",
 marketCapSourcePublishedAt:"2025-01-08",
 featureAsOf:"2025-01-09",predictionPublishedAt:"2025-01-09",
 entryDate:"2025-01-10",exitDate:"2025-02-03",
 phase3ReadoutDate:"2025-02-10",phase3ReadoutSourceUrl:"https://example.org/readout",
 phase3ReadoutSourcePublishedAt:"2025-02-10",
 entryPrice:price("2025-01-10",10),exitPrice:price("2025-02-03",15),
 predictedRaas:null,predictedReturnPercent:null,roundTripCostsPercent:1,
 featureSources:[{sourceUrl:"https://example.org/synthetic-research",publishedAt:"2025-01-08"}]
};
const rating=(overrides={})=>({
 caseId:"synthetic-a",nctId:"NCT12345678",ticker:"TEST",drug:"LAB-1",indication:"Test disorder",
 stage:"pre",metricId:"pre-1-1",score:75,benchmarkId:"synthetic-bench",
 ruleVersion:"synthetic-v1",assessedAt:"2025-01-09",
 sourceUrl:"https://example.org/synthetic-research",
 sourcePublishedAt:"2025-01-08",method:"synthetic only",...overrides
});
const back=(cases)=>engine.parseHistoricalFeed({...productionEvents,sourceAsOf:sourceDate,cases});
const grade=(records)=>metric.parseMetricHistory({...productionScores,sourceAsOf:sourceDate,records});
test("No fabricated metric or stock cases are passed off as calibrated history",()=>{
 const h=back([]),r=grade([]);
 const report=metric.evaluateMetricHistory(h,engine.evaluateHistoricalFeed(h),r);
 assert.equal(report.length,60);
 assert.ok(report.every(x=>x.independentPrograms===0&&x.status==="INSUFFICIENT_EVIDENCE"));
});
test("Exact pre-entry metric grade joins to source-supported historical outcome, not a certified RAAS score",()=>{
 const h=back([caseA]);
 const report=metric.evaluateMetricHistory(h,engine.evaluateHistoricalFeed(h),grade([rating()]));
 const a=report.find(x=>x.metricId==="pre-1-1");
 assert.equal(a.independentPrograms,1);
 assert.equal(a.observedReturnPairs,1);
 assert.equal(a.positiveReturnRateHigh,100);
 assert.equal(a.spearmanScoreToReturn,null);
 assert.equal(a.status,"INSUFFICIENT_EVIDENCE");
});
test("Future scores, future sources, wrong NCT, or wrong drug are rejected",()=>{
 const candidates=[
  rating({sourcePublishedAt:"2025-02-11",assessedAt:"2025-02-11"}),
  rating({assessedAt:"2025-02-11"}),
  rating({nctId:"NCT00000000"}),
  rating({drug:"other treatment"})
 ];
 for(const r of candidates){
  const h=back([caseA]);
  const out=metric.evaluateMetricHistory(h,engine.evaluateHistoricalFeed(h),grade([r]));
  assert.equal(out.find(x=>x.metricId==="pre-1-1").independentPrograms,0);
 }
});
test("Multiple NCTs of same drug program count once",()=>{
 const b={...caseA,caseId:"synthetic-b",nctIds:["NCT87654321"],
  entryDate:"2025-01-13",featureAsOf:"2025-01-10",
  predictionPublishedAt:"2025-01-10",entryPrice:price("2025-01-13",11)};
 const h=back([caseA,b]);
 const r=grade([rating(),rating({caseId:"synthetic-b",nctId:"NCT87654321",assessedAt:"2025-01-10"})]);
 const report=metric.evaluateMetricHistory(h,engine.evaluateHistoricalFeed(h),r);
 assert.equal(report.find(x=>x.metricId==="pre-1-1").independentPrograms,1);
});
test("Metric backtest TypeScript parses cleanly",()=>{
 const source=fs.readFileSync(path.join(__dirname,"../lib/raas-metric-backtest.ts"),"utf8");
 const out=ts.transpileModule(source,{fileName:"raas-metric-backtest.ts",reportDiagnostics:true,
 compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.equal((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error).length,0);
});


const plusDays=(day,count)=>new Date(Date.parse(day+"T00:00:00Z")+count*86400000).toISOString().slice(0,10);
const syntheticCohort=(count,sameDate=false)=>{
 const cases=[],ratings=[];
 for(let i=0;i<count;i++){
  const entry=plusDays("2024-01-08",sameDate?0:i*7);
  const exit=plusDays(entry,2),readout=plusDays(entry,7);
  const sourceDay=plusDays(entry,-2),assessedAt=plusDays(entry,-1);
  const ticker="CASE"+i,nctId="NCT"+String(10000000+i);
  const selected= i%2===0 ? 25:75;
  const item={...caseA,caseId:"synthetic-holdout-"+i,
   nctIds:[nctId],ticker,drug:"SYNTH-"+i,indication:"Synthetic comparator",
   marketCapSourcePublishedAt:sourceDay,featureAsOf:assessedAt,
   predictionPublishedAt:assessedAt,entryDate:entry,exitDate:exit,
   phase3ReadoutDate:readout,phase3ReadoutSourcePublishedAt:readout,
   entryPrice:{...caseA.entryPrice,date:entry,sourcePublishedAt:"2026-11-02"},
   exitPrice:{...caseA.exitPrice,date:exit,sourcePublishedAt:"2026-11-02",
    adjustedClose:selected===75?14:9},
   featureSources:[{sourceUrl:"https://example.org/historical-synthetic",publishedAt:sourceDay}]
  };
  cases.push(item);
  ratings.push(rating({caseId:item.caseId,nctId,ticker,drug:item.drug,
   indication:item.indication,score:selected,assessedAt,sourcePublishedAt:sourceDay}));
 }
 return {cases,ratings};
};
test("Sixty source-dated independent programs support a purged 30/30 research holdout, not calibration approval",()=>{
 const {cases,ratings}=syntheticCohort(60);
 const history=engine.parseHistoricalFeed({...productionEvents,sourceAsOf:"2026-11-02",cases});
 const scores=metric.parseMetricHistory({...productionScores,sourceAsOf:"2026-11-02",records:ratings});
 const outcomes=engine.evaluateHistoricalFeed(history);
 assert.equal(outcomes.accepted.length,60);
 const d=metric.evaluateMetricHistory(history,outcomes,scores).find(x=>x.metricId==="pre-1-1");
 assert.equal(d.independentPrograms,60);
 assert.equal(d.benchmarkId,"synthetic-bench");
 assert.equal(d.ruleVersion,"synthetic-v1");
 assert.equal(d.protocolConsistent,true);
 assert.ok(d.holdoutTrainPrograms>=30&&d.holdoutTestPrograms>=30);
 assert.equal(d.status,"REVIEW_ELIGIBLE_NOT_APPROVED");
 assert.match(d.reason,/independent audit/);
});
test("Incompatible metric scoring versions cannot create a spurious return correlation",()=>{
 const {cases,ratings}=syntheticCohort(60);
 ratings[20].ruleVersion="synthetic-v2";
 const history=engine.parseHistoricalFeed({...productionEvents,sourceAsOf:"2026-11-02",cases});
 const scores=metric.parseMetricHistory({...productionScores,sourceAsOf:"2026-11-02",records:ratings});
 const d=metric.evaluateMetricHistory(history,engine.evaluateHistoricalFeed(history),scores)
  .find(x=>x.metricId==="pre-1-1");
 assert.equal(d.independentPrograms,60);
 assert.equal(d.protocolConsistent,false);
 assert.equal(d.benchmarkId,null);
 assert.equal(d.ruleVersion,null);
 assert.equal(d.spearmanScoreToReturn,null);
 assert.equal(d.meanHighMinusLowPercent,null);
 assert.equal(d.status,"INSUFFICIENT_EVIDENCE");
 assert.match(d.reason,/Mixed benchmark or rule versions/);
});
test("Sixty same-date programs cannot masquerade as a chronological historical holdout",()=>{
 const {cases,ratings}=syntheticCohort(60,true);
 const history=engine.parseHistoricalFeed({...productionEvents,sourceAsOf:"2026-11-02",cases});
 const scores=metric.parseMetricHistory({...productionScores,sourceAsOf:"2026-11-02",records:ratings});
 const d=metric.evaluateMetricHistory(history,engine.evaluateHistoricalFeed(history),scores)
  .find(x=>x.metricId==="pre-1-1");
 assert.equal(d.independentPrograms,60);
 assert.ok(d.holdoutTrainPrograms<30||d.holdoutTestPrograms<30);
 assert.equal(d.status,"INSUFFICIENT_EVIDENCE");
 assert.match(d.reason,/No issuer-disjoint, purged chronological/);
});
test("Approved RAAS ledger requires matching benchmark AND rule version AND holdout before accepting any metric",()=>{
 const {parseRaasCalibrations,parseRaasReviewedLedger,reviewedScoreForTrial}=
  require("../lib/raas-reviewed-score-ledger.ts");
 const calibration=parseRaasCalibrations({
  schemaVersion:1,scope:"RAAS_VALIDATED_METRIC_CALIBRATIONS",sourceAsOf:"2026-11-02",
  note:"Synthetic test, not production",entries:[{
   metricId:"pre-1-1",stage:"pre",benchmarkId:"synthetic-bench",ruleVersion:"synthetic-v1",
   validatedAt:"2025-01-01",validationSourceUrl:"https://example.org/synthetic-calibration",
   outOfSampleTrials:30,benchmarkDescription:"Hypothetical cohort",
   scoreThresholds:[0,25,50,75,100].map(grade=>({grade,rule:"Synthetic test band"})),
   status:"APPROVED_FOR_COMPOSITE"
  }]
 });
 const record={nctId:"NCT12345678",ticker:"TEST",drug:"LAB-1",indication:"Test disorder",
  stage:"pre",snapshot:"CURRENT",asOf:"2026-10-01",reviewedAt:"2026-10-02",
  reviewer:"synthetic-test",note:"not for production",
  ratings:[{nctId:"NCT12345678",ticker:"TEST",stage:"pre",snapshot:"CURRENT",
   metricId:"pre-1-1",score:75,assessedAt:"2026-09-30",sourceDate:"2026-09-29",
   sourceUrl:"https://example.org/synthetic-score",benchmarkId:"synthetic-bench",ruleVersion:"synthetic-v1",
   method:"Synthetic grade",evidenceId:"synthetic-1",status:"VERIFIED"}],
  gates:[{name:"Synthetic eligibility",status:"PASSED"}]};
 const ledger=parseRaasReviewedLedger({schemaVersion:1,scope:"RAAS_REVIEWED_TRIAL_SNAPSHOTS",
  sourceAsOf:"2026-11-02",note:"Synthetic",records:[record]});
 const d={stage:"pre",metricId:"pre-1-1",status:"REVIEW_ELIGIBLE_NOT_APPROVED",
  independentPrograms:60,holdoutTrainPrograms:30,holdoutTestPrograms:30,
  holdoutLowPrograms:15,holdoutHighPrograms:15,
  holdoutSpearmanScoreToReturn:.45,holdoutHighMinusLowPercent:25,
  protocolConsistent:true,benchmarkId:"synthetic-bench",ruleVersion:"synthetic-v1",
  spearmanScoreToReturn:.45};
 const run=(diag)=>reviewedScoreForTrial(ledger,calibration,record,"pre","CURRENT",
  "2026-11-02",[diag]);
 assert.equal(run({...d,ruleVersion:"synthetic-v2"}).acceptedRatings.length,0);
 assert.equal(run({...d,benchmarkId:"other"}).acceptedRatings.length,0);
 assert.equal(run({...d,holdoutTrainPrograms:29}).acceptedRatings.length,0);
 assert.equal(run({...d,holdoutTestPrograms:29}).acceptedRatings.length,0);
 assert.equal(run({...d,protocolConsistent:false}).acceptedRatings.length,0);
 assert.equal(run({...d,holdoutSpearmanScoreToReturn:-.2}).acceptedRatings.length,0);
 assert.equal(run({...d,holdoutHighMinusLowPercent:-4}).acceptedRatings.length,0);
 assert.equal(run({...d,holdoutHighPrograms:4}).acceptedRatings.length,0);
 assert.equal(run({...d,holdoutLowPrograms:4}).acceptedRatings.length,0);
 assert.equal(run({...d,holdoutSpearmanScoreToReturn:null}).acceptedRatings.length,0);
 const oldRecord={...record,ratings:record.ratings.map(({ruleVersion,...older})=>older)};
 const oldLedger=parseRaasReviewedLedger({schemaVersion:1,scope:"RAAS_REVIEWED_TRIAL_SNAPSHOTS",
  sourceAsOf:"2026-11-02",note:"Synthetic legacy",records:[oldRecord]});
 assert.equal(reviewedScoreForTrial(oldLedger,calibration,record,"pre","CURRENT",
  "2026-11-02",[d]).acceptedRatings.length,0);
 assert.equal(run(d).acceptedRatings.length,1);
 assert.equal(run(d).score.score,null); // 29 other metric grades remain missing.
});

test("Large positive pooled correlation cannot rescue an inverse later issuer holdout",()=>{
 const {cases,ratings}=syntheticCohort(60);
 cases.forEach((row,i)=>{
  const high=ratings[i].score===75;
  row.exitPrice.adjustedClose=i<30?(high?25:5):(high?9.5:10.5);
 });
 const history=engine.parseHistoricalFeed({...productionEvents,sourceAsOf:"2026-11-02",cases});
 const scores=metric.parseMetricHistory({...productionScores,sourceAsOf:"2026-11-02",records:ratings});
 const d=metric.evaluateMetricHistory(history,engine.evaluateHistoricalFeed(history),scores)
  .find(x=>x.metricId==="pre-1-1");
 assert.ok(d.spearmanScoreToReturn>0,"Pooled history may look favorable");
 assert.ok(d.holdoutSpearmanScoreToReturn<0,"Later holdout must reveal inverse score/return relationship");
 assert.ok(d.holdoutHighMinusLowPercent<0);
 assert.equal(d.holdoutTrainPrograms,30);
 assert.equal(d.holdoutTestPrograms,30);
 assert.equal(d.status,"INSUFFICIENT_EVIDENCE");
 assert.match(d.reason,/Held-out issuer scores do not demonstrate/);
});
test("Repeated ticker with another drug is not an independent train/test issuer",()=>{
 const {cases,ratings}=syntheticCohort(60);
 for(let i=30;i<60;i++){
  cases[i].ticker="CASE"+(i-30);
  ratings[i].ticker=cases[i].ticker;
 }
 const history=engine.parseHistoricalFeed({...productionEvents,sourceAsOf:"2026-11-02",cases});
 const scores=metric.parseMetricHistory({...productionScores,sourceAsOf:"2026-11-02",records:ratings});
 const d=metric.evaluateMetricHistory(history,engine.evaluateHistoricalFeed(history),scores)
  .find(x=>x.metricId==="pre-1-1");
 assert.equal(d.independentPrograms,60);
 assert.ok(d.holdoutIssuerPurgedPrograms>0);
 assert.ok(d.holdoutTrainPrograms<30||d.holdoutTestPrograms<30);
 assert.equal(d.status,"INSUFFICIENT_EVIDENCE");
});
test("Held-out rating class missing blocks review even with 60 issuer records",()=>{
 const {cases,ratings}=syntheticCohort(60);
 for(let i=30;i<60;i++)ratings[i].score=75;
 const history=engine.parseHistoricalFeed({...productionEvents,sourceAsOf:"2026-11-02",cases});
 const scores=metric.parseMetricHistory({...productionScores,sourceAsOf:"2026-11-02",records:ratings});
 const d=metric.evaluateMetricHistory(history,engine.evaluateHistoricalFeed(history),scores)
  .find(x=>x.metricId==="pre-1-1");
 assert.equal(d.holdoutTrainPrograms,30);
 assert.equal(d.holdoutTestPrograms,30);
 assert.equal(d.holdoutLowPrograms,0);
 assert.equal(d.status,"INSUFFICIENT_EVIDENCE");
 assert.match(d.reason,/Held-out issuer cohort lacks/);
});
