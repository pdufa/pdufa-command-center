/** Source- and time-gated RAAS pilot calculations. No missing input is scored zero. */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
export type Snapshot="ENTRY"|"CURRENT"|"EXIT";
export type ObservationKind="active_control_mean_change"|"active_control_response"|"single_arm_response"|"cash_balance"|"readout_window"|"study_design";
export type RaasObservation={
 id:string;metricIds:string[];kind:ObservationKind;title:string;
 unit:string;assessmentDate:string;measurementDate:string;sourceUrl:string;method:string;note:string;
 activeChange?:number;controlChange?:number;activePercent?:number;controlPercent?:number;
 value?:number;valueText?:string;
};
export type RaasPilotRecord={nctId:string;ticker:string;drug:string;indication:string;stage:RaasStage;observations:RaasObservation[]};
export type RaasPilotFeed={schemaVersion:1;sourceAsOf:string;scope:"HISTORICAL_PHASE3_RAAS_PILOT_OBSERVATIONS";note:string;records:RaasPilotRecord[]};
export type MetricRating={
 nctId:string;ticker:string;stage:RaasStage;snapshot:Snapshot;metricId:string;
 score:0|25|50|75|100;assessedAt:string;sourceDate:string;sourceUrl:string;
 benchmarkId:string;method:string;evidenceId:string;status:"VERIFIED";
};
export type RiskGate={name:string;status:"PASSED"|"FAILED"|"UNKNOWN";sourceUrl?:string;sourceDate?:string};
export type RaasResult={
 score:number|null;categories:Array<{id:string;name:string;weight:number;score:number|null;graded:number;total:number}>;
 missing:string[];rejected:string[];blocked:boolean;reason:string;graded:number;total:30;
};
const dateOk=(v:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(v)&&
 Number.isFinite(Date.parse(v+"T00:00:00Z"))&&new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
const urlOk=(v:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(v);
const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
const finite=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const validPercent=(v:unknown):v is number=>finite(v)&&v>=0&&v<=100;
export function parseRaasPilotFeed(input:unknown):RaasPilotFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_FEED_INVALID");
 const raw=input as RaasPilotFeed;
 if(raw.schemaVersion!==1||raw.scope!=="HISTORICAL_PHASE3_RAAS_PILOT_OBSERVATIONS"||
  !raw.sourceAsOf||!dateOk(raw.sourceAsOf)||!Array.isArray(raw.records)||raw.records.length>2000)
  throw Error("RAAS_FEED_INVALID");
 const ids=new Set<string>(),obsIds=new Set<string>();
 for(const r of raw.records){
  if(!r||!/^NCT\d{8}$/.test(r.nctId)||!r.ticker||!r.drug||!r.indication||
   (r.stage!=="pre"&&r.stage!=="post")||!Array.isArray(r.observations))
   throw Error("RAAS_IDENTITY_INVALID");
  const key=[r.nctId,r.ticker,r.drug,r.indication,r.stage].map(s=>s.toLowerCase()).join("|");
  if(ids.has(key))throw Error("RAAS_DUPLICATE_TRIAL");ids.add(key);
  const validMetrics=new Set(RAAS_METRIC_CATALOG[r.stage].flatMap(c=>c.metrics.map(m=>m.id)));
  for(const o of r.observations){
   if(!o||!o.id||obsIds.has(o.id)||!o.title||!o.method||!o.note||!o.unit||
    !Array.isArray(o.metricIds)||o.metricIds.length===0||
    o.metricIds.some(id=>!validMetrics.has(id))||
    !dateOk(o.assessmentDate)||!dateOk(o.measurementDate)||
    o.assessmentDate>raw.sourceAsOf||o.measurementDate>o.assessmentDate||
    !urlOk(o.sourceUrl))throw Error("RAAS_OBSERVATION_INVALID");
   obsIds.add(o.id);
   if(o.kind==="active_control_mean_change"&&(!finite(o.activeChange)||!finite(o.controlChange)))throw Error("RAAS_MEAN_INVALID");
   if(o.kind==="active_control_response"&&(!validPercent(o.activePercent)||!validPercent(o.controlPercent)))throw Error("RAAS_RESPONSE_INVALID");
   if(o.kind==="single_arm_response"&&!validPercent(o.activePercent))throw Error("RAAS_RATE_INVALID");
   if(o.kind==="cash_balance"&&(!finite(o.value)||o.value<0))throw Error("RAAS_CASH_INVALID");
   if((o.kind==="readout_window"||o.kind==="study_design")&&!o.valueText)throw Error("RAAS_TEXT_INVALID");
  }
 }
 return raw;
}
export function observationsForTrial(
 feed:RaasPilotFeed,trial:{nctId:string;ticker:string;drug:string;indication:string},
 stage:RaasStage,asOf:string
):RaasObservation[]{
 if(!dateOk(asOf))return [];
 const matches=feed.records.filter(r=>r.stage===stage&&r.nctId===trial.nctId&&
  same(r.ticker,trial.ticker)&&same(r.drug,trial.drug)&&same(r.indication,trial.indication));
 return matches.length===1?matches[0].observations.filter(o=>o.assessmentDate<=asOf):[];
}
/** Clinical measurements or corporate balances, NOT RAAS grades. */
export function observedCalculation(o:RaasObservation):{label:string;value:number;unit:string}|null{
 if(o.kind==="active_control_mean_change"&&typeof o.activeChange==="number"&&typeof o.controlChange==="number"&&
   o.activeChange<=0&&o.controlChange<=0)
  return {label:"Additional symptom-scale reduction versus placebo",value:Math.round((o.controlChange-o.activeChange)*100)/100,unit:o.unit};
 if(o.kind==="active_control_response"&&typeof o.activePercent==="number"&&typeof o.controlPercent==="number")
  return {label:"Absolute responder-rate difference versus placebo",value:Math.round((o.activePercent-o.controlPercent)*100)/100,unit:"percentage points"};
 if(o.kind==="single_arm_response"&&typeof o.activePercent==="number")
  return {label:"Reported treated-arm responder rate (no comparator available)",value:o.activePercent,unit:"%"};
 if(o.kind==="cash_balance"&&typeof o.value==="number")
  return {label:"Reported cash-related balance (not cash runway)",value:o.value,unit:o.unit};
 return null;
}
export function computeRaasScore(input:{
 stage:RaasStage;snapshot:Snapshot;asOf:string;trial:{nctId:string;ticker:string};
 ratings:readonly MetricRating[];gates:readonly RiskGate[];
}):RaasResult{
 const categories=RAAS_METRIC_CATALOG[input.stage];
 const metricIds=categories.flatMap(c=>c.metrics.map(m=>m.id));
 const accepted=new Map<string,MetricRating>(),rejected:string[]=[];
 for(const r of input.ratings){
  const okay=r.nctId===input.trial.nctId&&same(r.ticker,input.trial.ticker)&&
   r.stage===input.stage&&r.snapshot===input.snapshot&&metricIds.includes(r.metricId)&&
   dateOk(input.asOf)&&dateOk(r.assessedAt)&&dateOk(r.sourceDate)&&
   r.sourceDate<=r.assessedAt&&r.assessedAt<=input.asOf&&urlOk(r.sourceUrl)&&
   !!r.method&&!!r.benchmarkId&&!!r.evidenceId&&r.status==="VERIFIED"&&
   [0,25,50,75,100].includes(r.score);
  if(!okay||accepted.has(r.metricId)||rejected.includes(r.metricId)){
   accepted.delete(r.metricId);rejected.push(r.metricId);continue;
  }
  accepted.set(r.metricId,r);
 }
 const missing=metricIds.filter(id=>!accepted.has(id));
 const gradedCategories=categories.map(c=>{
  const values=c.metrics.map(m=>accepted.get(m.id)?.score);
  const present=values.filter((v):v is 0|25|50|75|100=>v!==undefined);
  return {id:c.id,name:c.name,weight:c.weight,graded:present.length,total:5,
   score:present.length===5?present.reduce((a,b)=>a+b,0)/5:null};
 });
 const blocked=input.gates.length===0||input.gates.some(g=>g.status!=="PASSED");
 const full=missing.length===0&&rejected.length===0&&!blocked;
 const score=full?Math.round(gradedCategories.reduce((s,c)=>s+(c.score??0)*c.weight/100,0)*10)/10:null;
 const reason=blocked?"Eligibility or critical-risk gates have not all passed.":
  rejected.length?"At least one rating failed source or time validation.":
  missing.length?"Missing verified metric grades; incomplete data are not zero.":
  "Source checks passed; independent historical validation is still required.";
 return {score,categories:gradedCategories,missing,rejected,blocked,reason,graded:30-missing.length,total:30};
}
export type RaasReturnScenario={
 entryPrice:number;bearPrice:number;basePrice:number;bullPrice:number;
 bearProbability:number;baseProbability:number;bullProbability:number;
 entryDate:string;exitDate:string;priceSourceUrl:string;priceSourceDate:string;
 scenarioMethod:string;scenarioSourceUrl:string;calibrationId:string;
};
export type RaasScenarioResult={
 upsidePercent:number;downsidePercent:number;rewardDownsideRatio:number;
 probabilityWeightedReturnPercent:number;bearReturnPercent:number;baseReturnPercent:number;bullReturnPercent:number;
};
const pct=(n:number)=>Math.round(n*100)/100;
export function calculateRaasReturn(s:RaasReturnScenario,asOf:string):RaasScenarioResult|null{
 const nums=[s.entryPrice,s.bearPrice,s.basePrice,s.bullPrice,s.bearProbability,s.baseProbability,s.bullProbability];
 if(!dateOk(asOf)||!dateOk(s.entryDate)||!dateOk(s.exitDate)||!dateOk(s.priceSourceDate)||
  s.priceSourceDate>s.entryDate||s.entryDate>asOf||s.exitDate<=s.entryDate||
  !urlOk(s.priceSourceUrl)||!urlOk(s.scenarioSourceUrl)||!s.scenarioMethod||!s.calibrationId||
  !nums.every(finite)||s.entryPrice<=0||s.bearPrice<0||s.bearPrice>s.basePrice||s.basePrice>s.bullPrice||
  s.bearProbability<0||s.baseProbability<0||s.bullProbability<0||
  Math.abs(s.bearProbability+s.baseProbability+s.bullProbability-1)>0.000001)return null;
 const bear=s.bearPrice/s.entryPrice-1,base=s.basePrice/s.entryPrice-1,bull=s.bullPrice/s.entryPrice-1;
 return {upsidePercent:pct(bull*100),downsidePercent:pct((1-s.bearPrice/s.entryPrice)*100),
  rewardDownsideRatio:s.bearPrice<s.entryPrice&&s.bullPrice>s.entryPrice?pct((s.bullPrice-s.entryPrice)/(s.entryPrice-s.bearPrice)):0,
  probabilityWeightedReturnPercent:pct((bear*s.bearProbability+base*s.baseProbability+bull*s.bullProbability)*100),
  bearReturnPercent:pct(bear*100),baseReturnPercent:pct(base*100),bullReturnPercent:pct(bull*100)};
}
