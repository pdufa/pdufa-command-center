"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true}}).outputText,file);
const reviews=require("../data/raas-reviewed-metric-assessments.json");
const {uniquelyReviewedUnverifiedProgram,stageResearchReviewsForUnverifiedTrial}
 =require("../lib/raas-reviewed-full-score.ts");
const {buildRaasMetricGradebook}
 =require("../lib/raas-metric-gradebook.ts");

test("exact-NCT/therapy unverified-stage drawer exposes 17 trials' saved reviewed metrics",()=>{
 const seen=new Set(),byStage=new Map();
 for(const source of reviews.records){
  const stageKey=source.nctId+"|"+source.stage;
  const previous=byStage.get(stageKey);
  if(previous)assert.equal(source.ticker,previous.ticker);
  else byStage.set(stageKey,source);
  seen.add(source.nctId);
 }
 assert.equal(reviews.records.length,82);
 assert.equal(seen.size,17);
 let visibleGrades=0;
 for(const r of byStage.values()){
  const trial={nctId:r.nctId,ticker:r.ticker};
  const found=uniquelyReviewedUnverifiedProgram(trial,r.stage);
  assert.ok(found,"Missing exact NCT matched therapy for "+r.nctId);
  assert.equal(found.drug,r.drug);
  assert.equal(found.indication,r.indication);
  const candidate=stageResearchReviewsForUnverifiedTrial(trial,r.stage);
  const book=buildRaasMetricGradebook(found,r.stage,null,false);
  assert.ok(candidate.reviewedCount>0);
  assert.equal(book.reviewedCandidate.reviewedCount,candidate.reviewedCount);
  assert.equal(book.approvedOverallScore,null);
  assert.equal(book.total,30);
  assert.equal(book.categories.flatMap(x=>x.rows).length,30);
  visibleGrades+=book.reviewedCandidate.reviewedCount;
 }
 assert.equal(visibleGrades,82);
});
test("ambiguous same NCT+stage but different therapy must not pick a research grade",()=>{
 const r=reviews.records[0];
 const source={...reviews,records:[r,{...r,drug:"DIFFERENT THERAPY",indication:"DIFFERENT INDICATION"}]};
 const trial={nctId:r.nctId,ticker:r.ticker};
 assert.equal(uniquelyReviewedUnverifiedProgram(trial,r.stage,source),null);
 assert.equal(stageResearchReviewsForUnverifiedTrial(trial,r.stage,source),null);
 assert.equal(uniquelyReviewedUnverifiedProgram({...trial,ticker:"WRONG"},r.stage),null);
 assert.equal(uniquelyReviewedUnverifiedProgram({...trial,nctId:"UNKNOWN"},r.stage),null);
});
test("762-row scoring component uses unique research identity without promoting stage",()=>{
 const code=fs.readFileSync(path.resolve(__dirname,"../app/RaasMetricGradebook.tsx"),"utf8");
 assert.match(code,/uniquelyReviewedUnverifiedProgram/);
 assert.match(code,/!row\.evidence/);
 assert.match(code,/reviewedProgram\?\.drug/);
 assert.match(code,/reviewedProgram\?\.indication/);
 assert.match(code,/stageVerified=bucket!==null/);
 assert.match(code,/buildRaasMetricGradebook\(metricTrial/);
});
