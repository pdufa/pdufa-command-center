const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");
require.extensions[".tsx"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,filename
);
const data=require("../data/september2026FdaActionsResearch.json");
const Chart=require("../app/September2026HistoricalAuditPanel.tsx").default;

test("September Level 3 research has 20 distinct predecision-sourced calls and no blind claims",()=>{
  assert.equal(data.rows.length,20);
  const ids=new Set();
  for(const row of data.rows){
    assert.equal(ids.has(row.id),false,"duplicate September FDA case");
    ids.add(row.id);
    assert.equal(row.actionDate.startsWith("2026-09-"),true);
    assert.equal(row.researchState,"COMPLETE_OUTCOME_AWARE_DESK_RECONSTRUCTION");
    assert.equal(row.levelStyle,3);
    assert.equal(row.observedDisposition,"APPROVAL");
    assert.equal(row.level3AssessmentState,"OUTCOME_AWARE_LEVEL3_STYLE_DESK_RECONSTRUCTION");
    assert.equal(row.predecision.sourceDate<row.actionDate,true,"source after decision");
    assert.ok(row.predecision.sourceUrl.startsWith("https://"));
    assert.ok(row.fdaSourceUrl.startsWith("https://"));
    assert.ok(row.predecision.phaseFirst);
    assert.ok(row.predecision.level1ClinicalEvidence);
    assert.ok(row.predecision.level2BenefitRisk);
    assert.ok(row.predecision.level3RegulatoryFit);
    assert.equal(row.predecision.originalSourceVersionIndependentlyVerified,false);
    assert.equal(row.researchBlind,false);
    assert.equal(row.bonaFidePriorForecast,false);
    assert.equal(row.match,row.reconstructedLevel3Call===row.observedDisposition);
  }
  assert.equal(data.expected.level3ReconstructedCalls,20);
  assert.equal(data.expected.comparableLevel3Pairs,20);
  assert.equal(data.expected.retrospectiveMatches,19);
  assert.equal(data.expected.retrospectiveMisses,1);
  assert.equal(data.expected.alwaysApproveComparatorMatches,20);
  assert.equal(data.expected.validBlindCases,0);
  assert.equal(data.researchBlind,false);
  assert.equal(data.accuracy,null);
  assert.equal(data.calibratedFdaAccuracy,null);
  assert.equal(data.validatedBlindForecasts,0);
  assert.equal(data.affectsActiveForecasts,false);
  const miss=data.rows.find(row=>row.match===false);
  assert.equal(miss.ticker,"INCY/MIRM");
  assert.match(miss.predecision.level1ClinicalEvidence,/0\.0986/);
});

test("September chart renders 20 research rows with 95.0% nonblind agreement and 100% trivial baseline",()=>{
  const html=renderToStaticMarkup(React.createElement(Chart));
  assert.match(html,/data-testid="september-2026-historical-audit"/);
  assert.match(html,/data-testid="september-historical-direction-chart"/);
  assert.match(html,/data-testid="september-historical-data-table"/);
  assert.match(html,/95\.0%/);
  assert.match(html,/19 matched/);
  assert.match(html,/20\/20 \(100%\)/);
  assert.match(html,/NOT MEASURABLE/);
  assert.match(html,/NOT BLIND/);
  assert.match(html,/FAYUVI/);
  assert.match(html,/Atebrioz/);
});
