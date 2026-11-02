/** TOP-only historical research observations.
 * Retrospective prices cannot be passed off as archived RAAS signals.
 */
export type TopRetrospectiveRecord={
 id:string;ticker:string;drug:string;indication:string;nctIds:string[];
 stage:"pre";historicalWindowSelected:"RETROSPECTIVELY";entryDecisionArchiveAvailable:false;
 priorGuidanceDate:string;priorGuidanceSourceUrl:string;priorGuidance:string;
 publicReadoutDate:string;publicReadoutSourceUrl:string;
 entry:{date:string;close:number;currency:"USD";sourceUrl:string};
 exit:{date:string;close:number;currency:"USD";sourceUrl:string};
 marketCapAtEntry:{usdMillions:number;sourceUrl:string;basis:string};
 eventQuality:{priceCorporateActionChecked:false;tradingFrictionAssessed:false;
 actualTradeOrArchivedPrediction:false;eligibleForValidatedRAAS:false};
 reviewStatus:"RETROSPECTIVE_EXAMPLE_ONLY";reviewNote:string;
};
export type TopRetrospectiveFeed={
 schemaVersion:1;scope:"RAAS_RETROSPECTIVE_PRE_READOUT_INTAKE";
 sourceAsOf:string;note:string;records:TopRetrospectiveRecord[];
};
export type TopRetrospectiveResult={
 id:string;ticker:string;stage:"pre";nctCount:number;
 entryDate:string;exitDate:string;entryClose:number;exitClose:number;
 marketCapUsdMillions:number;readoutDate:string;priorGuidanceDate:string;
 observedGrossChangePercent:number;forecastScore:null;forecastError:null;
 status:"RESEARCH_ONLY_NOT_CALIBRATED";
};
const date=(v:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(v)&&
 Number.isFinite(Date.parse(v+"T00:00:00Z"))&&
 new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
const source=(v:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(v);
const weekday=(s:string):boolean=>{
 const w=new Date(s+"T00:00:00Z").getUTCDay();return w!==0&&w!==6;
};
const positive=(v:unknown)=>typeof v==="number"&&Number.isFinite(v)&&v>0;
export function parseTopRetrospective(input:unknown):TopRetrospectiveFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_TOP_HISTORY_INVALID");
 const feed=input as TopRetrospectiveFeed;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_RETROSPECTIVE_PRE_READOUT_INTAKE"||
 !date(feed.sourceAsOf)||!Array.isArray(feed.records)||feed.records.length>5000)
  throw Error("RAAS_TOP_HISTORY_INVALID");
 const ids=new Set<string>();
 for(const r of feed.records){
  if(!r||!r.id?.trim()||ids.has(r.id)||!r.ticker?.trim()||
   !r.drug?.trim()||!r.indication?.trim()||r.stage!=="pre"||
   !Array.isArray(r.nctIds)||r.nctIds.length===0||
   r.nctIds.some(x=>!/^NCT\d{8}$/.test(x))||
   new Set(r.nctIds).size!==r.nctIds.length||
   r.historicalWindowSelected!=="RETROSPECTIVELY"||
   r.entryDecisionArchiveAvailable!==false||
   !date(r.priorGuidanceDate)||!source(r.priorGuidanceSourceUrl)||
   !r.priorGuidance?.trim()||!date(r.publicReadoutDate)||
   !source(r.publicReadoutSourceUrl)||!r.entry||!r.exit||
   !r.marketCapAtEntry||!r.eventQuality||
   r.eventQuality.priceCorporateActionChecked!==false||
   r.eventQuality.tradingFrictionAssessed!==false||
   r.eventQuality.actualTradeOrArchivedPrediction!==false||
   r.eventQuality.eligibleForValidatedRAAS!==false||
   r.reviewStatus!=="RETROSPECTIVE_EXAMPLE_ONLY"||
   !r.reviewNote?.trim())throw Error("RAAS_TOP_HISTORY_IDENTITY_INVALID");
  ids.add(r.id);
  for(const p of [r.entry,r.exit]){
   if(!date(p.date)||!weekday(p.date)||!positive(p.close)||
     p.currency!=="USD"||!source(p.sourceUrl))
    throw Error("RAAS_TOP_HISTORY_PRICE_INVALID");
  }
  if(!(r.priorGuidanceDate<=r.entry.date&&r.entry.date<r.exit.date&&
    r.exit.date<r.publicReadoutDate&&r.publicReadoutDate<=feed.sourceAsOf))
    throw Error("RAAS_TOP_HISTORY_WINDOW_INVALID");
  if(!positive(r.marketCapAtEntry.usdMillions)||
    r.marketCapAtEntry.usdMillions<300||r.marketCapAtEntry.usdMillions>10000||
    !source(r.marketCapAtEntry.sourceUrl)||!r.marketCapAtEntry.basis?.trim())
    throw Error("RAAS_TOP_HISTORY_MARKET_CAP_INVALID");
 }
 return feed;
}
export function topRetrospectiveResults(feed:TopRetrospectiveFeed):TopRetrospectiveResult[]{
 return feed.records.map(r=>({
  id:r.id,ticker:r.ticker,stage:r.stage,nctCount:r.nctIds.length,
  entryDate:r.entry.date,exitDate:r.exit.date,entryClose:r.entry.close,
  exitClose:r.exit.close,marketCapUsdMillions:r.marketCapAtEntry.usdMillions,
  readoutDate:r.publicReadoutDate,priorGuidanceDate:r.priorGuidanceDate,
  observedGrossChangePercent:Math.round((r.exit.close/r.entry.close-1)*10000)/100,
  forecastScore:null,forecastError:null,status:"RESEARCH_ONLY_NOT_CALIBRATED"
 }));
}
