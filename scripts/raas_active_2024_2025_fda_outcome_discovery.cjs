#!/usr/bin/env node
"use strict";
/**
 * OFFICIAL FDA 2024–2025 retrospective *outcome discovery*, not a PDUFA
 * target calendar and not approved RAAS trading evidence. Covers original
 * AND supplemental NDA/BLA approvals, and the FDA's INCOMPLETE redacted
 * historical CRL archive. A pending, withdrawn, late or unpublished CRL is
 * not ruled out by absence from either source.
 *
 * Crucially 2024 ARQT Zoryve atopic dermatitis was a SUPPL approval: never
 * falsely claim all programs are covered by ORIG-only FDA searches.
 */
const fs=require("node:fs"),path=require("node:path");
const oldApprovals=require("./raas_openfda_2016_2019_discovery.cjs");
const crlSource=require("./raas_openfda_historical_crl_discovery.cjs");
const root=path.resolve(__dirname,"..");
const YEARS=Object.freeze([2024,2025]);
const MAX_PAGES=80,LIMIT=99;
const SOURCE_URL="https://open.fda.gov/apis/drug/drugsfda/";
const appUrl=app=>"https://api.fda.gov/drug/drugsfda.json?"+
 new URLSearchParams({search:"application_number:"+app,limit:"1"});
const day8=s=>typeof s==="string"&&/^\d{8}$/.test(s)&&
 !Number.isNaN(Date.parse(s.slice(0,4)+"-"+s.slice(4,6)+"-"+s.slice(6)+"T00:00:00Z"))&&
 new Date(s.slice(0,4)+"-"+s.slice(4,6)+"-"+s.slice(6)+"T00:00:00Z").toISOString().slice(0,10)===
 s.slice(0,4)+"-"+s.slice(4,6)+"-"+s.slice(6);
const date8=s=>s.slice(0,4)+"-"+s.slice(4,6)+"-"+s.slice(6);
function buildUrl(year,skip=0){
 if(!YEARS.includes(year)||!Number.isInteger(skip)||skip<0||skip%LIMIT!==0)
  throw Error("RAAS_ACTIVE_FDA_QUERY_YEAR_OR_OFFSET_INVALID");
 const u=new URL("https://api.fda.gov/drug/drugsfda.json");
 // Query ANY approval outcome on the action date; do not restrict to ORIG:
 // original AND supplemental programs must be eligible for discovery.
 u.searchParams.set("search",
  "submissions.submission_status_date:["+year+"0101 TO "+year+"1231]"+
  " AND submissions.submission_status:AP");
 u.searchParams.set("limit",String(LIMIT));
 u.searchParams.set("skip",String(skip));
 return u.toString();
}
function extractFDAApprovals(applications,year){
 if(!YEARS.includes(year)||!Array.isArray(applications))
  throw Error("RAAS_ACTIVE_FDA_APPROVAL_SOURCE_INVALID");
 const seen=new Set(),rows=[];
 for(const a of applications){
  const app=String(a?.application_number||"").toUpperCase();
  if(!/^(NDA|BLA)\d{5,6}$/.test(app))continue;
  const names=[...(Array.isArray(a.products)?a.products:[]).map(p=>p.brand_name),
   ...(Array.isArray(a.openfda?.brand_name)?a.openfda.brand_name:[])]
   .filter(x=>typeof x==="string"&&x.trim());
  const productNames=[...new Set(names)].slice(0,15);
  const sponsorName=typeof a.sponsor_name==="string"?a.sponsor_name.trim():"";
  for(const s of Array.isArray(a.submissions)?a.submissions:[]){
   const type=String(s?.submission_type||"").toUpperCase();
   if(!["ORIG","SUPPL"].includes(type)||
    s?.submission_status!=="AP"||!day8(s.submission_status_date)||
    Number(s.submission_status_date.slice(0,4))!==year)continue;
   const submissionNumber=String(s.submission_number||"").trim();
   if(!/^\d{1,5}$/.test(submissionNumber))continue;
   const actionDate=date8(s.submission_status_date);
   const id=[app,type,submissionNumber,actionDate].join("|");
   if(seen.has(id))continue;
   seen.add(id);
   rows.push({id,applicationNumber:app,submissionType:type,
    submissionNumber,year,actualApprovalDate:actionDate,
    sponsorName,productNames,sourceUrl:appUrl(app),
    status:"FDA_APPROVAL_ACTION_DISCOVERY_ONLY",
    contemporaneousPdufaTargetDate:null,firstPublicTargetAnnouncementDate:null,
    phase3ReadoutFirstPublicDate:null,historicalIssuerTicker:null,
    independentMarketCapVerified:false,approvedHistoricalTrade:false,
    approvedRaasGrade:false,
    caveat:"FDA actual approval date is not a scheduled PDUFA target; supplementary approvals may represent separate indications or label changes. FDA outcome is retrospective."});
  }
 }
 return rows.sort((a,b)=>a.actualApprovalDate.localeCompare(b.actualApprovalDate)||
  a.applicationNumber.localeCompare(b.applicationNumber)||
  a.submissionType.localeCompare(b.submissionType)||
  a.submissionNumber.localeCompare(b.submissionNumber));
}
async function scanApprovalYear(year,request=fetch){
 if(!YEARS.includes(year))throw Error("RAAS_ACTIVE_FDA_YEAR_INVALID");
 const applications=[];let total=null,pages=0;
 for(let p=0;p<MAX_PAGES;p++){
  const skip=p*LIMIT;
  const result=await oldApprovals.fetchJson(buildUrl(year,skip),request);
  const size=result.meta.results.total;
  if(total===null)total=size;
  else if(total!==size)throw Error("RAAS_ACTIVE_FDA_PAGINATION_CHANGED");
  if(result.results.length===0&&skip<total)
   throw Error("RAAS_ACTIVE_FDA_EMPTY_PAGE_BEFORE_TOTAL");
  applications.push(...result.results);
  pages++;
  if(skip+result.results.length>=total){
   const rows=extractFDAApprovals(applications,year);
   return {year,status:"FDA_APPROVAL_DISCOVERY_ONLY",
    returnedApplicationRecords:applications.length,
    reportedQueryApplications:total,pages,approvalActions:rows,
    originalActions:rows.filter(x=>x.submissionType==="ORIG").length,
    supplementalActions:rows.filter(x=>x.submissionType==="SUPPL").length};
  }
 }
 throw Error("RAAS_ACTIVE_FDA_TOO_MANY_PAGES");
}
function synthesize({approvals,crls,sourceLeads,intake}){
 if(!Array.isArray(approvals)||approvals.length!==2||
  !YEARS.every(y=>approvals.some(x=>x.year===y&&x.status==="FDA_APPROVAL_DISCOVERY_ONLY"&&
   Array.isArray(x.approvalActions)&&Number.isInteger(x.reportedQueryApplications)))||
  crls?.scope!=="FDA_ARCHIVED_CRL_OUTCOMES_2016_2025_DISCOVERY_ONLY"||
  crls.status!=="FDA_CRL_DOCUMENTS_RETRIEVED_INCOMPLETE_EVENT_DENOMINATOR"||
  !Array.isArray(crls.cases)||
  sourceLeads?.scope!=="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH"||
  !Array.isArray(sourceLeads.records)||
  intake?.scope!=="RAAS_2024_2025_PDUFA_POINT_IN_TIME_INTAKE"||
  !Array.isArray(intake.yearAudits)||intake.yearAudits.length!==2||
  !YEARS.every(y=>intake.yearAudits.some(a=>a.year===y&&a.status==="NOT_AUDITED")))
  throw Error("RAAS_ACTIVE_FDA_SYNTHESIS_INPUT_INVALID");
 const fdaActions=approvals.flatMap(x=>x.approvalActions);
 const crlActions=crls.cases.filter(x=>YEARS.includes(x.year)&&
  x.actualFdaActionType==="CRL"&&x.eligibleForRaasCalibration===false);
 const known=sourceLeads.records.filter(x=>YEARS.includes(Number(x.pdufaTargetDate?.slice(0,4))));
 const knownByApplication=known.map(e=>{
  const number=/^(NDA|BLA)\s*(\d{5,6})/.exec(e.application||"");
  const normalized=number?number[1]+number[2]:null;
  const possible=fdaActions.filter(x=>x.applicationNumber===normalized&&
   x.actualApprovalDate===e.actualFDAActionDate);
  const matched=possible.filter(x=>{
   if(!e.application.includes("/")||x.submissionType!=="SUPPL")return true;
   const match=/\/S-?0*(\d+)/.exec(e.application);
   return match&&Number(x.submissionNumber)===Number(match[1]);
  });
  return {caseId:e.caseId,ticker:e.ticker,
   pdufaTargetDate:e.pdufaTargetDate,actualFDAActionDate:e.actualFDAActionDate,
   actualFDAOutcome:e.actualFDAOutcome,
   fdaApprovalDatabaseActionMatches:matched.map(x=>x.id),
   sourceConfidence:matched.length===1?
    "FDA_ACTION_DATE_AND_APPLICATION_DISCOVERY_MATCHED_OUTCOME_ONLY":
    matched.length===0?"FDA_ACTION_DISCOVERY_MATCH_MISSING":"AMBIGUOUS_MULTIPLE_ACTIONS",
   validatedTrade:false,completeFDAEventCensus:false};
 });
 const yearStats=YEARS.map(year=>{
  const a=approvals.find(x=>x.year===year);
  return {year,
   fdaApplicationRecordsReturned:a.returnedApplicationRecords,
   originalApprovalActions:a.originalActions,
   supplementalApprovalActions:a.supplementalActions,
   totalFdaApprovalActionLeads:a.approvalActions.length,
   archivedCRLLetterLeads:crlActions.filter(x=>x.year===year).length,
   independentlyLocatedOriginalPdufaTargets:known.filter(x=>x.pdufaTargetDate.startsWith(String(year))).length,
   completePdufaEventCensus:false,
   approvedHistoricalTrades:0,calibratedRaasMetrics:0};
 });
 return {schemaVersion:1,scope:"RAAS_ACTIVE_2024_2025_OFFICIAL_FDA_ACTION_DISCOVERY_NOT_CENSUS",
  status:"SOURCE_DISCOVERY_COMPLETE_FOR_OFFICIAL_ENDPOINTS_NOT_PDUFA_DENOMINATOR",
  studyYears:YEARS.slice(),
  actionYearIsNotPdufaTargetYear:true,
  officialFDAApprovalSource:SOURCE_URL,
  officialCRLArchiveSource:crls.sourceEndpoint,
  officialCRLArchiveUpdated:crls.sourceLastUpdated,
  years:yearStats,
  totalOriginalApprovalActions:yearStats.reduce((n,x)=>n+x.originalApprovalActions,0),
  totalSupplementalApprovalActions:yearStats.reduce((n,x)=>n+x.supplementalApprovalActions,0),
  totalRedactedArchiveCRLLetters:crlActions.length,
  fullFDAEventCensusYearsAudited:0,approvedHistoricalTrades:0,
  approvedRaasCalibrations:0,optimalTradingWindow:null,
  originalSourceLeadsCrosscheck:knownByApplication,
  approvalActionLeads:fdaActions,
  crlLetterLeads:crlActions,
  caveats:[
   "Regulatory action dates are NOT historically scheduled PDUFA target dates; action-year sampling alone cannot define the user's 2024–2025 target-year cohort.",
   "ORIG and SUPPL actions include products, indications and label changes not necessarily backed by a Phase 3 program; application numbers alone are not therapeutic opportunities.",
   "The FDA redacted CRL archive is selective and sometimes only published long after the original letter. An absent CRL is not an approval or a non-event.",
   "A complete PDUFA denominator also needs extensions, withdrawals, incomplete sponsor disclosure, private sponsors, failed reviews and delisted issuers.",
   "Historical FDA action matching does not verify exchange, shares, stock price, clinical phase, capital eligibility, return or RAAS scores.",
   "These rows are research leads only. Neither 2024 nor 2025 FDA event census is marked independently audited or complete."]};
}
async function execute({request=fetch,sourceLeads,intake}={}){
 const leads=sourceLeads||JSON.parse(fs.readFileSync(path.join(root,
  "new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json"),"utf8"));
 const approved=intake||JSON.parse(fs.readFileSync(path.join(root,
  "new-platform/frontend/data/raas-active-2024-2025-pdufa-intake.json"),"utf8"));
 // A failure must fail the whole census-discovery job: do not quietly
 // use only the year or the first CRL page that happened to succeed.
 const approvals=[];
 for(const year of YEARS)approvals.push(await scanApprovalYear(year,request));
 const crls=await crlSource.execute({request});
 return synthesize({approvals,crls,sourceLeads:leads,intake:approved});
}
async function main(){
 try{
  const result=await execute();
  const dest=process.env.RAAS_ACTIVE_FDA_OUTCOME_DISCOVERY_OUTPUT||
   path.join(root,"raas-active-2024-2025-fda-outcome-discovery.json");
  fs.mkdirSync(path.dirname(dest),{recursive:true});
  fs.writeFileSync(dest,JSON.stringify(result,null,2)+"\n");
  const summary={status:result.status,years:result.years,
   approvedHistoricalTrades:result.approvedHistoricalTrades,
   approvedRaasCalibrations:result.approvedRaasCalibrations,
   completeCensusYears:result.fullFDAEventCensusYearsAudited,
   knownPrograms:result.originalSourceLeadsCrosscheck};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### ACTIVE 2024–2025 FDA original, supplemental approval and redacted CRL discovery (NOT census)\n\n"+
   JSON.stringify(summary,null,2)+"\n\n0 independently verified trading cases/RAAS calibrations.\n");
 }catch(err){
  console.error("RAAS_ACTIVE_FDA_ACTION_FATAL_"+
   String(err.message||err).replace(/[^A-Z0-9_]/g,"_"));
  process.exitCode=1;
 }
}
if(require.main===module)main();
module.exports={buildUrl,extractFDAApprovals,scanApprovalYear,synthesize,execute};
