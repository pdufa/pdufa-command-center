const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const React = require("react");
const {create,act} = require("react-test-renderer");

for (const ext of [".ts",".tsx"]) require.extensions[ext] = (module,file) =>
  module._compile(ts.transpileModule(fs.readFileSync(file,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true},
  }).outputText,file);

const {createNumericForecastDisplay,HISTORICAL_SIMILARITY_DIMENSIONS} = require("../lib/numeric-forecast-metrics.ts");
const {ASSESSMENT_WEIGHTS} = require("../lib/candidate-assessments.ts");
const {default:NumericForecastMetrics} = require("../app/NumericForecastMetrics.tsx");
const trialId = "TRIAL|NCT02142738";

function createDetail(stage="PIPELINE",mode="PARTIAL") {
  const categories = ASSESSMENT_WEIGHTS[stage].map((maximum,i)=>{
    const complete = mode==="COMPLETE" || (mode==="PARTIAL" && i<2);
    const partial = mode==="PARTIAL" && i===2;
    const coverage = complete?maximum:partial?3:0;
    const observedPoints = complete?(i===0?0:maximum/2):partial?1:0;
    return {
      id:"M"+(i+1),label:"Metric "+(i+1),maximum,
      score:complete?observedPoints:null,
      observedPoints,coverage,
      status:complete?"COMPLETE":partial?"PARTIAL":"MISSING",
      metrics:[{coverage,points:complete||partial?observedPoints:null}],
    };
  });
  const coverage=categories.reduce((n,c)=>n+c.coverage,0);
  const observedPoints=categories.reduce((n,c)=>n+c.observedPoints,0);
  const model={
    score:mode==="COMPLETE"?observedPoints:null,coverage,observedPoints,
    status:mode==="COMPLETE"?"COMPLETE":"PARTIAL",categories,
  };
  return {id:trialId,nctId:"NCT02142738",modelVersion:"test-v1",asOf:"2026-10-26",
    models:{[stage]:model},qualification:{note:"Research only"},riskFlags:[]};
}

test("numeric scorecard shows genuine zero, observed partial points and complete-category score, never a phantom probability",()=>{
  const s=createNumericForecastDisplay(createDetail(),"PIPELINE");
  assert.equal(s.metrics.length,7);
  assert.equal(s.categoryTotal,7);
  assert.equal(s.completeCategories,2);
  assert.equal(s.researchModelScore,null);
  assert.equal(s.metrics[0].ratingOutOf100,0);
  assert.equal(s.metrics[1].ratingOutOf100,50);
  assert.equal(s.metrics[2].ratingOutOf100,null);
  assert.equal(s.metrics[2].points,1);
  assert.equal(s.metrics[2].evidencePoints,3);
  assert.equal(s.metrics[2].reviewedMeasurements,1);
  assert.equal(s.metrics[3].reviewedMeasurements,0);
  assert.equal(s.evidenceCoverageOutOf100,48);
  assert.equal(s.observedResearchPoints,11);
  assert.equal(s.comparableTrialCount,null);
  assert.equal(s.historicalApprovalCount,null);
  assert.equal(s.historicalDecisionDenominator,null);
  assert.equal(s.readinessGradeOutOf100,null);
  assert.equal(s.reluctanceGradeOutOf100,null);
  assert.equal(s.preliminaryHistoricalForecast,null);
  assert.equal(s.calibratedFdaApprovalProbability,null);
  assert.equal(s.scientificAssessmentCount,null);
  assert.equal(s.scientificAssessmentDenominator,40);
  assert.equal(HISTORICAL_SIMILARITY_DIMENSIONS.length,8);
});

test("all three existing ranking models use exactly 7 categories totaling 100 points",()=>{
  for(const stage of ["PIPELINE","GEM_JR","GEM"]){
    const model=createDetail(stage,"COMPLETE");
    const s=createNumericForecastDisplay(model,stage);
    assert.equal(s.metrics.reduce((n,x)=>n+x.maximum,0),100);
    assert.equal(s.completeCategories,7);
    assert.equal(s.researchModelScore,s.observedResearchPoints);
    assert.equal(s.evidenceCoverageOutOf100,100);
    assert.equal(s.metrics[0].ratingOutOf100,0); // score of zero, NOT missing
  }
});

test("missing category evidence, contradicted totals and invalid dates cannot produce a rating",()=>{
  let d=createDetail();d.models.PIPELINE.categories[2].score=1;
  assert.throws(()=>createNumericForecastDisplay(d,"PIPELINE"),/metric rating/);
  d=createDetail();d.models.PIPELINE.coverage=99;
  assert.throws(()=>createNumericForecastDisplay(d,"PIPELINE"),/do not reconcile/);
  d=createDetail();d.models.PIPELINE.categories[0].observedPoints=30;
  assert.throws(()=>createNumericForecastDisplay(d,"PIPELINE"),/metric rating/);
  d=createDetail();d.models.PIPELINE.score=96;
  assert.throws(()=>createNumericForecastDisplay(d,"PIPELINE"),/do not reconcile/);
  d=createDetail();d.asOf="unverified";
  assert.throws(()=>createNumericForecastDisplay(d,"PIPELINE"),/unavailable/);
  d=createDetail();d.models.PIPELINE.categories[1].id=d.models.PIPELINE.categories[0].id;
  assert.throws(()=>createNumericForecastDisplay(d,"PIPELINE"),/metric rating/);
});

test("trial-level display includes numeric denominators and explicit withheld historical and FDA ratings",async()=>{
  global.IS_REACT_ACT_ENVIRONMENT=true;
  let root;
  try{
    await act(async()=>{root=create(React.createElement(NumericForecastMetrics,{detail:createDetail(),stage:"PIPELINE"}))});
    const body=JSON.stringify(root.toJSON());
    assert.match(body,/Numerical trial ratings/);
    assert.match(body,/0 \/ 100/);
    assert.match(body,/50 \/ 100/);
    assert.match(body,/— \/ 100/);
    assert.match(body,/— \/ 40/);
    assert.match(body,/2 \/ 7/);
    assert.match(body,/FDA approval probability/);
    assert.match(body,/NOT YET SCORED/);
    assert.match(body,/Historical comparable scoring/);
    assert.doesNotMatch(body,/66\.7% approval/);
  } finally { if(root) await act(async()=>root.unmount()); }
});

test("UI remains read-only; source trial scores are not overwritten by a new forecast",()=>{
  const ui=fs.readFileSync(path.join(__dirname,"../app/NumericForecastMetrics.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(__dirname,"../app/CandidateAssessments.tsx"),"utf8");
  assert.match(parent, /<NumericForecastMetrics detail=\{data\} stage=\{stage\} \/>/);
  assert.match(ui,/Historical-comparable forecast: NOT YET SCORED/);
  assert.doesNotMatch(ui,/fetch\(|\bPUT\b|\bPOST\b|\bonClick=|\bonSubmit=/);
});
