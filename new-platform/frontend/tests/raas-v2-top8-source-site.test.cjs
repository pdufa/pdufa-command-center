"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const dir=path.resolve(__dirname,"..");
const d=require("../data/raas-v2-top8-2026-source-intake.json");
const source=fs.readFileSync(path.join(dir,"app/raas-worklist/page.tsx"),"utf8");

test("Eight original issuer source leads are research, not certified FDA predictions",()=>{
 assert.equal(d.scope,"RAAS_V2_TOP8_2026_ISSUER_GOAL_PUBLICATION_SOURCE_RESEARCH_NOT_VALIDATED");
 assert.equal(d.records.length,8);
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
