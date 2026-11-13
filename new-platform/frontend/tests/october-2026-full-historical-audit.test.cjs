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
const frozen=require("../data/october2026EvidenceCutoffFreeze.json");
const comparison=require("../data/october2026OfficialOutcomeComparison.json");
const Panel=require("../app/October2026HistoricalAudit.tsx").default;

test("October 2026 audit preserves predecision freeze and correct 15/16 comparison denominator",()=>{
  assert.equal(frozen.dataset,"OCTOBER_2026_EXPOSED_EVIDENCE_CUTOFF_ASSESSMENT_FREEZE");
  assert.equal(frozen.totalCases,17);
  assert.equal(frozen.independentOutcomeBlind,false);
  assert.equal(frozen.validForAccuracy,false);
  assert.equal(frozen.validForCalibration,false);
  assert.equal(comparison.dataset,"OCTOBER_2026_OUTCOME_VERIFICATION_AFTER_OUTCOME_EXPOSED_FREEZE");
  assert.equal(comparison.freezeCommitSha,"9ec4e1d564496f05aae05fcb1b98c0aa69db6410");
  assert.equal(comparison.caseComparisons.length,17);
  const id=new Set();
  for(const row of frozen.predecisionAssessmentCases){
    assert.equal(id.has(row.id),false,"Duplicate case id");
    id.add(row.id);
    assert.equal(row.actualFdaDecision,null);
    assert.equal(row.actualFdaActionDate,null);
    assert.equal(row.officialPostdecisionSource,null);
    assert.equal(row.scoreEligibleForBlindAccuracy,false);
    assert.equal(row.knownOutcomesExposedToAuthorBeforeResearch,true);
    assert.equal(row.levelStyle,3);
    assert.ok(row.levels.level1TrialDesignAndEfficacy);
    assert.ok(row.levels.level2ClinicalBenefitAndSafety);
    assert.ok(row.levels.level3RegulatoryFit);
    assert.equal(row.predecisionUrls.every(url=>/^https:\/\//.test(url)),true);
    const c=comparison.caseComparisons.find(x=>x.caseId===row.id);
    assert.ok(c);
    assert.equal(c.predecisionPrediction,row.prediction);
    assert.equal(c.drug,row.drug);
    assert.equal(c.ticker,row.ticker);
    assert.equal(c.directionMatch,c.eligibleForBinaryAgreement?(c.observedDisposition===row.prediction):null);
  }
  assert.equal(comparison.cohortCount,17);
  assert.equal(comparison.binaryScoredCases,16);
  assert.equal(comparison.directionalMatches,15);
  assert.equal(comparison.directionalMisses,1);
  assert.equal(comparison.nonDecisionWithdrawals,1);
  assert.equal(comparison.directionalAgreementFraction,0.9375);
  assert.equal(comparison.alwaysApproveBaselineMatches,16);
  assert.equal(comparison.alwaysApproveBaselineDenominator,16);
  assert.equal(comparison.validatedBlindAccuracy,null);
  assert.equal(comparison.validBlindPredictionCount,0);
  const withdrawal=comparison.caseComparisons.find(x=>x.observedDisposition==="WITHDRAWN_NO_FDA_DECISION");
  assert.equal(withdrawal.ticker,"MRK");
  assert.equal(withdrawal.actualFdaActionDate,null);
  assert.equal(withdrawal.finalDispositionDate,"2026-09-25");
  assert.equal(withdrawal.eligibleForBinaryAgreement,false);
  assert.equal(withdrawal.directionMatch,null);
  const miss=comparison.caseComparisons.find(x=>x.directionMatch===false);
  assert.equal(miss.ticker,"INO");
  assert.equal(miss.predecisionPrediction,"CRL");
  assert.equal(miss.observedDisposition,"APPROVAL");
});

test("isolated October audit renders 17 cases, 93.75 percent and the all-approve comparator",()=>{
  const html=renderToStaticMarkup(React.createElement(Panel));
  assert.match(html,/data-testid="october-2026-historical-audit"/);
  assert.match(html,/data-testid="october-2026-agreement-chart"/);
  assert.match(html,/data-testid="october-2026-historical-case-data"/);
  assert.match(html,/93\.75%/);
  assert.match(html,/15 matched/);
  assert.match(html,/Missed directions/);
  assert.match(html,/voluntarily withdrawn/);
  assert.match(html,/0 valid blind/i);
  assert.match(html,/NOT MEASURABLE/);
  assert.match(html,/always guessing APPROVAL/);
  assert.match(html,/16 of 16/);
  for(const ticker of ["LLY","MRK","NVS","PFE","TEVA","AMGN","RHHBY","IBRX","IRD \/ VTRS","GSK","AZN","ABBV","PHAR","INO"])
    assert.equal(html.includes(ticker.replace("\\/","/"))||html.includes(ticker),true,ticker+" missing");
  assert.match(html,/Withdrawn \(no decision\)/);
  assert.match(html,/Unscored/);
  assert.match(html,/Outcome/);
});

test("monthly historical view only appears in the separated section, leaving original 4-case subset and live metrics untouched",()=>{
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.match(page,/<HistoricalTestingChart\/>/);
  assert.match(page,/<October2026HistoricalAuditPanel\/>/);
  assert.match(page,/<AssessmentLevelChart\/>/);
  assert.match(page,/<UltomirisHistoricalLevelThreePanel\/>/);
  const older=require("../data/levelThreeOutcomeAwareRerunComparison2026.json");
  assert.equal(older.rawMatches,3);
  assert.equal(older.total,4);
  const active=fs.readFileSync(path.join(root,"app/AssessmentLevelChart.tsx"),"utf8");
  const scoring=fs.readFileSync(path.join(root,"lib/focus-assessment-chart.ts"),"utf8");
  assert.doesNotMatch(active,/october2026EvidenceCutoffFreeze|october2026OfficialOutcomeComparison/);
  assert.doesNotMatch(scoring,/october2026EvidenceCutoffFreeze|october2026OfficialOutcomeComparison/);
  const prospective=require("../data/fdaPredictionDecisionAudit.json");
  assert.equal(prospective.records.length,1);
  assert.equal(prospective.records[0].actualOutcome,"PENDING");
  const roster=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(roster.records.length,32);
});
