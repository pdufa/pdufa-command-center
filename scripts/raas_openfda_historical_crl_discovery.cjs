#!/usr/bin/env node
"use strict";
/**
 * Official FDA historic complete-response-letter archive discovery.
 *
 * CRLs are FDA outcome documents. FDA began proactive historical publication
 * years after some original action dates, so the *letter date* is NEVER
 * the date its text became public or an eligible entry-time RAAS feature.
 * This archive is incomplete and must not replace an FDA PDUFA event census.
 * Only explicit "COMPLETE RESPONSE" letter types count as CRL outcomes.
 */
const fs=require("node:fs"),path=require("node:path");
const API="https://api.fda.gov/transparency/crl.json";
const ROOT=path.resolve(__dirname,"..");
const LIMIT=50,MAX_PAGES=30,MAX_BODY=16000000;
const wait=ms=>new Promise(ok=>setTimeout(ok,ms));
function parseLetterDate(s) {
 if(typeof s!=="string")return null;
 const m=/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s);
 if(!m)return null;
 const y=+m[3],month=+m[1],d=+m[2];
 if(y<1900||y>2100||month<1||month>12||d<1||d>31)return null;
 const date=[m[3],String(month).padStart(2,"0"),String(d).padStart(2,"0")].join("-");
 return new Date(date+"T00:00:00Z").toISOString().slice(0,10)===date?date:null;
}
function applicationNumber(s) {
 const m=/^(NDA|BLA)\s*(\d{5,7})$/i.exec(String(s||"").trim());
 return m?m[1].toUpperCase()+" "+m[2]:null;
}
function linkForApplication(app) {
 const u=new URL(API);
 u.searchParams.set("search",'application_number:"'+app+'"');
 u.searchParams.set("limit","50");
 return u.toString();
}
function parseCRLRecords(records) {
 if(!Array.isArray(records))throw Error("RAAS_CRL_RESULTS_INVALID");
 const out=[],seen=new Set();
 let nonCrl=0,unparseable=0,otherYears=0;
 for(const record of records){
  if(!record || typeof record!=="object"){unparseable++;continue;}
  if(String(record.letter_type||"").trim().toUpperCase()!=="COMPLETE RESPONSE"){
   nonCrl++;continue;
  }
  const date=parseLetterDate(record.letter_date);
  if(!date){unparseable++;continue;}
  const y=Number(date.slice(0,4));
  if(y<2016||y>2025){otherYears++;continue;}
  const apps=(Array.isArray(record.application_number)?
   record.application_number:[record.application_number])
   .map(applicationNumber).filter(Boolean);
  const unique=[...new Set(apps)];
  if(!unique.length){unparseable++;continue;}
  const fileName=String(record.file_name||"").trim().slice(0,160);
  const sponsor=String(record.company_name||"").trim().slice(0,160);
  for(const app of unique) {
   const id=[app,date,fileName||"NO_FILE_NAME",sponsor||"NO_COMPANY_NAME"].join("|");
   if(seen.has(id))continue;
   seen.add(id);
   out.push({caseId:id,applicationNumber:app,letterDate:date,year:y,
    letterType:"COMPLETE RESPONSE",companyName:sponsor||null,
    filename:fileName||null,sourceUrl:linkForApplication(app),
    status:"FDA_REDACTED_CRL_OUTCOME_RESEARCH_ONLY",
    actualFdaActionType:"CRL",
    originalPdufaTargetDate:null,firstPublicPdufaAnnouncementDate:null,
    originalPublicCRLDisclosureDate:null,
    currentIssuerTicker:null,preDecisionInformationEligible:false,
    marketCapAtEntryVerified:false,phase3FirstPublicDate:null,
    eligibleForRaasCalibration:false,
    reason:"Retrospective CRL outcome; initial public disclosure and trading eligibility not independently dated."});
  }
 }
 out.sort((a,b)=>a.letterDate.localeCompare(b.letterDate)||
  a.applicationNumber.localeCompare(b.applicationNumber)||a.caseId.localeCompare(b.caseId));
 return {records:out,nonCrl,unparseable,otherYears};
}
async function getPage(skip,request=fetch){
 const u=new URL(API);
 u.searchParams.set("limit",String(LIMIT));
 u.searchParams.set("skip",String(skip));
 let res;
 for(let attempt=0;attempt<4;attempt++){
  try{
   res=await request(u.toString(),{headers:{Accept:"application/json"},
    redirect:"error",signal:AbortSignal.timeout(25000)});
  }catch(e){
   if(attempt===3)throw Error("RAAS_CRL_NETWORK_FAILED");
   await wait(300*(attempt+1));continue;
  }
  if(res.status===429||res.status>=500){
   if(attempt===3)throw Error("RAAS_CRL_UPSTREAM_HTTP_"+res.status);
   await wait(450*(attempt+1));continue;
  }
  if(!res.ok)throw Error("RAAS_CRL_HTTP_"+res.status);
  break;
 }
 const txt=await res.text();
 if(txt.length>MAX_BODY)throw Error("RAAS_CRL_PAGE_TOO_LARGE");
 let body;
 try{body=JSON.parse(txt);}catch(e){throw Error("RAAS_CRL_JSON_INVALID");}
 if(!body||!Array.isArray(body.results)||
  !Number.isSafeInteger(body.meta?.results?.total)||
  body.meta.results.total<0)throw Error("RAAS_CRL_PAGE_SCHEMA_INVALID");
 return {records:body.results,total:body.meta.results.total,
  sourceLastUpdated:typeof body.meta?.last_updated==="string"?body.meta.last_updated:null};
}
async function execute({request=fetch}={}){
 let total=null,lastUpdated=null;
 const records=[];
 let complete=false,pages=0;
 for(let i=0;i<MAX_PAGES;i++){
  const data=await getPage(i*LIMIT,request);
  if(total===null)total=data.total;
  else if(data.total!==total)throw Error("RAAS_CRL_PAGINATION_CHANGED");
  if(lastUpdated===null)lastUpdated=data.sourceLastUpdated;
  else if(lastUpdated!==data.sourceLastUpdated)throw Error("RAAS_CRL_SOURCE_VERSION_CHANGED");
  records.push(...data.records);
  pages++;
  if(records.length>=total){complete=true;break;}
  if(!data.records.length)throw Error("RAAS_CRL_INCOMPLETE_EMPTY_PAGE");
  await wait(250);
 }
 if(!complete||records.length!==total)throw Error("RAAS_CRL_INCOMPLETE_SOURCE_PAGINATION");
 const parsed=parseCRLRecords(records);
 const counts=Object.fromEntries(Array.from({length:10},(_,i)=>{
  const y=i+2016;
  return [y,parsed.records.filter(x=>x.year===y).length];
 }));
 return {schemaVersion:1,
  scope:"FDA_ARCHIVED_CRL_OUTCOMES_2016_2025_DISCOVERY_ONLY",
  status:"FDA_CRL_DOCUMENTS_RETRIEVED_INCOMPLETE_EVENT_DENOMINATOR",
  sourceEndpoint:API,sourceDocumentationUrl:"https://open.fda.gov/apis/transparency/completeresponseletters/",
  sourceLastUpdated:lastUpdated,sourceRecordsFetched:total,
  sourcePagesFetched:pages,
  crlApplicationLetterLeads:parsed.records.length,
  archiveNonCrlLetterTypes:parsed.nonCrl,
  archiveOutsideStudyYears:parsed.otherYears,
  archiveUnparseableRows:parsed.unparseable,
  countsByLetterYear:counts,
  cases:parsed.records,
  limits:[
   "Redacted FDA CRLs cover a retrospective, incomplete selection of regulatory outcomes; missing CRL does not imply approval.",
   "Letter date is the date on the FDA correspondence, NOT the date the agency published it publicly.",
   "FDA started proactive publication of batches of older letters in 2025; never use those contents as a pre-2025 model feature.",
   "Application identity does not establish ticker, Phase 3 readout, PDUFA target or entry-day historical market cap.",
   "CRLs here are independent outcome leads, not a complete 2016-2025 PDUFA or investment universe.",
   "No source lead can become an approved RAAS grade or historical profit observation without independent source review."
  ]};
}
if(require.main===module){
 execute().then(x=>{
  const file=process.env.RAAS_FDA_CRL_OUTPUT||
   path.join(ROOT,"raas-fda-historical-crl-discovery.json");
  fs.writeFileSync(file,JSON.stringify(x,null,2)+"\n");
  const s={status:x.status,sourceRecordsFetched:x.sourceRecordsFetched,
   crlApplicationLetterLeads:x.crlApplicationLetterLeads,
   archiveUnparseableRows:x.archiveUnparseableRows,countsByLetterYear:x.countsByLetterYear};
  process.stdout.write(JSON.stringify(s)+"\n");
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### Original FDA CRL documents — outcome discovery only\n\n"+
   JSON.stringify(s)+"\n\nNo backtest or predecision scoring eligibility granted.\n");
 }).catch(e=>{process.stderr.write("RAAS_CRL_FATAL_"+String(e.message)+"\n");process.exitCode=1;});
}
module.exports={parseLetterDate,applicationNumber,parseCRLRecords,getPage,execute};
