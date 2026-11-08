"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {RAAS_PROVISIONAL_RUBRICS,RAAS_PROVISIONAL_FINDINGS,provisionalReviewedGrade,
 provisionalStageCoverage}=require("../lib/raas-provisional-rubric-engine.ts");
const {buildRaasMetricGradebook}=require("../lib/raas-metric-gradebook.ts");
const trial={nctId:"NCT07363577",ticker:"LBRX",
 drug:"LB-102 (100 mg tablet) | LB-102 (50 mg tablet)",indication:"Schizophrenia"};
const sampleReview={
 ...trial,stage:"pre",metricId:"pre-1-2",finding:"ABOVE_BENCHMARK",
 assessedAt:"2026-11-04",sourceDate:"2026-10-15",
 sourceUrl:"https://example.org/pivotal-protocol",
 benchmarkSourceUrl:"https://benchmark.example.org/independent-standard",
 benchmarkId:"independent-protocol-power-benchmark-v1",
 benchmarkContext:"Prespecified sample-size and endpoint comparator requirements for this indication",
 observedResult:"Pivotal randomized protocol shows the specified design and comparator",
 uncertaintyReview:"Confidence interval sensitivity and trial power reviewed independently",
 criticalRiskReview:"Endpoint alignment, multiplicity, and protocol amendments explicitly reviewed",
 reviewerMethod:"Two-source review of prespecified endpoint alignment and design deviations",
 independentReview:"PASSED"
};
test("every one of 60 TOP/BOTTOM metrics has deterministic provisional 5-level rules",()=>{
 assert.equal(RAAS_PROVISIONAL_RUBRICS.length,60);
 assert.equal(new Set(RAAS_PROVISIONAL_RUBRICS.map(x=>x.stage+"/"+x.metricId)).size,60);
 assert.deepEqual(Object.values(RAAS_PROVISIONAL_FINDINGS),[0,25,50,75,100]);
 for(const stage of ["pre","post"]){
  const metrics=RAAS_PROVISIONAL_RUBRICS.filter(x=>x.stage===stage);
  assert.equal(metrics.length,30);
  assert.equal(metrics.reduce((s,x)=>s+x.metricWeightPercent,0),100);
  for(const m of metrics){
   assert.deepEqual(m.bands.map(x=>x.score),[0,25,50,75,100]);
   assert.ok(m.bands.every(x=>x.definition.length>25));
   assert.ok(m.requiredEvidence.length>10&&m.benchmarkRequirement.length>10);
   assert.equal(m.approvedForComposite,false);
  }
 }
});
test("dated independent contextual benchmark review scores a metric, not the overall RAAS",()=>{
 const grade=provisionalReviewedGrade(trial,"pre",sampleReview,"2026-11-04");
 assert.ok(grade);
 assert.equal(grade.score,75);
 assert.equal(grade.approvedForComposite,false);
 assert.equal(grade.metricId,"pre-1-2");
 assert.equal(grade.ruleVersion,"raas-provisional-review-v1");
});
test("unknown, wrong-trial, backdated, self-benchmarked, and missing uncertainty all fail closed",()=>{
 const cases=[
  {...sampleReview,nctId:"NCT99999999"},
  {...sampleReview,ticker:"FAKE"},
  {...sampleReview,drug:"Other Drug"},
  {...sampleReview,indication:"Unrelated disease"},
  {...sampleReview,stage:"post"},
  {...sampleReview,metricId:"post-1-2"},
  {...sampleReview,finding:"UNKNOWN"},
  {...sampleReview,sourceDate:"2026-11-05"},
  {...sampleReview,assessedAt:"2026-11-05"},
  {...sampleReview,sourceUrl:"http://not-secure.org/data"},
  {...sampleReview,benchmarkSourceUrl:sampleReview.sourceUrl},
  {...sampleReview,benchmarkId:"missing"},
  {...sampleReview,uncertaintyReview:""},
  {...sampleReview,criticalRiskReview:""},
  {...sampleReview,independentReview:"PENDING"}
 ];
 for(const rev of cases)assert.equal(provisionalReviewedGrade(trial,"pre",rev,"2026-11-04"),null);
});
test("a missing score is never zero, full aggregation blocked until all 30 grades available",()=>{
 const none=provisionalStageCoverage("post",[]);
 assert.equal(none.observedComponentMean,null);
 assert.equal(none.fullyCoveredProvisionalScore,null);
 assert.equal(none.missing,30);
 const partial=provisionalStageCoverage("pre",[{metricId:"pre-4-1",score:50}]);
 assert.equal(partial.scored,1);
 assert.equal(partial.missing,29);
 assert.equal(partial.weightCoveredPercent,3);
 assert.equal(partial.observedComponentMean,50);
 assert.equal(partial.fullyCoveredProvisionalScore,null);
 const duplicate=provisionalStageCoverage("pre",[
  {metricId:"pre-4-1",score:50},{metricId:"pre-4-1",score:75}]);
 assert.equal(duplicate.scored,0);assert.equal(duplicate.rejected.length,1);
 const fake=provisionalStageCoverage("pre",[{metricId:"post-1-1",score:100}]);
 assert.equal(fake.observedComponentMean,null);assert.equal(fake.rejected.length,1);
 const all=RAAS_PROVISIONAL_RUBRICS.filter(x=>x.stage==="post")
  .map(x=>({metricId:x.metricId,score:75}));
 const full=provisionalStageCoverage("post",all);
 assert.equal(full.scored,30);
 assert.equal(full.weightCoveredPercent,100);
 assert.equal(full.fullyCoveredProvisionalScore,75);
});
test("trial gradebook exposes all 30 rubrics and does not promote timing to full RAAS",()=>{
 const book=buildRaasMetricGradebook(trial,"pre");
 const all=book.categories.flatMap(x=>x.rows);
 assert.equal(all.length,30);
 assert.ok(all.every(x=>x.rubric.metricId===x.id&&x.rubric.bands.length===5));
 assert.equal(book.provisionalDiagnostic.scored,5);
 assert.equal(book.provisionalDiagnostic.weightCoveredPercent,22);
 assert.equal(book.provisionalDiagnostic.missing,25);
 assert.equal(book.provisionalDiagnostic.fullyCoveredProvisionalScore,null);
 assert.equal(book.approvedOverallScore,null);
 const ml=buildRaasMetricGradebook({nctId:"NCT06641076",ticker:"MLTX",
  drug:"sonelokimab",indication:"psoriatic arthritis"},"post");
 assert.equal(ml.provisionalDiagnostic.scored,0);
 assert.equal(ml.provisionalDiagnostic.observedComponentMean,null);
});
test("UI discloses five anchor descriptions, model coverage and incomplete status",()=>{
 const ui=fs.readFileSync(path.join(root,"app/RaasMetricGradebook.tsx"),"utf8");
 assert.match(ui,/metric.rubric.bands.map/);
 assert.match(ui,/model weight has any experimental component grade/);
 assert.match(ui,/NOT an overall RAAS/);
 const result=ts.transpileModule(ui,{fileName:"RaasMetricGradebook.tsx",reportDiagnostics:true,
  compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.deepEqual((result.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error),[]);
});
