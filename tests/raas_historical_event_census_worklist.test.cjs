"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const m=require("../scripts/raas_historical_event_census_worklist.cjs");
const root=path.resolve(__dirname,"..");
const primary=JSON.parse(fs.readFileSync(path.join(root,
 "new-platform/frontend/data/raas-historical-2020-primary-source-leads.json"),"utf8"));
const archive=fs.readFileSync(path.join(root,"data/historical_assessed_decisions.csv"),"utf8");
const issuerCrosswalk={scope:"FDA_2016_2019_APPROVAL_SPONSOR_CURRENT_REGISTRY_NAME_RESEARCH",
 rows:[{fdaCandidateId:"NDA123456|ORIG|1|20180111",
  status:"EXACT_NAME_PUBLIC_REGISTRY_LEAD",candidateTicker:"TEST"}]};
const crlDiscovery={schemaVersion:1,
 scope:"FDA_ARCHIVED_CRL_OUTCOMES_2016_2025_DISCOVERY_ONLY",
 status:"FDA_CRL_DOCUMENTS_RETRIEVED_INCOMPLETE_EVENT_DENOMINATOR",
 cases:[{caseId:"NDA 209510|2018-10-05|test.pdf|ACACIA",
 applicationNumber:"NDA 209510",letterDate:"2018-10-05",
 companyName:"Acacia Pharma Ltd",sourceUrl:"https://api.fda.gov/transparency/crl.json?search=NDA",
 actualFdaActionType:"CRL",status:"FDA_REDACTED_CRL_OUTCOME_RESEARCH_ONLY",
 preDecisionInformationEligible:false,eligibleForRaasCalibration:false}]};
const fda={scope:"FDA_DRUGS_AT_FDA_2016_2019_APPROVAL_DISCOVERY_NOT_PDUFA_CENSUS",
 candidates:[{id:"NDA123456|ORIG|1|20180111",year:2018,
  status:"FDA_APPROVAL_DISCOVERY_ONLY",actualApprovalDate:"2018-01-11",
  applicationNumber:"NDA123456",sponsorName:"Research Sponsor",
  fdaRecordUrl:"https://api.fda.gov/drug/drugsfda.json?search=NDA123456"}]};
test("first-public source findings validate without promoting historical market-cap or scores",()=>{
 const a=m.validateSourceLeads(primary);
 assert.equal(a.length,2);
 assert.ok(a.every(x=>x.historicalCapitalizationAtEntryVerified===false));
 assert.ok(a.every(x=>x.firstLocatedNotFirstEverPublicDisclosure===true));
 assert.ok(a.every(x=>x.nctIds.length>=1));
});
test("source-based event date mismatch is exposed for DBVT, without changing real PDUFA goal date",()=>{
 const r=m.consolidate({archiveCsv:archive,primaryLeads:primary,approvalDiscovery:fda,issuerCrosswalk,crlDiscovery});
 assert.equal(r.summary.archiveCandidates,126);
 assert.equal(r.summary.fdaApprovalLeads,1);
 assert.equal(r.summary.fdaCrlDocumentLeads,1);
 const crl=r.candidates.find(c=>c.source==="FDA_REDACTED_CRL_OUTCOME_DISCOVERY");
 assert.equal(crl.actualOutcome,"CRL");
 assert.equal(crl.pdufaTargetDate,null);
 assert.equal(crl.preDecisionInformationEligible,false);
 assert.equal(crl.eligibleForCalibration,false);
 assert.equal(r.coverage[2018].fdaArchivedCrlLeads,1);
 assert.equal(r.summary.primaryTargetSourceLeads,2);
 const dbvt=r.archiveTargetMismatches.find(x=>x.ticker==="DBVT");
 assert.ok(dbvt);
 assert.equal(dbvt.previouslyLabeledDate,"2020-08-03");
 assert.equal(dbvt.verifiedTargetDate,"2020-08-05");
 assert.equal(dbvt.actualActionDate,"2020-08-03");
 const kala=r.candidates.find(x=>x.primarySourceCaseId?.startsWith("KALA|EYSUVIS"));
 assert.ok(kala);assert.equal(kala.pdufaTargetDate,"2020-10-30");
 assert.equal(kala.actualFDAActionDate,"2020-10-26");
 assert.equal(kala.firstLocatedTargetDisclosureDate,"2020-05-26");
 assert.equal(r.summary.approvedRaasMetrics,0);
 assert.equal(r.summary.historicallyEligibleTrades,0);
 assert.ok(r.candidates.every(x=>x.eligibleForCalibration===false));
});
test("FDA action date is not used as PDUFA target date for legacy approval rows",()=>{
 const r=m.consolidate({archiveCsv:archive,primaryLeads:primary,approvalDiscovery:fda,issuerCrosswalk,crlDiscovery});
 const first=r.candidates.find(x=>x.source==="FDA_ORIGINAL_APPROVAL_DISCOVERY");
 assert.equal(first.actualFDAActionDate,"2018-01-11");
 assert.equal(first.pdufaTargetDate,null);
 assert.equal(first.ticker,"TEST");
 assert.equal(first.historicalIssuerIdentityVerified,false);
 assert.equal(r.summary.currentTickerNameMatchLeads,1);
 assert.equal(r.coverage[2018].completePdufaCensus,false);
});
test("invalid dates, duplicate case identity and false capitalization review status fail closed",()=>{
 assert.throws(()=>m.validateSourceLeads({...primary,records:[
  ...primary.records,{...primary.records[0]}]}),/RAAS_PRIMARY_EVENT_SOURCE_INVALID/);
 assert.throws(()=>m.validateSourceLeads({...primary,records:[
  {...primary.records[0],historicalCapitalizationAtEntryVerified:true}]}),/RAAS_PRIMARY_EVENT_SOURCE_INVALID/);
 assert.throws(()=>m.validateSourceLeads({...primary,records:[
  {...primary.records[0],targetAnnouncementDate:"2020-11-01"}]}),/RAAS_PRIMARY_EVENT_SOURCE_INVALID/);
 assert.throws(()=>m.consolidate({archiveCsv:archive,primaryLeads:primary,
   approvalDiscovery:{scope:"FDA_ACTIONS_CALIBRATED",candidates:[]},issuerCrosswalk,crlDiscovery}),/RAAS_FDA_ARCHIVE_INVALID/);
});

test("incomplete CRL archive does not create source-complete years or ex ante ratings",()=>{
 const r=m.consolidate({archiveCsv:archive,primaryLeads:primary,
  approvalDiscovery:fda,issuerCrosswalk,crlDiscovery});
 assert.equal(r.summary.fullCensusYears,0);
 assert.equal(r.summary.historicallyEligibleTrades,0);
 assert.equal(r.summary.approvedRaasMetrics,0);
 assert.equal(r.candidates.filter(x=>x.source==="FDA_REDACTED_CRL_OUTCOME_DISCOVERY").length,1);
 assert.ok(r.candidates.every(x=>x.eligibleForCalibration!==true));
 assert.throws(()=>m.consolidate({archiveCsv:archive,primaryLeads:primary,
  approvalDiscovery:fda,issuerCrosswalk,crlDiscovery:{...crlDiscovery,cases:[
   {...crlDiscovery.cases[0],preDecisionInformationEligible:true}]}}),
  /RAAS_FDA_CRL_ARCHIVE_INVALID/);
});
