"use strict";
const test=require("node:test"),assert=require("node:assert/strict"),
 fs=require("node:fs"),path=require("node:path");
const repo=path.resolve(__dirname,"../../.."),front=path.resolve(__dirname,"..");
const gate=require(path.join(repo,"scripts/raas_provisional_validation_readiness.cjs"));
const load=f=>JSON.parse(fs.readFileSync(path.join(repo,f),"utf8"));
const inputs=()=>({
 pilot:load("new-platform/frontend/data/raas-pilot-observations.json"),
 readout:load("new-platform/frontend/public/phase3-public-readout-evidence-2026-11-01.json"),
 history:load("new-platform/frontend/data/raas-trial-score-history.json"),
 calibrations:load("new-platform/frontend/data/raas-approved-calibrations.json"),
 reviewed:load("new-platform/frontend/data/raas-reviewed-snapshots.json"),
 historical:load("new-platform/frontend/data/raas-historical-cases.json"),
 fda:load("new-platform/frontend/data/raas-fda-three-way-accuracy-site-snapshot.json"),
 policySource:fs.readFileSync(path.join(front,"lib/raas-provisional-rubric-engine.ts"),"utf8"),
 metricSpecSource:fs.readFileSync(path.join(front,"lib/raas-metric-specs.ts"),"utf8")
});
test("numeric pilot metrics never become validated RAAS or FDA predictive accuracy",()=>{
 const result=gate.readiness(inputs());
 assert.equal(result.proposedMetrics,60);
 assert.equal(result.sourceConfirmedReadoutTrials,5);
 assert.equal(result.readyToValidateOverallRaas,false);
 assert.equal(result.validatedRaasAccuracy,null);
 assert.equal(result.validatedFdaThreeWayAccuracy,null);
 assert.equal(result.approvedMetricCalibrations,0);
 assert.equal(result.auditedEventReturnCases,0);
 assert.equal(result.predecisionIndependentThreeWayForecasts,0);
 assert.ok(result.experimentalTrialsWithMetrics>=4);
 assert.ok(result.distinctSourceGradedMetricSlots>=6);
 assert.equal(result.blockers.length,5);
});
test("invented prediction percentage cannot be promoted by raw score history",()=>{
 const x=inputs();
 x.history.records=[...x.history.records,{
  kind:"METRIC_SCORE_UPDATED",scoreKind:"VALIDATED",score:95,
  stage:"post",nctId:"NCT06445023",metricGrades:[{metricId:"post-1-1",score:100,
   ruleId:"fabricated",sourceUrl:"https://example.org"}]}];
 assert.throws(()=>gate.readiness(x),/HISTORY_UNSAFE/);
});
test("historical coverage alone cannot claim performance when review and outcome gates are missing",()=>{
 const x=inputs();
 x.historical.cases=Array.from({length:40},()=>({fake:true}));
 x.fda.predecisionThreeWayIndependentlyVerifiedForecasts=40;
 const result=gate.readiness(x);
 assert.equal(result.readyToValidateOverallRaas,false);
 assert.equal(result.validatedRaasAccuracy,null);
 assert.ok(result.blockers.some(x=>/calibration/.test(x)));
});
