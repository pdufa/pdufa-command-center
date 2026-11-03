#!/usr/bin/env node
"use strict";
/** Real dated SEC cover shares x Alpaca RAW SIP close (NOT a validated
 * historical market-cap series or a qualified RAAS backtest). Separate
 * adjusted SIP prices are requested for return arithmetic only.
 *
 * Never multiply a split-adjusted close by unadjusted historical shares.
 */
const fs=require("node:fs"),path=require("node:path");
const prior=require("./raas_alpaca_historical_price_study.cjs");
const root=path.resolve(__dirname,"..");
const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const url=s=>typeof s==="string"&&/^https:\/\/[^\s/]+\.[^\s/]+/i.test(s);
const round=x=>Math.round((x+Number.EPSILON)*100)/100;
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));
function checkedLead(share,caseEvent){
 if(!share||share.status!=="COVER_SHARE_RESEARCH_ONLY"||
  !caseEvent||share.caseId!==caseEvent.caseId||share.ticker!==caseEvent.ticker||
  !/^[A-Z][A-Z0-9.-]{0,11}$/.test(share.ticker)||
  !Number.isSafeInteger(share.sharesOutstanding)||share.sharesOutstanding<=0||
  !date(share.sharesMeasurementDate)||!date(share.filedDate)||
  !date(share.firstConservativeEntryDate)||!date(caseEvent.pdufaTargetDate)||
  share.sharesMeasurementDate>share.filedDate||
  share.firstConservativeEntryDate<=share.filedDate||
  !url(share.sourceUrl)||!url(share.filingIndexUrl)||
  share.securityCurrency!=="USD"||share.rawCloseCurrency!=="USD"||
  share.venue!=="NASDAQ"||
  !date(caseEvent.targetAnnouncementDate)||!date(caseEvent.phase3ReadoutDate)||
  !date(caseEvent.actualFDAActionDate)||
  caseEvent.targetAnnouncementDate>=caseEvent.pdufaTargetDate||
  caseEvent.phase3ReadoutDate>=caseEvent.pdufaTargetDate)
  throw Error("RAAS_CAP_SOURCE_IDENTITY_OR_ASOF_INVALID");
 return share;
}
async function fetchBars(ticker,asOf,start,end,adjustment,key,secret,request=fetch) {
 if(!["raw","all"].includes(adjustment)||!key||!secret||
  !/^[A-Z][A-Z0-9.-]{0,11}$/.test(ticker)||!date(asOf)||!date(start)||!date(end))
  throw Error("RAAS_CAP_PRICE_REQUEST_INVALID");
 let token=null,page=0;const bars=[],seen=new Set();
 do {
  if(++page>8)throw Error("RAAS_CAP_PRICE_PAGES_EXCEEDED");
  const u=new URL("https://data.alpaca.markets/v2/stocks/"+ticker+"/bars");
  for(const [k,v] of Object.entries({timeframe:"1Day",start,end,limit:"1000",
   adjustment,asof:asOf,feed:"sip",sort:"asc"}))u.searchParams.set(k,v);
  if(token)u.searchParams.set("page_token",token);
  const response=await request(u.toString(),{method:"GET",redirect:"error",
   signal:AbortSignal.timeout(20000),headers:{"APCA-API-KEY-ID":key,
    "APCA-API-SECRET-KEY":secret,Accept:"application/json"}});
  if(!response.ok)throw Error("RAAS_CAP_ALPACA_HTTP_"+response.status);
  if(!(response.headers?.get("content-type")||"").toLowerCase().includes("json"))
   throw Error("RAAS_CAP_PRICE_CONTENT_TYPE_INVALID");
  const body=await response.text();
  if(body.length>1200000)throw Error("RAAS_CAP_PRICE_RESPONSE_TOO_LARGE");
  const payload=JSON.parse(body);
  for(const bar of prior.parseBars(payload,ticker,{firstBarDate:start,lastBarDate:end})) {
   if(seen.has(bar.date))throw Error("RAAS_CAP_DUPLICATE_SESSION");
   seen.add(bar.date);bars.push(bar);
  }
  token=payload.next_page_token??null;
  if(token!==null&&(typeof token!=="string"||!token||token.length>1200))
   throw Error("RAAS_CAP_PAGE_TOKEN_INVALID");
 }while(token);
 return bars.sort((a,b)=>a.date.localeCompare(b.date));
}
function examine(share,event,raw,adjusted){
 checkedLead(share,event);
 if(raw.length<30||adjusted.length<30)throw Error("RAAS_CAP_INSUFFICIENT_BARS");
 if(raw.length!==adjusted.length||raw.some((r,i)=>r.date!==adjusted[i]?.date))
  throw Error("RAAS_CAP_PRICE_CALENDARS_MISMATCH");
 const knownPublic=Math.max(Date.parse(share.firstConservativeEntryDate),
  Date.parse(event.targetAnnouncementDate),Date.parse(event.phase3ReadoutDate));
 const result=[];
 for(const [i,b] of raw.entries()){
  const adjustedBar=adjusted[i];
  const afterEvidence=Date.parse(b.date+"T00:00:00Z")>=knownPublic;
  const beforeAction=b.date<event.actualFDAActionDate;
  // Only entry-time known cover shares, not current shares nor adjusted price.
  const cap=afterEvidence ? b.close*share.sharesOutstanding/1000000:null;
  result.push({session:b.date,rawClose:b.close,adjustedClose:adjustedBar.close,
   sharesOutstandingKnownFromFiling:afterEvidence?share.sharesOutstanding:null,
   historicMarketCapResearchMillions:cap===null?null:round(cap),
   within300mTo10bUnreviewed:cap===null?null:cap>=300&&cap<=10000,
   beforeActualFDAAction:beforeAction,
   sourceStatus:cap===null?"PRE_DISCLOSURE_OR_MISSING_FACT":
     "RESEARCH_ONLY_NEEDS_SHARE_CLASS_AND_CORPORATE_ACTION_AUDIT",
   sourceUrl:share.sourceUrl});
 }
 const historicalCaps=result.filter(x=>x.historicMarketCapResearchMillions!==null&&
  x.beforeActualFDAAction);
 return {caseId:event.caseId,ticker:event.ticker,
  pdufaTargetDate:event.pdufaTargetDate,actualFDAActionDate:event.actualFDAActionDate,
  shareFactFiledDate:share.filedDate,conservativeEligibleInformationDate:share.firstConservativeEntryDate,
  originalSharesMeasurementDate:share.sharesMeasurementDate,
  shareFactSourceUrl:share.sourceUrl,
  marketCapResearchDays:historicalCaps.length,
  researchDaysIn300mTo10b:historicalCaps.filter(x=>x.within300mTo10bUnreviewed).length,
  eventTradeCasesValidated:0,
  approvedRaasRatings:0,
  source:"ALPACA_SIP_RAW_CLOSE_X_SEC_COVER_SHARES",
  priceReturnSource:"ALPACA_SIP_ADJUSTMENT_ALL_SEPARATE",
  status:"RAW_MARKET_CAP_DIAGNOSTICS_NOT_PROVEN_TRADING_ELIGIBILITY",
  observations:result,
  blockers:["Publication cutoff is enforced but exact cap/share continuity per date is unreviewed.",
   "Raw and adjusted bars must be independently reconciled for split/ADR treatment.",
   "SEC issuer share count is not diluted or necessarily stable across all entry dates.",
   "No full 2016–2025 event census or issuer-disjoint RAAS scoring holdout."]};
}
async function execute({key,secret,request=fetch,shares=read("new-platform/frontend/data/raas-2020-sec-cover-share-leads.json"),
 events=read("new-platform/frontend/data/raas-historical-2020-primary-source-leads.json")}={}){
 if(shares.scope!=="RAAS_MANUALLY_LOCATED_SEC_HISTORIC_COMMON_SHARE_RESEARCH"||
  events.scope!=="RAAS_HISTORICAL_PRIMARY_PDUFA_EVENT_EVIDENCE_RESEARCH")
  throw Error("RAAS_CAP_RESEARCH_SCOPE_INVALID");
 if(!key||!secret)return {status:"BLOCKED_MISSING_ALPACA_CREDENTIALS",cases:[],notes:[]};
 const result=[];
 for(const share of shares.records){
  const event=events.records.find(x=>x.caseId===share.caseId);
  checkedLead(share,event);
  const start=prior.minusDays(event.pdufaTargetDate,100);
  const end=prior.minusDays(event.pdufaTargetDate,1);
  const raw=await fetchBars(event.ticker,event.pdufaTargetDate,start,end,"raw",key,secret,request);
  const adjusted=await fetchBars(event.ticker,event.pdufaTargetDate,start,end,"all",key,secret,request);
  result.push(examine(share,event,raw,adjusted));
 }
 return {scope:"RAAS_HISTORIC_RAW_CAP_RESEARCH",status:"UNVALIDATED_HISTORICAL_CAP_RESEARCH_ONLY",
  cases:result,rawSessions:result.reduce((a,x)=>a+x.observations.length,0),
  possible300mTo10bResearchSessions:result.reduce((a,x)=>a+x.researchDaysIn300mTo10b,0),
  historicallyEligibleTrades:0,approvedRaasRatings:0,
  notes:["Read-only source research. No scores or market-cap eligibility are written to approved RAAS intake.",
   "Do not use current market cap, post-event facts or adjusted stock prices with unadjusted share counts."]};
}
if(require.main===module) {
 const key=process.env.APCA_API_KEY_ID||process.env.ALPACA_API_KEY_ID||process.env.ALPACA_API_KEY;
 const secret=process.env.APCA_API_SECRET_KEY||process.env.ALPACA_SECRET_KEY;
 execute({key,secret}).then(x=>{
  const p=process.env.RAAS_RAW_CAP_OUTPUT||path.join(root,"raas-historical-raw-cap-research.json");
  fs.writeFileSync(p,JSON.stringify(x,null,2)+"\n");
  const s={status:x.status,cases:x.cases.length,rawSessions:x.rawSessions,
   possible300mTo10bResearchSessions:x.possible300mTo10bResearchSessions,
   historicallyEligibleTrades:x.historicallyEligibleTrades,approvedRaasRatings:x.approvedRaasRatings};
  console.log(JSON.stringify(s));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "### SEC dated shares × Alpaca RAW prices (research only)\n\n"+
   JSON.stringify(s)+"\n\nNo verified market caps or RAAS grades.\n");
  if(x.status==="BLOCKED_MISSING_ALPACA_CREDENTIALS")process.exitCode=1;
 }).catch(e=>{console.error("RAAS_CAP_RESEARCH_FATAL_"+String(e.message).replace(/[^A-Z0-9_]/g,"_"));process.exitCode=1;});
}
module.exports={checkedLead,fetchBars,examine,execute};
