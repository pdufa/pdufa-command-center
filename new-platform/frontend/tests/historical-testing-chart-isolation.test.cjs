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
const freeze=require("../data/levelThreeOutcomeAwareRerunFreeze2026.json");
const compared=require("../data/levelThreeOutcomeAwareRerunComparison2026.json");
const quarantine=require("../data/historicalOutcomeAwareQuarantine2026.json");

test("standalone historical chart truthfully displays all four Level 3 research directions",()=>{
  const Chart=require("../app/HistoricalTestingChart.tsx").default;
  const html=renderToStaticMarkup(React.createElement(Chart));
  assert.match(html,/data-testid="historical-testing-chart"/);
  assert.match(html,/data-testid="historical-testing-donut"/);
  assert.match(html,/data-testid="historical-testing-data"/);
  assert.match(html,/Level 3 retrospective comparisons/);
  assert.match(html,/75%/);
  assert.match(html,/3 matched/);
  assert.match(html,/1 missed/);
  assert.match(html,/0 valid blind cases/);
  assert.match(html,/not blind predictions/);
  assert.match(html,/not validated model accuracy/);
  for(const ticker of ["INO","GSK","PHAR","ABBV"])
    assert.match(html,new RegExp(ticker+" ·"));
  assert.match(html,/INO-3107/);
  assert.match(html,/bepirovirsen/);
  assert.match(html,/Joenja/);
  assert.match(html,/SKYRIZI/);
  assert.match(html,/2026-10-30/);
  assert.match(html,/2026-10-20/);
  assert.match(html,/2026-09-11/);
  assert.match(html,/2026-10-23/);
  assert.match(html,/Open Historical Testing data in PDUFA Master Scan Data/);
});

test("four-case outcome comparison and freeze are correct, but not eligible for accuracy",()=>{
  assert.equal(freeze.caseStudies.length,4);
  assert.equal(compared.caseComparisons.length,4);
  assert.equal(freeze.blind,false);
  assert.equal(compared.notBlind,true);
  assert.equal(freeze.validForIndependentPredictionAccuracy,false);
  assert.equal(compared.notValidForAccuracy,true);
  assert.equal(compared.notValidForCalibration,true);
  const m=new Map(compared.caseComparisons.map(x=>[x.caseId,x]));
  let matched=0;
  for(const item of freeze.caseStudies){
    const actual=m.get(item.caseId);
    assert.ok(actual);
    assert.equal(item.actualOutcome,null);
    assert.equal(actual.frozenPrediction,item.prediction);
    assert.equal(actual.didMatch,actual.fdaDecision===item.prediction);
    assert.equal(item.excludedFromProspectiveAccuracy,true);
    assert.equal(item.excludedFromRetrospectiveBlindValidation,true);
    assert.equal(item.excludedFromCalibration,true);
    if(actual.didMatch)matched++;
  }
  assert.equal(matched,3);
  assert.equal(compared.rawMatches,3);
  assert.equal(compared.total,4);
  assert.equal(quarantine.quarantined.length,4);
  assert.equal(compared.validBlindAccuracy,null);
});

test("the historical visualization stays isolated from active review level and prediction metrics",()=>{
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  const active=fs.readFileSync(path.join(root,"app/AssessmentLevelChart.tsx"),"utf8");
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.match(page,/<HistoricalTestingChart\/>/);
  assert.match(page,/<AssessmentLevelChart\/>/);
  assert.match(page,/<UltomirisHistoricalLevelThreePanel\/>/);
  assert.doesNotMatch(active,/levelThreeOutcomeAwareRerun(?:Freeze|Comparison)2026/);
  assert.doesNotMatch(model,/levelThreeOutcomeAwareRerun(?:Freeze|Comparison)2026/);
  assert.doesNotMatch(page,/BepirovirsenHistoricalLevelThreePanel|JoenjaHistoricalLevelThreePanel|SkyriziHistoricalLevelThreePanel|BlindHistoricalPredictionPanel/);
  assert.equal(fs.existsSync(path.join(root,"app/BepirovirsenHistoricalLevelThreePanel.tsx")),false);
  assert.equal(fs.existsSync(path.join(root,"app/JoenjaHistoricalLevelThreePanel.tsx")),false);
  assert.equal(fs.existsSync(path.join(root,"app/SkyriziHistoricalLevelThreePanel.tsx")),false);
  const prospective=require("../data/fdaPredictionDecisionAudit.json");
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].ticker,"SMMT");
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,32);
});
