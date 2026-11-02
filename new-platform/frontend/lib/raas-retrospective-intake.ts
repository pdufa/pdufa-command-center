/** Sourced historical reference windows: NEVER an archived investment forecast.
 * Research-only observations remain separated from the ex-ante calibration
 * ledger and cannot be promoted into it without pre-entry prediction records.
 */
import type {RaasStage} from "./raas-metric-specs";
export type RetrospectiveEvidence={
 kind:"PHASE3_PUBLIC_READOUT"|"PDUFA_CONFIRMED"|"PRE_ENTRY_COMPANY_UPDATE";
 date:string;sourceUrl:string;notes:string;
};
export type RetrospectiveClose={
 date:string;close:number;currency:"USD";
 priceKind:"VENDOR_REPORTED_CLOSE_UNADJUSTED_STATUS_UNKNOWN";
 sourceUrl:string;
};
export type RetrospectiveWindow={
 id:string;ticker:string;drug:string;indication:string;nctIds:string[];
 stage:RaasStage;historicalWindowSelected:"RETROSPECTIVELY";
 entryDecisionArchiveAvailable:false;verifiedBeforeEntry:RetrospectiveEvidence[];
 pdufaDate:string;entry:RetrospectiveClose;exit:RetrospectiveClose;
 marketCapAtEntry:{usdMillions:number;sourceUrl:string;basis:string};
 realizedFDAAction:{date:string;status:"FDA_APPROVED"|"FDA_REJECTED"|"FDA_DELAYED";sourceUrl:string;isPostEntryKnowledge:true};
 eventQuality:{
  priceCorporateActionChecked:false;exchangeHolidayCalendarChecked:false;
  tradingFrictionAssessed:false;actualTradeOrArchivedPrediction:false;
  eligibleForValidatedRAAS:false;
 };
 reviewStatus:"RETROSPECTIVE_EXAMPLE_ONLY";reviewNote:string;
};
export type RetrospectiveFeed={
 schemaVersion:1;scope:"RAAS_RETROSPECTIVE_EVIDENCE_INTAKE";sourceAsOf:string;
 note:string;records:RetrospectiveWindow[];
};
export type RetrospectiveResult={
 id:string;stage:RaasStage;programKey:string;ticker:string;
 entryDate:string;exitDate:string;entryClose:number;exitClose:number;
 marketCapUsdMillions:number;calendarCutoff:string;
 observedGrossChangePercent:number;forecastScore:null;forecastError:null;
 status:"RESEARCH_ONLY_NOT_CALIBRATED";
};
const day=(s:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const secure=(s:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(s);
const finitePositive=(n:unknown):n is number=>typeof n==="number"&&Number.isFinite(n)&&n>0;
const cutoff=(date:string,days:number):string=>
 new Date(Date.parse(date+"T00:00:00Z")+days*86400000).toISOString().slice(0,10);
const weekday=(date:string):boolean=>{
 const n=new Date(date+"T00:00:00Z").getUTCDay();return n!==0&&n!==6;
};
const key=(r:Pick<RetrospectiveWindow,"ticker"|"drug"|"indication">)=>
 [r.ticker,r.drug,r.indication].map(x=>x.toLowerCase().trim().replace(/\s+/g," ")).join("|");
export function parseRetrospectiveFeed(input:unknown):RetrospectiveFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_RETROSPECTIVE_FEED_INVALID");
 const f=input as RetrospectiveFeed;
 if(f.schemaVersion!==1||f.scope!=="RAAS_RETROSPECTIVE_EVIDENCE_INTAKE"||
 !day(f.sourceAsOf)||!Array.isArray(f.records)||f.records.length>5000)
  throw Error("RAAS_RETROSPECTIVE_FEED_INVALID");
 const seen=new Set<string>();
 for(const r of f.records){
  if(!r||!r.id?.trim()||seen.has(r.id)||!r.ticker?.trim()||
   !r.drug?.trim()||!r.indication?.trim()||r.stage!=="post"||
   !Array.isArray(r.nctIds)||r.nctIds.length===0||
   new Set(r.nctIds).size!==r.nctIds.length||
   r.nctIds.some(x=>!/^NCT\d{8}$/.test(x))||
   r.historicalWindowSelected!=="RETROSPECTIVELY"||
   r.entryDecisionArchiveAvailable!==false||!Array.isArray(r.verifiedBeforeEntry)||
   !r.verifiedBeforeEntry.length||!day(r.pdufaDate)||!r.entry||!r.exit||
   !r.marketCapAtEntry||!r.realizedFDAAction||!r.eventQuality||
   r.eventQuality.eligibleForValidatedRAAS!==false||
   r.eventQuality.actualTradeOrArchivedPrediction!==false||
   r.eventQuality.priceCorporateActionChecked!==false||
   r.eventQuality.exchangeHolidayCalendarChecked!==false||
   r.eventQuality.tradingFrictionAssessed!==false||
   r.reviewStatus!=="RETROSPECTIVE_EXAMPLE_ONLY"||
   !r.reviewNote?.trim())throw Error("RAAS_RETROSPECTIVE_IDENTITY_INVALID");
  seen.add(r.id);
  for(const p of [r.entry,r.exit]){
   if(!day(p.date)||!weekday(p.date)||!finitePositive(p.close)||
    p.currency!=="USD"||
    p.priceKind!=="VENDOR_REPORTED_CLOSE_UNADJUSTED_STATUS_UNKNOWN"||
    !secure(p.sourceUrl))throw Error("RAAS_RETROSPECTIVE_PRICE_INVALID");
  }
  if(r.entry.date>=r.exit.date||r.exit.date>f.sourceAsOf||
   r.exit.date>cutoff(r.pdufaDate,-3))throw Error("RAAS_RETROSPECTIVE_WINDOW_INVALID");
  if(!finitePositive(r.marketCapAtEntry.usdMillions)||
   r.marketCapAtEntry.usdMillions<300||r.marketCapAtEntry.usdMillions>10000||
   !secure(r.marketCapAtEntry.sourceUrl)||!r.marketCapAtEntry.basis?.trim())
   throw Error("RAAS_RETROSPECTIVE_MARKET_CAP_INVALID");
  if(!r.verifiedBeforeEntry.some(e=>e.kind==="PDUFA_CONFIRMED")||
   !r.verifiedBeforeEntry.some(e=>e.kind==="PHASE3_PUBLIC_READOUT")||
   r.verifiedBeforeEntry.some(e=>!day(e.date)||e.date>r.entry.date||
    !secure(e.sourceUrl)||!e.notes?.trim()))
   throw Error("RAAS_RETROSPECTIVE_SOURCE_INVALID");
  if(!day(r.realizedFDAAction.date)||
   r.realizedFDAAction.date<r.entry.date||
   r.realizedFDAAction.date>f.sourceAsOf||
   r.realizedFDAAction.isPostEntryKnowledge!==true||
   !secure(r.realizedFDAAction.sourceUrl)||
   !["FDA_APPROVED","FDA_REJECTED","FDA_DELAYED"].includes(r.realizedFDAAction.status))
   throw Error("RAAS_RETROSPECTIVE_OUTCOME_INVALID");
 }
 return f;
}
export function retrospectiveResults(feed:RetrospectiveFeed):RetrospectiveResult[]{
 return feed.records.map(r=>({
  id:r.id,stage:r.stage,programKey:key(r),ticker:r.ticker,
  entryDate:r.entry.date,exitDate:r.exit.date,
  entryClose:r.entry.close,exitClose:r.exit.close,
  marketCapUsdMillions:r.marketCapAtEntry.usdMillions,
  calendarCutoff:cutoff(r.pdufaDate,-3),
  observedGrossChangePercent:Math.round((r.exit.close/r.entry.close-1)*10000)/100,
  forecastScore:null,forecastError:null,status:"RESEARCH_ONLY_NOT_CALIBRATED"
 }));
}
