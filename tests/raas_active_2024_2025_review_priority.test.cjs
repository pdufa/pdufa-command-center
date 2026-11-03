"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const m=require("../scripts/raas_active_2024_2025_review_priority.cjs");
function row(i,track,year,ticker=null){
 const p=track==="ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD"?1:
  track==="ARCHIVE_TARGET_DATE_TO_VERIFY"?2:
  track==="RETROSPECTIVE_FDA_CRL_LETTER"?3:
  track==="FDA_ORIGINAL_APPROVAL_ACTION"?4:5;
 return {id:"ROW|"+i,year,yearBasis:p<=2?"UNVERIFIED_ARCHIVE_PDUFA_TARGET_YEAR":"FDA_APPROVAL_ACTION_YEAR_ONLY",
  reviewTrack:track,reviewPriority:p,
  ticker:p<=2?ticker:null,
  preliminaryPresentDayTickerNameLead:p>3?ticker:null,
  blockers:["DATE_UNAUDITED","HISTORIC_CAP_UNVERIFIED"],
  sourceUrls:p===2?[]:["https://api.fda.gov/drug/drugsfda.json"],
  historicallyValidatedTrade:false,approvedRaasMetric:false};
}
const rows=[
 row(1,"ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD",2024,"ARQT"),
 row(2,"ARCHIVE_TARGET_DATE_TO_VERIFY",2025,"AXSM"),
 row(3,"RETROSPECTIVE_FDA_CRL_LETTER",2024),
 row(4,"FDA_ORIGINAL_APPROVAL_ACTION",2025,"AXSM"),
 row(5,"FDA_SUPPLEMENTAL_APPROVAL_ACTION",2024,"ARQT"),
 row(6,"FDA_ORIGINAL_APPROVAL_ACTION",2024),
 row(7,"FDA_SUPPLEMENTAL_APPROVAL_ACTION",2025)
];
const queue=()=>({scope:"RAAS_ACTIVE_2024_2025_FDA_SOURCE_EVIDENCE_TRIAGE_QUEUE",
 status:"ALL_OFFICIAL_ACTIONS_AND_ARCHIVE_LEADS_QUEUED_NOT_QUALIFIED_TRADES",
 studyYears:[2024,2025],reviewRows:structuredClone(rows),
 fullYearsAudited:0,validatedHistoricalTradingCases:0,
 approvedRaasCalibrations:0,approvedTradingWindow:null,
 totals:{reviewRows:7,originalSourceLeads:1,archiveUnverifiedTargetDateLeads:1,
 FDAApprovalActionLeads:4,FDAArchivedCRLLetterLeads:1}});
test("Seven action- and target-year research tiers stay distinct without scoring",()=>{
 const x=m.build(queue());
 assert.equal(x.totalTasks,7);
 assert.equal(Object.values(x.tiers).reduce((a,b)=>a+b,0),7);
 assert.deepEqual(x.reviewRows.map(r=>r.priority),[1,2,3,4,5,6,7]);
 assert.equal(x.fullPdufaTargetYearsAudited,0);
 assert.equal(x.independentlyValidatedTradingCases,0);
 assert.equal(x.approvedRaasMetrics,0);
 assert.equal(x.declaredBestTradingWindow,null);
 assert.deepEqual(Object.keys(x.yearBasisCounts).sort(),[
  "FDA_APPROVAL_ACTION_YEAR_ONLY|2024",
  "FDA_APPROVAL_ACTION_YEAR_ONLY|2025",
  "UNVERIFIED_ARCHIVE_PDUFA_TARGET_YEAR|2024",
  "UNVERIFIED_ARCHIVE_PDUFA_TARGET_YEAR|2025"
 ]);
 assert.ok(x.reviewRows.every(r=>r.eligibleForScoring===false&&
  r.historicalCap300mTo10bConfirmed===false&&
  r.validatedTradingCase===false));
});
test("Original case and archive ticker remain separately sourced, never historical listing proof",()=>{
 const x=m.build(queue());
 assert.equal(x.reviewRows[0].originalKnownTicker,"ARQT");
 assert.equal(x.reviewRows[0].presentDayRegistryTickerLead,null);
 assert.equal(x.reviewRows[1].archiveSuggestedTicker,"AXSM");
 assert.equal(x.reviewRows[1].pdufaTargetFirstPublic,null);
 assert.equal(x.reviewRows[3].presentDayRegistryTickerLead,"AXSM");
 assert.equal(x.reviewRows[3].originalKnownTicker,null);
 assert.equal(x.reviewRows[3].historicalIssuerListingConfirmed,false);
 assert.ok(x.reviewRows[2].reviewerChecks.some(s=>s.includes("ACTION YEAR")));
 assert.ok(x.reviewRows[4].reviewerChecks.some(s=>s.includes("label update")));
});
test("Do not drop source rows, duplicate IDs, wrong year, or fabricated validated records",()=>{
 let x=queue();x.reviewRows.pop();
 assert.throws(()=>m.build(x),/PRIORITIZATION_INVALID_INCOMPLETE_STUDY/);
 x=queue();x.reviewRows.push(x.reviewRows[0]);x.totals.reviewRows=8;
 assert.throws(()=>m.build(x),/PRIORITIZATION_UNTRUSTED_RESEARCH_ROW/);
 x=queue();x.reviewRows[0].year=2023;
 assert.throws(()=>m.build(x),/PRIORITIZATION_UNTRUSTED_RESEARCH_ROW/);
 x=queue();x.reviewRows[0].historicallyValidatedTrade=true;
 assert.throws(()=>m.build(x),/PRIORITIZATION_UNTRUSTED_RESEARCH_ROW/);
 x=queue();x.reviewRows[0].sourceUrls=["javascript:alert(1)"];
 assert.throws(()=>m.build(x),/PRIORITIZATION_UNTRUSTED_RESEARCH_ROW/);
 x=queue();x.totals.FDAApprovalActionLeads=3;
 assert.throws(()=>m.build(x),/PRIORITIZATION_LOST_OFFICIAL_ACTIONS/);
});
test("Spreadsheet CSV exports neutralize formula-like leading text and retain all rows",()=>{
 const data=m.build(queue());
 assert.equal(m.csvEscape('=HYPERLINK("https://bad.test","x")'),
  '"\'=HYPERLINK(""https://bad.test"",""x"")"');
 assert.equal(m.csvEscape(" +SUM(1,1)"),"\"' +SUM(1,1)\"");
 assert.equal(m.csvEscape("@SUM(1,1)"),"\"'@SUM(1,1)\"");
 assert.equal(m.csvEscape("-1+2"),"\"'-1+2\"");
 assert.equal(m.csvEscape("Normal Name"),'"Normal Name"');
 data.reviewRows[0].reviewId='=HYPERLINK("https://bad.test","x")';
 const csv=m.csvForReview(data);
 assert.equal(csv.trim().split("\n").length,data.totalTasks+1);
 assert.ok(csv.includes("'=HYPERLINK"));
 assert.ok(!csv.includes('"=HYPERLINK'));
});
test("Distinct 2024/2025 year bases retained, and review queue cannot certify study",()=>{
 const x=m.build(queue());
 assert.equal(x.trainingYear,2024);
 assert.equal(x.holdoutYear,2025);
 assert.equal(x.independentIssuersForTrain,0);
 assert.equal(x.independentIssuersForHoldout,0);
 assert.ok(x.caveats.some(s=>s.includes("not one denominator")));
 assert.ok(x.topTwenty.every(r=>r.evidenceBlockers.length>0));
});
