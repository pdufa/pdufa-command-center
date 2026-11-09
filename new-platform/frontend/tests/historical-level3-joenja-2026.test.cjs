const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const phar=require("../data/levelThreePharHistorical2026.json");
const quarantine=require("../data/historicalOutcomeAwareQuarantine2026.json");

test("original PHAR Joenja FDA result and history remain read-only and excluded",()=>{
  const r=phar.records[0];
  assert.equal(r.assessmentId,"HIST-PHAR-JOENJA-2026-10-24-LEVEL3-001");
  assert.deepEqual(r.ncts,["NCT05438407"]);
  assert.equal(r.assessmentLevelStyle,3);
  assert.equal(r.assessmentDirection,"APPROVAL");
  assert.equal(r.actualOutcome,"APPROVAL");
  assert.equal(r.actualFdaActionDate,"2026-09-11");
  assert.equal(r.outcomeExposedBeforeAssessment,true);
  assert.equal(r.excludedFromProspectiveAccuracy,true);
  assert.equal(r.excludedFromRetrospectiveBlindValidation,true);
  assert.equal(r.excludedFromCalibration,true);
});

test("PHAR old panel is not imported or represented on the live assessment chart",()=>{
  assert.equal(quarantine.quarantined.some(r=>r.ticker==="PHAR"),true);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  const chart=fs.readFileSync(path.join(root,"app/AssessmentLevelChart.tsx"),"utf8");
  assert.doesNotMatch(page,/JoenjaHistoricalLevelThreePanel/);
  assert.doesNotMatch(chart,/PHAR|Joenja|levelThreePharHistorical2026/);
  assert.equal(fs.existsSync(path.join(root,"app/JoenjaHistoricalLevelThreePanel.tsx")),false);
  assert.equal(fs.existsSync(path.join(root,"docs/2026-oct24-phar-joenja-level3-retrospective.md")),true);
});
