const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
const root=path.resolve(__dirname,"..");
require.extensions[".tsx"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,filename
);
const historical=require("../data/levelThreeAbbvieHistorical2026.json");
const prior=require("../data/levelThreePharHistorical2026.json");
const prospective=require("../data/fdaPredictionDecisionAudit.json");
const ino=require("../data/blindHistoricalForecasts2026.json");
const Chart=require("../app/AssessmentLevelChart.tsx").default;
const Panel=require("../app/SkyriziHistoricalLevelThreePanel.tsx").default;

test("October 23 ABBV action is before October 24 PHAR and is date-caveated",()=>{
  const x=historical.records[0],p=prior.records[0];
  assert.equal(historical.dataset,"OUTCOME_AWARE_HISTORICAL_LEVEL3_COMPARISON_NOT_BLIND");
  assert.equal(x.assessmentId,"HIST-ABBV-SKYRIZI-2026-10-23-LEVEL3-001");
  assert.equal(x.ticker,"ABBV");
  assert.equal(x.fdaApplicationId,"BLA 761105/S-053");
  assert.deepEqual(x.ncts,["NCT06063967"]);
  assert.equal(x.clinicalPhase,"PHASE_3_RANDOMIZED_DOUBLE_BLIND");
  assert.equal(x.trackerListedPdufaDate,"2026-10-23");
  assert.ok(x.trackerListedPdufaDate<p.originalPdufaDate);
  assert.match(x.pdufaDateVerification,/THIRD_PARTY_TRACKER_ONLY/);
  assert.equal(x.evidenceCutoff,"2026-10-13");
  assert.ok(x.evidenceCutoff<x.actualFdaActionDate);
  assert.equal(x.assessmentLevelStyle,3);
  assert.equal(x.assessmentDirection,"APPROVAL");
  assert.equal(x.assessmentStrength,"LEAN");
  assert.equal(x.actualOutcome,"APPROVAL");
  assert.equal(x.actualFdaActionDate,"2026-10-23");
  assert.equal(x.calibratedProbability,null);
  assert.equal(x.certainty,"NOT_VALIDATED");
  assert.equal(x.outcomeExposedBeforeAssessment,true);
  assert.equal(x.blind,false);
  assert.equal(x.outcomeAssessment,"DIRECTION_MATCHED_BUT_NOT_PREDICTIVE");
  assert.equal(x.excludedFromProspectiveAccuracy,true);
  assert.equal(x.excludedFromRetrospectiveBlindValidation,true);
  assert.equal(x.excludedFromCalibration,true);
});

test("the assessment chart and case display include ABBV level, forecast and actual FDA decision",()=>{
  const chart=renderToStaticMarkup(React.createElement(Chart));
  const panel=renderToStaticMarkup(React.createElement(Panel));
  assert.match(chart,/data-testid="research-assessment-level-chart"/);
  assert.match(chart,/ABBV · SKYRIZI/);
  assert.match(chart,/Level 3-style/);
  assert.match(chart,/FDA approved/);
  assert.match(chart,/outcome-aware/);
  assert.match(panel,/data-testid="historical-level3-abbv-skyrizi"/);
  assert.match(panel,/data-testid="abbv-assessment-level"/);
  assert.match(panel,/Approval lean/);
  assert.match(panel,/data-testid="abbv-actual-outcome"/);
  assert.match(panel,/October 23, 2026/);
  assert.match(panel,/NCT06063967/);
  assert.match(panel,/original predecision sponsor-announced PDUFA target date/);
  assert.match(panel,/NOT A BLIND PREDICTION/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<SkyriziHistoricalLevelThreePanel\/>/);
  assert.match(page,/<JoenjaHistoricalLevelThreePanel\/>/);
  assert.match(page,/<AssessmentLevelChart\/>/);
});

test("the new retrospective case cannot count as prospective performance or overwrite FOCUS",()=>{
  const x=historical.records[0];
  assert.equal(x.excludedFromProspectiveAccuracy,true);
  assert.equal(x.excludedFromRetrospectiveBlindValidation,true);
  assert.equal(x.excludedFromCalibration,true);
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].ticker,"SMMT");
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  assert.equal(ino.records[0].ticker,"INO");
  assert.equal(ino.records[0].predictedOutcome,"CRL");
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(model,/levelThreeAbbvieHistorical2026/);
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,29);
  assert.equal(focus.records.some(r=>r.nct==="NCT06063967"),false);
});
