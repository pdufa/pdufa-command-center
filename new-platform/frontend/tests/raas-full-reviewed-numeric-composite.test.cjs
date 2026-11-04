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
test("AI source crosschecks do not count as independent 30-of-30 reviews even when all 30 have grades",()=>{
 const feed=makeFeed("post");
 const ai=parseReviewedMetricFeed({...feed,records:feed.records.map(r=>({
  ...r,independentReview:"AI_SOURCE_CROSSCHECKED",
  reviewerMethod:"AI model source and independent literature crosscheck, no external human reviewer"
 }))});
 const result=fullReviewedTrialCandidate(trial,"post",true,ai);
 assert.equal(result.reviewedCount,30);
 assert.equal(result.aiCrosscheckedCount,30);
 assert.equal(result.independentReviewedCount,0);
 assert.equal(result.fullResearchScore,null);
 assert.equal(result.approvedOverallScore,null);
});
test("live exact-trial Celldex source checks contain six provisional grades and zero human independent reviews",()=>{
 const path=require("node:path");
 const raw=JSON.parse(fs.readFileSync(path.join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const feed=parseReviewedMetricFeed(raw);
 assert.equal(feed.records.length,82);
 assert.ok(feed.records.every(r=>r.independentReview==="AI_SOURCE_CROSSCHECKED"));
 for(const nctId of ["NCT06445023","NCT06455202"]){
  const x=fullReviewedTrialCandidate({nctId,ticker:"CLDX",drug:"barzolvolimab",
   indication:"chronic spontaneous urticaria"},"post",true,feed);
  assert.equal(x.aiCrosscheckedCount,3);
  assert.equal(x.independentReviewedCount,0);
  assert.deepEqual(x.grades.map(g=>g.metricId).sort(),["post-1-1","post-1-2","post-1-4"]);
  assert.equal(x.fullResearchScore,null);
  assert.equal(x.missingMetricIds.length,27);
  assert.ok(x.grades.every(g=>g.reviewClass==="AI_SOURCE_CROSSCHECKED"));
 }
});
test("AI clinical score does not leak to another drug, indication or readout stage",()=>{
 const raw=JSON.parse(fs.readFileSync(require("node:path").join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const feed=parseReviewedMetricFeed(raw);
 const t={nctId:"NCT06445023",ticker:"CLDX",drug:"barzolvolimab",
  indication:"chronic spontaneous urticaria"};
 for(const bad of [{...t,ticker:"OTHER"},{...t,drug:"wrong drug"},
  {...t,indication:"wrong indication"}]){
  const x=fullReviewedTrialCandidate(bad,"post",true,feed);
  assert.equal(x.aiCrosscheckedCount,0);
  assert.equal(x.fullResearchScore,null);
 }
 const pre=fullReviewedTrialCandidate(t,"pre",true,feed);
 assert.equal(pre.aiCrosscheckedCount,0);
});

test("dual pivotal replicated and durable Week-24 responses are source-checked but do not imply approval or complete RAAS",()=>{
 const p=require("node:path");
 const source=JSON.parse(fs.readFileSync(p.join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const feed=parseReviewedMetricFeed(source);
 const x=feed.records.filter(r=>r.metricId==="post-1-4"&&r.ticker==="CLDX");
 assert.equal(x.length,2);
 assert.deepEqual(x.map(r=>r.nctId).sort(),["NCT06445023","NCT06455202"]);
 for(const r of x){
  assert.equal(r.finding,"MIXED_EVIDENCE");
  assert.equal(r.independentReview,"AI_SOURCE_CROSSCHECKED");
  assert.match(r.observedResult,/Week-24 complete response/);
  assert.match(r.uncertaintyReview,/52-week outcomes/);
  assert.match(r.benchmarkSourceUrl,/fda.gov/);
  const grade=fullReviewedTrialCandidate({nctId:r.nctId,
   ticker:r.ticker,drug:r.drug,indication:r.indication},"post",true,feed);
  assert.equal(grade.independentReviewedCount,0);
  assert.equal(grade.aiCrosscheckedCount,3);
  assert.equal(grade.fullResearchScore,null);
 }
});

test("10-trial real clinical pilot has only research grades, not full RAAS or fabricated FDA probabilities",()=>{
 const pilot=require("node:fs").readFileSync(require("node:path").join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8");
 const feed=parseReviewedMetricFeed(JSON.parse(pilot));
 const cases=new Set(feed.records.filter(r=>r.stage==="post").map(r=>r.nctId));
 assert.equal(cases.size,10);
 assert.equal(feed.records.length,82);
 for(const nctId of cases){
  const r=feed.records.find(x=>x.nctId===nctId);
  const scored=fullReviewedTrialCandidate({nctId,ticker:r.ticker,drug:r.drug,
   indication:r.indication},"post",true,feed);
  assert.ok(scored.aiCrosscheckedCount>=2 && scored.aiCrosscheckedCount<=9);
  assert.equal(scored.independentReviewedCount,0);
  assert.equal(scored.fullResearchScore,null);
  assert.equal(scored.approvedOverallScore,null);
  assert.equal(scored.missingMetricIds.length,30-scored.aiCrosscheckedCount);
 }
});

test("Actual trial-specific safety and pre-action CMC findings remain distinct from full 30-metric RAAS",()=>{
 const fs=require("node:fs"),p=require("node:path");
 const j=JSON.parse(fs.readFileSync(p.join(__dirname,"../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const x=parseReviewedMetricFeed(j),safety=x.records.filter(r=>r.metricId==="post-1-5");
 const cmc=x.records.filter(r=>r.metricId==="post-3-4");
 assert.equal(safety.length,8);
 assert.equal(cmc.length,2);
 assert.deepEqual(cmc.map(r=>r.nctId).sort(),["NCT04576949","NCT05206370"]);
 for(const r of cmc){
  assert.equal(r.finding,"MATERIAL_ADVERSE");
  assert.equal(r.sourceDate,"2026-05-12");
  assert.equal(r.independentReview,"AI_SOURCE_CROSSCHECKED");
  assert.ok(!r.sourceUrl.includes("20260630"));
  const score=fullReviewedTrialCandidate({nctId:r.nctId,ticker:r.ticker,
   drug:r.drug,indication:r.indication},"post",true,x);
  assert.equal(score.fullResearchScore,null);
  assert.equal(score.approvedOverallScore,null);
  assert.equal(score.independentReviewedCount,0);
 }
});

test("Eight CI/multiplicity reviews and six shared-NDA filing/target metrics are genuine, explicitly historical and unvalidated",()=>{
 const p=require("node:path"),src=JSON.parse(fs.readFileSync(p.join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const feed=parseReviewedMetricFeed(src);
 const ci=feed.records.filter(r=>r.metricId==="post-1-3");
 assert.equal(ci.length,8);
 assert.ok(ci.every(r=>r.independentReview==="AI_SOURCE_CROSSCHECKED"&&
  r.benchmarkSourceUrl.includes("fda.gov")&&/CI|interval|confidence/i.test(r.observedResult)));
 const expected=["post-3-1","post-3-5","post-6-1"];
 for(const id of expected){
  const rows=feed.records.filter(r=>r.metricId===id);
  assert.equal(rows.length,2);
  assert.deepEqual(rows.map(r=>r.nctId).sort(),["NCT04576949","NCT05206370"]);
  for(const r of rows){
   assert.match(r.criticalRiskReview,/NDA|PDUFA|target/i);
   const result=fullReviewedTrialCandidate({nctId:r.nctId,
    ticker:r.ticker,drug:r.drug,indication:r.indication},"post",true,feed);
   assert.equal(result.independentReviewedCount,0);
   assert.equal(result.fullResearchScore,null);
   assert.equal(result.approvedOverallScore,null);
  }
 }
});

test("Two source-checked current Phase 3 TOP trial research grades are exact-identity and never FDA probabilities",()=>{
 const path=require("node:path"),raw=JSON.parse(fs.readFileSync(path.join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const feed=parseReviewedMetricFeed(raw);
 assert.equal(feed.records.filter(r=>r.stage==="pre").length,27);
 const trials=[
  {nctId:"NCT07671911",ticker:"TRVI",drug:"NAL ER",
   indication:"Idiopathic Pulmonary Fibrosis"},
  {nctId:"NCT07363577",ticker:"LBRX",
   drug:"LB-102 (100 mg tablet) | LB-102 (50 mg tablet)",
   indication:"Schizophrenia"}
 ];
 const ids=["pre-1-1","pre-1-2","pre-1-4","pre-3-2","pre-4-1"];
 for(const trial of trials){
  const current=fullReviewedTrialCandidate(trial,"pre",true,feed);
  assert.equal(current.aiCrosscheckedCount,5);
  assert.equal(current.independentReviewedCount,0);
  assert.deepEqual(current.grades.map(g=>g.metricId).sort(),ids);
  assert.equal(current.missingMetricIds.length,25);
  assert.equal(current.fullResearchScore,null);
  assert.equal(current.approvedOverallScore,null);
  const wrong=fullReviewedTrialCandidate({...trial,drug:"WRONG DRUG"},"pre",true,feed);
  assert.equal(wrong.reviewedCount,0);
  const notPost=fullReviewedTrialCandidate(trial,"post",true,feed);
  assert.equal(notPost.reviewedCount,0);
 }
});


test("additional TOP NCTs keep prior response, open-label safety, and previous FDA CRL distinct",()=>{
 const path=require("node:path"),raw=JSON.parse(fs.readFileSync(path.join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const feed=parseReviewedMetricFeed(raw);
 const cases=[
  {nctId:"NCT07868419",ticker:"TRVI",drug:"NAL ER",
   indication:"Idiopathic Pulmonary Fibrosis",metricIds:["pre-1-1","pre-1-2","pre-1-4","pre-3-2","pre-4-1"]},
  {nctId:"NCT07369154",ticker:"LBRX",drug:"LB-102",
   indication:"Schizophrenia",metricIds:["pre-1-1","pre-1-2","pre-1-4","pre-3-2"]},
  {nctId:"NCT06736574",ticker:"CYTK",drug:"omecamtiv mecarbil",
   indication:"Heart Failure With Reduced Ejection Fraction",
   metricIds:["pre-1-1","pre-1-2","pre-1-4","pre-1-5","pre-3-2"]}
 ];
 for(const c of cases){
  const result=fullReviewedTrialCandidate(c,"pre",true,feed);
  assert.equal(result.aiCrosscheckedCount,c.metricIds.length);
  assert.deepEqual(result.grades.map(x=>x.metricId).sort(),c.metricIds);
  assert.equal(result.independentReviewedCount,0);
  assert.equal(result.missingMetricIds.length,30-c.metricIds.length);
  assert.equal(result.fullResearchScore,null);
  assert.equal(result.approvedOverallScore,null);
  assert.equal(fullReviewedTrialCandidate(c,"post",true,feed).reviewedCount,0);
  assert.equal(fullReviewedTrialCandidate({...c,drug:"unrelated drug"},"pre",true,feed).reviewedCount,0);
 }
 const fda=feed.records.find(x=>x.nctId==="NCT06736574"&&x.metricId==="pre-1-5");
 assert.equal(fda.finding,"BELOW_BENCHMARK");
 assert.match(fda.observedResult,/2023/);
 assert.match(fda.criticalRiskReview,/2023/);
 assert.equal(fda.independentReview,"AI_SOURCE_CROSSCHECKED");
});

test("MLTX IZAR-2 reviewed as separate PRE trial and COGT GIST PEAK as POST accepted NDA, no invented odds",()=>{
 const path=require("node:path"),raw=JSON.parse(fs.readFileSync(path.join(__dirname,
  "../data/raas-reviewed-metric-assessments.json"),"utf8"));
 const feed=parseReviewedMetricFeed(raw);
 const izar={nctId:"NCT06641089",ticker:"MLTX",drug:"sonelokimab",
  indication:"Psoriatic Arthritis"};
 const peak={nctId:"NCT05208047",ticker:"COGT",
  drug:"bezuclastinib plus sunitinib",indication:"Gastrointestinal Stromal Tumors"};
 const a=fullReviewedTrialCandidate(izar,"pre",true,feed);
 assert.equal(a.aiCrosscheckedCount,3);
 assert.deepEqual(a.grades.map(x=>x.metricId).sort(),["pre-1-2","pre-3-2","pre-4-1"]);
 assert.equal(a.independentReviewedCount,0);
 assert.equal(a.fullResearchScore,null);
 assert.equal(a.approvedOverallScore,null);
 assert.equal(fullReviewedTrialCandidate(izar,"post",true,feed).reviewedCount,0);
 const b=fullReviewedTrialCandidate(peak,"post",true,feed);
 assert.equal(b.aiCrosscheckedCount,5);
 assert.deepEqual(b.grades.map(x=>x.metricId).sort(),
  ["post-1-1","post-1-2","post-1-3","post-3-1","post-6-1"]);
 assert.equal(b.independentReviewedCount,0);
 assert.equal(b.fullResearchScore,null);
 assert.equal(b.approvedOverallScore,null);
 assert.equal(fullReviewedTrialCandidate(peak,"pre",true,feed).reviewedCount,0);
 assert.equal(fullReviewedTrialCandidate({...peak,drug:"bezuclastinib"},"post",true,feed).reviewedCount,0);
});
