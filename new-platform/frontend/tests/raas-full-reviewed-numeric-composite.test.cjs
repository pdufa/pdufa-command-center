"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),ts=require("typescript");
require.extensions[".ts"]=(module,file)=>module._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {RAAS_METRIC_CATALOG}=require("../lib/raas-metric-specs.ts");
const {parseReviewedMetricFeed,fullReviewedTrialCandidate}=require("../lib/raas-reviewed-full-score.ts");
const trial={nctId:"NCT12345678",ticker:"TEST",drug:"Experimental Drug",
 indication:"Test indication"};
const make=(stage,metricId,i)=>({
 ...trial,stage,metricId,finding:i%2===0?"ABOVE_BENCHMARK":"MIXED_EVIDENCE",
 assessedAt:"2026-11-04",sourceDate:"2026-11-03",
 sourceUrl:"https://clinicaltrials.gov/study/NCT12345678",
 benchmarkSourceUrl:"https://www.fda.gov/drugs/development-approval-process-drugs",
 benchmarkId:"Independent disease-specific benchmark rubric "+metricId,
 benchmarkContext:"Independent comparator assumptions and confidence reference defined in review",
 observedResult:"Observed trial result against exact disease control and treatment endpoint.",
 uncertaintyReview:"Prespecified model sensitivity and confidence bounds require ongoing audit",
 criticalRiskReview:"Safety and comparator direction considered with all applicable caveats",
 reviewerMethod:"Second reviewer crosschecked source values with independent benchmarks",
 independentReview:"PASSED"
});
const makeFeed=(stage,missing=0)=>{
 const metrics=RAAS_METRIC_CATALOG[stage].flatMap(group=>group.metrics);
 return parseReviewedMetricFeed({schemaVersion:1,
  scope:"RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY",sourceAsOf:"2026-11-04",
  records:metrics.slice(0,30-missing).map((m,i)=>make(stage,m.id,i))});
};
test("actual full TOP and BOTTOM weighted score only with all 30 independently described reviews and verified stage",()=>{
 for(const stage of ["pre","post"]){
  const feed=makeFeed(stage);
  const x=fullReviewedTrialCandidate(trial,stage,true,feed);
  const expected=Math.round(RAAS_METRIC_CATALOG[stage].reduce((total,g)=>
   total+g.metrics.reduce((subtotal,m)=>{
    const i=feed.records.findIndex(r=>r.metricId===m.id);
    return subtotal+(i%2===0?75:50)*g.weight/5;
   },0),0)/10)/10;
  assert.equal(x.reviewedCount,30);
  assert.deepEqual(x.missingMetricIds,[]);
  assert.equal(x.weightedCoveragePercent,100);
  assert.equal(x.fullResearchScore,expected);
  assert.equal(x.approvedOverallScore,null);
  assert.equal(x.type,"UNVALIDATED_REVIEWED_RESEARCH_SCORE_NOT_FDA_PROBABILITY");
 }
});
test("29 of 30 reviewed metrics cannot fabricate an overall grade",()=>{
 const x=fullReviewedTrialCandidate(trial,"pre",true,makeFeed("pre",1));
 assert.equal(x.reviewedCount,29);assert.equal(x.missingMetricIds.length,1);
 assert.equal(x.fullResearchScore,null);
 assert.notEqual(x.observedMean,null);
 assert.equal(x.approvedOverallScore,null);
});
test("an unverified readout stage cannot output a whole stage score even for 30/30",()=>{
 const x=fullReviewedTrialCandidate(trial,"post",false,makeFeed("post"));
 assert.equal(x.reviewedCount,30);
 assert.equal(x.fullResearchScore,null);
});
test("exact NCT+ticker+drug+indication+stage prevent cross-program grade leakage",()=>{
 const feed=makeFeed("post");
 for(const bad of [
  {...trial,nctId:"NCT00000001"},{...trial,ticker:"BAD"},
  {...trial,drug:"Different drug"},{...trial,indication:"Other disease"}
 ]){
  const x=fullReviewedTrialCandidate(bad,"post",true,feed);
  assert.equal(x.reviewedCount,0);assert.equal(x.fullResearchScore,null);
 }
});
test("future, duplicate, sham and missing documented review fields fail closed",()=>{
 const feed=makeFeed("pre");
 const base={...feed,records:[...feed.records]};
 for(const patch of [
  {sourceDate:"2026-11-05"},{assessedAt:"2026-11-05"},
  {sourceUrl:"https://clinicaltrials.gov/study/NCT00000002",benchmarkSourceUrl:"https://clinicaltrials.gov/study/NCT00000002"},
  {benchmarkContext:""},{independentReview:"PENDING"}
 ]){
  const xs={...base,records:[{...base.records[0],...patch},...base.records.slice(1)]};
  assert.throws(()=>parseReviewedMetricFeed(xs),/RAAS_REVIEWED_FEED/);
 }
 assert.throws(()=>parseReviewedMetricFeed({...base,records:[...base.records,base.records[0]]}),/RAAS_REVIEWED_FEED/);
});
test("unfilled source intake truthfully contains no numerical reviewed composite",()=>{
 const source=JSON.parse(fs.readFileSync(require("node:path").join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const result=fullReviewedTrialCandidate(trial,"pre",true,parseReviewedMetricFeed(source));
 assert.equal(result.reviewedCount,0);
 assert.equal(result.fullResearchScore,null);
 assert.equal(result.missingMetricIds.length,30);
});