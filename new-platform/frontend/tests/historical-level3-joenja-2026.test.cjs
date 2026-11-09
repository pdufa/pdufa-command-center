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
const phar=require("../data/levelThreePharHistorical2026.json");
const prospective=require("../data/fdaPredictionDecisionAudit.json");
const ino=require("../data/blindHistoricalForecasts2026.json");
const bepi=require("../data/levelThreeHistoricalReconstruction2026.json");
const Chart=require("../app/AssessmentLevelChart.tsx").default;
const Panel=require("../app/JoenjaHistoricalLevelThreePanel.tsx").default;

test("Joenja is the immediately earlier planned October PDUFA with a separate actual approval action date",()=>{
  const r=phar.records[0];
  assert.equal(phar.dataset,"OUTCOME_AWARE_HISTORICAL_LEVEL3_COMPARISON_NOT_BLIND");
  assert.equal(r.assessmentId,"HIST-PHAR-JOENJA-2026-10-24-LEVEL3-001");
  assert.equal(r.ticker,"PHAR");
  assert.equal(r.originalPdufaDate,"2026-10-24");
  assert.equal(bepi.records[0].originalPdufaDate,"2026-10-26");
  assert.ok(r.originalPdufaDate<bepi.records[0].originalPdufaDate);
  assert.deepEqual(r.ncts,["NCT05438407"]);
  assert.equal(r.fdaApplicationId,"NDA 217759/S-006");
  assert.equal(r.clinicalPhase,"PHASE_3_PEDIATRIC_OPEN_LABEL");
  assert.equal(r.assessmentLevelStyle,3);
  assert.equal(r.assessmentDirection,"APPROVAL");
  assert.equal(r.assessmentStrength,"LEAN");
  assert.equal(r.calibratedProbability,null);
  assert.equal(r.certainty,"NOT_VALIDATED");
  assert.equal(r.actualOutcome,"APPROVAL");
  assert.equal(r.actualFdaActionDate,"2026-09-11");
  assert.equal(r.daysBeforePdufa,43);
  assert.ok(r.evidenceCutoff<r.actualFdaActionDate);
  assert.equal(r.outcomeExposedBeforeAssessment,true);
  assert.equal(r.blind,false);
  assert.equal(r.outcomeAssessment,"DIRECTION_MATCHED_BUT_NOT_PREDICTIVE");
  assert.equal(r.excludedFromProspectiveAccuracy,true);
  assert.equal(r.excludedFromRetrospectiveBlindValidation,true);
  assert.equal(r.excludedFromCalibration,true);
  assert.match(r.fdaOutcomeSourceUrl,/^https:\/\/www\.fda\.gov\//);
});

test("PHAR appears in the research level chart and a separate human-readable display",()=>{
  const chart=renderToStaticMarkup(React.createElement(Chart));
  const panel=renderToStaticMarkup(React.createElement(Panel));
  assert.match(chart,/data-testid="research-assessment-level-chart"/);
  assert.match(chart,/PHAR · Joenja/);
  assert.match(chart,/Level 3-style/);
  assert.match(chart,/FDA approved/);
  assert.match(chart,/outcome-aware/);
  assert.match(panel,/data-testid="historical-level3-phar-joenja"/);
  assert.match(panel,/data-testid="phar-assessment-level"/);
  assert.match(panel,/Approval lean/);
  assert.match(panel,/data-testid="phar-actual-outcome"/);
  assert.match(panel,/September 11, 2026/);
  assert.match(panel,/October 24, 2026/);
  assert.match(panel,/NCT05438407/);
  assert.match(panel,/NOT A BLIND PREDICTION/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<JoenjaHistoricalLevelThreePanel\/>/);
  assert.match(page,/<AssessmentLevelChart\/>/);
});

test("PHAR historical outcome cannot alter prospective and prior retrospective model accuracy or FOCUS roster",()=>{
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].ticker,"SMMT");
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  assert.equal(ino.records[0].ticker,"INO");
  assert.equal(ino.records[0].predictedOutcome,"CRL");
  assert.equal(bepi.records.length,1);
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(model,/levelThreePharHistorical2026/);
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,29);
  assert.equal(focus.records.some(r=>r.nct==="NCT05438407"),false);
});
