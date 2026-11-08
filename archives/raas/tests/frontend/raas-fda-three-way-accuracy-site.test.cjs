"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const snapshot=require("../data/raas-fda-three-way-accuracy-site-snapshot.json");
const source=fs.readFileSync(path.join(root,"app/raas-worklist/page.tsx"),"utf8");
const protocol=require("../../../data/raas_fda_three_way_protocol.json");
const forecast=require("../../../data/raas_fda_three_way_frozen_forecasts.json");
const outcome=require("../../../data/raas_fda_three_way_outcomes.json");
const roster=require("../../../data/raas_fda_three_way_eligible_cases.json");

test("FDA outcome dashboard never advertises historical reconstructs as validated RAAS predictions",()=>{
 assert.equal(snapshot.scope,"RAAS_FDA_THREE_WAY_DECISION_ACCURACY_SITE_SNAPSHOT");
 assert.equal(snapshot.legacyRetrospectiveCases,146);
 assert.equal(snapshot.legacyCorrect,102);
 assert.equal(snapshot.alwaysApproveCorrect,106);
 assert.equal(snapshot.legacyRetrospectiveAccuracyPct,69.86);
 assert.equal(snapshot.alwaysApproveRetrospectiveAccuracyPct,72.6);
 assert.equal(snapshot.historicalExtensions,0);
 assert.equal(snapshot.predecisionThreeWayIndependentlyVerifiedForecasts,0);
 assert.equal(snapshot.certifiedFDAThreeWayPredictionAccuracyPct,null);
 assert.equal(snapshot.approvedThreeWayFDAOutcomeModel,false);
 assert.equal(snapshot.approvedRaasMetricCalibrations,0);
 assert.deepEqual(snapshot.classes,["PASS","CRL","EXTENSION"]);
 assert.match(snapshot.status,/NO_INDEPENDENT/);
});
test("FDA decision model protocol stays unapproved without verified independent review-cycle and frozen forecast evidence",()=>{
 assert.deepEqual(protocol.classes,["PASS","CRL","EXTENSION"]);
 assert.equal(protocol.approvalOfHistoricalAccuracy,false);
 assert.equal(protocol.approvalOfCalibratedRAASMetrics,false);
 assert.equal(protocol.cohortCompleteVerified,false);
 assert.equal(protocol.immutableForecastReceiptAuditComplete,false);
 assert.equal(protocol.FDAOutcomeAdjudicationIndependentAuditComplete,false);
 assert.equal(protocol.minAdjudicatedProspectivePrograms,30);
 assert.equal(protocol.minProgramsPerClass,5);
 for(const x of [roster,forecast,outcome])assert.deepEqual(x.records,[]);
});
test("Mobile RAAS worklist shows proof limits, independent baseline, three-way categories and live nightly audit",()=>{
 assert.match(source,/function FDAAccuracySection\(/);
 assert.match(source,/<FDAAccuracySection\/>/);
 assert.match(source,/raas-fda-prediction-accuracy/);
 assert.match(source,/fdaDecisionAccuracy\.legacyRetrospectiveCases|x\.legacyRetrospectiveCases/);
 assert.match(source,/x\.alwaysApproveRetrospectiveAccuracyPct/);
 assert.match(source,/x\.predecisionThreeWayIndependentlyVerifiedForecasts/);
 assert.match(source,/github.com\/pdufa\/pdufa-command-center\/actions\/workflows\/raas-fda-decision-accuracy\.yml|x\.workflowUrl/);
 assert.match(source,/Not independently validated/);
 assert.ok(!source.includes("100% FDA accuracy"));
});
