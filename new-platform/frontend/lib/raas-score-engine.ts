/** RAAS calculation and exact-program observation validation, v1.
 * Data availability is NOT a scientific, investment, or regulatory grade.
 * No forward price or PDUFA date is created from the historical issuer census.
 */
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
 score:0|25|50|75|100;
 assessedAt:string;sourceDate:string;sourceUrl:string;
 benchmarkId:string;method:string;evidenceId:string;status:"VERIFIED";
};
export type RiskGate={name:string;status:"PASSED"|"FAILED"|"UNKNOWN";sourceUrl?:string;sourceDate?:string};
export type RaasResult={
 score:number|null;categories:{id:string;name:string;weight:number;score:number|null;graded:number;total:number}[];
 missing:string[];rejected:string[];blocked:boolean;reason:string;graded:number;total:30;
};
const dateOk=(v:string):boolean=>/^\d{4}-\d{2}-\d{2}$/.test(v)&&
 Number.isFinite(Date.parse(v+"T00:00:00Z"))&&
 new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
const urlOk=(v:string):boolean=>/^https:\/\/[^\s/]+\/\S+/.test(v);
const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
const finite=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const validPercent=(v:unknown):v is number=>finite(v)&&v>=0&&v<=100;
/** All pilot records are checked as data, not inferred from matching ticker alone. */
export function parseRaasPilotFeed(input:unknown):RaasPilotFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_FEED_INVALID");
 const raw=input as Partial<RaasPilotFeed>;
 if(raw.schemaVersion!==1||raw.scope!=="HISTORICAL_PHASE3_RAAS_PILOT_OBSERVATIONS"||
    !raw.sourceAsOf||!dateOk(raw.sourceAsOf)||!Array.isArray(raw.records)||raw.records.length>2000)
    throw Error("RAAS_FEED_INVALID");
 const keys=new Set<string>();const obsIds=new Set<string>();
 for(const r of raw.records){
  if(!/^NCT\d{8}$/.test(r.nctId)||!r.ticker?.trim()||!r.drug?.trim()||
     !r.indication?.trim()||!["pre","post"].includes(r.stage)||!Array.isArray(r.observations))
     throw Error("RAAS_IDENTITY_INVALID");
  const key=[r.nctId,r.ticker,r.drug,r.indication,r.stage].map(s=>s.toLowerCase()).join("|");
  if(keys.has(key))throw Error("RAAS_IDENTITY_DUPLICATE");
  keys.add(key);
  const known=new Set(RAAS_METRIC_CATALOG[r.stage].flatMap(c=>c.metrics.map(m=>m.id)));
  for(const o of r.observations){
   if(!o.id?.trim()||obsIds.has(o.id)||!o.title?.trim()||!o.method?.trim()||
     !o.note?.trim()||!o.unit?.trim()||!Array.isArray(o.metricIds)||o.metricIds.length===0||
     o.metricIds.some(id=>!known.has(id))||!dateOk(o.assessmentDate)||
     !dateOk(o.measurementDate)||o.assessmentDate>raw.sourceAsOf||
     o.measurementDate>o.assessmentDate||!urlOk(o.sourceUrl))
     throw Error("RAAS_OBSERVATION_INVALID");
   obsIds.add(o.id);
   if(o.kind==="active_control_mean_change"&&(!finite(o.activeChange)||!finite(o.controlChange)))
    throw Error("RAAS_MEAN_INVALID");
   if(o.kind==="active_control_response"&&(!validPercent(o.activePercent)||!validPercent(o.controlPercent)))
    throw Error("RAAS_RESPONSE_INVALID");
   if(o.kind==="single_arm_response"&&!validPercent(o.activePercent))
    throw Error("RAAS_SINGLE_ARM_INVALID");
   if(o.kind==="cash_balance"&&(!finite(o.value)||o.value<0))
    throw Error("RAAS_CASH_INVALID");
   if((o.kind==="readout_window"||o.kind==="study_design")&&!o.valueText?.trim())
    throw Error("RAAS_TEXT_INVALID");
  }
 }
 return raw as RaasPilotFeed;
}
export function observationsForTrial(
 feed:RaasPilotFeed,trial:{nctId:string;ticker:string;drug:string;indication:string},stage:RaasStage,
 asOf:string
):RaasObservation[]{
 if(!dateOk(asOf))return [];
 const matches=feed.records.filter(r=>r.stage===stage&&r.nctId===trial.nctId&&
  same(r.ticker,trial.ticker)&&same(r.drug,trial.drug)&&same(r.indication,trial.indication));
 if(matches.length!==1)return [];
 return matches[0].observations.filter(o=>o.assessmentDate<=asOf);
}
/** Numerical measurements from observed data only. They are not RAAS 0–100 scores. */
export function observedCalculation(o:RaasObservation):{label:string;value:number;unit:string}|null{
 if(o.kind==="active_control_mean_change"&&finite(o.activeChange)&&finite(o.controlChange)){
  // Data are mean CHANGE on symptom burden scale; reduction is negative.
  if(o.activeChange>0||o.controlChange>0)return null;
  return {label:"Additional symptom-scale reduction versus placebo",value:Math.round((o.controlChange-o.activeChange)*100)/100,unit:o.unit};
 }
 if(o.kind==="active_control_response"&&validPercent(o.activePercent)&&validPercent(o.controlPercent))
  return {label:"Absolute responder-rate difference versus placebo",value:Math.round((o.activePercent-o.controlPercent)*100)/100,unit:"percentage points"};
 if(o.kind==="single_arm_response"&&validPercent(o.activePercent))
  return {label:"Reported treated-arm responder rate (no comparator available)",value:o.activePercent,unit:"%"};
 if(o.kind==="cash_balance"&&finite(o.value))
  return {label:"Reported cash-related balance (not cash runway)",value:o.value,unit:o.unit};
 return null;
}
const allMetrics=(stage:RaasStage)=>RAAS_METRIC_CATALOG[stage].flatMap(g=>g.metrics);
/** Strict all-or-nothing grading: incomplete category/overall ratings remain null.
 * Gates operate independently from attractive weighted numerical averages.
 */
export function computeRaasScore(input:{
 stage:RaasStage;snapshot:Snapshot;asOf:string;
 trial:{nctId:string;ticker:string};ratings:readonly MetricRating[];gates:readonly RiskGate[];
}):RaasResult{
 const categories=RAAS_METRIC_CATALOG[input.stage];
 const validIds=new Set(allMetrics(input.stage).map(m=>m.id));
 const accepted=new Map<string,MetricRating>();
 const rejected:string[]=[];
 const identity=(r:MetricRating)=>r.nctId===input.trial.nctId&&same(r.ticker,input.trial.ticker)&&
  r.stage===input.stage&&r.snapshot===input.snapshot;
 for(const r of input.ratings){
  if(!identity(r)||!validIds.has(r.metricId)||!dateOk(input.asOf)||
     !dateOk(r.assessedAt)||!dateOk(r.sourceDate)||
     r.sourceDate>r.assessedAt||r.assessedAt>input.asOf||
     !urlOk(r.sourceUrl)||!r.method.trim()||!r.benchmarkId.trim()||
     !r.evidenceId.trim()||r.status!=="VERIFIED"||![0,25,50,75,100].includes(r.score)){
    rejected.push(r.metricId);continue;
  }
  if(accepted.has(r.metricId)){accepted.delete(r.metricId);rejected.push(r.metricId);continue;}
  if(!rejected.includes(r.metricId))accepted.set(r.metricId,r);
 }
 const missing=allMetrics(input.stage).filter(x=>!accepted.has(x.id)).map(x=>x.id);
 const scoredCategories=categories.map(c=>{
  const scores=c.metrics.map(m=>accepted.get(m.id)?.score);
  const graded=scores.filter((s):s is MetricRating["score"]=>s!==undefined);
  return {id:c.id,name:c.name,weight:c.weight,
   score:graded.length===c.metrics.length?graded.reduce((a,b)=>a+b,0)/c.metrics.length:null,
   graded:graded.length,total:c.metrics.length};
 });
 // FAIL or UNKNOWN gates both prevent full confidence, with explicit status.
 const blocked=input.gates.some(g=>g.status!=="PASSED")||input.gates.length===0;
 const full=missing.length===0&&!blocked&&rejected.length===0;
 const score=full?Math.round(scoredCategories.reduce((sum,c)=>sum+(c.score??0)*c.weight/100,0)*10)/10:null;
 const reason=blocked?"Eligibility or critical-risk gates have not all passed.":
  rejected.length?"At least one rating failed source or time validation.":
  missing.length?"Missing verified metric grades; incomplete data are not zero.":
  "Complete sourced ratings with eligibility gates passed (model still requires independent validation).";
 return {score,categories:scoredCategories,missing,rejected,blocked,reason,graded:30-missing.length,total:30};
}
export type RaasReturnScenario={
 entryPrice:number;bearPrice:number;basePrice:number;bullPrice:number;
 bearProbability:number;baseProbability:number;bullProbability:number;
 entryDate:string;exitDate:string;priceSourceUrl:string;priceSourceDate:string;
 scenarioMethod:string;scenarioSourceUrl:string;calibrationId:string;
};
export type RaasScenarioResult={
 upsidePercent:number;downsidePercent:number;rewardDownsideRatio:number;
 probabilityWeightedReturnPercent:number;bearReturnPercent:number;baseReturnPercent:number;
 bullReturnPercent:number;
};
const pct=(n:number)=>Math.round(n*100)/100;
/** Calculate forward payoff only when dated, sourced and internally valid. */
export function calculateRaasReturn(s:RaasReturnScenario,asOf:string):RaasScenarioResult|null{
 if(!dateOk(asOf)||!dateOk(s.entryDate)||!dateOk(s.exitDate)||!dateOk(s.priceSourceDate)||
    s.priceSourceDate>s.entryDate||s.entryDate>asOf||s.exitDate<=s.entryDate||
    !urlOk(s.priceSourceUrl)||!urlOk(s.scenarioSourceUrl)||!s.scenarioMethod.trim()||
    !s.calibrationId.trim()||
    ![s.entryPrice,s.bearPrice,s.basePrice,s.bullPrice,s.bearProbability,s.baseProbability,s.bullProbability].every(finite)||
    s.entryPrice<=0||s.bearPrice<0||s.bearPrice>s.basePrice||s.basePrice>s.bullPrice||
    s.bearProbability<0||s.baseProbability<0||s.bullProbability<0||
    Math.abs(s.bearProbability+s.baseProbability+s.bullProbability-1)>0.000001)return null;
 const bear=s.bearPrice/s.entryPrice-1,base=s.basePrice/s.entryPrice-1,bull=s.bullPrice/s.entryPrice-1;
 return {upsidePercent:pct(bull*100),downsidePercent:pct((1-s.bearPrice/s.entryPrice)*100),
  rewardDownsideRatio:s.bearPrice<s.entryPrice&&s.bullPrice>s.entryPrice?pct((s.bullPrice-s.entryPrice)/(s.entryPrice-s.bearPrice)):0,
  probabilityWeightedReturnPercent:pct((bear*s.bearProbability+base*s.baseProbability+bull*s.bullProbability)*100),
  bearReturnPercent:pct(bear*100),baseReturnPercent:pct(base*100),bullReturnPercent:pct(bull*100)};
}
