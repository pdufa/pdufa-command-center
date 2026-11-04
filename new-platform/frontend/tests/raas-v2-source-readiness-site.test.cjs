"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const root=path.resolve(__dirname,"..");
const snapshot=require("../data/raas-v2-candidate-source-readiness-site-snapshot.json");
const existing=require("../data/raas-fda-three-way-accuracy-site-snapshot.json");
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
 assert.equal(snapshot.issuerDocumentedNearTermCycleSourceLeads,15);
 assert.equal(snapshot.knownRevisedGoalExcludedFromOriginalDeadlineQueue,4);
 assert.equal(snapshot.remainingUnexcludedLegacyDateResearchLeads,32);
 assert.equal(snapshot.legacyCasesStillUnreviewedByIssuerSources,21);
 assert.equal(snapshot.additionalIssuerDocumentedFormallyExtendedCases,3);
 assert.equal(snapshot.additionalOriginalGoalIssuerSourceLeads,4);
 assert.equal(snapshot.pivotalPhase2SourceLeadsNotStrictPhase3Eligible,2);
 assert.equal(snapshot.nov14IndependentPhase3RegistryCrossChecks,2);
 assert.equal(snapshot.nov14NumberedCurrentFdaApplicationCyclesCertified,0);
 assert.equal(snapshot.nov14FrozenThreeWayForecasts,0);
 assert.equal(snapshot.nightlyPublicFDAApplicationHistoryWatch,
   "RESEARCH_ONLY_MONITOR_SOURCE_STATUS_ARTIFACT_NOT_SITE_LIVE");
 assert.equal(snapshot.nov14KnownUnrelatedAlreadyApprovedFdaSupplementRemsControls,1);
 assert.equal(snapshot.nov14IssuerReportedOSRequirementPrimaryNonsignificantCases,1);
 assert.equal(snapshot.provenIndependentFirstGoalForecasts,0);
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
 assert.match(source,/x\.knownRevisedGoalExcludedFromOriginalDeadlineQueue/);
 assert.match(source,/x\.legacyCasesStillUnreviewedByIssuerSources/);
 assert.match(source,/The remaining \{x\.remainingUnexcludedLegacyDateResearchLeads\} are not independently certified original-goal forecasts/);
});

test("Mobile nightly official FDA lookup is explicitly separate from a scored forecast",()=>{
 assert.match(source,/raas-v2-daily-openfda-application-watch/);
 assert.match(source,/S-001 is a February REMS-only action/);
 assert.match(source,/the pending MAPLE-HCM efficacy supplement/);
 assert.ok(source.includes("<strong>not</strong>"));
 assert.match(source,/the numbered pending BLA remains unverified/);
 assert.match(source,/Live results are in the/);
 assert.match(source,/not this dated website snapshot/);
});
