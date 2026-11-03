#!/usr/bin/env node
"use strict";
/**
 * Official FDA 2016–2019 approval discovery ONLY.
 * Drugs@FDA/openFDA does not establish historically known PDUFA target dates,
 * CRLs/withdrawals, Phase 3 readout timing or publicly traded issuer identity.
 * These rows MUST NOT enter RAAS trade eligibility or RAAS score calibration.
 */
const fs=require("node:fs"),path=require("node:path");
const BASE="https://api.fda.gov/drug/drugsfda.json";
const YEARS=[2016,2017,2018,2019];
const LIMIT=99,MAX_PAGES=200;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const ymd=s=>typeof s==="string" && /^\d{8}$/.test(s) &&
 !Number.isNaN(Date.parse(s.slice(0,4)+"-"+s.slice(4,6)+"-"+s.slice(6)+"T00:00:00Z")) &&
 new Date(s.slice(0,4)+"-"+s.slice(4,6)+"-"+s.slice(6)+"T00:00:00Z")
  .toISOString().slice(0,10)===s.slice(0,4)+"-"+s.slice(4,6)+"-"+s.slice(6);
const sourceUrl=application=>"https://api.fda.gov/drug/drugsfda.json?"+
 new URLSearchParams({search:"application_number:"+application,limit:"1"});
function extract(records,year){
 const out=[],seen=new Set();
 for(const a of records) {
  const app=String(a?.application_number||"").toUpperCase();
  if(!/^(NDA|BLA)\d{5,6}$/.test(app))continue;
  const names=[...(Array.isArray(a.products)?a.products:[]).map(p=>p.brand_name),
   ...(a.openfda?.brand_name||[])].filter(s=>typeof s==="string"&&s.trim());
  const products=[...new Set(names)].slice(0,15);
  const sponsor=typeof a.sponsor_name==="string"?a.sponsor_name.trim():"";
  for(const s of Array.isArray(a.submissions)?a.submissions:[]){
   if(s?.submission_type!=="ORIG" || s?.submission_status!=="AP" ||
    !ymd(s.submission_status_date) || +s.submission_status_date.slice(0,4)!==year)
    continue;
   const number=String(s.submission_number||"").trim();
   const id=app+"|ORIG|"+number+"|"+s.submission_status_date;
   if(seen.has(id))continue;
   seen.add(id);
   out.push({id,applicationNumber:app,submissionNumber:number,
    year,actualApprovalDate:s.submission_status_date.slice(0,4)+"-"+
      s.submission_status_date.slice(4,6)+"-"+s.submission_status_date.slice(6),
    sponsorName:sponsor,productNames:products,
    fdaRecordUrl:sourceUrl(app),
    status:"FDA_APPROVAL_DISCOVERY_ONLY",
    historicalPdufaTargetDate:null,historicalTargetFirstPublicDate:null,
    phase3FirstPublicDate:null,listedIssuerTicker:null,historicalMarketCapMillions:null,
    notes:"FDA approval observed retrospectively. No contemporaneous PDUFA trading event proven."});
  }
 }
 return out.sort((a,b)=>a.actualApprovalDate.localeCompare(b.actualApprovalDate)||
  a.applicationNumber.localeCompare(b.applicationNumber));
}
function buildUrl(year,skip){
 const u=new URL(BASE);
 u.searchParams.set("search",
  "submissions.submission_status_date:["+year+"0101 TO "+year+"1231]"+
  " AND submissions.submission_status:AP AND submissions.submission_type:ORIG");
 u.searchParams.set("limit",String(LIMIT));
 u.searchParams.set("skip",String(skip));
 return u.toString();
}
async function fetchJson(url,request=fetch){
 for(let i=0;i<4;i++){
  let res;
  try {res=await request(url,{headers:{Accept:"application/json"},
    signal:AbortSignal.timeout(25000),redirect:"error"});}
  catch(e){if(i===3)throw Error("OPENFDA_NETWORK_FAILED");await pause(500*(i+1));continue;}
  if(res.status===429 || res.status>=500){
   if(i===3)throw Error("OPENFDA_HTTP_"+res.status);
   await pause(1000*(i+1));continue;
  }
  if(!res.ok)throw Error("OPENFDA_HTTP_"+res.status);
  const body=await res.text();
  if(body.length>12000000)throw Error("OPENFDA_RESPONSE_TOO_LARGE");
  const parsed=JSON.parse(body);
  if(!parsed||!Array.isArray(parsed.results)||!Number.isSafeInteger(parsed.meta?.results?.total))
   throw Error("OPENFDA_PAYLOAD_INVALID");
  return parsed;
 }
 throw Error("OPENFDA_RETRIES_EXHAUSTED");
}
async function scanYear(year,request=fetch){
 if(!YEARS.includes(year))throw Error("OPENFDA_YEAR_INVALID");
 const pages=[];let total=null;
 for(let page=0;page<MAX_PAGES;page++){
  const skip=page*LIMIT;
  const obj=await fetchJson(buildUrl(year,skip),request);
  if(total===null)total=obj.meta.results.total;
  if(obj.meta.results.total!==total)throw Error("OPENFDA_PAGINATION_TOTAL_CHANGED");
  pages.push(...obj.results);
  if(skip+obj.results.length>=total) {
   return {year,status:"FDA_ORIGINAL_APPROVAL_DISCOVERY_ONLY",applicationsSearched:pages.length,
    candidates:extract(pages,year),pages:page+1,reportedMatchingApplications:total};
  }
  if(obj.results.length===0)throw Error("OPENFDA_EMPTY_PAGE_WITH_REMAINING_RESULTS");
 }
 throw Error("OPENFDA_PAGE_LIMIT_EXCEEDED");
}
async function run({request=fetch,years=YEARS}={}){
 const results=[],failures=[];
 for(const year of years){
  try{results.push(await scanYear(year,request));}
  catch(e){failures.push({year,status:"DISCOVERY_FAILED",
   reason:String(e.message).replace(/[^A-Z0-9_]/g,"_").slice(0,80)});}
 }
 return {scope:"FDA_DRUGS_AT_FDA_2016_2019_APPROVAL_DISCOVERY_NOT_PDUFA_CENSUS",
  status:failures.length?"PARTIAL_OR_FAILED":"FDA_APPROVAL_LEADS_COLLECTED",
  source:"https://open.fda.gov/apis/drug/drugsfda/",
  limitations:[
   "Only original FDA-approved NDA/BLA submissions are enumerated; CRLs, withdrawals, and nonapproval events are absent.",
   "The FDA action date is NOT the historically published PDUFA target date. Never substitute one for the other.",
   "FDA sponsor is not necessarily a public company's listed issuer or rights holder.",
   "No historic capitalization, Phase 3 first-public date, or contemporaneous entry-time notice has been established.",
   "No generated candidate may populate a validated RAAS score or recommended trading window."],
  researchedYears:years,completedYears:results.map(r=>r.year),
  totalApplicationsSearched:results.reduce((n,r)=>n+r.applicationsSearched,0),
  approvalCandidates:results.reduce((n,r)=>n+r.candidates.length,0),
  yearStats:results.map(r=>({year:r.year,candidates:r.candidates.length,
   matchingApplications:r.reportedMatchingApplications,pages:r.pages})),
  failures,candidates:results.flatMap(r=>r.candidates)};
}
if(require.main===module){
 run().then(x=>{
  const output=process.env.RAAS_FDA_BACKFILL_OUTPUT||
   path.join(__dirname,"..","raas-fda-2016-2019-discovery.json");
  fs.writeFileSync(output,JSON.stringify(x,null,2)+"\n");
  const headline={status:x.status,years:x.completedYears,
   approvalCandidates:x.approvalCandidates,failures:x.failures,
   output};
  process.stdout.write(JSON.stringify(headline)+"\n");
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
    "### FDA 2016-2019 original-approval discovery (NOT PDUFA target dates)\n\n"+
    JSON.stringify(headline)+"\n\nNo results qualify as a RAAS trade or prediction.\n");
  if(x.failures.length)process.exitCode=1;
 }).catch(e=>{process.stderr.write("OPENFDA_FATAL_"+e.message+"\n");process.exitCode=1;});
}
module.exports={extract,buildUrl,fetchJson,scanYear,run};
