/** RAAS historical study/return ledger and non-leaky event-window evaluator.
 * Study rows with the same ticker+therapy+indication are ONE independent
 * asset opportunity, even when they involve different NCTs.
 * Never use future-known evidence or same-asset observations in both folds.
 */
import type {RaasStage} from "./raas-metric-specs";
export type HistoricalPrice={
 date:string;adjustedClose:number;currency:"USD";
 sourceUrl:string;sourcePublishedAt:string;
};
export type HistoricalCase={
 caseId:string;nctIds:string[];ticker:string;drug:string;indication:string;
 stage:RaasStage;marketCapUsdMillions:number;marketCapSourceUrl:string;marketCapSourcePublishedAt:string;
 featureAsOf:string;predictionPublishedAt:string;entryDate:string;exitDate:string;
 phase3ReadoutDate:string;phase3ReadoutSourceUrl:string;phase3ReadoutSourcePublishedAt:string;
 pdufaDate?:string;pdufaSourceUrl?:string;pdufaSourcePublishedAt?:string;
 entryPrice:HistoricalPrice;exitPrice:HistoricalPrice;
 predictedRaas:number|null;predictedReturnPercent:number|null;
 predictedScenarioSourceUrl?:string;
 roundTripCostsPercent:number;featureSources:{sourceUrl:string;publishedAt:string}[];
};
export type HistoricalFeed={
 schemaVersion:1;scope:"RAAS_HISTORICAL_EVENT_BACKTEST";sourceAsOf:string;
 note:string;cases:HistoricalCase[];
};
export type HistoricalResult={
 caseId:string;programKey:string;stage:RaasStage;entryDate:string;
 exitDate:string;realizedReturnPercent:number;predictedRaas:number|null;
 predictedReturnPercent:number|null;returnErrorPercent:number|null;
};
export type HistoricalDiagnostics={
 stage:RaasStage;cases:number;independentPrograms:number;predictionCoverage:number;
 maePercent:number|null;meanRealizedReturnPercent:number|null;
 spearmanRaasVsReturn:number|null;
 topVsBottomQuartileSpreadPercent:number|null;
 calibrationReady:boolean;reason:string;
};
export type HistoricalValidation={
 accepted:HistoricalResult[];excluded:{caseId:string;reason:string}[];
 byStage:HistoricalDiagnostics[];
};
const day=(x:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 Number.isFinite(Date.parse(x+"T00:00:00Z"))&&new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const url=(x:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(x);
const finite=(n:unknown):n is number=>typeof n==="number"&&Number.isFinite(n);
export const RAAS_HISTORICAL_MIN_INDEPENDENT_PROGRAMS=30;
export function programKey(x:{ticker:string;drug:string;indication:string}):string{
 return [x.ticker,x.drug,x.indication].map(v=>v.trim().toLowerCase().replace(/\s+/g," ")).join("|");
}
/** Minimum calendar safeguard. Full NYSE holiday-session evidence is still required for independent review. */
function weekday(date:string):boolean{
 const w=new Date(date+"T00:00:00Z").getUTCDay();
 return w!==0&&w!==6;
}
function calendarDayOffset(date:string,days:number):string{
 const time=Date.parse(date+"T00:00:00Z");
 return new Date(time+days*86400000).toISOString().slice(0,10);
}
export function parseHistoricalFeed(input:unknown):HistoricalFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_HISTORY_INVALID");
 const feed=input as HistoricalFeed;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_HISTORICAL_EVENT_BACKTEST"||
  !day(feed.sourceAsOf)||!Array.isArray(feed.cases)||feed.cases.length>10000)
  throw Error("RAAS_HISTORY_INVALID");
 const keys=new Set<string>();
 for(const c of feed.cases){
  if(!c||!c.caseId?.trim()||keys.has(c.caseId)||!Array.isArray(c.nctIds)||
   c.nctIds.length===0||new Set(c.nctIds).size!==c.nctIds.length||
   c.nctIds.some(x=>!/^NCT\d{8}$/.test(x))||
   !c.ticker?.trim()||!c.drug?.trim()||!c.indication?.trim()||
   (c.stage!=="pre"&&c.stage!=="post")||
   !finite(c.marketCapUsdMillions)||c.marketCapUsdMillions<300||c.marketCapUsdMillions>10000||
   !url(c.marketCapSourceUrl)||!day(c.marketCapSourcePublishedAt)||
   !day(c.featureAsOf)||!day(c.predictionPublishedAt)||!day(c.entryDate)||!day(c.exitDate)||
   !day(c.phase3ReadoutDate)||!url(c.phase3ReadoutSourceUrl)||
   !day(c.phase3ReadoutSourcePublishedAt)||
   !Array.isArray(c.featureSources)||c.featureSources.length===0||
   c.featureSources.some(x=>!x||!url(x.sourceUrl)||!day(x.publishedAt))||!finite(c.roundTripCostsPercent)||
   c.roundTripCostsPercent<0||c.roundTripCostsPercent>30||
   !c.entryPrice||!c.exitPrice)throw Error("RAAS_HISTORY_CASE_INVALID");
  keys.add(c.caseId);
  if(![c.entryPrice,c.exitPrice].every(p=>p.currency==="USD"&&
   finite(p.adjustedClose)&&p.adjustedClose>0&&
   day(p.date)&&day(p.sourcePublishedAt)&&url(p.sourceUrl)))throw Error("RAAS_HISTORY_PRICES_INVALID");
  if(c.predictedRaas!==null&&(!finite(c.predictedRaas)||c.predictedRaas<0||c.predictedRaas>100))
   throw Error("RAAS_HISTORY_GRADE_INVALID");
  if(c.predictedReturnPercent!==null&&(!finite(c.predictedReturnPercent)||c.predictedReturnPercent< -100||
   c.predictedReturnPercent>100000||!c.predictedScenarioSourceUrl||!url(c.predictedScenarioSourceUrl)))
   throw Error("RAAS_HISTORY_PREDICTION_INVALID");
  if(c.pdufaDate!==undefined&&(!day(c.pdufaDate)||!c.pdufaSourceUrl||
   !url(c.pdufaSourceUrl)||!c.pdufaSourcePublishedAt||!day(c.pdufaSourcePublishedAt)))
   throw Error("RAAS_HISTORY_PDUFA_INVALID");
 }
 return feed;
}
export function eligibleHistoricalCase(c:HistoricalCase,sourceAsOf:string):string|null{
 if(c.exitDate>sourceAsOf)return "Exit outcome not yet observable as of ledger date";
 if(c.featureSources.some(x=>x.publishedAt>c.featureAsOf))
  return "Look-ahead: evidence source was published after prediction features";
 if(c.featureAsOf>c.predictionPublishedAt||c.predictionPublishedAt>c.entryDate)
  return "Look-ahead: prediction or features not known at entry";
 if(c.marketCapSourcePublishedAt>c.entryDate)
  return "Look-ahead: entry-time market cap disclosed after entry";
 if(c.entryPrice.date!==c.entryDate||c.exitPrice.date!==c.exitDate)
  return "Price records do not match entry and exit dates";
 if(!weekday(c.entryDate)||!weekday(c.exitDate))
  return "Entry or exit falls on a weekend rather than a trading session";
 if(c.entryPrice.sourcePublishedAt>sourceAsOf||c.exitPrice.sourcePublishedAt>sourceAsOf)
  return "Historical price provenance not yet available";
 if(c.phase3ReadoutSourcePublishedAt>sourceAsOf||c.phase3ReadoutDate>sourceAsOf)
  return "Phase 3 outcome is not yet confirmed";
 if(c.entryDate>=c.exitDate)return "Invalid buy/sell chronology";
 if(c.stage==="pre"){
  if(c.entryDate>=c.phase3ReadoutDate||c.exitDate>=c.phase3ReadoutDate)
   return "TOP entry and exit must precede the public readout";
 }else{
  if(c.phase3ReadoutSourcePublishedAt>c.entryDate||c.phase3ReadoutDate>=c.entryDate)
   return "BOTTOM decision must follow publicly disclosed Phase 3 data";
  if(!c.pdufaDate||!c.pdufaSourcePublishedAt||
   c.pdufaSourcePublishedAt>c.entryDate||!c.pdufaSourceUrl)
   return "Verified exact-program PDUFA target was not known at BOTTOM entry";
  if(c.exitDate>calendarDayOffset(c.pdufaDate,-3))
   return "BOTTOM exit violates PDUFA-minus-three-calendar-day cutoff";
 }
 // Prevent results from using price/diagnostic information that did not exist when the signal was issued.
 if(c.entryPrice.sourcePublishedAt<c.entryDate||c.exitPrice.sourcePublishedAt<c.exitDate)
  return "Historical price source timestamp predates the observed session";
 if(c.predictedReturnPercent!==null&&c.featureAsOf>c.entryDate)
  return "Predicted return is not ex ante";
 return null;
}
const round=(v:number)=>Math.round(v*100)/100;
function rank(values:number[]):number[]{
 const order=values.map((value,index)=>({value,index})).sort((a,b)=>a.value-b.value);
 const ranks:number[]=Array(values.length).fill(0);
 for(let i=0;i<order.length;){
  let j=i+1;while(j<order.length&&order[j].value===order[i].value)j++;
  const r=(i+j-1)/2+1;
  for(let k=i;k<j;k++)ranks[order[k].index]=r;
  i=j;
 }
 return ranks;
}
function spearman(a:number[],b:number[]):number|null{
 if(a.length<3||a.length!==b.length)return null;
 const x=rank(a),y=rank(b),mx=x.reduce((s,v)=>s+v,0)/x.length;
 const my=y.reduce((s,v)=>s+v,0)/y.length;
 const top=x.reduce((s,v,i)=>s+(v-mx)*(y[i]-my),0);
 const vx=x.reduce((s,v)=>s+(v-mx)**2,0),vy=y.reduce((s,v)=>s+(v-my)**2,0);
 return vx>0&&vy>0?round(top/Math.sqrt(vx*vy)):null;
}
function diagnostics(stage:RaasStage,items:HistoricalResult[]):HistoricalDiagnostics{
 const groupCount=new Set(items.map(x=>x.programKey)).size;
 // RAAS-to-return ranking requires each independent company/therapy/indication
 // represented once, never treating separate NCTs as independent validation.
 const earliest=new Map<string,HistoricalResult>();
 for(const row of [...items].sort((a,b)=>a.entryDate.localeCompare(b.entryDate))){
  if(!earliest.has(row.programKey))earliest.set(row.programKey,row);
 }
 const singles=[...earliest.values()];
 const pairs=singles.filter((r):r is HistoricalResult & {predictedRaas:number}=>r.predictedRaas!==null);
 const forecasted=singles.filter((r):r is HistoricalResult & {predictedReturnPercent:number;returnErrorPercent:number}=>
  r.predictedReturnPercent!==null&&r.returnErrorPercent!==null);
 const n=singles.length;
 const mae=forecasted.length?forecasted.reduce((s,r)=>s+Math.abs(r.returnErrorPercent),0)/forecasted.length:null;
 let spread:null|number=null;
 if(pairs.length>=4){
  const sorted=[...pairs].sort((a,b)=>a.predictedRaas-b.predictedRaas);
  const q=Math.floor(sorted.length/4);
  const mean=(a:typeof sorted)=>a.reduce((s,r)=>s+r.realizedReturnPercent,0)/a.length;
  spread=round(mean(sorted.slice(-q))-mean(sorted.slice(0,q)));
 }
 const enough=groupCount>=RAAS_HISTORICAL_MIN_INDEPENDENT_PROGRAMS&&
  forecasted.length>=RAAS_HISTORICAL_MIN_INDEPENDENT_PROGRAMS&&
  pairs.length>=RAAS_HISTORICAL_MIN_INDEPENDENT_PROGRAMS;
 return {stage,cases:items.length,independentPrograms:groupCount,
  predictionCoverage:n?round(forecasted.length/n*100):0,
  maePercent:mae===null?null:round(mae),
  meanRealizedReturnPercent:n?round(singles.reduce((s,r)=>s+r.realizedReturnPercent,0)/n):null,
  spearmanRaasVsReturn:spearman(pairs.map(x=>x.predictedRaas),pairs.map(x=>x.realizedReturnPercent)),
  topVsBottomQuartileSpreadPercent:spread,
  calibrationReady:false,
  reason:!enough?"Insufficient independent, dated, out-of-sample asset opportunities. No calibration approval allowed.":
   "Minimum coverage met; additional walk-forward testing, statistical uncertainty, outcome audit and independent review still required."};
}
export function evaluateHistoricalFeed(feed:HistoricalFeed):HistoricalValidation{
 const accepted:HistoricalResult[]=[],excluded:HistoricalValidation["excluded"]=[];
 for(const c of feed.cases){
  const reason=eligibleHistoricalCase(c,feed.sourceAsOf);
  if(reason){excluded.push({caseId:c.caseId,reason});continue;}
  const realized=round((c.exitPrice.adjustedClose/c.entryPrice.adjustedClose-1)*100-c.roundTripCostsPercent);
  accepted.push({caseId:c.caseId,stage:c.stage,programKey:programKey(c),
   entryDate:c.entryDate,exitDate:c.exitDate,realizedReturnPercent:realized,
   predictedRaas:c.predictedRaas,predictedReturnPercent:c.predictedReturnPercent,
   returnErrorPercent:c.predictedReturnPercent===null?null:round(c.predictedReturnPercent-realized)});
 }
 return {accepted,excluded,byStage:(["pre","post"] as const).map(stage=>
  diagnostics(stage,accepted.filter(c=>c.stage===stage)))};
}
export type WalkForwardFold={stage:RaasStage;cutoffDate:string;trainIds:string[];testIds:string[];
 trainPrograms:number;testPrograms:number;status:"READY_FOR_REVIEW"|"INSUFFICIENT_DATA"};
/** Deterministic, purged temporal holdouts: no program appears on both sides
 * and no test ENTRY occurs before the latest training EXIT.
 * This organizes review; it is NOT model fitting or claimed validation.
 */
export function walkForwardFolds(results:readonly HistoricalResult[],stage:RaasStage):WalkForwardFold[]{
 const items=results.filter(r=>r.stage===stage).sort((a,b)=>a.entryDate.localeCompare(b.entryDate));
 const entryDates=[...new Set(items.map(r=>r.entryDate))];
 const out:WalkForwardFold[]=[];
 for(const cutoffDate of entryDates){
  const tests=items.filter(r=>r.entryDate>=cutoffDate);
  const testKeys=new Set(tests.map(r=>r.programKey));
  const train=items.filter(r=>r.exitDate<cutoffDate&&!testKeys.has(r.programKey));
  const eligibleTests=tests.filter(r=>!train.some(x=>x.programKey===r.programKey));
  const tp=new Set(train.map(r=>r.programKey)).size,ep=new Set(eligibleTests.map(r=>r.programKey)).size;
  if(!train.length||!eligibleTests.length)continue;
  out.push({stage,cutoffDate,trainIds:train.map(x=>x.caseId),
   testIds:eligibleTests.map(x=>x.caseId),trainPrograms:tp,testPrograms:ep,
   status:tp>=RAAS_HISTORICAL_MIN_INDEPENDENT_PROGRAMS&&
     ep>=RAAS_HISTORICAL_MIN_INDEPENDENT_PROGRAMS?"READY_FOR_REVIEW":"INSUFFICIENT_DATA"});
 }
 return out;
}
