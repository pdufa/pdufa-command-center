"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const snapshot=require("../data/raas-v2-candidate-source-readiness-site-snapshot.json");
const existing=require("../data/raas-fda-three-way-accuracy-site-snapshot.json");
const nearTerm=require("../data/raas-v2-upcoming-2026-cycle-source-research.json");
const source=fs.readFileSync(path.join(root,"app/raas-worklist/page.tsx"),"utf8");
const metricSpecs=fs.readFileSync(path.join(root,"lib/raas-metric-specs.ts"),"utf8");

test("V2 source-readiness snapshot cannot pretend to be a calibrated model",()=>{
 assert.equal(snapshot.scope,"RAAS_V2_CANDIDATE_PROSPECTIVE_SOURCE_READINESS_SITE_SNAPSHOT");
 assert.equal(snapshot.candidateIteration,"V2_RESEARCH_CANDIDATE_STAGE_0");
 assert.equal(snapshot.activeFoundationIteration,"2026-11-02-foundation-v1");
 assert.equal(snapshot.status,"RESEARCH_CANDIDATE_NOT_A_CALIBRATED_PREDICTOR");
 assert.equal(snapshot.remainingLegacyFutureCaseSourceLeadsAtSnapshot,36);
 assert.equal(snapshot.verifiedOriginalGoalProspectiveThreeWayForecasts,0);
 assert.equal(snapshot.independentlyValidatedThreeWayFdaAccuracy,null);
 assert.equal(snapshot.approvedMetricCalibrations,0);
 assert.equal(snapshot.issuerDocumentedNearTermSourceLeads,3);
 assert.equal(snapshot.issuerDocumentedFutureOriginalGoalLeads,2);
 assert.equal(snapshot.revisedGoalNotFutureOriginalGoal,1);
 assert.equal(snapshot.independentlyVerifiedThreeWayOutcomeLabels,0);
 assert.equal(nearTerm.verifiedProspectiveFDADecisionForecasts,0);
 assert.equal(nearTerm.independentlyAdjudicatedThreeWayOutcomes,0);
 assert.equal(nearTerm.records.length,3);
 assert.equal(existing.approvedRaasMetricCalibrations,0);
 assert.match(metricSpecs,/RAAS_SPEC_VERSION="2026-11-02-foundation-v1"/);
});

test("Mobile site distinguishes V1 active foundation and V2 source candidate and provides nightly evidence link",()=>{
 assert.match(source,/function V2CandidateReadiness\(\)/);
 assert.match(source,/<V2CandidateReadiness\/>/);
 assert.match(source,/id="raas-v2-source-readiness"/);
 assert.match(source,/data-raas-v2-status="RESEARCH_CANDIDATE_NOT_CALIBRATED"/);
 assert.match(source,/Foundation V1 remains installed/);
 assert.match(source,/No V2 FDA accuracy percentage can yet be reported/);
 assert.match(source,/x\.remainingLegacyFutureCaseSourceLeadsAtSnapshot/);
 assert.match(source,/x\.approvedMetricCalibrations/);
 assert.match(source,/x\.nightlySourceReadinessAuditUrl/);
 assert.match(source,/href="#raas-v2-source-readiness"/);
 assert.match(source,/id="raas-v2-near-term-cycle-source-review"/);
 assert.match(source,/v2UpcomingCycleSources\.records\.map/);
 assert.match(source,/CAPR's November 22 date must not enter the future first-goal prediction denominator/);
 assert.match(source,/SMMT is a BLA/);
});
