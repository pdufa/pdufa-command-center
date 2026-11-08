#!/usr/bin/env node
"use strict";
/**
 * Stand-alone source-led, never approved 2024/25 FDA historical market-cap
 * and return research for TVTX/URGN, independent of nine selected cases.
 * SEC cover shares: originally published snapshots, conservative next-session
 * use. Alpaca SIP RAW closes for provisional cap, adjustment=all for returns.
 * No exact daily shares, diluted capitalization, independent vendor parity,
 * eligibility or predictive performance is certified here.
 */
const fs=require("node:fs"),path=require("node:path");
const {fetchBars}=require("./raas_historical_raw_market_cap_research.cjs");
const {allWindows}=require("./raas_historical_provisional_window_grid.cjs");
const root=path.resolve(__dirname,"..");
const SOURCE="RAAS_2024_2025_EXPANDED_CANDIDATE_SEC_COVER_SNAPSHOTS_RESEARCH_ONLY";
const CANDIDATES="RAAS_2024_2025_ADDITIONAL_PHASE3_FDA_SOURCE_LEADS_RESEARCH_ONLY";
const OUT="RAAS_2024_2025_EXPANDED_SEC_ASOF_ALPACA_PROVISIONAL_T90_T3";
const ISO=/^\d{4}-\d{2}-\d{2}$/;
const date=s=>typeof s==="string"&&ISO.test(s)&&!Number.isNaN(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const shift=(s,n)=>new Date(Date.parse(s+"T00:00:00Z")+n*86400000).toISOString().slice(0,10);
const age=(a,b)=>(Date.parse(a+"T00:00:00Z")-Date.parse(b+"T00:00:00Z"))/86400000;
const round=x=>Math.round((x+Number.EPSILON)*100)/100;
const fail=x=>{throw Error("RAAS_EXPANDED_CAP_"+x)};
const SOURCE_CASES=new Set(["TVTX|FILSPARI_SPARSENTAN_IGAN|NDA216403_SCONVERSION|2024",
 "URGN|ZUSDURI_UGN102_LGIRNMIBC|NDA215793|2025"]);
function checkSources(candidates,shareFeed,primary){
 if(candidates?.scope!==CANDIDATES||candidates.schemaVersion!==1||
  candidates.allResearchOnly!==true||
  candidates.approvedAdditionsTo2024To2025Backtest!==0||
  candidates.independentlyVerifiedTradingCases!==0||
  candidates.fullFDAEventCensusCompleted!==false||
  !Array.isArray(candidates.records)||candidates.records.length!==2||
  shareFeed?.scope!==SOURCE||shareFeed.schemaVersion!==1||
  shareFeed.allResearchOnly!==true||
  shareFeed.independentlyValidatedDailyShareCounts!==0||
  shareFeed.independentlyValidatedEntryMarketCaps!==0||
  shareFeed.approvedStudyCases!==0||
  !Array.isArray(shareFeed.records)||shareFeed.records.length!==2||
  !Array.isArray(primary?.records)||primary.records.length!==9)
  fail("SOURCE_SCHEMA_OR_RESEARCH_GATE_INVALID");
 const selected=new Set(primary.records.map(x=>x.ticker));
 if(selected.size!==9)fail("PRIMARY_SAMPLE_DUPLICATE_TICKER");
 const out=new Map();
 const shareMap=new Map(shareFeed.records.map(x=>[x.caseId,x]));
 if(shareMap.size!==2)fail("SEC_SNAPSHOT_DUPLICATE_CASE");
 for(const c of candidates.records){
  if(!SOURCE_CASES.has(c.caseId)||selected.has(c.ticker)||out.has(c.caseId)||
   !["TVTX","URGN"].includes(c.ticker)||!c.nctIds?.length||
   !date(c.pdufaTargetDate)||!date(c.actualFDAActionDate)||
   !date(c.targetAnnouncementDate)||!date(c.phase3EvidenceDate)||
   c.targetAnnouncementDate>shift(c.pdufaTargetDate,-90)||
   c.phase3EvidenceDate>shift(c.pdufaTargetDate,-90)||
   c.actualFDAActionDate>c.pdufaTargetDate||
   c.actualFDAActionDate<=shift(c.pdufaTargetDate,-3)||
   c.eligibleForApprovedTradingStudy!==false||
   c.historicalEntryMarketCap300m10bValidated!==false||
   c.adjustedPriceBarsIndependentlyReconciled!==false)
   fail("CANDIDATE_CHRONOLOGY_OR_APPROVAL_INVALID");
  const shares=shareMap.get(c.caseId);
  if(!shares||shares.ticker!==c.ticker||shares.cik!==(c.ticker==="TVTX"?"0001438533":"0001668243")||
   shares.venue!=="NASDAQ"||shares.rawCloseCurrency!=="USD"||
   !Array.isArray(shares.snapshots)||shares.snapshots.length!==2||
   !shares.shareClass.includes(c.ticker==="URGN"?"Ordinary Shares":"Common Stock"))
   fail("SEC_ISSUER_SHARE_CLASS_INVALID");
  let prior=null;
  for(const x of shares.snapshots){
   if(!Number.isSafeInteger(x.sharesOutstanding)||x.sharesOutstanding<=0||
    !date(x.sharesMeasurementDate)||!date(x.filedDate)||
    !date(x.firstConservativeEntryDate)||
    x.sharesMeasurementDate>x.filedDate||
    x.firstConservativeEntryDate<=x.filedDate||
    x.firstConservativeEntryDate!==shift(x.filedDate,1)&&
     x.firstConservativeEntryDate!==shift(x.filedDate,2)&&
     x.firstConservativeEntryDate!==shift(x.filedDate,3)||
    x.firstConservativeEntryDate>=c.actualFDAActionDate||
    !/^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\/\d+\//.test(x.sourceUrl)||
    !/^https:\/\/www\.sec\.gov\/Archives\/edgar\/data\/\d+\//.test(x.filingIndexUrl)||
    !/^000\d{7}-\d{2}-\d{6}$/.test(x.accession)||
    !["10-Q","10-K"].includes(x.form)||
    (prior&&(x.firstConservativeEntryDate<=prior.firstConservativeEntryDate||
     x.filedDate<=prior.filedDate||x.sharesMeasurementDate<=prior.sharesMeasurementDate)))
    fail("SEC_SNAPSHOT_DATE_OR_PUBLISHED_FACT_INVALID");
   prior=x;
  }
  out.set(c.caseId,{event:c,shares});
 }
 if(out.size!==2)fail("CANDIDATE_COUNT_MISMATCH");
 return out;
}
function validateBars(bars,start,end,kind){
 if(!Array.isArray(bars)||bars.length<45)fail("MISSING_ALPACA_"+kind+"_BARS");
 let last="";
 for(const b of bars){
  if(!b||!date(b.date)||b.date<=last||b.date<start||b.date>end||
   !Number.isFinite(b.close)||b.close<=0)
   fail("UNTRUSTED_ALPACA_"+kind+"_BAR");
  last=b.date;
 }
 return bars;
}
function combine(raw,adjusted,start,end){
 validateBars(raw,start,end,"RAW");
 validateBars(adjusted,start,end,"ADJUSTED");
 if(raw.length!==adjusted.length||raw.some((b,i)=>b.date!==adjusted[i].date))
  fail("ALPACA_RAW_ADJUSTED_SESSION_MISMATCH");
 return raw.map((r,i)=>({date:r.date,rawClose:r.close,adjustedClose:adjusted[i].close}));
}
function inspectCase(event,shares,bars,e,x){
 if(!Number.isInteger(e)||!Number.isInteger(x)||e>90||e<4||x<3||x>=e)
  fail("LEAD_DAYS_INVALID");
 const plannedEntry=shift(event.pdufaTargetDate,-e),plannedExit=shift(event.pdufaTargetDate,-x);
 const base={caseId:event.caseId,ticker:event.ticker,cohortYear:Number(event.pdufaTargetDate.slice(0,4)),
  entryLeadDays:e,exitLeadDays:x,plannedEntry,plannedExit,
  entrySession:null,exitSession:null,publishedSECSourceUsed:null,
  shareDisclosureSafeSince:null,daysSinceShareSourcePublished:null,
  approximateMarketCapUSDMillions:null,provisionalGrossReturnPct:null,
  provisionalNetAfter1ptCostPct:null,marketCapSnapshotKnownAtEntry:false,
  independentlyVerifiedDailyShares:false,independentAdjustedPriceParity:false,
  independentlyValidatedTrade:false,approvedRAASScore:null};
 if(event.targetAnnouncementDate>plannedEntry||
  event.phase3EvidenceDate>plannedEntry)
  return {...base,reason:"FDA_GOAL_OR_PHASE3_NOT_PUBLIC_AT_PLANNED_ENTRY"};
 if(!bars)return {...base,reason:"ALPACA_SIP_BARS_NOT_OBTAINED"};
 const first=bars.find(z=>z.date>=plannedEntry&&z.date<=shift(plannedEntry,4));
 const last=[...bars].reverse().find(z=>z.date<=plannedExit&&z.date>=shift(plannedExit,-4));
 const times={entrySession:first?.date??null,exitSession:last?.date??null};
 if(!first||!last)return {...base,...times,reason:"NO_ALIGNED_ENTRY_OR_EXIT_SESSION"};
 if(first.date>=last.date)return {...base,...times,reason:"NO_ORDERED_SESSIONS"};
 if(first.date<event.targetAnnouncementDate||first.date<event.phase3EvidenceDate)
  return {...base,...times,reason:"FDA_GOAL_OR_PHASE3_NOT_PUBLIC_AT_ENTRY"};
 if(last.date>=event.actualFDAActionDate)
  return {...base,...times,reason:"RETROSPECTIVE_EARLY_FDA_ACTION_CENSORS_EXIT"};
 const source=shares.snapshots.filter(s=>s.firstConservativeEntryDate<=first.date)
  .sort((a,b)=>b.firstConservativeEntryDate.localeCompare(a.firstConservativeEntryDate))[0];
 if(!source)return {...base,...times,reason:"NO_SEC_COVER_PUBLISHED_BY_ENTRY"};
 const cap=first.rawClose*source.sharesOutstanding/1000000;
 const sec={publishedSECSourceUsed:source.sourceUrl,
  shareDisclosureSafeSince:source.firstConservativeEntryDate,
  daysSinceShareSourcePublished:age(first.date,source.firstConservativeEntryDate),
  marketCapSnapshotKnownAtEntry:true};
 if(!Number.isFinite(cap)||cap<=0)fail("INVALID_RAW_CAP_MULTIPLICATION");
 const marketCap=round(cap);
 if(cap<300||cap>10000)
  return {...base,...times,...sec,approximateMarketCapUSDMillions:marketCap,
   reason:"PROVISIONAL_CAP_OUTSIDE_300M_TO_10B"};
 const gross=round((last.adjustedClose/first.adjustedClose-1)*100);
 return {...base,...times,...sec,approximateMarketCapUSDMillions:marketCap,
  provisionalGrossReturnPct:gross,provisionalNetAfter1ptCostPct:round(gross-1),
  reason:"SOURCE_ELIGIBLE_RESEARCH_ONLY_NOT_VALIDATED_TRADE"};
}
function build({candidates,shareFeed,primary,barsByTicker={}}){
 const byCase=checkSources(candidates,shareFeed,primary);
 const pairs=allWindows();if(pairs.length!==3828)fail("FULL_GRID_INVALID");
 const rows=[],counts={};
 for(const {event,shares} of byCase.values()){
  const bars=barsByTicker[event.ticker]??null;
  for(const p of pairs){
   const result=inspectCase(event,shares,bars,p.entryLeadDays,p.exitLeadDays);
   rows.push(result);
   const k=result.reason;counts[k]=(counts[k]||0)+1;
  }
 }
 const reviewed=rows.filter(r=>r.provisionalGrossReturnPct!==null);
 return {schemaVersion:1,scope:OUT,
  status:Object.keys(barsByTicker).length===0?
   "BLOCKED_NO_ALPACA_BARS":"PROVISIONAL_SEC_PRICE_RESEARCH_UNVALIDATED",
  sourceAsOf:shareFeed.sourceAsOf,sourceCaseCount:byCase.size,
  SECOriginalPublishedSnapshots:4,allValidPairsPerCase:pairs.length,
  totalCaseWindowEvaluations:rows.length,provisionalReturnWindowCount:reviewed.length,
  distinctIssuerCasesWithProvisionalReturns:new Set(reviewed.map(x=>x.ticker)).size,
  reasons:counts,independentlyValidatedTrades:0,
  independentlyValidatedMarketCaps:0,independentlyValidatedCorporateActions:0,
  calibratedRaasMetrics:0,approvedBestTradingWindow:null,
  addedToNineCaseStudy:0,completeFDACensus:false,
  candidateReport:rows,
  warnings:[
   "TVTX and URGN are supplemental case leads, NOT backfill into the pre-existing nine-case outcome-selected sample.",
   "TVTX is a supplemental conversion to traditional approval, not an original NDA. Compare only within matched review-cycle strata.",
   "Original SEC cover shares are publication-timed snapshots, not continuous fully diluted market caps; 0 market caps independently approved.",
   "Alpaca adjustment=raw and adjustment=all are distinct. No independent adjusted-price vendor parity or security-level corporate action reconciliation.",
   "Returns are hypothetically based on historical adjusted closes. No fills, slippage, bid-ask or trade execution verification.",
   "Zero approved trades, zero approved optimum, zero validated RAAS grades and no independent test of a window chosen after looking at the cases."
  ]};
}
function csv(report){
 if(report?.scope!==OUT||report.independentlyValidatedTrades!==0||
  report.approvedBestTradingWindow!==null)fail("CSV_RESEARCH_SCOPE_INVALID");
 const cols=["ticker","cohortYear","entryLeadDays","exitLeadDays","plannedEntry","plannedExit",
  "entrySession","exitSession","shareDisclosureSafeSince","daysSinceShareSourcePublished",
  "approximateMarketCapUSDMillions","provisionalGrossReturnPct",
  "provisionalNetAfter1ptCostPct","reason","publishedSECSourceUsed"];
 const v=(n)=>{if(n===null||n===undefined)return "";
  if(typeof n==="number")return String(n);
  const s=String(n);return '"'+(/^[\s\u0000-\u001f]*[=+\-@]/u.test(s)?"'":"")+
   s.replaceAll('"','""')+'"';};
 return cols.join(",")+"\n"+report.candidateReport.map(r=>cols.map(k=>v(r[k])).join(",")).join("\n")+"\n";
}
async function execute({candidates,shareFeed,primary,key,secret,request=fetch,
 fetcher=fetchBars}){
 const byCase=checkSources(candidates,shareFeed,primary);
 if(!key||!secret) return build({candidates,shareFeed,primary});
 const prices={};
 for(const {event} of byCase.values()){
  const start=shift(event.pdufaTargetDate,-100),end=shift(event.pdufaTargetDate,-1);
  const raw=await fetcher(event.ticker,event.pdufaTargetDate,start,end,
   "raw",key,secret,request);
  const adjusted=await fetcher(event.ticker,event.pdufaTargetDate,start,end,
   "all",key,secret,request);
  prices[event.ticker]=combine(raw,adjusted,start,end);
 }
 return build({candidates,shareFeed,primary,barsByTicker:prices});
}
async function main(){
 try{
  const get=f=>JSON.parse(fs.readFileSync(path.join(root,f),"utf8"));
  const credentials={key:process.env.APCA_API_KEY_ID||process.env.ALPACA_API_KEY_ID,
   secret:process.env.APCA_API_SECRET_KEY||process.env.ALPACA_SECRET_KEY};
  const result=await execute({...credentials,
   candidates:get("new-platform/frontend/data/raas-2024-2025-expanded-candidate-source-leads.json"),
   shareFeed:get("new-platform/frontend/data/raas-2024-2025-expanded-candidate-sec-snapshots.json"),
   primary:get("new-platform/frontend/data/raas-active-2024-2025-primary-source-leads.json")});
  const out=process.env.RAAS_EXPANDED_SEC_CAP_JSON||
   path.join(root,"raas-2024-2025-expanded-sec-cap-prices.json");
  const outCsv=process.env.RAAS_EXPANDED_SEC_CAP_CSV||
   path.join(root,"raas-2024-2025-expanded-sec-cap-prices.csv");
  for(const p of [out,outCsv])fs.mkdirSync(path.dirname(p),{recursive:true});
  fs.writeFileSync(out,JSON.stringify(result)+"\n");
  fs.writeFileSync(outCsv,csv(result));
  const summary={status:result.status,cases:result.sourceCaseCount,
   SECOriginalPublishedSnapshots:result.SECOriginalPublishedSnapshots,
   pairsPerCase:result.allValidPairsPerCase,
   evaluations:result.totalCaseWindowEvaluations,
   provisionalReturnWindows:result.provisionalReturnWindowCount,
   casesWithProvisionalReturns:result.distinctIssuerCasesWithProvisionalReturns,
   reasons:result.reasons,approvedTrades:0,approvedBestWindow:null};
  console.log(JSON.stringify(summary));
  if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
   "\n### Additional TVTX/URGN published SEC cover shares × Alpaca, research only\n\n"+
   JSON.stringify(summary,null,2)+"\n\nNo independently validated market cap or approved strategy.\n");
  if(result.status==="BLOCKED_NO_ALPACA_BARS")process.exitCode=1;
 }catch(e){
  console.error("RAAS_EXPANDED_CAP_FATAL_"+String(e.message||e).replace(/[^A-Z0-9_]/g,"_").slice(0,200));
  process.exitCode=1;
 }
}
if(require.main===module)main();
module.exports={checkSources,combine,inspectCase,build,csv,execute};
