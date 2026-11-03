"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const data=require("../new-platform/frontend/data/raas-2025-nine-archived-goal-original-source-triage.json");
const iso=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
test("2025 nine archived PDUFA targets become source-review leads only, not FDA validation",()=>{
 assert.equal(data.scope,"RAAS_2025_NINE_ARCHIVE_GOAL_EVIDENCE_TRIAGE_RESEARCH_ONLY");
 assert.equal(data.records.length,9);
 assert.equal(data.originalArchiveUnverifiedRows,9);
 assert.equal(data.sourceLeadsWithPreGoalOriginalAnnouncement,8);
 assert.equal(data.formalExtensionSourceLeads,2);
 assert.equal(data.independentlyAdjudicatedFDAThreeWayOutcomes,0);
 assert.equal(data.independentProspectiveForecasts,0);
 assert.equal(data.independentlyValidatedRAASTrades,0);
 assert.equal(data.approvedTrainingCases,0);
 assert.equal(data.full2025OriginalGoalCensus,false);
 assert.deepEqual(data.records.map(x=>x.ticker).sort(),
  ["BCRX","CAPR","CORT","ETON","LQDA","NVAX","TNXP","UNCY","VNDA"]);
 for(const x of data.records){
  assert.equal(x.caseId,"ARCHIVE_2025_"+x.ticker);
  assert.ok(iso(x.archivedSuggestedGoalDate)&&iso(x.firstCycleGoalDate));
  assert.equal(x.year,2025);
  assert.equal(x.originalGoalSourceIndependentlyCertified,false);
  assert.equal(x.exactApplicationReviewCycleIndependentlyCertified,false);
  assert.equal(x.FDAOriginalGoalDispositionIndependentlyAdjudicated,false);
  assert.equal(x.actualThreeWayForecastReceiptBeforeActionVerified,false);
  assert.equal(x.postPhase3ListingAndCapVerified,false);
  assert.equal(x.eligibleForFDAProspectiveAccuracy,false);
  assert.equal(x.eligibleForRAASTradeTraining,false);
  assert.equal(x.revision!==null,x.isLaterGoalRevised);
  if(x.goalFirstPublicDate!==null){
   assert.ok(iso(x.goalFirstPublicDate)&&x.goalFirstPublicDate<x.firstCycleGoalDate);
   assert.match(x.goalSourceUrl,/^https:\/\//);
  }else assert.equal(x.goalSourceUrl,null);
  if(x.revision){
   assert.equal(x.archivedSuggestedGoalDate,x.revision.newDate);
   assert.ok(iso(x.revision.publicDate));
   assert.ok(x.goalFirstPublicDate<=x.revision.publicDate);
   assert.ok(x.revision.publicDate<x.firstCycleGoalDate);
   assert.ok(x.firstCycleGoalDate<x.revision.newDate);
   assert.match(x.revision.url,/^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\//);
   assert.equal(x.observedOriginalGoalResearchLabel,"EXTENSION_RESEARCH_LEAD");
  }else assert.equal(x.archivedSuggestedGoalDate,x.firstCycleGoalDate);
 }
});
test("ETON and BCRX original PDUFA extensions are NOT December or May approvals",()=>{
 const eton=data.records.find(x=>x.ticker==="ETON"),
  bcrx=data.records.find(x=>x.ticker==="BCRX");
 assert.deepEqual([eton.firstCycleGoalDate,eton.revision.newDate,
  eton.revision.publicDate],["2025-02-28","2025-05-28","2025-02-06"]);
 assert.deepEqual([bcrx.firstCycleGoalDate,bcrx.revision.newDate,
  bcrx.revision.publicDate],["2025-09-12","2025-12-12","2025-06-25"]);
 assert.match(eton.goalSourceUrl,/etonpharma.com/);
 assert.match(bcrx.goalSourceUrl,/sec.gov/);
});
test("NVAX no action at goal cannot be made into a formal PDUFA extension",()=>{
 const x=data.records.find(x=>x.ticker==="NVAX");
 assert.equal(x.firstCycleGoalDate,"2025-04-01");
 assert.equal(x.goalFirstPublicDate,null);
 assert.equal(x.revision,null);
 assert.equal(x.observedOriginalGoalResearchLabel,"NO_PUBLIC_ACTION_AT_ORIGINAL_GOAL_RESEARCH_LEAD");
});
test("Original review-cycle source and later FDA action remain separate across CRL and approvals",()=>{
 const tnxp=data.records.find(x=>x.ticker==="TNXP");
 assert.equal(tnxp.firstCycleGoalDate,"2025-08-15");
 assert.equal(tnxp.observedOriginalGoalResearchLabel,"PASS_RESEARCH_LEAD");
 const cort=data.records.find(x=>x.ticker==="CORT");
 assert.equal(cort.observedOriginalGoalResearchLabel,"CRL_RESEARCH_LEAD");
 assert.equal(cort.postGoalOrActionDisclosure.reportedPublicDate,"2025-12-31");
 const capr=data.records.find(x=>x.ticker==="CAPR");
 assert.match(capr.explanatoryReviewNotes,/Phase 3 pivotal evidence.*not established/);
 const lqda=data.records.find(x=>x.ticker==="LQDA");
 assert.match(lqda.explanatoryReviewNotes,/Class 1 resubmission/);
});
