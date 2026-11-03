"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const m=require("../scripts/raas_active_2024_2025_fda_source_triage_queue.cjs");
const config=require("../new-platform/frontend/data/raas-active-study-config.json");
const intake=require("../new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json");
const known=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const archiveCsv="event_key,ticker,pdufa_date,other\n"+
 "A-2024,ARQT,2024-07-07,suspect\n"+
 "B-2025,AXSM,2025-01-31,suspect\n"+
 "OLD-2020,AIMT,2020-09-04,archive\n";
const registryCsv="ticker,company,cik10,exchange,sic,sic_description,status\n"+
 "AXSM,Axsome Therapeutics Inc,0001579428,Nasdaq,2834,Pharma,OK\n"+
 "ABCD,Acme Bio,0000000001,Nasdaq,2834,Pharma,OK\n";
const action=(app,type,num,dt,sponsor)=>({
 id:app+"|"+type+"|"+num+"|"+dt,applicationNumber:app,
 submissionType:type,submissionNumber:num,year:Number(dt.slice(0,4)),
 actualApprovalDate:dt,sponsorName:sponsor,productNames:[],
 sourceUrl:"https://api.fda.gov/drug/drugsfda.json",
 status:"FDA_APPROVAL_ACTION_DISCOVERY_ONLY",
 contemporaneousPdufaTargetDate:null,firstPublicTargetAnnouncementDate:null,
 phase3ReadoutFirstPublicDate:null,historicalIssuerTicker:null,
 independentMarketCapVerified:false,approvedHistoricalTrade:false,approvedRaasGrade:false
});
const a=action("NDA215985","SUPPL","7","2024-07-09","ARCUTIS BIOTHERAPEUTICS");
const b=action("NDA215431","ORIG","1","2025-01-30","AXSOME THERAPEUTICS INC");
const c=action("NDA333333","SUPPL","2","2025-06-03","ACME BIO");
const crl=year=>({caseId:"NDA 33333|"+year,applicationNumber:"NDA 33333",
 letterDate:year+"-06-06",year,letterType:"COMPLETE RESPONSE",
 companyName:"Unknown",sourceUrl:"https://api.fda.gov/transparency/crl.json",
 actualFdaActionType:"CRL",originalPdufaTargetDate:null,
 originalPublicCRLDisclosureDate:null,preDecisionInformationEligible:false,
 eligibleForRaasCalibration:false});
const discovery={
 scope:"RAAS_ACTIVE_2024_2025_OFFICIAL_FDA_ACTION_DISCOVERY_NOT_CENSUS",
 status:"SOURCE_DISCOVERY_COMPLETE_FOR_OFFICIAL_ENDPOINTS_NOT_PDUFA_DENOMINATOR",
 studyYears:[2024,2025],actionYearIsNotPdufaTargetYear:true,
 years:[
  {year:2024,totalFdaApprovalActionLeads:1,archivedCRLLetterLeads:1,
   completePdufaEventCensus:false,approvedHistoricalTrades:0,calibratedRaasMetrics:0},
  {year:2025,totalFdaApprovalActionLeads:2,archivedCRLLetterLeads:1,
   completePdufaEventCensus:false,approvedHistoricalTrades:0,calibratedRaasMetrics:0}
 ],approvalActionLeads:[a,b,c],crlLetterLeads:[crl("2024"),crl("2025")],
 originalSourceLeadsCrosscheck:[],fullFDAEventCensusYearsAudited:0,
 approvedHistoricalTrades:0,approvedRaasCalibrations:0
};
const make=overrides=>m.build({discovery,config,archiveCsv,known,intake,
 registryCsv,...overrides});
test("review queue enumerates all official original, supplemental and CRL actions without loss",()=>{
 const r=make();
 assert.equal(r.scope,"RAAS_ACTIVE_2024_2025_FDA_SOURCE_EVIDENCE_TRIAGE_QUEUE");
 assert.equal(r.totals.originalSourceLeads,2);
 assert.equal(r.totals.archiveUnverifiedTargetDateLeads,2);
 assert.equal(r.totals.FDAApprovalActionLeads,3);
 assert.equal(r.totals.FDAArchivedCRLLetterLeads,2);
 assert.equal(r.totals.reviewRows,9);
 assert.deepEqual(r.reviewRows.map(x=>x.reviewPriority),[1,1,2,2,3,3,4,5,5]);
 assert.equal(r.fullYearsAudited,0);
 assert.equal(r.validatedHistoricalTradingCases,0);
 assert.equal(r.approvedRaasCalibrations,0);
 assert.equal(r.approvedTradingWindow,null);
 assert.ok(r.reviewRows.every(x=>x.historicallyValidatedTrade===false));
 assert.ok(r.reviewRows.every(x=>x.approvedRaasMetric===false));
 assert.ok(r.reviewRows.every(x=>x.blockers.length>0));
});
test("2024 Zoryve supplemental outcome and 2025 Symbravo original FDA action match their separate announced PDUFA targets",()=>{
 const r=make();
 const original=r.reviewRows.filter(x=>x.reviewPriority===1);
 assert.equal(original[0].ticker,"ARQT");
 assert.equal(original[0].originalPublicPdufaTargetDate,"2024-07-07");
 assert.equal(original[0].retrospectiveActionDate,"2024-07-09");
 assert.deepEqual(original[0].matchedOfficialApprovalActionIds,[a.id]);
 assert.equal(original[1].ticker,"AXSM");
 assert.equal(original[1].originalPublicPdufaTargetDate,"2025-01-31");
 assert.equal(original[1].retrospectiveActionDate,"2025-01-30");
 assert.deepEqual(original[1].matchedOfficialApprovalActionIds,[b.id]);
 assert.ok(original.every(x=>x.currentStage.includes("UNVALIDATED")));
 const official=r.reviewRows.filter(x=>x.reviewPriority>=4);
 assert.ok(official.every(x=>x.originalPublicPdufaTargetDate===null));
 assert.equal(official.find(x=>x.applicationNumber==="NDA215431").preliminaryPresentDayTickerNameLead,"AXSM");
 assert.equal(r.totals.currentRegistryExactSingleTickerLeads,2);
});
test("archive ticker and alleged target year never become FDA action year or certified event",()=>{
 const r=make();
 const archive=r.reviewRows.filter(x=>x.reviewPriority===2);
 assert.deepEqual(archive.map(x=>x.year),[2024,2025]);
 assert.equal(archive[0].originalPublicPdufaTargetDate,null);
 assert.equal(archive[0].archiveSuggestedPdufaDate,"2024-07-07");
 assert.equal(archive[0].yearBasis,"UNVERIFIED_ARCHIVE_PDUFA_TARGET_YEAR");
 assert.equal(r.reviewRows.find(x=>x.reviewPriority===3).yearBasis,"FDA_LETTER_ACTION_YEAR_ONLY");
 assert.equal(r.reviewRows.find(x=>x.reviewPriority===4).yearBasis,"FDA_APPROVAL_ACTION_YEAR_ONLY");
 assert.ok(r.caveats.some(x=>x.includes("not a single event denominator")));
});
test("two-year FDA action source must be complete, error on even one missing or duplicated action",()=>{
 const without=structuredClone(discovery);
 without.approvalActionLeads.pop();
 assert.throws(()=>make({discovery:without}),/FDA_ACTION_COUNTS_MISMATCH/);
 const duplicate=structuredClone(discovery);
 duplicate.approvalActionLeads.push(duplicate.approvalActionLeads[0]);
 assert.throws(()=>make({discovery:duplicate}),/FDA_APPROVAL_UNTRUSTED/);
 const bogus=structuredClone(discovery);
 bogus.approvalActionLeads[0].contemporaneousPdufaTargetDate="2024-07-07";
 assert.throws(()=>make({discovery:bogus}),/FDA_APPROVAL_UNTRUSTED/);
 const outOfPeriod=structuredClone(discovery);
 outOfPeriod.approvalActionLeads[0].year=2023;
 assert.throws(()=>make({discovery:outOfPeriod}),/FDA_APPROVAL_UNTRUSTED/);
});
test("original lead cannot claim FDA approval without matching actual official action, or become reviewed intake",()=>{
 const wrong=structuredClone(discovery);
 wrong.approvalActionLeads[0].actualApprovalDate="2024-07-07";
 wrong.approvalActionLeads[0].id="NDA215985|SUPPL|7|2024-07-07";
 assert.throws(()=>make({discovery:wrong}),/ORIGINAL_FDA_ACTION_NOT_INDEPENDENTLY_MATCHED/);
 const promoted=structuredClone(intake);
 promoted.records.push({caseId:known.records[0].caseId,ticker:"ARQT",
  pdufaDate:"2024-07-07",programId:"FAKE"});
 assert.throws(()=>make({intake:promoted}),/UNAPPROVED_INTAKE_OR_SOURCE_INVALID/);
 const census=structuredClone(intake);
 census.yearAudits[0]={year:2024,status:"FULL_EVENT_CENSUS_AUDITED",
  sourceUrl:"https://example.com/fake"};
 assert.throws(()=>make({intake:census}),/UNAPPROVED_INTAKE_OR_SOURCE_INVALID/);
});
test("review CSV retains all source blockers and escapes hostile CSV text",()=>{
 const d=make();
 const csv=m.csvForReview(d);
 const lines=csv.trim().split("\n");
 assert.equal(lines.length,10);
 assert.match(csv,/FDA_ORIGINAL_APPROVAL_ACTION/);
 assert.match(csv,/FDA_SUPPLEMENTAL_APPROVAL_ACTION/);
 assert.match(csv,/ORIGINAL_FDA_AND_ISSUER_SOURCE_LEAD/);
 const modified={...d,reviewRows:[{...d.reviewRows[0],drug:'"danger,\n"'}]};
 const result=m.csvForReview(modified);
 assert.ok(result.includes('"""danger,'));
});
