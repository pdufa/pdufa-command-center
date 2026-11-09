const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const historical=require("../data/levelThreeAbbvieHistorical2026.json");
const quarantine=require("../data/historicalOutcomeAwareQuarantine2026.json");

test("ABBV SKYRIZI original outcome-aware history remains an immutable-quality audit",()=>{
  const x=historical.records[0];
  assert.equal(x.assessmentId,"HIST-ABBV-SKYRIZI-2026-10-23-LEVEL3-001");
  assert.deepEqual(x.ncts,["NCT06063967"]);
  assert.equal(x.assessmentLevelStyle,3);
  assert.equal(x.assessmentDirection,"APPROVAL");
  assert.equal(x.actualOutcome,"APPROVAL");
  assert.equal(x.actualFdaActionDate,"2026-10-23");
  assert.equal(x.outcomeExposedBeforeAssessment,true);
  assert.equal(x.excludedFromProspectiveAccuracy,true);
  assert.equal(x.excludedFromRetrospectiveBlindValidation,true);
  assert.equal(x.excludedFromCalibration,true);
  assert.match(x.pdufaDateVerification,/THIRD_PARTY_TRACKER_ONLY/);
});

test("ABBV historical display was deleted from runtime but its evidence dossier is retained",()=>{
  assert.equal(quarantine.quarantined.some(r=>r.ticker==="ABBV"),true);
  const page=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  const chart=fs.readFileSync(path.join(root,"app/AssessmentLevelChart.tsx"),"utf8");
  assert.doesNotMatch(page,/SkyriziHistoricalLevelThreePanel/);
  assert.doesNotMatch(chart,/ABBV|SKYRIZI|levelThreeAbbvieHistorical2026/);
  assert.equal(fs.existsSync(path.join(root,"app/SkyriziHistoricalLevelThreePanel.tsx")),false);
  assert.equal(fs.existsSync(path.join(root,"docs/2026-oct23-abbv-skyrizi-level3-retrospective.md")),true);
});
