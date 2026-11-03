"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const dir=path.resolve(__dirname,"..");
const d=require("../data/raas-v2-top8-2026-source-intake.json");
const nov14=require("../data/raas-v2-nov14-review-cycle-triangulation.json");
const source=fs.readFileSync(path.join(dir,"app/raas-worklist/page.tsx"),"utf8");

test("Eight original issuer source leads are research, not certified FDA predictions",()=>{
 assert.equal(d.scope,"RAAS_V2_TOP8_2026_ISSUER_GOAL_PUBLICATION_SOURCE_RESEARCH_NOT_VALIDATED");
 assert.equal(d.records.length,8);
 assert.equal(d.additionalFormalRevisionCases.length,3);
 assert.equal(d.additionalFormallyExtendedLegacyReviewLeads,3);
 assert.equal(d.goalSourceLeads,8);
 assert.equal(d.issuerPublicationSourcesLocated,8);
 assert.equal(d.scoredThreeWayForecasts,0);
 assert.equal(d.caseCountIndependentlyCertified,0);
 assert.equal(d.independentlyVerifiedOriginalGoalFDAOutcomeCases,0);
 assert.equal(d.eligibleForPredictionFreeze,0);
 assert.equal(d.independentlyCalibratedRaasMetrics,0);
 assert.equal(d.activeScoringVersion,"2026-11-02-foundation-v1");
 assert.ok(d.records.every(x=>x.sourceDocumentLocated===true &&
  x.enrolledInV2ProspectiveCohort===false && x.FDAThreeWayAccuracyQualified===false &&
  x.approvalForTradingModel===false));
});

test("Website keeps review-cycle, revised-goal and third-party sponsor distinctions",()=>{
 assert.match(source,/import v2Top8Sources from/);
 assert.match(source,/raas-v2-source-verified-eight/);
 assert.match(source,/v2Top8Sources\.records\.map/);
 assert.match(source,/CAPR's first target already passed/);
 assert.match(source,/CYTK is a supplemental NDA/);
 assert.match(source,/ANAB receives financial rights to a Vanda-licensed program/);
 assert.match(source,/no immutable three-way forecast receipts/);
 assert.match(source,/V2 candidate/);
});

test("Four new distinct original-goal source leads preserve the Phase 3-only filter",()=>{
 assert.equal(d.additionalOriginalGoalIssuerSourceLeads,4);
 const rows=d.additionalOriginalGoalIssuerSourceCases;
 assert.equal(rows.length,4);
 const by=Object.fromEntries(rows.map(x=>[x.legacyCaseKey,x]));
 assert.equal(by["COGT|BEZUCLASTINIB_GIST_20261130"].issuerReportedFirstGoalDate,"2026-11-30");
 assert.equal(by["BEZUCLASTINIB_NONADVSM_US_20261230"].issuerReportedFirstGoalDate,"2026-12-30");
 assert.equal(by["ANITOCEL_RRMM_US_20261223"].pivotalPhaseEvidence,"PIVOTAL_PHASE_2_REPORTED_IMMAGINE1");
 assert.equal(by["BEZUCLASTINIB_NONADVSM_US_20261230"].pivotalPhaseEvidence,"PIVOTAL_PHASE_2_REPORTED_SUMMIT");
 assert.ok(rows.every(x=>x.approvalForTradingModel===false &&
   x.approvedPipelinePhase3Qualification===false &&
   x.prospectivelyFrozenThreeWayProbabilities===false &&
   x.exactReviewCycleIndependentlyVerified===false));
 assert.match(source,/raas-v2-additional-original-goals/);
 assert.ok(source.includes("additionalOriginalGoalIssuerSourceCases.map"));
});

test("Additional SVRA PRAX EXEL source-led formal extensions cannot become forecasts",()=>{
 const by=Object.fromEntries(d.additionalFormalRevisionCases.map(r=>[r.ticker,r]));
 assert.deepEqual(Object.keys(by).sort(),["EXEL","PRAX","SVRA"]);
 assert.equal(by.SVRA.firstCycleGoalDate,"2026-08-22");
 assert.equal(by.SVRA.revisedGoalDate,"2026-11-22");
 assert.equal(by.PRAX.firstCycleGoalDate,"2026-09-27");
 assert.equal(by.PRAX.revisedGoalDate,"2026-12-27");
 assert.equal(by.EXEL.firstCycleGoalDate,"2026-12-03");
 assert.equal(by.EXEL.revisedGoalDate,"2027-03-03");
 assert.equal(by.EXEL.legacyGoalDate,by.EXEL.firstCycleGoalDate);
 assert.ok(d.additionalFormalRevisionCases.every(x=>
   x.sourceDocumentLocated===true && x.exactApplicationCycleIndependentlyVerified===false &&
   x.prospectivelyFrozenThreeWayProbabilities===false && x.eligibleForV2OriginalGoalPrediction===false));
 assert.match(source,/id="raas-v2-formally-revised-goals"/);
 assert.match(source,/v2Top8Sources\.additionalFormalRevisionCases\.map/);
});

test("Historical first-goal, supplemental, post-CRL and third-party license evidence remain explicit",()=>{
 const by=Object.fromEntries(d.records.map(x=>[x.ticker,x]));
 assert.equal(by.CAPR.firstCycleGoalDate,"2026-08-22");
 assert.equal(by.CAPR.formalGoalRevision.revisedGoalDate,"2026-11-22");
 assert.equal(by.CYTK.applicationType,"SUPPLEMENTAL_NDA");
 assert.equal(by.CORT.applicationType,"NDA_RESUBMISSION_AFTER_PRIOR_CRL");
 assert.equal(by.ANAB.clinicalSponsor,"Vanda Pharmaceuticals");
 assert.match(by.SMMT.issuerSourceUrl,/sec\.gov/);
 assert.equal(by.MLYS.sourcePublicationDate,"2026-03-09");
});

test("November 14 CYTK and SMMT have independent Phase 3 trial links but no certified current FDA cycle",()=>{
 assert.equal(nov14.casesCrossChecked,2);
 assert.equal(nov14.independentlyVerifiedCurrentApplicationCycleCount,0);
 assert.equal(nov14.independentlyVerifiedFrozenThreeWayForecastCount,0);
 const cases=Object.fromEntries(nov14.records.map(r=>[r.ticker,r]));
 assert.equal(cases.CYTK.clinicalTrialsGovId,"NCT05767346");
 assert.equal(cases.SMMT.clinicalTrialsGovId,"NCT06396065");
 assert.equal(cases.CYTK.usFDAParentOriginalNdaNumber,"219083");
 assert.equal(cases.CYTK.currentSupplementSequenceNumber,null);
 assert.equal(cases.CYTK.currentSupplementSequenceIndependentlyVerified,false);
 assert.equal(cases.SMMT.currentBlaNumber,null);
 assert.equal(cases.SMMT.currentBlaNumberIndependentlyVerified,false);
 assert.ok(nov14.records.every(x=>x.clinicalTrialsGovPhase==="PHASE_3" &&
   x.clinicalTrialsGovPhaseAndSponsorCrossChecked===true &&
   x.exactCurrentFDAReviewCycleIndependentlyCertified===false &&
   x.approvedPipelineMarketCapAndPhase3Qualification===false &&
   x.independentlyVerifiedThreeWayForecast===false));
 assert.match(source,/raas-v2-nov14-cross-source-registry/);
 assert.ok(source.includes("nov14Triangulation.records.map"));
 assert.ok(source.includes("this does not verify the pending supplement number"));
});
