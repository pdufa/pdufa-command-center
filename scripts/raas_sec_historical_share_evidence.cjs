#!/usr/bin/env node
"use strict";
/** Point-in-time SEC cover-share evidence collection for archived PDUFA
 * discovery events. Shares are NOT entry market capitalization, a verified
 * historical listing, diluted shares or a complete trade qualification.
 */
const fs=require("node:fs"),path=require("node:path");
const {rows:parseCsv}=require("./raas_match_fda_2016_2019_sponsors.cjs");
const {candidateQueue}=require("./raas_alpaca_ten_year_study.cjs");
const root=path.resolve(__dirname,"..");
const leadDays=[90,79,60,45,30,21,14,7,3];
const ms=86400000;
const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const minus=(d,n)=>new Date(Date.parse(d+"T00:00:00Z")-n*ms).toISOString().slice(0,10);
const cikOk=s=>typeof s==="string"&&/^\d{1,10}$/.test(s);
const cik10=s=>s.padStart(10,"0");
const urlFor=cik=>"https://data.sec.gov/api/xbrl/companyconcept/CIK"+
 cik10(cik)+"/dei/EntityCommonStockSharesOutstanding.json";
function issuers(csv) {
 const map=new Map(),duplicate=new Set();
 for(const r of parseCsv(csv)) {
  if(r.status!=="OK"||!/^[A-Z][A-Z0-9.-]{0,11}$/.test(r.ticker))continue;
  const cik=String(r.cik10||"").trim();
  if(!cikOk(cik))continue;
  if(map.has(r.ticker) && map.get(r.ticker).cik!==cik10(cik))
   duplicate.add(r.ticker);
  else map.set(r.ticker,{ticker:r.ticker,cik:cik10(cik),company:r.company,exchange:r.exchange});
 }
 for(const key of duplicate)map.delete(key);
 return {map,conflicts:[...duplicate].sort()};
}
function sourceFacts(payload,cik) {
 if(!payload||typeof payload!=="object"||String(payload.cik||"").padStart(10,"0")!==cik10(cik))
  throw Error("SEC_COMPANY_IDENTITY_MISMATCH");
 const units=payload.units?.shares;
 if(!Array.isArray(units))throw Error("SEC_SHARES_NOT_DISCLOSED");
 const out=[];
 for(const f of units){
  if(!f||!date(f.filed)||!date(f.end)||f.filed<f.end||
   !Number.isSafeInteger(f.val)||f.val<=0||
   !/^(10-K|10-Q|10-K\/A|10-Q\/A|20-F|20-F\/A|40-F|40-F\/A)$/.test(f.form||"")||
   !/^\d{10}-\d{2}-\d{6}$/.test(f.accn||""))continue;
  out.push({filed:f.filed,measurementDate:f.end,shares:f.val,
   accession:f.accn,form:f.form,sourceUrl:
    "https://www.sec.gov/Archives/edgar/data/"+String(Number(cik))+"/"+
     f.accn.replace(/-/g,"")+"/"});
 }
 return out;
}
function latestVisible(facts,entryDate) {
 if(!date(entryDate))throw Error("SEC_ASOF_DATE_INVALID");
 const candidates=facts.filter(f=>f.filed<=entryDate&&f.measurementDate<=entryDate&&
  (Date.parse(entryDate+"T00:00:00Z")-Date.parse(f.measurementDate+"T00:00:00Z"))/ms<=550);
 candidates.sort((a,b)=>b.filed.localeCompare(a.filed)||
  b.measurementDate.localeCompare(a.measurementDate)||
  b.accession.localeCompare(a.accession));
 if(!candidates.length)return null;
 const first=candidates[0];
 // A given report may have multiple share-class / amended conflicts. Mark
 // conflicting facts ambiguous instead of picking whichever number is first.
 const contemporaneous=candidates.filter(x=>x.filed===first.filed&&
  x.measurementDate===first.measurementDate);
 if(new Set(contemporaneous.map(x=>x.shares)).size>1)
  return {status:"MULTIPLE_SHARE_VALUES_REQUIRE_CLASS_REVIEW",
   filed:first.filed,measurementDate:first.measurementDate,values:contemporaneous.length,
   sourceUrls:[...new Set(contemporaneous.map(x=>x.sourceUrl))]};
 return {status:"SEC_PUBLIC_COVER_SHARES_RESEARCH_ONLY",...first,
  staleDays:Math.round((Date.parse(entryDate+"T00:00:00Z")-Date.parse(first.measurementDate+"T00:00:00Z"))/ms),
  historicShareClassVerified:false,adsRatioVerified:false,fullyDiluted:false,
  marketCapAtEntryVerified:false};
}
async function getFacts(cik,request=fetch){
 const url=urlFor(cik);
 let resp;
 try {resp=await request(url,{
  headers:{"User-Agent":"PDUFA-Command-Center research https://github.com/pdufa/pdufa-command-center","Accept":"application/json"},
  redirect:"error",signal:AbortSignal.timeout(18000)});
 } catch(e){throw Error("SEC_NETWORK_UNAVAILABLE");}
 if(!resp.ok)throw Error("SEC_HTTP_"+resp.status);
 const t=await resp.text();
 if(t.length>12000000)throw Error("SEC_RESPONSE_TOO_LARGE");
 let o;
 try{o=JSON.parse(t);}catch(e){throw Error("SEC_JSON_INVALID");}
 return sourceFacts(o,cik);
}
async function execute({archiveCsv,registryCsv,request=fetch,maxIssuers=150,pause=ms=>new Promise(ok=>setTimeout(ok,ms))}={}){
 if(!archiveCsv)archiveCsv=fs.readFileSync(path.join(root,"data/historical_assessed_decisions.csv"),"utf8");
 if(!registryCsv)registryCsv=fs.readFileSync(path.join(root,"data/company_registry.csv"),"utf8");
 const discovery=candidateQueue(archiveCsv);
 const index=issuers(registryCsv),symbols=[...new Set(discovery.map(x=>x.ticker))].sort();
 const limit=Math.max(0,Math.min(150,Math.floor(maxIssuers)));
 const selected=symbols.filter(t=>index.map.has(t)).slice(0,limit);
 const factMap=new Map(),requests=[];
 let consecutiveAccessDenied=0,accessDeniedCircuitOpen=false;
 for(const ticker of selected){
  const cik=index.map.get(ticker).cik;
  if(accessDeniedCircuitOpen){
   requests.push({ticker,cik,status:"NOT_ATTEMPTED_SOURCE_ACCESS_DENIED",
    reason:"SEC_API_HTTP_403_CIRCUIT_OPEN",sourceUrl:urlFor(cik)});
   continue;
  }
  try{
   const facts=await getFacts(cik,request);
   consecutiveAccessDenied=0;
   factMap.set(ticker,facts);
   requests.push({ticker,cik,status:facts.length?"SHARE_FACTS_RECEIVED":"NO_USABLE_SEC_COVER_SHARES",
    facts:facts.length,sourceUrl:urlFor(cik)});
  }catch(e){
   const reason=String(e.message);
   if(reason==="SEC_HTTP_403")consecutiveAccessDenied++;
   else consecutiveAccessDenied=0;
   requests.push({ticker,cik,status:"SEC_SOURCE_UNAVAILABLE",reason,
    sourceUrl:urlFor(cik)});
   if(consecutiveAccessDenied>=3)accessDeniedCircuitOpen=true;
  }
  if(!accessDeniedCircuitOpen)await pause(550);
 }
 const cases=discovery.map(c=>{
  const issuer=index.map.get(c.ticker),facts=factMap.get(c.ticker)||[];
  const observations=Object.fromEntries(leadDays.map(n=>{
   const entryDate=minus(c.pdufaDate,n);
   return ["T_MINUS_"+n,{asOfDate:entryDate,
    ...(facts.length?{shareEvidence:latestVisible(facts,entryDate)}:{shareEvidence:null})}];
  }));
  return {eventKey:c.eventKey,ticker:c.ticker,pdufaDate:c.pdufaDate,
   secCurrentRegistryIdentity:issuer??null,
   secCoverShareFactsFound:facts.length,observations,
   status:!issuer?"MISSING_CURRENT_REGISTRY_CIK":facts.length?"POINT_IN_TIME_SHARE_LEADS_ONLY":
     "MISSING_USABLE_COVER_SHARE_FACTS",
   historicListingVerified:false,pdufaFirstPublicDateVerified:false,
   phase3FirstPublicDateVerified:false,marketCapAtEntryVerified:false};
 });
 const found=cases.filter(x=>x.secCoverShareFactsFound>0).length;
 const asof=cases.reduce((n,c)=>n+Object.values(c.observations).filter(x=>x.shareEvidence?.status==="SEC_PUBLIC_COVER_SHARES_RESEARCH_ONLY").length,0);
 return {scope:"RAAS_SEC_POINT_IN_TIME_SHARE_EVIDENCE_RESEARCH_ONLY",status:"SEC_SHARE_LEADS_COLLECTED_NOT_MARKET_CAP_AUDITED",
  archivedEvents:discovery.length,archiveYears:[...new Set(discovery.map(x=>x.pdufaDate.slice(0,4)))].sort(),
  uniqueCurrentRegistryTickers:symbols.length,
  issuersQueried:requests.filter(x=>x.status!=="NOT_ATTEMPTED_SOURCE_ACCESS_DENIED").length,
  issuersSkippedByAccessDenied:requests.filter(x=>x.status==="NOT_ATTEMPTED_SOURCE_ACCESS_DENIED").length,
  accessDeniedCircuitOpen,eventsWithShareFacts:found,datedAsOfShareLeads:asof,
  requests,registryCikConflicts:index.conflicts,cases,
  notes:["A modern CIK mapping does not establish ownership, rights or historical listing.",
   "SEC cover-share facts must be reconciled to class, ADS ratio and split history before computing historical market cap.",
   "An entry-day cap must use a contemporaneous RAW price; adjusted historical prices cannot be multiplied by unadjusted shares.",
   "SEC fact's filed date must precede entry; later amended filings must not overwrite what was known at entry.",
   "No historical event is promoted into the RAAS qualified backtest or calibration registry by this research."]};
}
if(require.main===module){
 execute().then(x=>{
  const output=process.env.RAAS_SEC_SHARE_OUTPUT||path.join(root,"raas-sec-historical-shares.json");
  fs.writeFileSync(output,JSON.stringify(x,null,2)+"\n");
  const h={status:x.status,archivedEvents:x.archivedEvents,issuersQueried:x.issuersQueried,
   eventsWithShareFacts:x.eventsWithShareFacts,datedAsOfShareLeads:x.datedAsOfShareLeads,
   sourceErrors:x.requests.filter(x=>x.status==="SEC_SOURCE_UNAVAILABLE").length,
   accessDeniedCircuitOpen:x.accessDeniedCircuitOpen,
   issuersSkippedByAccessDenied:x.issuersSkippedByAccessDenied};
  console.log(JSON.stringify(h));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### Historical SEC cover-share intake (not qualifying market cap)\n\n"+
   JSON.stringify(h)+"\n\nDownload artifact for as-of evidence and source gaps.\n");
  if(x.accessDeniedCircuitOpen || h.sourceErrors===x.issuersQueried&&x.issuersQueried)process.exitCode=1;
 }).catch(e=>{console.error("RAAS_SEC_SHARES_FATAL_"+String(e.message));process.exitCode=1;});
}
module.exports={issuers,sourceFacts,latestVisible,getFacts,execute};
