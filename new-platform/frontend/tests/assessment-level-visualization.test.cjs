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

test("assessment level is visible inside comparison chart without changing accuracy statistics",()=>{
  const Chart=require("../app/AssessmentLevelChart.tsx").default;
  const html=renderToStaticMarkup(React.createElement(Chart));
  assert.match(html,/data-testid="research-assessment-level-chart"/);
  assert.match(html,/Scientific review depth/);
  assert.match(html,/Level 1-style/);
  assert.match(html,/Level 3-style/);
  assert.match(html,/SMMT/);
  assert.match(html,/INO/);
  assert.match(html,/Bepirovirsen/);
  assert.match(html,/Later reassessment/);
  assert.match(html,/not certified engine levels/);
  assert.match(html,/outcome-aware/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<AssessmentLevelChart\/>/);
  assert.match(page,/Assessment level","Clinical review/);
  assert.match(page,/ASSESSMENT LEVEL: NOT YET ASSESSED/);
  const pie=fs.readFileSync(path.join(root,"app/AssessmentStatusPies.tsx"),"utf8");
  assert.match(pie,/assessmentLevelLabel/);
  assert.match(pie,/data-testid="latest-chart-assessment-level"/);
  assert.match(pie,/Level 1-style/);
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(model,/AssessmentLevelChart|researchAssessmentLevels2026|levelThreeHistoricalReconstruction2026/);
});

test("individual trial displays show distinct original and retrospective research levels",()=>{
  const Ino=require("../app/BlindHistoricalPredictionPanel.tsx").default;
  const Bepi=require("../app/BepirovirsenHistoricalLevelThreePanel.tsx").default;
  const inoHtml=renderToStaticMarkup(React.createElement(Ino));
  const bepiHtml=renderToStaticMarkup(React.createElement(Bepi));
  assert.match(inoHtml,/data-testid="ino-assessment-level"/);
  assert.match(inoHtml,/Level 1-style/);
  assert.match(inoHtml,/Later Level 3-style reassessment/);
  assert.match(bepiHtml,/data-testid="bepirovirsen-assessment-level"/);
  assert.match(bepiHtml,/Level 3-style/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/data-testid="smmt-assessment-level"/);
  const prospective=require("../data/fdaPredictionDecisionAudit.json");
  const retrospective=require("../data/blindHistoricalComparisons2026.json");
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  assert.equal(retrospective.records.length,1);
  assert.equal(retrospective.records[0].outcomeMatch,"NOT_ACCURATE");
});
