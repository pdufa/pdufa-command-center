const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
const root=path.resolve(__dirname,"..");

for(const ext of [".ts",".tsx"]){
  require.extensions[ext]=(module,filename)=>module._compile(
    ts.transpileModule(fs.readFileSync(filename,"utf8"),{
      compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
        jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
    }).outputText,filename
  );
}

const {getAssessmentPieData,summarizeFdaPredictionAccuracy}=require("../lib/focus-assessment-chart.ts");
const Pies=require("../app/AssessmentStatusPies.tsx").default;
const create=(overrides={})=>({
  predictionId:"frozen-a",applicationCycleId:"cycle-a",ticker:"AAA",
  ncts:["NCT12345678"],drug:"Study A",indication:"Disease A",
  status:"COMPLETED",completedAt:"2026-01-10T18:00:00Z",
  predictedOutcome:"APPROVAL",calibrationStatus:"VALIDATED",
  approvalProbability:0.72,crlProbability:0.28,
  evaluationCohort:"PROSPECTIVE",
  actualOutcome:"APPROVAL",actualDecisionAt:"2026-05-10T18:00:00Z",
  actualDecisionSourceUrl:"https://www.fda.gov/drugs/decision-a",
  actualDecisionVerified:true,
  ...overrides
});

test("current production audit does not invent completed predictions or historical accuracy",()=>{
  const model=getAssessmentPieData();
  assert.equal(model.totalCompleted,0);
  assert.equal(model.compared,0);
  assert.equal(model.correct,0);
  assert.equal(model.incorrect,0);
  assert.equal(model.accuracyPercent,null);
  assert.equal(model.latest,null);
  assert.equal(model.comparisonSlices.reduce((sum,slice)=>sum+slice.value,0),0);
  assert.deepEqual(model.comparisonSlices.map(x=>x.label),["Accurate","Not Accurate"]);
  assert.deepEqual(model.comparisonSlices.map(x=>x.value),[0,0]);
});

test("overall FDA validity counts only earliest predecision completed prediction per cycle",()=>{
  const model=summarizeFdaPredictionAccuracy([
    create(),
    create({predictionId:"revised-a",completedAt:"2026-03-10T18:00:00Z",predictedOutcome:"CRL"}),
    create({predictionId:"frozen-b",applicationCycleId:"cycle-b",ticker:"BBB",
      completedAt:"2026-02-10T18:00:00Z",predictedOutcome:"CRL",
      actualOutcome:"APPROVAL",actualDecisionAt:"2026-06-10T18:00:00Z"}),
    create({predictionId:"frozen-c",applicationCycleId:"cycle-c",ticker:"CCC",
      completedAt:"2026-03-20T18:00:00Z",actualOutcome:"PENDING",
      actualDecisionAt:null,actualDecisionSourceUrl:null,actualDecisionVerified:false}),
    create({predictionId:"after-outcome",applicationCycleId:"cycle-d",ticker:"DDD",
      completedAt:"2026-09-10T18:00:00Z",actualDecisionAt:"2026-05-10T18:00:00Z"}),
  ]);
  assert.equal(model.totalCompleted,4);
  assert.equal(model.compared,2);
  assert.equal(model.correct,1);
  assert.equal(model.incorrect,1);
  assert.equal(model.awaitingDecision,2);
  assert.equal(model.accuracyPercent,50);
  assert.equal(model.latest.predictionId,"after-outcome");
  assert.equal(model.latest.decisionVerdict,"AWAITING_DECISION");
});

test("unverified actual decisions and abstentions never become correct or incorrect",()=>{
  const rows=[
    create({actualDecisionVerified:false}),
    create({predictionId:"b",applicationCycleId:"cycle-b",
      actualDecisionSourceUrl:"http://unverified.example/decision"}),
    create({predictionId:"c",applicationCycleId:"cycle-c",
      predictedOutcome:"ABSTAIN"}),
    create({predictionId:"d",applicationCycleId:"cycle-d",status:"DRAFT"}),
  ];
  const model=summarizeFdaPredictionAccuracy(rows);
  assert.equal(model.compared,0);
  assert.equal(model.totalCompleted,2);
  assert.equal(model.awaitingDecision,2);
  assert.equal(model.accuracyPercent,null);
});

test("last completed prediction shows only valid calibrated probabilities",()=>{
  const validated=summarizeFdaPredictionAccuracy([
    create({predictionId:"a",completedAt:"2026-01-01T18:00:00Z"}),
    create({predictionId:"b",applicationCycleId:"cycle-b",ticker:"BBB",
      completedAt:"2026-03-01T18:00:00Z",calibrationStatus:"VALIDATED",
      approvalProbability:0.27,crlProbability:0.73,
      predictedOutcome:"CRL",actualOutcome:"PENDING"})
  ]);
  assert.equal(validated.latest.predictionId,"b");
  assert.equal(validated.latest.decisionVerdict,"AWAITING_DECISION");
  assert.deepEqual(validated.latest.probabilitySlices.map(x=>x.value),[0.27,0.73]);
  for(const changed of [
    {calibrationStatus:"NOT_VALIDATED"},
    {approvalProbability:null},
    {approvalProbability:0.8,crlProbability:0.7}
  ]){
    const candidate=summarizeFdaPredictionAccuracy([create(changed)]);
    assert.deepEqual(candidate.latest.probabilitySlices,[]);
  }
});

test("two chart panels show real accuracy semantics and fail closed on empty audit",()=>{
  const html=renderToStaticMarkup(React.createElement(Pies,getAssessmentPieData()));
  assert.match(html,/data-testid="total-assessments-pie"/);
  assert.match(html,/data-testid="latest-prediction-pie"/);
  assert.equal((html.match(/role="img"/g)||[]).length,2);
  assert.match(html,/Overall prediction accuracy/);
  assert.match(html,/No verified comparisons yet/);
  assert.match(html,/Accurate: 0/);
  assert.match(html,/Not Accurate: 0/);
  assert.match(html,/FDA decisions/);
  assert.match(html,/No independently validated probabilities yet|NO COMPLETED PREDICTION/);
  assert.match(html,/Last completed prediction/);
  assert.match(html,/NO COMPLETED PREDICTION/);
  assert.doesNotMatch(html,/203 evidence checks/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<AssessmentStatusPies \{\.\.\.pies\}\/>/);
});

test("verified latest prediction switches from probability forecast to accurate/not accurate comparison",()=>{
  const accurate=summarizeFdaPredictionAccuracy([create()]);
  assert.equal(accurate.latest.decisionVerdict,"ACCURATE");
  assert.deepEqual(accurate.latest.decisionComparisonSlices.map(x=>x.value),[1,0]);
  const matchedHtml=renderToStaticMarkup(React.createElement(Pies,accurate));
  assert.match(matchedHtml,/Prediction validity: Accurate/);
  const notAccurate=summarizeFdaPredictionAccuracy([create({
    predictedOutcome:"CRL",approvalProbability:0.25,crlProbability:0.75
  })]);
  assert.equal(notAccurate.latest.decisionVerdict,"NOT_ACCURATE");
  assert.deepEqual(notAccurate.latest.decisionComparisonSlices.map(x=>x.value),[0,1]);
  const missedHtml=renderToStaticMarkup(React.createElement(Pies,notAccurate));
  assert.match(missedHtml,/Prediction validity: Not Accurate/);
  const pending=summarizeFdaPredictionAccuracy([create({
    actualDecisionVerified:false
  })]);
  assert.equal(pending.latest.decisionVerdict,"AWAITING_DECISION");
  assert.equal(pending.compared,0);
  assert.deepEqual(pending.latest.decisionComparisonSlices.map(x=>x.value),[0,0]);
  const pendingHtml=renderToStaticMarkup(React.createElement(Pies,pending));
  assert.match(pendingHtml,/Awaiting FDA Decision/);
});

test("historical not-blind backtests stay excluded from the current prediction-accuracy engine",()=>{
  const source=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(source,/historical_assessed_decisions|raas_|prediction_engine_history/);
});
