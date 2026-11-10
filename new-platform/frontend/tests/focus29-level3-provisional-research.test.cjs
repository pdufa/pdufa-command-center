const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const ts=require("typescript");
const React=require("react");
const {renderToStaticMarkup}=require("react-dom/server");

require.extensions[".tsx"]=(module,filename)=>module._compile(
  ts.transpileModule(fs.readFileSync(filename,"utf8"),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,
      jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}
  }).outputText,filename
);

const manifest=require("../data/focus29Level3ProvisionalResearch20261110.json");
const roster=require("../data/p3PostDataActive.json");
const panel=require("../app/Focus29Level3ProvisionalPanel.tsx").default;
const root=path.resolve(__dirname,"..");

test("29 original FOCUS trials map to exactly 23 provisional FDA cycles without double-counting",()=>{
  assert.equal(manifest.schemaVersion,1);
  assert.match(manifest.kind,/NOT_PRODUCTION_FORECAST/);
  assert.equal(manifest.summary.exactNcts,29);
  assert.equal(manifest.summary.applicationCycles,23);
  assert.equal(manifest.summary.linkedTrialApplicationPairs,30);
  assert.equal(manifest.trials.length,29);
  assert.equal(manifest.cycles.length,23);
  assert.equal(roster.records.length,29);

  const rosterById=new Map(roster.records.map(x=>[x.nct,x]));
  const cycleById=new Map(manifest.cycles.map(x=>[x.cycleId,x]));
  assert.equal(rosterById.size,29);
  assert.equal(cycleById.size,23);
  const pairs=[];
  for(const trial of manifest.trials){
    assert.equal(rosterById.get(trial.nct)?.ticker,trial.ticker,trial.nct);
    assert.match(trial.sourceRegistryUrl,new RegExp("/"+trial.nct+"$"));
    assert.equal(trial.independentScientificReviewComplete,false);
    assert.equal(trial.probabilityCalibrated,false);
    assert.ok(trial.calls.length>=1,trial.nct);
    assert.deepEqual(trial.applicationCycleIds,trial.calls.map(x=>x.cycleId));
    for(const call of trial.calls){
      const cycle=cycleById.get(call.cycleId);
      assert.ok(cycle,call.cycleId);
      assert.equal(call.call,cycle.call,trial.nct+" / "+call.cycleId);
      assert.ok(cycle.associatedNcts.includes(trial.nct),trial.nct+" / "+call.cycleId);
      pairs.push(trial.nct+":"+call.cycleId);
    }
  }
  assert.equal(pairs.length,30);
  assert.equal(new Set(pairs).size,30);
  assert.equal(manifest.cycles.reduce((n,c)=>n+c.associatedNcts.length,0),30);
  for(const c of manifest.cycles){
    for(const nct of c.associatedNcts){
      assert.ok(pairs.includes(nct+":"+c.cycleId),c.cycleId+" / "+nct);
    }
  }
});

test("all 23 directional research judgments remain visibly unvalidated and sourced",()=>{
  const counts={APPROVAL_LEAN:0,CRL_LEAN:0,ABSTAIN:0,ALREADY_APPROVED:0};
  for(const cycle of manifest.cycles){
    assert.ok(Object.hasOwn(counts,cycle.call),cycle.cycleId);
    counts[cycle.call]++;
    assert.equal(cycle.assessmentStyleLevel,3);
    assert.equal(cycle.independentSignoff,false);
    assert.equal(cycle.validatedAsProspectivePrediction,false);
    assert.equal(cycle.proposedForecastProbability,null);
    assert.equal(cycle.calibratedConfidence,null);
    assert.ok(cycle.sourceDate);
    for(const k of ["clinicalEvidenceReferenceUrl","applicationReferenceUrl"]){
      assert.match(cycle[k],/^https:\/\//,cycle.cycleId+" / "+k);
    }
    for(const k of ["level1ClinicalEvidence","level2BenefitRisk",
      "level3RegulatoryManufacturing","additionalEvidenceNeeded"]){
      assert.ok(cycle[k]?.length>12,cycle.cycleId+" / "+k);
    }
    if(cycle.call==="ABSTAIN")assert.equal(cycle.confidenceDescription,"NOT_RATED");
  }
  assert.deepEqual(counts,{APPROVAL_LEAN:12,CRL_LEAN:5,ABSTAIN:5,ALREADY_APPROVED:1});
  assert.equal(manifest.policy.independentLevel3ScientificReviewsComplete,false);
  assert.equal(manifest.policy.approvedNumericProbabilities,0);
  assert.equal(manifest.policy.validatedFDAForecasts,0);
  assert.equal(manifest.policy.verifiedBlindForecasts,0);
  assert.equal(manifest.policy.notActivePredictionEngine,true);
  assert.equal(manifest.policy.notEligibleForLiveProspectiveAccuracy,true);
  assert.equal(manifest.policy.notEligibleForTradingExecution,true);
  assert.equal(manifest.policy.preserveExistingCanonicalForecasts,true);
});

test("research preview renders the complete cycle roster and separate NCT mapping without altering live metrics",()=>{
  const html=renderToStaticMarkup(React.createElement(panel));
  assert.match(html,/data-testid="focus-29-level3-provisional-research"/);
  assert.match(html,/data-testid="focus29-level3-cycle-table"/);
  assert.match(html,/data-testid="focus29-level3-exact-nct-table"/);
  assert.match(html,/NOT completed independent Level 3/);
  assert.match(html,/Validated forecasts/);
  assert.match(html,/29-trial research file does not alter the live FDA prediction record/);
  for(const cycle of manifest.cycles){
    assert.ok(html.includes('data-cycle-id="'+cycle.cycleId+'"'),cycle.cycleId);
    assert.ok(html.includes('data-testid="research-call-'+cycle.cycleId+'"'),cycle.cycleId);
  }
  const assessment=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  const predictions=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
  assert.match(assessment,/Focus29Level3ProvisionalPanel/);
  assert.match(assessment,/HistoricalMonthlyLevelTrend/);
  assert.match(assessment,/AssessmentStatusPies/);
  assert.match(predictions,/focus-29-level3-research/);
  const liveAudit=require("../data/fdaPredictionDecisionAudit.json");
  assert.equal(liveAudit.records.length,1);
  assert.equal(liveAudit.records[0].ticker,"SMMT");
});
