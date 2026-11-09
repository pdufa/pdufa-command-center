const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const historical=require("../data/levelThreeHistoricalReconstruction2026.json");
const quarantine=require("../data/historicalOutcomeAwareQuarantine2026.json");

test("original Bepirovirsen research is preserved as a nonblind, uncalibrated archive",()=>{
  assert.equal(historical.dataset,"OUTCOME_EXPOSED_HISTORICAL_LEVEL3_RECONSTRUCTION");
  assert.equal(historical.records.length,1);
  const x=historical.records[0];
  assert.equal(x.assessmentId,"HIST-2026-10-26-BEPIROVIRSEN-LEVEL3-001");
  assert.equal(x.ticker,"GSK");
  assert.deepEqual(x.ncts,["NCT05630807","NCT05630820"]);
  assert.equal(x.level3Prediction,"APPROVAL");
  assert.equal(x.outcomeExposedBeforeAssessment,true);
  assert.equal(x.actualOutcome,null);
  assert.equal(x.excludedFromProspectiveAccuracy,true);
  assert.equal(x.excludedFromRetrospectiveBlindValidation,true);
  assert.equal(x.excludedFromCalibration,true);
  assert.equal(x.sourceFreezeCommit,"63e1fbd8eb645c17e635608a03921f319b3d00ba");
});

test("GSK comparison is no longer part of active program, but audit history remains",()=>{
  assert.equal(quarantine.quarantined.some(r=>r.ticker==="GSK"),true);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  const chart=fs.readFileSync(path.join(root,"app/AssessmentLevelChart.tsx"),"utf8");
  assert.doesNotMatch(page,/BepirovirsenHistoricalLevelThreePanel/);
  assert.doesNotMatch(chart,/Bepirovirsen|levelThreeHistoricalReconstruction2026/);
  assert.equal(fs.existsSync(path.join(root,"app/BepirovirsenHistoricalLevelThreePanel.tsx")),false);
  assert.equal(fs.existsSync(path.join(root,"docs/2026-oct26-bepirovirsen-level3-reconstruction.md")),true);
});
