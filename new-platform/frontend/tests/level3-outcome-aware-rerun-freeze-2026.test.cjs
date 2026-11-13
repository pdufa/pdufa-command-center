const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const freeze=require("../data/levelThreeOutcomeAwareRerunFreeze2026.json");
const compared=require("../data/levelThreeOutcomeAwareRerunComparison2026.json");
const quarantine=require("../data/historicalOutcomeAwareQuarantine2026.json");

test("Four decisions are sealed separately from evidence-only Level 3 re-evaluations",()=>{
  assert.equal(freeze.dataset,"POST_OUTCOME_EVIDENCE_CUTOFF_LEVEL3_REASSESSMENTS_EXCLUDED");
  assert.equal(freeze.studyCount,4);
  assert.equal(freeze.caseStudies.length,4);
  assert.equal(freeze.blind,false);
  assert.equal(freeze.strictBlind,false);
  assert.equal(freeze.validForIndependentPredictionAccuracy,false);
  assert.equal(freeze.validForCalibration,false);
  assert.equal(freeze.actualOutcomesInThisFile,false);
  assert.equal(compared.assessmentFreezeCommit,"19aefeff35590a32f6ca9e6988c536368c421b2c");
  assert.equal(compared.caseComparisons.length,4);
  assert.equal(compared.notBlind,true);
  assert.equal(compared.notValidForAccuracy,true);
  assert.equal(compared.notValidForCalibration,true);
  assert.equal(compared.quarantineRetained,true);
  assert.equal(compared.activeProgramChanges,false);
  const expected={"INO":"CRL","GSK":"APPROVAL","PHAR":"APPROVAL","ABBV":"APPROVAL"};
  for(const row of freeze.caseStudies){
    assert.equal(row.prediction,expected[row.ticker]);
    assert.equal(row.actualOutcome,null);
    assert.equal(row.actualActionDate,null);
    assert.equal(row.officialOutcomeSource,null);
    assert.equal(row.independentProbability,null);
    assert.equal(row.excludedFromProspectiveAccuracy,true);
    assert.equal(row.excludedFromRetrospectiveBlindValidation,true);
    assert.equal(row.excludedFromCalibration,true);
    assert.ok(row.cutoff<"2026-11-09");
    assert.equal(row.predecisionLinks.every(url=>url.startsWith("https://")),true);
    assert.equal(row.trialIds.every(nct=>/^NCT\d{8}$/.test(nct)),true);
    const actual=compared.caseComparisons.find(x=>x.caseId===row.caseId);
    assert.ok(actual,"Outcome lookup must match exact review case");
    assert.equal(actual.frozenPrediction,row.prediction);
    assert.equal(actual.didMatch,actual.fdaDecision===row.prediction);
    assert.ok(row.cutoff<actual.fdaActionDate);
  }
  assert.equal(compared.caseComparisons.filter(row=>row.didMatch).length,3);
  assert.equal(compared.rawMatches,3);
  assert.equal(compared.total,4);
  assert.equal(compared.validBlindMatches,null);
  assert.equal(compared.validBlindAccuracy,null);
});

test("Rerun stays archival and cannot resurrect deleted historical assessment UI",()=>{
  assert.deepEqual(quarantine.quarantined.map(x=>x.ticker),["INO","GSK","PHAR","ABBV"]);
  assert.equal(quarantine.activeExceptions.length,1);
  assert.equal(quarantine.activeExceptions[0].ticker,"AZN");
  const files=[
    "app/AssessmentLevelChart.tsx",
    "app/predictions/assessment/page.tsx",
    "lib/focus-assessment-chart.ts"
  ];
  for(const file of files){
    const source=fs.readFileSync(path.join(root,file),"utf8");
    assert.doesNotMatch(source,/levelThreeOutcomeAwareRerun(?:Freeze|Comparison)2026/);
  }
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  for(const component of ["BlindHistoricalPredictionPanel","BepirovirsenHistoricalLevelThreePanel","JoenjaHistoricalLevelThreePanel","SkyriziHistoricalLevelThreePanel"])
    assert.equal(page.includes(component),false);
  assert.ok(page.includes("<UltomirisHistoricalLevelThreePanel/>"));
  assert.ok(page.includes("<AssessmentLevelChart/>"));
  const focus=JSON.parse(fs.readFileSync(path.join(root,"../backend/app/data/focus_snapshot.json"),"utf8"));
  assert.equal(focus.records.length,32);
});
