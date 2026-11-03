#!/usr/bin/env node
"use strict";
/**
 * RAAS event-aligned historical market-data research, NOT a historically
 * available entry signal. The eight retrospectively selected examples are a
 * fixed diagnostic cohort, NOT a 2016–2026 exhaustive PDUFA universe.
 *
 * Source: official Alpaca historical 1Day SIP bars with adjustment=all.
 * Never silently downgrade to IEX, raw, or missing bars; never claim that
 * split/dividend adjusted vendor bars have passed independent auditing.
 */
const fs=require("node:fs");
const path=require("node:path");
const root=path.resolve(__dirname,"..");
const topFile="new-platform/frontend/data/raas-retrospective-top-cases.json";
const bottomFile="new-platform/frontend/data/raas-retrospective-source-cases.json";
const ms=86400000;
const round=n=>Math.round((n+Number.EPSILON)*100)/100;
const day=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const epoch=d=>Date.parse(d+"T00:00:00Z");
const minusDays=(d,n)=>new Date(epoch(d)-n*ms).toISOString().slice(0,10);
const ymd=t=>new Date(t).toISOString().slice(0,10);
const pct=(a,b)=>round((b/a-1)*100);
const isNum=n=>typeof n==="number"&&Number.isFinite(n);
const median=xs=>{
 const a=[...xs].sort((x,y)=>x-y),n=a.length;
 return n%2?a[(n-1)/2]:(a[n/2-1]+a[n/2])/2;
};
const readJSON=p=>JSON.parse(fs.readFileSync(path.join(root,p),"utf8"));

function originalWindows(top,bottom){
 if(top.scope!=="RAAS_RETROSPECTIVE_PRE_READOUT_INTAKE"||
   bottom.scope!=="RAAS_RETROSPECTIVE_EVIDENCE_INTAKE")
  throw Error("RAAS_RESEARCH_SCOPE_INVALID");
 const input=[
  ...top.records.map(r=>({...r,knownDate:r.priorGuidanceDate,eventDate:r.publicReadoutDate,
   actualActionDate:r.publicReadoutDate,stage:"pre"})),
  ...bottom.records.map(r=>{
   const p=r.verifiedBeforeEntry.filter(e=>e.kind==="PDUFA_CONFIRMED"&&e.date<=r.entry.date);
   if(!p.length)throw Error("RAAS_PDUFA_KNOWN_DATE_MISSING");
   return {...r,knownDate:p.map(x=>x.date).sort()[0],eventDate:r.pdufaDate,
    actualActionDate:r.realizedFDAAction.date,stage:"post"};
  })
 ];
 const seen=new Set();
 return input.map(r=>{
  if(seen.has(r.id)||!day(r.entry.date)||!day(r.exit.date)||
    !day(r.eventDate)||!day(r.knownDate)||!day(r.actualActionDate)||
    !/^[A-Z][A-Z0-9.-]{0,11}$/.test(r.ticker)||
    r.entry.date>=r.exit.date||r.exit.date>=r.actualActionDate||
    r.knownDate>r.entry.date||
    r.marketCapAtEntry.usdMillions<300||r.marketCapAtEntry.usdMillions>10000||
    (r.stage==="pre"&&r.exit.date>=r.eventDate))
    throw Error("RAAS_RESEARCH_WINDOW_INVALID");
  seen.add(r.id);
  const clinicalPublic=r.stage==="post"?
   r.verifiedBeforeEntry.filter(x=>x.kind==="PHASE3_PUBLIC_READOUT").map(x=>x.date).sort()[0]:null;
  if(r.stage==="post"&&(!clinicalPublic||clinicalPublic>r.entry.date))
   throw Error("RAAS_POST_PHASE3_KNOWN_DATE_INVALID");
  return {caseId:r.id,stage:r.stage,ticker:r.ticker,
   nctIds:r.nctIds,drug:r.drug,indication:r.indication,
   scheduledEventDate:r.eventDate,actualActionDate:r.actualActionDate,
   eventFirstKnownDate:r.knownDate,clinicalReadoutKnownDate:clinicalPublic,
   priorSelectedEntryDate:r.entry.date,
   vendorHistoricalMarketCapMillions:r.marketCapAtEntry.usdMillions,
   historicalCapOnlyAtSelectedEntry:true,
   firstBarDate:minusDays(r.eventDate,101),
   lastBarDate:r.eventDate};
 });
}

/** Vendor market data is a research observation, never a derived RAAS grade. */
function parseBars(payload,ticker,range){
 if(!payload||typeof payload!=="object"||!Array.isArray(payload.bars)||
   typeof payload.symbol!=="string"||payload.symbol!==ticker)
  throw Error("RAAS_ALPACA_RESPONSE_INVALID");
 const data=[],seen=new Set();
 for(const b of payload.bars){
  if(!b||!isNum(b.o)||!isNum(b.c)||!isNum(b.h)||!isNum(b.l)||
   !isNum(b.v)||b.o<=0||b.c<=0||b.h<=0||b.l<=0||b.v<0||
   b.h<Math.max(b.o,b.c)||b.l>Math.min(b.o,b.c)||
   b.l>b.h||typeof b.t!=="string"||!/^\d{4}-\d{2}-\d{2}T/.test(b.t))
   throw Error("RAAS_ALPACA_BAR_INVALID");
  const d=b.t.slice(0,10);
  if(!day(d)||d<range.firstBarDate||d>range.lastBarDate||seen.has(d))
   throw Error("RAAS_ALPACA_DATE_OR_DUPLICATE_INVALID");
  seen.add(d);
  data.push({date:d,open:b.o,close:b.c,high:b.h,low:b.l,volume:b.v});
 }
 return data.sort((a,b)=>a.date.localeCompare(b.date));
}
async function downloadBars(win,key,secret,request=fetch){
 const out=[],seen=new Set();
 let pageToken=null,page=0;
 do{
  if(++page>20)throw Error("RAAS_ALPACA_PAGINATION_LIMIT");
  const url=new URL("https://data.alpaca.markets/v2/stocks/"+encodeURIComponent(win.ticker)+"/bars");
  url.searchParams.set("timeframe","1Day");
  url.searchParams.set("start",win.firstBarDate);
  url.searchParams.set("end",win.lastBarDate);
  url.searchParams.set("limit","1000");
  url.searchParams.set("adjustment","all");
  url.searchParams.set("feed","sip");
  url.searchParams.set("sort","asc");
  if(pageToken)url.searchParams.set("page_token",pageToken);
  const res=await request(url.toString(),{
   headers:{"APCA-API-KEY-ID":key,"APCA-API-SECRET-KEY":secret,
    "Accept":"application/json"},
   method:"GET",signal:AbortSignal.timeout(20000),redirect:"error"
  });
  if(!res.ok)throw Error("RAAS_ALPACA_HTTP_"+res.status);
  if(!(res.headers.get("content-type")||"").toLowerCase().includes("json"))
   throw Error("RAAS_ALPACA_CONTENT_TYPE_INVALID");
  const body=await res.text();
  if(body.length>1000000)throw Error("RAAS_ALPACA_RESPONSE_TOO_LARGE");
  const j=JSON.parse(body);
  for(const b of parseBars(j,win.ticker,win)){
   if(seen.has(b.date))throw Error("RAAS_ALPACA_CROSS_PAGE_DUPLICATE");
   seen.add(b.date);out.push(b);
  }
  if(j.next_page_token!==null&&j.next_page_token!==undefined&&
    (typeof j.next_page_token!=="string"||j.next_page_token.length>1200))
   throw Error("RAAS_ALPACA_PAGE_TOKEN_INVALID");
  pageToken=j.next_page_token||null;
 }while(pageToken);
 return out.sort((a,b)=>a.date.localeCompare(b.date));
}

const entryLeads=[90,75,60,45,30,21,14,10,7,5,4];
const exitLeads=[30,21,14,10,7,5,3];
/** Fixed windows—not optimized on the outcomes being evaluated. */
function studyWindow(win,bars,entryLead,exitLead){
 if(!entryLeads.includes(entryLead)||!exitLeads.includes(exitLead)||
  exitLead>=entryLead)throw Error("RAAS_WINDOW_GRID_INVALID");
 // Entry first trading session on/after offset; exit last on/before.
 const targetEntry=minusDays(win.scheduledEventDate,entryLead);
 const targetExit=minusDays(win.scheduledEventDate,exitLead);
 const entry=bars.find(x=>x.date>=targetEntry);
 const exit=[...bars].reverse().find(x=>x.date<=targetExit);
 const result={caseId:win.caseId,ticker:win.ticker,stage:win.stage,
  eventDate:win.scheduledEventDate,entryLeadDays:entryLead,exitLeadDays:exitLead,
  entryDate:entry?.date??null,exitDate:exit?.date??null,
  adjustedCloseEntry:entry?.close??null,adjustedCloseExit:exit?.close??null,
  closeToCloseReturnPercent:null,afterAssumed1pctRoundTripCost:null,
  status:"BLOCKED",reason:""};
 if(!entry||!exit){result.reason="MISSING_DAILY_PRICE_BARS";return result;}
 if(entry.date>=exit.date){result.reason="ENTRY_NOT_BEFORE_EXIT";return result;}
 if(entry.date<win.eventFirstKnownDate||win.stage==="post"&&
   (!win.clinicalReadoutKnownDate||entry.date<=win.clinicalReadoutKnownDate)){
  result.reason="HISTORICAL_EVENT_NOT_YET_PUBLIC_AT_ENTRY";return result;
 }
 if(exit.date>=win.actualActionDate){
  result.reason="CENSORED_EARLY_FDA_OR_READOUT_ACTION";return result;
 }
 // A vendor cap at a different historical date does not qualify THIS entry.
 // This grid is for research; independent eligibility and execution remain open.
 result.closeToCloseReturnPercent=pct(entry.close,exit.close);
 result.afterAssumed1pctRoundTripCost=round(result.closeToCloseReturnPercent-1);
 result.status="RETROSPECTIVE_PRICE_RESEARCH";
 result.reason="VALID_RAW_ARITHMETIC_NOT_VALIDATED_TRADING_CASE";
 return result;
}
function summarize(rows){
 const by=new Map();
 for(const r of rows){
  const k=r.stage+"|"+r.entryLeadDays+"|"+r.exitLeadDays;
  if(!by.has(k))by.set(k,[]);
  by.get(k).push(r);
 }
 const summaries=[...by.entries()].map(([key,s])=>{
  const [stage,e,x]=key.split("|");
  const used=s.filter(r=>r.status==="RETROSPECTIVE_PRICE_RESEARCH");
  const returns=used.map(r=>r.closeToCloseReturnPercent);
  return {stage,entryLeadDays:+e,exitLeadDays:+x,
   eligiblePriceWindows:used.length,
   distinctIssuers:new Set(used.map(r=>r.ticker)).size,
   availableCases:s.length,
   earlyActionCensored:s.filter(r=>r.reason==="CENSORED_EARLY_FDA_OR_READOUT_ACTION").length,
   blocked:s.length-used.length,
   meanGrossPercent:returns.length?round(returns.reduce((a,b)=>a+b,0)/returns.length):null,
   medianGrossPercent:returns.length?round(median(returns)):null,
   medianAfterAssumedCost:returns.length?round(median(returns)-1):null,
   observationalOnly:true,
   validatedRaasSignal:false};
 });
 return summaries.sort((a,b)=>a.stage.localeCompare(b.stage)||
  b.entryLeadDays-a.entryLeadDays||b.exitLeadDays-a.exitLeadDays);
}
async function execute({key,secret,request=fetch,top=readJSON(topFile),
 bottom=readJSON(bottomFile)}={}){
 const cases=originalWindows(top,bottom),entries=[],status=[];
 if(!key||!secret)return {status:"BLOCKED_MISSING_ALPACA_CREDENTIALS",
  studyScope:"8_RETROSPECTIVELY_SELECTED_WINDOWS_NOT_10_YEAR_UNIVERSE",
  adjustedPricePoints:0,examinedCases:cases.length,successfulCases:0,
  feed:"SIP",adjustment:"all",priceRows:[],windowReturns:[],windowSummaries:[],
  failures:[],note:"No Alpaca keys were supplied. No historical bars or RAAS results invented."};
 for(const win of cases){
  try{
   const bars=await downloadBars(win,key,secret,request);
   if(bars.length<30)throw Error("RAAS_ALPACA_INSUFFICIENT_BARS");
   status.push({ticker:win.ticker,caseId:win.caseId,source:"ALPACA_SIP_ADJUSTMENT_ALL",
    bars:bars.length,status:"RESEARCH_BARS_COLLECTED"});
   for(const bar of bars)entries.push({
    caseId:win.caseId,ticker:win.ticker,session:bar.date,
    adjustedOpen:bar.open,adjustedClose:bar.close,
    volume:bar.volume,sourceUrl:"https://data.alpaca.markets/v2/stocks/"+
     encodeURIComponent(win.ticker)+"/bars",
    feed:"sip",adjustment:"all",
    independentlyCorporateActionAudited:false});
   for(const e of entryLeads)for(const x of exitLeads)if(e>x)
    status.push(studyWindow(win,bars,e,x));
  }catch(error){
   // No upstream body/secret logging; avoid user-visible credentials.
   status.push({ticker:win.ticker,caseId:win.caseId,status:"SOURCE_UNAVAILABLE",
    reason:String(error?.message||"UNAVAILABLE").replace(/[^A-Z0-9_]/g,"_").slice(0,75)});
  }
 }
 const rows=status.filter(x=>x.entryLeadDays);
 const ok=new Set(status.filter(x=>x.status==="RESEARCH_BARS_COLLECTED").map(x=>x.caseId));
 return {status:ok.size===cases.length?"RESEARCH_PRICE_GRID_COLLECTED":"PARTIAL_OR_BLOCKED",
  studyScope:"8_RETROSPECTIVELY_SELECTED_WINDOWS_NOT_10_YEAR_UNIVERSE",
  examinedCases:cases.length,successfulCases:ok.size,
  adjustedPricePoints:entries.length,feed:"SIP",adjustment:"all",
  priceRows:entries,windowReturns:rows,windowSummaries:summarize(rows),
  failures:status.filter(x=>x.status==="SOURCE_UNAVAILABLE"),
  caveats:[
   "SIP and adjustment=all were explicitly requested, not independently cross-audited.",
   "Event-aligned TOP entry/exit offsets use the realized first readout date, hindsight not available to a trader.",
   "Selected event windows are not all PDUFA/Phase 3 cases from 2016–2026; historical capitalization eligibility at each grid entry remains unverified.",
   "Censor any window crossing an earlier FDA action; do not treat after-decision prices as pre-event profits.",
   "Prices do not establish trading spreads, slippage, market-cap eligibility at every entry, or predictive RAAS grades.",
   "Identical issuer across multiple programs cannot be treated as issuer-disjoint holdout."
  ]};
}
if(require.main===module){
 const env=process.env,key=env.APCA_API_KEY_ID||env.ALPACA_API_KEY_ID||env.ALPACA_API_KEY;
 const secret=env.APCA_API_SECRET_KEY||env.ALPACA_SECRET_KEY;
 execute({key,secret}).then(result=>{
  const output=env.RAAS_ALPACA_RESULT_PATH||
   path.join(root,"raas-alpaca-historical-research.json");
  fs.mkdirSync(path.dirname(output),{recursive:true});
  fs.writeFileSync(output,JSON.stringify(result,null,2)+"\n");
  const summary={status:result.status,examinedCases:result.examinedCases,
   successfulCases:result.successfulCases,adjustedPricePoints:result.adjustedPricePoints,
   windowReturnCount:result.windowReturns.length,sourceErrors:result.failures.length,
   resultsArtifact:output};
  process.stdout.write(JSON.stringify(summary)+"\n");
  if(env.GITHUB_STEP_SUMMARY)fs.appendFileSync(env.GITHUB_STEP_SUMMARY,
   "### RAAS Alpaca historical research\n\n\`"+
    JSON.stringify(summary)+"\`\n\nThis is NOT validated RAAS calibration.\n");
 }).catch(err=>{process.stderr.write("RAAS_ALPACA_FATAL_"+String(err?.message||"UNKNOWN").replace(/[^A-Z0-9_]/g,"_").slice(0,80)+"\n");process.exitCode=1;});
}
module.exports={originalWindows,parseBars,downloadBars,studyWindow,summarize,execute,
 entryLeads,exitLeads,minusDays};
