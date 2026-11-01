/**
 * One master TOOLS market-cap restriction, applied BEFORE the independent Phase
 * and FDA Special Designation breakdowns. Never apply a Phase-3-only census
 * before the Phase selector: that would erase the early-stage comparisons.
 *
 * Saved issuer market caps are dated source readings, not live quotes.
 * Missing or stale cap coverage is UNKNOWN, never zero or a qualified pass.
 */
import {isPoolTrial,poolStageStatistics} from "./pool-pipeline-funnel";
import {parseEvidenceCsv} from "./restriction-evidence";
import type {verifiedToolPool} from "./tools-pool-inventory";

type Snapshot=ReturnType<typeof verifiedToolPool>;
export const TOOL_MIN_CAP_USD=300_000_000;
export const TOOL_MAX_CAP_USD=10_000_000_000;
export type RestrictedToolsScope={
  scope:"DATED_300M_10B_ISSUER_MARKET_CAP_SCREEN";
  qualification:"NOT_VERIFIED";
  capAsOf:string;
  originalPoolTrials:number;
  screenedTrials:number;
  unverifiedCapTrials:number;
  outsideCapTrials:number;
  eligibleIssuers:number;
  excludedIssuerTrials:number;
  outstanding:["UNVERIFIED_AND_STALE_CAP_COVERAGE","CURRENT_LISTING_AND_CAP","FDA_NCT_EVIDENCE","PDUFA_AND_STUDY_ROLE"];
};
const tickerOk=(s:string)=>/^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(s);
const iso=(s:string)=>Number.isFinite(Date.parse(s))&&/^\d{4}-\d{2}-\d{2}T/.test(s);
const capTrusted=(source:string,ticker:string)=>
  source==="https://api.nasdaq.com/api/quote/"+ticker+"/summary?assetclass=stocks";
export function restrictedToolsSnapshot(
  snapshot:Snapshot,capsCsv:string,registryCsv:string,now=Date.now()
):{snapshot:Snapshot;scope:RestrictedToolsScope}{
  const caps=parseEvidenceCsv(capsCsv);
  const companies=parseEvidenceCsv(registryCsv);
  if(!caps.length||caps.length>5000||!companies.length||companies.length>5000||
    !["ticker","market_cap","market_cap_source","market_cap_checked_at","market_cap_status"].every(k=>k in caps[0])||
    !["ticker","exchange","status"].every(k=>k in companies[0]))
    throw Error("RESTRICTED_MARKET_CAP_SOURCE_INVALID");

  const listed=new Set<string>();
  const conflictedIssuers=new Set<string>();
  const registrySeen=new Set<string>();
  for(const row of companies){
    const ticker=(row.ticker||"").toUpperCase();
    if(!tickerOk(ticker)||registrySeen.has(ticker)){conflictedIssuers.add(ticker);continue;}
    registrySeen.add(ticker);
    if(["Nasdaq","NYSE"].includes(row.exchange)&&
      ["OK","AUTO_ADDED_DISCOVERY_EXCHANGE_VERIFIED"].includes(row.status))
      listed.add(ticker);
  }
  for(const ticker of conflictedIssuers)listed.delete(ticker);
  const capsByTicker=new Map<string,number>();
  const capSeen=new Set<string>(),conflictedCaps=new Set<string>();
  let latestChecked=0;
  for(const row of caps){
    const ticker=(row.ticker||"").toUpperCase();
    if(!tickerOk(ticker)||capSeen.has(ticker)){conflictedCaps.add(ticker);continue;}
    capSeen.add(ticker);
    const cap=Number(row.market_cap),at=Date.parse(row.market_cap_checked_at||"");
    if(row.market_cap_status!=="VERIFIED"||!Number.isFinite(cap)||cap<=0||
      !iso(row.market_cap_checked_at||"")||!Number.isFinite(at)||
      at>now+300000||now-at>30*86400000||
      !capTrusted(row.market_cap_source||"",ticker))continue;
    capsByTicker.set(ticker,cap);
    latestChecked=Math.max(latestChecked,at);
  }
  for(const ticker of conflictedCaps)capsByTicker.delete(ticker);
  if(!capsByTicker.size||!Number.isFinite(latestChecked))
    throw Error("RESTRICTED_MARKET_CAP_SOURCE_UNAVAILABLE");

  let unverifiedCapTrials=0,outsideCapTrials=0,excludedIssuerTrials=0;
  const poolRows=snapshot.poolRows.filter(row=>{
    if(!isPoolTrial(row))return false;
    const ticker=(row.ticker||"").toUpperCase();
    if(!tickerOk(ticker)||!listed.has(ticker)){excludedIssuerTrials++;return false;}
    const cap=capsByTicker.get(ticker);
    if(cap===undefined){unverifiedCapTrials++;return false;}
    if(cap<TOOL_MIN_CAP_USD||cap>TOOL_MAX_CAP_USD){outsideCapTrials++;return false;}
    return true;
  });
  const stageStats=poolStageStatistics(poolRows);
  if(stageStats.trials===0)throw Error("RESTRICTED_MARKET_CAP_NO_RECONCILED_TRIALS");
  const scope:RestrictedToolsScope={
    scope:"DATED_300M_10B_ISSUER_MARKET_CAP_SCREEN",
    qualification:"NOT_VERIFIED",
    capAsOf:new Date(latestChecked).toISOString(),
    originalPoolTrials:snapshot.stageStats.trials,
    screenedTrials:stageStats.trials,
    unverifiedCapTrials,outsideCapTrials,excludedIssuerTrials,
    eligibleIssuers:new Set(poolRows.map(row=>row.ticker.toUpperCase())).size,
    outstanding:["UNVERIFIED_AND_STALE_CAP_COVERAGE","CURRENT_LISTING_AND_CAP","FDA_NCT_EVIDENCE","PDUFA_AND_STUDY_ROLE"]
  };
  return {snapshot:{...snapshot,poolRows,stageStats},scope};
}
