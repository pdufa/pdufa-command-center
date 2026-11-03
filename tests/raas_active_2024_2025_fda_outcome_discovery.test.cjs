"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const m=require("../scripts/raas_active_2024_2025_fda_outcome_discovery.cjs");
const sources=require("../new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json");
const intake=require("../new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json");
const x=(app,type,num,dt,brand)=>({
 application_number:app,sponsor_name:app==="NDA215985"?"ARCUTIS":app==="NDA217785"?"MADRIGAL":"AXSOME",
 products:[{brand_name:brand}],submissions:[
  {submission_type:type,submission_number:num,
   submission_status:"AP",submission_status_date:dt}]
});
const ARQT=x("NDA215985","SUPPL","007","20240709","ZORYVE");
const MDGL=x("NDA217785","ORIG","1","20240314","REZDIFFRA");
const AXSM=x("NDA215431","ORIG","1","20250130","SYMBRAVO");
const crl=(date,app,file)=>({
 letter_type:"COMPLETE RESPONSE",letter_date:date,
 application_number:[app],company_name:"Issuer",file_name:file});
const crlRecords=[crl("08/07/2024","NDA 212345","a.pdf"),
 crl("06/01/2025","BLA 123456","b.pdf"),
 crl("09/10/2023","NDA 211111","c.pdf")];
const payload=(results,total)=>({ok:true,status:200,headers:{get:()=>"application/json"},
 text:async()=>JSON.stringify({meta:{results:{total},last_updated:"2026-10-05"},results})});
function request(url){
 const u=new URL(url);
 assert.equal(u.hostname,"api.fda.gov");
 if(u.pathname==="/transparency/crl.json")
  return Promise.resolve(payload(crlRecords,crlRecords.length));
 assert.equal(u.pathname,"/drug/drugsfda.json");
 const query=u.searchParams.get("search");
 assert.match(query,/submission_status:AP/);
 assert.doesNotMatch(query,/submission_type:ORIG/);
 if(query.includes("20240101 TO 20241231"))return Promise.resolve(payload([ARQT,MDGL],2));
 if(query.includes("20250101 TO 20251231"))return Promise.resolve(payload([AXSM],1));
 throw Error("Unexpected FDA year query "+query);
}
test("2024 and 2025 endpoint queries include supplemental as well as original NDA/BLA approval actions",()=>{
 for(const year of [2024,2025]){
  const url=new URL(m.buildUrl(year));
  assert.equal(url.origin,"https://api.fda.gov");
  assert.equal(url.pathname,"/drug/drugsfda.json");
  assert.match(url.searchParams.get("search"),new RegExp(year+"0101 TO "+year+"1231"));
  assert.equal(url.searchParams.get("limit"),"99");
 }
 assert.throws(()=>m.buildUrl(2020),/QUERY_YEAR_OR_OFFSET_INVALID/);
 assert.throws(()=>m.buildUrl(2024,11),/QUERY_YEAR_OR_OFFSET_INVALID/);
});
test("separately identify 2024 Zoryve supplemental approval and 2025 Symbravo original approval",()=>{
 const records=m.extractFDAApprovals([ARQT,AXSM,ARQT,
  x("ANDA012345","ORIG","1","20240709","Generic"),
  x("NDA111111","SUPPL","002","20250709","Wrong year"),
  x("NDA333333","SUPPL","bad","20240709","Bad number"),
  x("NDA444444","ORIG","1","20240231","Bad day")],2024);
 assert.equal(records.length,1);
 assert.equal(records[0].id,"NDA215985|SUPPL|007|2024-07-09");
 assert.equal(records[0].status,"FDA_APPROVAL_ACTION_DISCOVERY_ONLY");
 assert.equal(records[0].contemporaneousPdufaTargetDate,null);
 assert.equal(records[0].independentMarketCapVerified,false);
 assert.equal(records[0].approvedHistoricalTrade,false);
 const later=m.extractFDAApprovals([ARQT,AXSM],2025);
 assert.equal(later.length,1);
 assert.equal(later[0].id,"NDA215431|ORIG|1|2025-01-30");
});
test("fully page FDA original AND supplementary approvals without silently truncating",async()=>{
 let calls=[];
 const first=Array.from({length:99},(_,i)=>x("NDA"+String(i+200000),"ORIG","1","20240709","Test"));
 const res=await m.scanApprovalYear(2024,async url=>{
  const q=new URL(url),skip=Number(q.searchParams.get("skip"));calls.push(skip);
  return payload(skip===0?first:[ARQT],100);
 });
 assert.deepEqual(calls,[0,99]);
 assert.equal(res.reportedQueryApplications,100);
 assert.equal(res.returnedApplicationRecords,100);
 assert.equal(res.pages,2);
 assert.equal(res.originalActions,99);
 assert.equal(res.supplementalActions,1);
 assert.equal(res.approvalActions.length,100);
 await assert.rejects(m.scanApprovalYear(2024,async url=>{
  const skip=Number(new URL(url).searchParams.get("skip"));
  return payload(skip===0?first:[],100);
 }),/EMPTY_PAGE_BEFORE_TOTAL/);
 await assert.rejects(m.scanApprovalYear(2024,async url=>{
  const skip=Number(new URL(url).searchParams.get("skip"));
  return payload(skip===0?first:[ARQT],skip===0?100:101);
 }),/PAGINATION_CHANGED/);
});
test("official FDA original and supplemental approval leads PLUS redacted CRLs remain research only",async()=>{
 const result=await m.execute({request,sourceLeads:sources,intake});
 assert.equal(result.status,"SOURCE_DISCOVERY_COMPLETE_FOR_OFFICIAL_ENDPOINTS_NOT_PDUFA_DENOMINATOR");
 assert.deepEqual(result.studyYears,[2024,2025]);
 assert.equal(result.totalOriginalApprovalActions,2);
 assert.equal(result.totalSupplementalApprovalActions,1);
 assert.equal(result.totalRedactedArchiveCRLLetters,2);
 assert.equal(result.years[0].supplementalApprovalActions,1);
 assert.equal(result.years[1].originalApprovalActions,1);
 assert.equal(result.years[0].archivedCRLLetterLeads,1);
 assert.equal(result.years[1].archivedCRLLetterLeads,1);
 assert.equal(result.originalSourceLeadsCrosscheck.length,3);
 const mdgl=result.originalSourceLeadsCrosscheck.find(x=>x.ticker==="MDGL");
 assert.deepEqual(mdgl.fdaApprovalDatabaseActionMatches,["NDA217785|ORIG|1|2024-03-14"]);
 assert.equal(mdgl.pdufaTargetDate,"2024-03-14");
 assert.equal(mdgl.actualFDAActionDate,"2024-03-14");
 const a=result.originalSourceLeadsCrosscheck.find(x=>x.ticker==="ARQT");
 const b=result.originalSourceLeadsCrosscheck.find(x=>x.ticker==="AXSM");
 assert.deepEqual(a.fdaApprovalDatabaseActionMatches,["NDA215985|SUPPL|007|2024-07-09"]);
 assert.deepEqual(b.fdaApprovalDatabaseActionMatches,["NDA215431|ORIG|1|2025-01-30"]);
 assert.equal(a.pdufaTargetDate,"2024-07-07");
 assert.equal(a.actualFDAActionDate,"2024-07-09");
 assert.equal(b.pdufaTargetDate,"2025-01-31");
 assert.equal(b.actualFDAActionDate,"2025-01-30");
 assert.equal(result.fullFDAEventCensusYearsAudited,0);
 assert.equal(result.approvedHistoricalTrades,0);
 assert.equal(result.approvedRaasCalibrations,0);
 assert.equal(result.optimalTradingWindow,null);
 assert.ok(result.approvalActionLeads.every(x=>x.contemporaneousPdufaTargetDate===null));
 assert.ok(result.crlLetterLeads.every(x=>x.originalPublicCRLDisclosureDate===null));
});
test("reject fake census completion, partial FDA query years, and unauthorized CRL inferred approvals",async()=>{
 const r=await m.execute({request,sourceLeads:sources,intake});
 const bad=structuredClone(intake);
 bad.yearAudits[0].status="FULL_EVENT_CENSUS_AUDITED";
 assert.throws(()=>m.synthesize({
  approvals:[{year:2024,status:"FDA_APPROVAL_DISCOVERY_ONLY",
   approvalActions:[],reportedQueryApplications:1,originalActions:0,supplementalActions:0},
   {year:2025,status:"FDA_APPROVAL_DISCOVERY_ONLY",
   approvalActions:[],reportedQueryApplications:1,originalActions:0,supplementalActions:0}],
  crls:{scope:"FDA_ARCHIVED_CRL_OUTCOMES_2016_2025_DISCOVERY_ONLY",
   status:"FDA_CRL_DOCUMENTS_RETRIEVED_INCOMPLETE_EVENT_DENOMINATOR",cases:[]},
  sourceLeads:sources,intake:bad}),/SYNTHESIS_INPUT_INVALID/);
 assert.ok(r.caveats.some(x=>x.includes("NOT historically scheduled PDUFA")));
 await assert.rejects(m.execute({request:async url=>{
  if(new URL(url).pathname==="/drug/drugsfda.json"&&
   new URL(url).searchParams.get("search").includes("20250101"))
   return {ok:false,status:403};
  return request(url);
 },sourceLeads:sources,intake}),/OPENFDA_HTTP_403/);
 await assert.rejects(m.execute({request:async url=>{
  if(new URL(url).pathname==="/transparency/crl.json")
   return {ok:false,status:403};
  return request(url);
 },sourceLeads:sources,intake}),/RAAS_CRL_HTTP_403/);
});
