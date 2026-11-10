const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const data=require("../data/september2026HistoricalAuditRoster.json");

test("September Level 3 cohort is source-led and has no fabricated retrospective accuracy",()=>{
  assert.equal(data.dataset,"SEPTEMBER_2026_CALENDAR_CANDIDATES_UNASSESSED");
  assert.equal(data.calendarRows,23);
  assert.equal(data.cases.length,23);
  assert.equal(new Set(data.cases.map(x=>x.id)).size,23);
  assert.equal(data.validatedLevel3Cases,0);
  assert.equal(data.validatedBlindCases,0);
  assert.equal(data.blindAccuracy,null);
  assert.equal(data.directionalAgreement,null);
  assert.equal(data.provisionalResearchForecastCount,0);
  assert.equal(data.affectsActivePredictions,false);
  assert.equal(data.affectsFocusRoster,false);
  for(const record of data.cases){
    assert.match(record.id,/^SEP26-\d{2}$/);
    assert.ok(record.ticker&&record.drug&&record.calendarDate&&record.sourceCalendarUrl);
    assert.equal(record.level3ResearchCall,null);
    assert.equal(record.predecisionEvidenceUrl,null);
    assert.equal(record.officialDecisionUrl,null);
    assert.equal(record.decisionIndependentlyVerified,false);
    assert.equal(record.eligibleForDirectionalAgreement,false);
    assert.equal(record.eligibleForBlindAccuracy,false);
  }
});
test("September uses separate page panel; original October is preserved",()=>{
  const page=fs.readFileSync(path.resolve(__dirname,"../app/predictions/assessment/page.tsx"),"utf8");
  const sep=fs.readFileSync(path.resolve(__dirname,"../app/September2026HistoricalAuditPanel.tsx"),"utf8");
  assert.ok(page.includes("<September2026HistoricalAuditPanel/>"));
  assert.ok(page.includes("<October2026HistoricalAuditPanel/>"));
  assert.ok(sep.includes("NOT YET MEASURABLE"));
  assert.ok(sep.includes("Unscored"));
  assert.ok(!sep.includes("16 / 17")&&!sep.includes("94.1%"));
});
