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

test("only retained AZN and original prospective SMMT appear on the active level chart",()=>{
  const Chart=require("../app/AssessmentLevelChart.tsx").default;
  const html=renderToStaticMarkup(React.createElement(Chart));
  assert.match(html,/data-testid="research-assessment-level-chart"/);
  assert.match(html,/Scientific review depth/);
  assert.match(html,/SMMT · HARMONi/);
  assert.match(html,/AZN · Ultomiris/);
  assert.match(html,/Level 1-style/);
  assert.match(html,/Level 3-style/);
  assert.match(html,/FDA accelerated approval/);
  assert.match(html,/outcome-aware, not blind/);
  for(const hidden of ["INO · INO-3107","GSK \/ IONS","Bepirovirsen","PHAR · Joenja","ABBV · SKYRIZI"]){
    assert.equal(html.includes(hidden),false,"Quarantined assessment leaked into active chart: "+hidden);
  }
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<AssessmentLevelChart\/>/);
  assert.match(page,/<UltomirisHistoricalLevelThreePanel\/>/);
  assert.match(page,/data-testid="smmt-assessment-level"/);
  assert.match(page,/Assessment level","Clinical review/);
  assert.match(page,/ASSESSMENT LEVEL: NOT YET ASSESSED/);
  for(const retired of ["BlindHistoricalPredictionPanel","BepirovirsenHistoricalLevelThreePanel",
      "JoenjaHistoricalLevelThreePanel","SkyriziHistoricalLevelThreePanel"]){
    assert.equal(page.includes(retired),false,retired+" must not load in the active page");
  }
  const pie=fs.readFileSync(path.join(root,"app/AssessmentStatusPies.tsx"),"utf8");
  assert.match(pie,/assessmentLevelLabel/);
  assert.match(pie,/data-testid="latest-chart-assessment-level"/);
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(model,/levelThree(HistoricalReconstruction|PharHistorical|AbbvieHistorical)2026/);
});

test("previously exposed assessments are archived and barred from active predictions",()=>{
  const manifest=require("../data/historicalOutcomeAwareQuarantine2026.json");
  assert.equal(manifest.policy,"RETAIN_FROZEN_HISTORY_EXCLUDE_FROM_ACTIVE_PROGRAM");
  assert.deepEqual(manifest.quarantined.map(r=>r.ticker),["INO","GSK","PHAR","ABBV"]);
  assert.equal(manifest.activeExceptions.length,1);
  assert.equal(manifest.activeExceptions[0].ticker,"AZN");
  assert.equal(manifest.activeExceptions[0].outcomeAware,true);
  assert.equal(manifest.activeExceptions[0].allowedInAccuracy,false);
  assert.equal(manifest.activeExceptions[0].allowedInCalibration,false);
  assert.equal(manifest.redoPolicy.status,"OWNER_ONLY_RECONSTRUCTION_ALLOWED_NOT_BLIND");
  assert.ok(manifest.redoPolicy.steps.every(s=>!s.includes("INDEPENDENT_CUSTODIAN")));
  assert.ok(manifest.redoPolicy.steps.includes("NONBLIND_COMPARISON_EXCLUDED_FROM_CALIBRATION_AND_CLAIMED_BLIND_ACCURACY"));
  const prospective=require("../data/fdaPredictionDecisionAudit.json");
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].ticker,"SMMT");
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  const originalIno=require("../data/blindHistoricalForecasts2026.json");
  assert.equal(originalIno.records.length,1);
  assert.equal(originalIno.records[0].predictedOutcome,"CRL");
});
