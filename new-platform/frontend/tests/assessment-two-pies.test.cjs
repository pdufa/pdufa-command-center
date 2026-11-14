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

test("first frozen prospective 2026 qualitative forecast is source-backed and produces no invented accuracy",()=>{
  const model=getAssessmentPieData();
  assert.equal(model.totalCompleted,1);
  assert.equal(model.compared,0);
  assert.equal(model.correct,0);
  assert.equal(model.incorrect,0);
  assert.equal(model.awaitingDecision,1);
  assert.equal(model.accuracyPercent,null);
  assert.equal(model.latest.ticker,"SMMT");
  assert.equal(model.latest.applicationCycleId,"SMMT-HARMONI-US-BLA-2026-NOV14");
  assert.deepEqual(model.latest.ncts,["NCT06396065"]);
  assert.equal(model.latest.completedAt,"2026-11-09T20:44:09Z");
  assert.equal(model.latest.predictedOutcome,"CRL");
  assert.equal(model.latest.calibrationStatus,"NOT_VALIDATED");
  assert.equal(model.latest.researchOnly,true);
  assert.equal(model.latest.decisionVerdict,"AWAITING_DECISION");
  assert.deepEqual(model.latest.probabilitySlices,[]);
  assert.match(model.latest.sourceFreezeUrl,/80254f5644dfab055bcca0eec28617888caeb293/);
  assert.deepEqual(model.overallTrend,[]);
  assert.deepEqual(model.latestTrend,[]);
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

test("two chart panels show a frozen research pilot but no invented validation or FDA decision",()=>{
  const html=renderToStaticMarkup(React.createElement(Pies,getAssessmentPieData()));
  assert.match(html,/data-testid="total-assessments-pie"/);
  assert.match(html,/data-testid="latest-prediction-pie"/);
  assert.equal((html.match(/role="img"/g)||[]).length,4);
  assert.match(html,/data-testid="overall-accuracy-line"/);
  assert.match(html,/data-testid="latest-outlook-line"/);
  assert.match(html,/Overall competitiveness trend/);
  assert.match(html,/Latest prediction outlook trend/);
  assert.match(html,/At least two different FDA decision dates/);
  assert.match(html,/At least two dated, independently calibrated prediction versions/);
  assert.doesNotMatch(html,/<polyline /);
  assert.match(html,/Overall prediction accuracy/);
  assert.match(html,/No verified comparisons yet/);
  assert.match(html,/Accurate: 0/);
  assert.match(html,/Not Accurate: 0/);
  assert.match(html,/FDA decisions/);
  assert.match(html,/No independently validated probabilities yet/);
  assert.match(html,/Last completed prediction/);
  assert.match(html,/SMMT/);
  assert.match(html,/RESEARCH-ONLY DIRECTIONAL CALL/);
  assert.match(html,/HARMONI-SMMT-PDUFA-2026-11-14-V1/);
  assert.doesNotMatch(html,/NO COMPLETED PREDICTION/);
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

test("total competitiveness trend matches dated FDA decisions and exact same cohort as accuracy pie",()=>{
  const compared=summarizeFdaPredictionAccuracy([
    create({predictionId:"a-first",actualDecisionAt:"2026-02-01T11:00:00Z"}),
    create({predictionId:"a-revised",completedAt:"2026-01-20T18:00:00Z",
      actualDecisionAt:"2026-02-01T11:00:00Z",predictedOutcome:"CRL"}),
    create({predictionId:"b",applicationCycleId:"cycle-b",ticker:"BBB",
      predictedOutcome:"CRL",approvalProbability:0.2,crlProbability:0.8,
      actualDecisionAt:"2026-02-01T17:00:00Z"}),
    create({predictionId:"c",applicationCycleId:"cycle-c",ticker:"CCC",
      actualDecisionAt:"2026-03-15T17:00:00Z"}),
    create({predictionId:"d",applicationCycleId:"cycle-d",ticker:"DDD",
      actualDecisionAt:"2026-05-15T17:00:00Z",actualDecisionVerified:false}),
    create({predictionId:"e",applicationCycleId:"cycle-e",ticker:"EEE",
      completedAt:"2026-06-15T17:00:00Z",
      actualDecisionAt:"2026-04-15T17:00:00Z"})
  ]);
  assert.equal(compared.compared,3);
  assert.equal(compared.correct,2);
  assert.equal(compared.incorrect,1);
  assert.deepEqual(compared.overallTrend.map(x=>x.date),["2026-02-01","2026-03-15"]);
  assert.deepEqual(compared.overallTrend.map(x=>x.compared),[2,3]);
  assert.deepEqual(compared.overallTrend.map(x=>x.accuratePct),[50,66.67]);
  assert.deepEqual(compared.overallTrend.map(x=>x.notAccuratePct),[50,33.33]);
  assert.ok(Math.abs(compared.overallTrend.at(-1).accuratePct-compared.accuracyPercent)<0.005);
});

test("line chart correctly plots misses, chronological cumulative percentages and no invented baseline",()=>{
  const model=summarizeFdaPredictionAccuracy([
    create({predictionId:"miss",applicationCycleId:"cycle-miss",
      predictedOutcome:"CRL",approvalProbability:0.3,crlProbability:0.7,
      actualDecisionAt:"2026-02-01T12:00:00Z"}),
    create({predictionId:"match",applicationCycleId:"cycle-match",
      actualDecisionAt:"2026-04-01T12:00:00Z"})
  ]);
  assert.deepEqual(model.overallTrend.map(p=>p.accuratePct),[0,50]);
  assert.deepEqual(model.overallTrend.map(p=>p.notAccuratePct),[100,50]);
  assert.equal(model.accuracyPercent,50);
  const markup=renderToStaticMarkup(React.createElement(Pies,model));
  assert.match(markup,/data-testid="overall-accuracy-pie-trend-best-fit"/);
  assert.match(markup,/data-testid="performance-best-fit-first"/);
  assert.match(markup,/data-testid="performance-best-fit-second"/);
  assert.doesNotMatch(markup,/<polyline /);
  assert.match(markup,/data-testid="overall-accuracy-pie-trend-line"/);
  assert.match(markup,/data-testid="overall-accuracy-line"/);
  assert.match(markup,/0%/);
  assert.match(markup,/100%/);
});

test("last competitiveness trend is exact-cycle, time-ordered, calibrated, excludes post-FDA decision versions",()=>{
  const rows=[
    create({predictionId:"first",completedAt:"2026-01-01T12:00:00Z",
      approvalProbability:0.80,crlProbability:0.20}),
    create({predictionId:"second",completedAt:"2026-01-05T12:00:00Z",
      approvalProbability:0.60,crlProbability:0.40}),
    create({predictionId:"unvalidated",completedAt:"2026-01-07T12:00:00Z",
      calibrationStatus:"NOT_VALIDATED",approvalProbability:0.55,crlProbability:0.45}),
    create({predictionId:"bad-sum",completedAt:"2026-01-08T12:00:00Z",
      approvalProbability:0.55,crlProbability:0.56}),
    create({predictionId:"other",applicationCycleId:"other-cycle",
      completedAt:"2026-01-09T12:00:00Z",
      approvalProbability:0.95,crlProbability:0.05}),
    create({predictionId:"last",completedAt:"2026-01-10T12:00:00Z",
      approvalProbability:0.45,crlProbability:0.55}),
  ];
  const trend=summarizeFdaPredictionAccuracy(rows);
  assert.equal(trend.latest.applicationCycleId,"cycle-a");
  assert.deepEqual(trend.latestTrend.map(x=>x.predictionId),["first","second","last"]);
  assert.deepEqual(trend.latestTrend.map(x=>x.approvalPct),[80,60,45]);
  assert.deepEqual(trend.latestTrend.map(x=>x.crlPct),[20,40,55]);
  const html=renderToStaticMarkup(React.createElement(Pies,trend));
  assert.match(html,/data-testid="latest-prediction-pie-trend-best-fit"/);
  assert.match(html,/data-testid="performance-best-fit-first"/);
  assert.match(html,/data-testid="performance-best-fit-second"/);
  assert.doesNotMatch(html,/<polyline /);
  assert.match(html,/data-testid="latest-prediction-pie-trend-line"/);
  const late=summarizeFdaPredictionAccuracy([...rows,create({
    predictionId:"after-fda",completedAt:"2026-05-15T12:00:00Z",
    actualDecisionAt:"2026-05-10T12:00:00Z",
    approvalProbability:0.99,crlProbability:0.01
  })]);
  assert.deepEqual(late.latestTrend.map(x=>x.predictionId),["first","second","last"]);
});

test("a single calibrated prediction snapshot is not a manufactured line trend",()=>{
  const one=summarizeFdaPredictionAccuracy([create()]);
  assert.equal(one.latestTrend.length,1);
  const html=renderToStaticMarkup(React.createElement(Pies,one));
  assert.match(html,/Latest prediction outlook trend/);
  assert.match(html,/No verified trend yet/);
  assert.doesNotMatch(html,/<polyline /);
});

test("prospective forecast freeze precedes PDUFA and did not mutate canonical 32-trial FOCUS eligibility",()=>{
  const record=JSON.parse(fs.readFileSync(path.join(root,"data/fdaPredictionDecisionAudit.json"),"utf8")).records[0];
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,32);
  assert.equal(focus.records.some(x=>x.nct==="NCT06396065"),false);
  assert.equal(record.researchOnly,true);
  assert.equal(record.actualDecisionVerified,false);
  assert.equal(record.actualDecisionAt,null);
  assert.equal(record.actualDecisionSourceUrl,null);
  assert.equal(record.actualOutcome,"PENDING");
  assert.equal(record.approvalProbability,null);
  assert.equal(record.crlProbability,null);
  assert.equal(record.status,"COMPLETED");
  assert.equal(record.evaluationCohort,"PROSPECTIVE");
  assert.ok(Date.parse(record.completedAt)<Date.parse(record.pdufaDate+"T00:00:00Z"));
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/FIRST PROSPECTIVE 2026 PDUFA PREDICTION PILOT/);
  assert.match(page,/2026-harmoni-first-prospective-forecast.md/);
  assert.match(page,/roster-gated automatic source worker was not started/);
});
