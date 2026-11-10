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

test("near-term original-issuer PDUFA goals are the earliest three, exact-cycle mapped and never FDA decisions",()=>{
  const sourceChecks=require("../data/focusNearTermPdufaSourceChecks20261110.json");
  assert.equal(sourceChecks.schemaVersion,1);
  assert.equal(sourceChecks.primaryIssuerGoalReadbacks,3);
  assert.equal(sourceChecks.independentlyFDAConfirmedGoalDates,0);
  assert.equal(sourceChecks.validatedBlindPredictionCount,0);
  assert.equal(sourceChecks.entries.length,3);
  const expected=[
    ["capr-deramiocel","CAPR","2026-11-22","2026-08-24"],
    ["svra-molgramostim","SVRA","2026-11-22","2026-11-09"],
    ["cogt-gist","COGT","2026-11-30","2026-11-05"]
  ];
  const cycleById=new Map(manifest.cycles.map(x=>[x.cycleId,x]));
  for(const [i,[id,ticker,goal,srcDate]] of expected.entries()){
    const rec=sourceChecks.entries[i];
    assert.equal(rec.cycleId,id);
    assert.equal(rec.ticker,ticker);
    assert.equal(rec.reportedGoalDate,goal);
    assert.equal(rec.sourcePublicationDate,srcDate);
    assert.equal(cycleById.get(id).reportedPdufaGoal,goal);
    assert.equal(cycleById.get(id).ticker,ticker);
    assert.equal(rec.sourceStatus,"ISSUER_REPORTED_GOAL_CORROBORATED");
    assert.equal(rec.fdaDecisionObserved,false);
    assert.equal(rec.independentlyFdaConfirmed,false);
    assert.equal(rec.clinicalScientificSignoff,false);
    assert.match(rec.primarySourceUrl,/^https:\/\/www\.sec\.gov\/Archives\/edgar\//);
    assert.ok(rec.verifiedSourceClaim.length>30);
  }
  const upcoming=manifest.cycles.filter(c=>c.reportedPdufaGoal&&
    c.reportedPdufaGoal>=sourceChecks.asOf)
    .sort((a,b)=>a.reportedPdufaGoal.localeCompare(b.reportedPdufaGoal));
  assert.deepEqual(upcoming.slice(0,3).map(c=>c.cycleId),expected.map(x=>x[0]));
  const Dates=require("../app/FocusNearTermPdufaSourceChecks.tsx").default;
  const html=renderToStaticMarkup(React.createElement(Dates));
  assert.match(html,/data-testid="focus-near-term-issuer-goals"/);
  assert.match(html,/data-testid="focus-near-term-goal-table"/);
  assert.match(html,/3\/23 application cycles/);
  assert.match(html,/not a direct FDA/);
  for(const [id] of expected) assert.ok(html.includes('data-cycle="'+id+'"'));
  const p=fs.readFileSync(path.join(root,"app/predictions/assessment/page.tsx"),"utf8");
  assert.ok(p.includes("<FocusNearTermPdufaSourceChecks/>"));
  assert.ok(p.indexOf("<FocusNearTermPdufaSourceChecks/>")<
    p.indexOf("<Focus29Level3ProvisionalPanel/>"));
});
