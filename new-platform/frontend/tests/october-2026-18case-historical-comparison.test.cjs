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
const base=require("../data/october2026EvidenceCutoffFreeze.json");
const additional=require("../data/october2026IlumyaEvidenceReconstruction.json");
const compared=require("../data/october2026RetrospectiveFdaComparison.json");
const Panel=require("../app/October2026HistoricalAuditPanel.tsx").default;

test("expanded 18-case October cohort carries correct outcomes, denominator and bias flags",()=>{
 assert.equal(base.predecisionAssessmentCases.length,17);
 assert.equal(additional.caseId,"OCT26-18-SUN");
 assert.equal(additional.predecisionGoal,"2026-10-29");
 assert.equal(additional.prediction,"APPROVAL");
 assert.equal(additional.actualFdaDecision,null);
 assert.equal(additional.authorHadSeenOutcomePriorToFreeze,true);
 assert.equal(additional.scoreEligibleForBlindAccuracy,false);
 assert.equal(compared.cases.length,18);
 assert.equal(compared.countTotal,18);
 assert.equal(compared.countDirectionalComparisons,17);
 assert.equal(compared.countMatches,16);
 assert.equal(compared.countMisses,1);
 assert.equal(compared.countWithdrawals,1);
 assert.equal(compared.directionalAgreement,16/17);
 assert.equal(compared.isBlind,false);
 assert.equal(compared.assessorKnewDecisions,true);
 assert.equal(compared.blindAccuracy,null);
 assert.equal(compared.calibratedProbability,null);
 assert.equal(compared.affectsActivePredictions,false);
 assert.equal(compared.affectsFocusRoster,false);
 const ids=new Set();
 for(const row of compared.cases){
  assert.equal(ids.has(row.id),false,"Duplicate exact review case ID");
  ids.add(row.id);
  assert.equal(row.eligibleForBlindAccuracy,false);
  assert.equal(row.eligibleForDirectionalMatchRate,row.actualOutcome!=="WITHDRAWN");
  assert.equal(row.sameDirection,
   row.actualOutcome==="WITHDRAWN"?null:row.prediction===row.actualOutcome);
  assert.match(row.decisionSource,/^https:\/\//);
 }
 const withdrawn=compared.cases.find(r=>r.actualOutcome==="WITHDRAWN");
 assert.equal(withdrawn.ticker,"MRK");
 assert.equal(withdrawn.actualFdaActionDate,null);
 assert.equal(withdrawn.withdrawalDate,"2026-09-25");
 const missed=compared.cases.filter(r=>r.sameDirection===false);
 assert.equal(missed.length,1);
 assert.equal(missed[0].ticker,"INO");
 const approvals=compared.cases.filter(r=>r.actualOutcome==="APPROVAL");
 assert.equal(approvals.length,17);
 assert.equal(approvals.every(r=>r.prediction==="APPROVAL"||r.prediction==="CRL"),true);
});

test("October panel renders 94.1 agreement, includes every case and 100 percent naive baseline",()=>{
 const html=renderToStaticMarkup(React.createElement(Panel));
 assert.match(html,/data-testid="october-2026-historical-audit"/);
 assert.match(html,/data-testid="october-historical-direction-chart"/);
 assert.match(html,/data-testid="october-historical-data-table"/);
 assert.match(html,/94\.1%/);
 assert.match(html,/16 matched/);
 assert.match(html,/1 missed/);
 assert.match(html,/1 withdrawn/);
 assert.match(html,/17 of 17/);
 assert.match(html,/100%/);
 assert.match(html,/NOT BLIND/i);
 assert.match(html,/not established/);
 assert.match(html,/INO-3107/);
 assert.match(html,/ILUMYA/);
 assert.match(html,/2026-10-29/);
 assert.match(html,/2026-09-25/);
 assert.match(html,/October 2026 Testing spreadsheet/);
});

test("October monthly comparison never enters active FOCUS, chart depth, or past four-case testing",()=>{
 const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
 const focus=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
 const active=fs.readFileSync(path.join(root,"app/AssessmentLevelChart.tsx"),"utf8");
 assert.match(page,/<October2026HistoricalAuditPanel\/>/);
 assert.doesNotMatch(page,/<October2026HistoricalAudit\/>/);
 assert.match(page,/<HistoricalTestingChart\/>/);
 assert.match(page,/<AssessmentLevelChart\/>/);
 assert.match(page,/<UltomirisHistoricalLevelThreePanel\/>/);
 assert.doesNotMatch(focus,/october2026RetrospectiveFdaComparison/);
 assert.doesNotMatch(active,/october2026RetrospectiveFdaComparison/);
 const prior=require("../data/levelThreeOutcomeAwareRerunComparison2026.json");
 assert.equal(prior.rawMatches,3);
 assert.equal(prior.total,4);
 const roster=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
 assert.equal(roster.records.length,32);
 const prospective=require("../data/fdaPredictionDecisionAudit.json");
 assert.equal(prospective.records.length,1);
 assert.equal(prospective.records[0].actualOutcome,"PENDING");
});
