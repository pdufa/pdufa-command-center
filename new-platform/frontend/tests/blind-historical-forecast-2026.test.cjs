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

const blind=require("../data/blindHistoricalForecasts2026.json");
const prospective=require("../data/fdaPredictionDecisionAudit.json");
const Panel=require("../app/BlindHistoricalPredictionPanel.tsx").default;

test("the first historical challenge is immutable directional research with outcome sealed",()=>{
  assert.equal(blind.dataset,"BLIND_RETROSPECTIVE_RESEARCH_ONLY");
  assert.equal(blind.records.length,1);
  const r=blind.records[0];
  assert.equal(r.forecastId,"BLIND-INO3107-2026-10-30-V1");
  assert.equal(r.ticker,"INO");
  assert.deepEqual(r.exactNcts,["NCT04398433"]);
  assert.equal(r.clinicalPhase,"PHASE_1_2");
  assert.equal(r.predictedOutcome,"CRL");
  assert.equal(r.retrospective,true);
  assert.equal(r.originalPdufaDate,"2026-10-30");
  assert.ok(Date.parse(r.forecastCreatedAt)>Date.parse("2026-10-30T23:59:59Z"));
  assert.equal(r.actualOutcome,null);
  assert.equal(r.actualDecisionDate,null);
  assert.equal(r.actualDecisionSourceUrl,null);
  assert.equal(r.outcomeViewed,false);
  assert.equal(r.approvalProbability,null);
  assert.equal(r.crlProbability,null);
  assert.equal(r.independentCalibration,"NOT_VALIDATED");
  assert.equal(r.sourceFreezeCommit,"6eacacd2728ac265f1b4b23571e8edb1108d5afe");
  assert.match(r.primaryEvidenceUrl,/ino-20260630.htm/);
  assert.match(r.researchDossierPath,/2026-blind-ino3107-historical-challenge.md/);
});

test("SMMT prospectively frozen forecast and FOCUS 29 roster remain unchanged",()=>{
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].ticker,"SMMT");
  assert.equal(prospective.records[0].predictionId,"HARMONI-SMMT-PDUFA-2026-11-14-V1");
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  assert.ok(prospective.records.every(r=>r.ticker!=="INO"));
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,29);
  assert.equal(focus.records.some(r=>r.nct==="NCT04398433"),false);
});

test("historical challenge panel is readable, clearly sealed, and is outside performance pies",()=>{
  const html=renderToStaticMarkup(React.createElement(Panel));
  assert.match(html,/data-testid="blind-2026-pdufa-forecast"/);
  assert.match(html,/INO-3107/);
  assert.match(html,/NCT04398433/);
  assert.match(html,/CRL lean/);
  assert.match(html,/October 30, 2026/);
  assert.match(html,/OUTCOME SEALED/);
  assert.match(html,/6eacacd2728ac265f1b4b23571e8edb1108d5afe/);
  assert.match(html,/after the original target date/);
  assert.doesNotMatch(html,/\d+\.\d+% probability|FDA APPROVED|PDUFA ACTUAL ACTION/);
  const chartSource=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(chartSource,/blindHistoricalForecasts2026/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<BlindHistoricalPredictionPanel\/>/);
  assert.match(page,/<AssessmentStatusPies \{\.\.\.pies\}\/>/);
});
