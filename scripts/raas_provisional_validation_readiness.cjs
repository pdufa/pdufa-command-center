#!/usr/bin/env node
/** Reconcile actual RAAS calibration evidence; NEVER claim performance from
 * numerical component proxies, historical cherry-picked trials, or source counts.
 */
"use strict";
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,".."),front=path.join(root,"new-platform/frontend");
const load=f=>JSON.parse(fs.readFileSync(path.join(root,f),"utf8"));
function readiness({pilot,readout,history,calibrations,reviewed,historical,fda,policySource,metricSpecSource}){
 if(pilot.scope!=="HISTORICAL_PHASE3_RAAS_PILOT_OBSERVATIONS"||
    readout.scope!=="HISTORICAL_US_LISTED_300M_10B_PHASE3_LEAD_SPONSOR_RESEARCH"||
    history.scope!=="RAAS_TRIAL_SCORE_HISTORY"||
    calibrations.scope!=="RAAS_VALIDATED_METRIC_CALIBRATIONS"||
    reviewed.scope!=="RAAS_REVIEWED_TRIAL_SNAPSHOTS"||
    historical.scope!=="RAAS_HISTORICAL_EVENT_BACKTEST"||
    fda.scope!=="RAAS_FDA_THREE_WAY_DECISION_ACCURACY_SITE_SNAPSHOT"||
    !Array.isArray(history.records)||!Array.isArray(calibrations.entries)||
    !Array.isArray(reviewed.records)||!Array.isArray(historical.cases))
  throw Error("RAAS_CALIBRATION_EVIDENCE_INVALID");
 const metrics=(metricSpecSource.match(/"id": "(?:pre|post)-\\d+-\\d+"/g)||[]).length;
 if(metrics!==60||!policySource.includes("RAAS_PROVISIONAL_RUBRICS"))
  throw Error("RAAS_CALIBRATION_RULES_UNVERIFIED");
 const experimentalHistory=history.records.filter(e=>e.kind==="METRIC_SCORE_UPDATED");
 const gradedTrials=new Set(),gradedMetricSlots=new Set();
 for(const e of experimentalHistory){
  if(e.score!==null||e.scoreKind!=="UNSCORED"||!Array.isArray(e.metricGrades)||
     !/^NCT\d{8}$/.test(e.nctId)||!["pre","post"].includes(e.stage))
   throw Error("RAAS_CALIBRATION_HISTORY_UNSAFE");
  for(const g of e.metricGrades){
   const pilotRule={"pre-4-1":"timing-specificity-exploratory-2026-11-02-v1",
    "post-1-1":"uas7-placebo-contrast-descriptive-2026-11-04-v1",
    "post-1-2":"uas7-placebo-contrast-descriptive-2026-11-04-v1"};
   if(g.ruleId!==pilotRule[g.metricId]||!pilotRule[g.metricId])
    throw Error("RAAS_CALIBRATION_UNAPPROVED_EXPERIMENTAL_METRIC");
   if(![0,25,50,75,100].includes(g.score)||
      !g.metricId?.startsWith(e.stage+"-")||!g.ruleId||!g.sourceUrl?.startsWith("https://"))
    throw Error("RAAS_CALIBRATION_GRADE_INVALID");
   gradedMetricSlots.add([e.nctId,e.stage,g.metricId].join("|"));
  }
  gradedTrials.add(e.nctId);
 }
 const outcomeCases=historical.cases.length;
 const frozen=fda.predecisionThreeWayIndependentlyVerifiedForecasts;
 const ready=outcomeCases>=30&&frozen>=30&&calibrations.entries.length>=60&&
  reviewed.records.length>=30&&fda.independentOutcomeAdjudicationComplete===true;
 const blockers=[];
 if(calibrations.entries.length<60)blockers.push("Need independently held-out calibration for all 60 metrics");
 if(reviewed.records.length<30)blockers.push("Need at least 30 independently reviewed full RAAS trial snapshots");
 if(outcomeCases<30)blockers.push("Need at least 30 fully audited prospective entry/exit outcome cases");
 if(frozen<30)blockers.push("Need at least 30 independently frozen, predecision three-way forecasts");
 if(fda.independentOutcomeAdjudicationComplete!==true)
  blockers.push("Independent FDA PASS/CRL/EXTENSION outcome adjudication is incomplete");
 return {
  schemaVersion:1,scope:"RAAS_PROVISIONAL_VALIDATION_READINESS",
  sourceAsOf:pilot.sourceAsOf,policy:"raas-provisional-review-v1",
  proposedMetrics:60,sourceConfirmedReadoutTrials:readout.entries.length,
  experimentalHistoryEvents:experimentalHistory.length,
  experimentalTrialsWithMetrics:gradedTrials.size,
  distinctSourceGradedMetricSlots:gradedMetricSlots.size,
  approvedMetricCalibrations:calibrations.entries.length,
  reviewedOverallTrialSnapshots:reviewed.records.length,
  auditedEventReturnCases:outcomeCases,
  predecisionIndependentThreeWayForecasts:frozen,
  independentFdaOutcomesConfirmed:fda.independentOutcomeAdjudicationComplete===true,
  readyToValidateOverallRaas:ready,
  validatedRaasAccuracy:null,validatedFdaThreeWayAccuracy:null,
  note:"Experimental component bins are NOT validated predictive ratings. Accuracy remains N/A until a frozen, complete prospective cohort and independently verified outcomes pass all gates. Eligibility counts are necessary, not sufficient, for out-of-sample validation.",
  blockers
 };
}
function main(){
 const inputs={
  pilot:load("new-platform/frontend/data/raas-pilot-observations.json"),
  readout:load("new-platform/frontend/public/phase3-public-readout-evidence-2026-11-01.json"),
  history:load("new-platform/frontend/data/raas-trial-score-history.json"),
  calibrations:load("new-platform/frontend/data/raas-approved-calibrations.json"),
  reviewed:load("new-platform/frontend/data/raas-reviewed-snapshots.json"),
  historical:load("new-platform/frontend/data/raas-historical-cases.json"),
  fda:load("new-platform/frontend/data/raas-fda-three-way-accuracy-site-snapshot.json"),
  policySource:fs.readFileSync(path.join(front,"lib/raas-provisional-rubric-engine.ts"),"utf8"),
  metricSpecSource:fs.readFileSync(path.join(front,"lib/raas-metric-specs.ts"),"utf8")
 };
 const out=readiness(inputs);
 const dest=path.join(root,"data/raas_provisional_validation_readiness.json");
 const text=JSON.stringify(out,null,2)+"\n";
 if(!fs.existsSync(dest)||fs.readFileSync(dest,"utf8")!==text)fs.writeFileSync(dest,text);
 process.stdout.write("RAAS validation gate: "+out.distinctSourceGradedMetricSlots+
  " experimental grade slots, "+out.approvedMetricCalibrations+
  " approved metric calibrations; accuracy N/A, validation gated.\n");
}
if(require.main===module)main();
module.exports={readiness};
