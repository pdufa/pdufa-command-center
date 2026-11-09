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
const historical=require("../data/levelThreeHistoricalReconstruction2026.json");
const prospective=require("../data/fdaPredictionDecisionAudit.json");
const priorBlind=require("../data/blindHistoricalForecasts2026.json");
const priorCompared=require("../data/blindHistoricalComparisons2026.json");
const Panel=require("../app/BepirovirsenHistoricalLevelThreePanel.tsx").default;

test("next earlier 2026 PDUFA historical research is explicitly nonblind and uncalibrated",()=>{
  assert.equal(historical.dataset,"OUTCOME_EXPOSED_HISTORICAL_LEVEL3_RECONSTRUCTION");
  assert.equal(historical.records.length,1);
  const x=historical.records[0];
  assert.equal(x.assessmentId,"HIST-2026-10-26-BEPIROVIRSEN-LEVEL3-001");
  assert.equal(x.ticker,"GSK");
  assert.equal(x.partnerTicker,"IONS");
  assert.deepEqual(x.ncts,["NCT05630807","NCT05630820"]);
  assert.equal(x.clinicalPhase,"PHASE_3");
  assert.equal(x.originalPdufaDate,"2026-10-26");
  assert.ok(x.originalPdufaDate<"2026-10-30");
  assert.equal(x.evidenceCutoff,"2026-05-28");
  assert.ok(x.evidenceCutoff<x.originalPdufaDate);
  assert.ok(Date.parse(x.authoredAt)>Date.parse(x.originalPdufaDate+"T23:59:59Z"));
  assert.equal(x.outcomeExposedBeforeAssessment,true);
  assert.equal(x.retrospective,true);
  assert.equal(x.status,"HISTORICAL_RECONSTRUCTION_NOT_BLIND");
  assert.equal(x.level3Prediction,"APPROVAL");
  assert.equal(x.predictionStrength,"LEAN");
  assert.equal(x.probability,null);
  assert.equal(x.certainty,"NOT_VALIDATED");
  assert.equal(x.actualOutcome,null);
  assert.equal(x.outcomeCompared,false);
  assert.equal(x.excludedFromProspectiveAccuracy,true);
  assert.equal(x.excludedFromRetrospectiveBlindValidation,true);
  assert.equal(x.excludedFromCalibration,true);
  assert.equal(x.sourceFreezeCommit,"63e1fbd8eb645c17e635608a03921f319b3d00ba");
  assert.match(x.pivotalPaperUrl,/10\.1056\/NEJMoa2515131$/);
});

test("Level 3 case remains separated from frozen original forecasts and 29 FOCUS trial identities",()=>{
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].ticker,"SMMT");
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  assert.equal(priorBlind.records.length,1);
  assert.equal(priorBlind.records[0].ticker,"INO");
  assert.equal(priorBlind.records[0].predictedOutcome,"CRL");
  assert.equal(priorBlind.records[0].actualOutcome,null);
  assert.equal(priorCompared.records.length,1);
  assert.equal(priorCompared.records[0].outcomeMatch,"NOT_ACCURATE");
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,29);
  assert.equal(focus.records.some(r=>r.nct==="NCT05630807"||r.nct==="NCT05630820"),false);
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(model,/levelThreeHistoricalReconstruction2026/);
});

test("the ASSESMENTS page shows three-level method and warning without calling it a blind success",()=>{
  const html=renderToStaticMarkup(React.createElement(Panel));
  assert.match(html,/data-testid="historical-level3-bepirovirsen"/);
  assert.match(html,/Bepirovirsen/i);
  assert.match(html,/Approval lean/);
  assert.match(html,/October 26, 2026/);
  assert.match(html,/NCT05630807/);
  assert.match(html,/NCT05630820/);
  assert.match(html,/1 · Trial evidence/);
  assert.match(html,/2 · Benefit \/ safety/);
  assert.match(html,/3 · Regulatory review/);
  assert.match(html,/HISTORICAL, NOT BLIND/);
  assert.match(html,/cannot/);
  assert.doesNotMatch(html,/100% accurate|verified successful prediction/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<BepirovirsenHistoricalLevelThreePanel\/>/);
  assert.match(page,/<AssessmentStatusPies \{\.\.\.pies\}\/>/);
});
