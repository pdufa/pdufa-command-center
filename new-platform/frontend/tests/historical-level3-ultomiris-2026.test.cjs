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
const frozen=require("../data/levelThreeAznFrozen2026.json");
const revealed=require("../data/levelThreeAznHistoricalComparison2026.json");
const prospective=require("../data/fdaPredictionDecisionAudit.json");
const historicalOriginal=require("../data/blindHistoricalForecasts2026.json");
const Panel=require("../app/UltomirisHistoricalLevelThreePanel.tsx").default;
const Chart=require("../app/AssessmentLevelChart.tsx").default;

test("predecision-only AZN Level 3 approval lean was frozen separately from official outcome",()=>{
  assert.equal(frozen.dataset,"FROZEN_MANUAL_LEVEL3_HISTORICAL_RECONSTRUCTION");
  assert.equal(frozen.records.length,1);
  const r=frozen.records[0];
  assert.equal(r.assessmentId,"HIST-AZN-ULTOMIRIS-2026-10-21-LEVEL3-V1");
  assert.equal(r.ticker,"AZN");
  assert.deepEqual(r.ncts,["NCT06291376"]);
  assert.equal(r.trialName,"I CAN");
  assert.equal(r.clinicalPhase,"PHASE_3");
  assert.equal(r.sourceOnlyEvidenceCutoff,"2026-06-15");
  assert.equal(r.pdufaGoalDisclosure,"Q4 2026");
  assert.equal(r.exactPdufaDateVerifiedPredecision,false);
  assert.equal(r.predictedOutcome,"APPROVAL");
  assert.equal(r.predictedApprovalType,"ACCELERATED_APPROVAL_LEAN");
  assert.equal(r.assessmentLevelStyle,3);
  assert.equal(r.approvalProbability,null);
  assert.equal(r.crlProbability,null);
  assert.equal(r.certainty,"NOT_VALIDATED");
  assert.equal(r.frozenResearchCommit,"e4c5a0221019075b03769781b4b3394178d9fd75");
  assert.equal(r.originalOutcomeExposedBeforeFreeze,true);
  assert.equal(r.blind,false);
  assert.equal(r.actualOutcome,null);
  assert.equal(r.actualDecisionDate,null);
  assert.equal(r.actualDecisionSourceUrl,null);
  assert.equal(r.officialDecisionCompared,false);
});

test("the later official comparison links original freeze but is excluded from both accuracy cohorts",()=>{
  assert.equal(revealed.dataset,"OUTCOME_AWARE_POST_FREEZE_HISTORICAL_COMPARISON_NOT_BLIND");
  assert.equal(revealed.records.length,1);
  const r=frozen.records[0],o=revealed.records[0];
  assert.equal(o.assessmentId,r.assessmentId);
  assert.equal(o.frozenResearchCommit,r.frozenResearchCommit);
  assert.equal(o.frozenRecordCommit,"0f1b06505535199e9ef8804fb195fa0c3e468620");
  assert.equal(o.predictedOutcome,r.predictedOutcome);
  assert.equal(o.predictedApprovalType,r.predictedApprovalType);
  assert.equal(o.actualOutcome,"APPROVAL");
  assert.equal(o.actualApprovalType,"ACCELERATED");
  assert.equal(o.actualFdaActionDate,"2026-10-21");
  assert.equal(o.fdaApplicationId,"BLA 761108/S-046");
  assert.equal(o.outcomeMatch,true);
  assert.equal(o.outcomeExposedBeforeFreeze,true);
  assert.equal(o.blind,false);
  assert.equal(o.exactGoalDayConfirmedPredecision,false);
  assert.equal(o.excludedFromProspectiveAccuracy,true);
  assert.equal(o.excludedFromRetrospectiveBlindValidation,true);
  assert.equal(o.excludedFromCalibration,true);
  assert.match(o.officialDecisionSourceUrl,/accessdata\.fda\.gov\/drugsatfda_docs\/appletter/);
  assert.equal(r.actualOutcome,null);
  assert.equal(r.officialDecisionCompared,false);
});

test("both level chart and case display show accurate, nonblind and source-limited labels",()=>{
  const chart=renderToStaticMarkup(React.createElement(Chart));
  const html=renderToStaticMarkup(React.createElement(Panel));
  assert.match(chart,/AZN · Ultomiris/);
  assert.match(chart,/Level 3-style/);
  assert.match(chart,/FDA accelerated approval/);
  assert.match(chart,/outcome-aware/);
  assert.match(html,/data-testid="historical-level3-azn-ultomiris"/);
  assert.match(html,/data-testid="azn-assessment-level"/);
  assert.match(html,/Approval lean/);
  assert.match(html,/data-testid="azn-actual-outcome"/);
  assert.match(html,/Accelerated approval/);
  assert.match(html,/October 21, 2026/);
  assert.match(html,/Q4 2026/);
  assert.match(html,/NCT06291376/);
  assert.match(html,/NOT A BLIND PREDICTION/);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<UltomirisHistoricalLevelThreePanel\/>/);
  assert.match(page,/<AssessmentLevelChart\/>/);
});

test("AZN outcome cannot affect live prospective accuracy, retired analyses, or FOCUS population",()=>{
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].ticker,"SMMT");
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  assert.equal(historicalOriginal.records[0].predictedOutcome,"CRL");
  const model=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(model,/levelThreeAznFrozen2026|levelThreeAznHistoricalComparison2026/);
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,32);
  assert.equal(focus.records.some(r=>r.nct==="NCT06291376"),false);
});
