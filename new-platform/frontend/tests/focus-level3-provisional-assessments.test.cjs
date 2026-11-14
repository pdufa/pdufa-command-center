const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const read=(...p)=>fs.readFileSync(path.join(root,...p),"utf8");
const research=JSON.parse(read("data","calFocusResearchOverlay20261110.json"));
const focus=JSON.parse(read("data","p3PostDataActive.json"));

test("ASSESSMENTS visibly offers 29 FOCUS linked trials with 23 frozen preliminary FDA calls",()=>{
  const page=read("app","predictions","assessment","page.tsx");
  const component=read("app","FocusLevelThreeResearchForecasts.tsx");
  assert.match(page,/import FocusLevelThreeResearchForecasts/);
  assert.match(page,/<FocusLevelThreeResearchForecasts selectedCycleId=\{cycle\?\.cycleId\}\/>/);
  assert.match(component,/CURRENT FOCUS · 29 EXACT NCTS · 23 FDA APPLICATION CYCLES/);
  assert.match(component,/data-testid="focus-level3-cycle-prediction-table"/);
  assert.match(component,/researchSnapshotPasses\(\)/);
  assert.match(component,/selectedCycleId/);
  assert.match(component,/clinicalRationale/);
  assert.match(component,/benefitRiskRationale/);
  assert.match(component,/fdaCmcRationale/);
  assert.match(component,/evidenceGap/);
  assert.match(component,/sourceResearchCommit/);
  assert.match(component,/Link href=\{linkTo\(nct,c\.cycleId\)\}/);
  assert.match(component,/NOT independently validated FDA forecasts/);
  assert.match(component,/production engine and verified-accuracy charts remain/);
  assert.doesNotMatch(component,/setForecast|updatePrediction|writePredictions|addToAccuracy/);
});
test("23 FDA application cycles keep separate NCT mappings and research direction counts",()=>{
  assert.equal(focus.records.length,29);
  assert.equal(research.cycles.length,23);
  assert.equal(research.kind,"CAL_FOCUS_LEVEL3_STYLE_RESEARCH_FREEZE_NOT_VALIDATED_FDA_FORECAST");
  assert.equal(research.policy.notActivePredictionEngine,true);
  assert.equal(research.policy.immutableHypothesisSnapshot,true);
  assert.equal(research.policy.numericalProbabilities,null);
  assert.equal(research.policy.independentScientificSignoff,false);
  const existing=new Map(focus.records.map(x=>[x.nct,x.ticker]));
  const ids=new Set(),ncts=new Set(),counts={APPROVAL_LEAN:0,CRL_LEAN:0,ABSTAIN:0,ALREADY_APPROVED:0};
  for(const c of research.cycles){
    assert.ok(!ids.has(c.cycleId),"application cycle ids must be unique");
    ids.add(c.cycleId);
    assert.equal(c.level,3);
    assert.equal(c.asOf,research.asOf);
    assert.equal(c.independentSignoff,false);
    assert.equal(c.calibratedProbability,null);
    assert.equal(c.scientificStatus,"PRELIMINARY_SOURCE_LINKED_RESEARCH_NOT_INDEPENDENTLY_VALIDATED");
    assert.ok(Object.hasOwn(counts,c.call));
    counts[c.call]++;
    assert.ok(c.associatedNcts.length);
    for(const nct of c.associatedNcts){
      assert.equal(existing.get(nct),c.ticker);
      ncts.add(nct);
    }
  }
  assert.deepEqual(counts,{APPROVAL_LEAN:12,CRL_LEAN:5,ABSTAIN:5,ALREADY_APPROVED:1});
  assert.equal(ids.size,23);
  assert.equal(ncts.size,29);
  const srpt=research.cycles.filter(x=>x.ticker==="SRPT");
  assert.equal(srpt.length,2);
  assert.notEqual(srpt[0].cycleId,srpt[1].cycleId);
});
test("owner-only preliminary research remains distinct from calibrated predictions",()=>{
  const api=read("app","api","focus-assessment-intake","route.ts");
  const page=read("app","predictions","assessment","page.tsx");
  assert.match(api,/FOCUS_SCIENTIFIC_RESEARCH_INTAKE_NOT_COMPLETED_ASSESSMENTS/);
  assert.match(api,/specialistReviewComplete:false/);
  assert.match(api,/predictionReleasePermitted:false/);
  assert.match(page,/validated production engine remains/);
  assert.match(page,/not a prediction/);
  assert.match(page,/Owner-reviewed trials/);
  assert.match(page,/No outside clinician, statistician/);
});
