/** Independent RAAS metric-level historical predictive review.
 * Scores are taken ONLY from a timestamped prior decision record, never
 * reconstructed after future readouts or FDA decisions.
 * This is a diagnostic, NOT validated approval of a metric for investing.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {programKey,type HistoricalFeed,type HistoricalValidation} from "./raas-historical-backtest";
export type MetricHistoricalRecord={
 caseId:string;nctId:string;ticker:string;drug:string;indication:string;
 stage:RaasStage;metricId:string;score:0|25|50|75|100;
 benchmarkId:string;ruleVersion:string;assessedAt:string;
 sourceUrl:string;sourcePublishedAt:string;method:string;
};
export type MetricHistoricalFeed={
 schemaVersion:1;scope:"RAAS_HISTORICAL_METRIC_SNAPSHOTS";
 sourceAsOf:string;note:string;records:MetricHistoricalRecord[];
};
export type MetricHistoricalDiagnostic={
 stage:RaasStage;metricId:string;name:string;
 independentPrograms:number;observedReturnPairs:number;
 benchmarkId:string|null;ruleVersion:string|null;protocolConsistent:boolean;
 holdoutTrainPrograms:number;holdoutTestPrograms:number;
 spearmanScoreToReturn:number|null;meanHighMinusLowPercent:number|null;
 positiveReturnRateHigh:number|null;positiveReturnRateLow:number|null;
 status:"INSUFFICIENT_EVIDENCE"|"REVIEW_ELIGIBLE_NOT_APPROVED";
 reason:string;
};
const day=(s:string)=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 Number.isFinite(Date.parse(s+"T00:00:00Z"))&&new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const url=(s:string)=>/^https:\/\/[^\s/]+\/\S+/.test(s);
const id=(x:{ticker:string;drug:string;indication:string})=>programKey(x);
const round=(v:number)=>Math.round(v*100)/100;
function ranks(nums:readonly number[]):number[]{
 const sorted=nums.map((v,i)=>({v,i})).sort((a,b)=>a.v-b.v);
 const out=nums.map(()=>0);
 for(let i=0;i<sorted.length;){
  let j=i+1;while(j<sorted.length&&sorted[j].v===sorted[i].v)j++;
  const rank=(i+j+1)/2;
  for(let k=i;k<j;k++)out[sorted[k].i]=rank;
  i=j;
 }
 return out;
}
function spearman(x:number[],y:number[]):number|null{
 if(x.length!==y.length||x.length<3)return null;
 const a=ranks(x),b=ranks(y);
 const avg=(z:number[])=>z.reduce((s,v)=>s+v,0)/z.length;
 const ma=avg(a),mb=avg(b);
 const cov=a.reduce((s,v,i)=>s+(v-ma)*(b[i]-mb),0);
 const va=a.reduce((s,v)=>s+(v-ma)**2,0),vb=b.reduce((s,v)=>s+(v-mb)**2,0);
 return va>0&&vb>0?round(cov/Math.sqrt(va*vb)):null;
}
export function parseMetricHistory(input:unknown):MetricHistoricalFeed{
 if(!input||typeof input!=="object")throw Error("RAAS_METRIC_HISTORY_INVALID");
 const feed=input as MetricHistoricalFeed;
 if(feed.schemaVersion!==1||feed.scope!=="RAAS_HISTORICAL_METRIC_SNAPSHOTS"||
  !day(feed.sourceAsOf)||!Array.isArray(feed.records)||feed.records.length>100000)
  throw Error("RAAS_METRIC_HISTORY_INVALID");
 const keys=new Set<string>();
 for(const r of feed.records){
  if(!r||!r.caseId?.trim()||!/^NCT\d{8}$/.test(r.nctId)||
   !r.ticker?.trim()||!r.drug?.trim()||!r.indication?.trim()||
   (r.stage!=="pre"&&r.stage!=="post")||
   !RAAS_METRIC_CATALOG[r.stage].some(g=>g.metrics.some(m=>m.id===r.metricId))||
   ![0,25,50,75,100].includes(r.score)||!r.benchmarkId?.trim()||
   !r.ruleVersion?.trim()||!r.method?.trim()||!day(r.assessedAt)||
   !day(r.sourcePublishedAt)||r.sourcePublishedAt>r.assessedAt||
   r.assessedAt>feed.sourceAsOf||!url(r.sourceUrl))
   throw Error("RAAS_METRIC_HISTORY_INVALID_RECORD");
  const k=r.caseId+"|"+r.stage+"|"+r.metricId;
  if(keys.has(k))throw Error("RAAS_METRIC_HISTORY_DUPLICATED");
  keys.add(k);
 }
 return feed;
}
/** Joins only historical trades that passed event-window validation and
 * grades demonstrably available before their original entry date.
 * Related NCTs are grouped into one opportunity; same asset cannot inflate n.
 */
export function evaluateMetricHistory(
 history:HistoricalFeed,
 outcomes:HistoricalValidation,
 rated:MetricHistoricalFeed
):MetricHistoricalDiagnostic[]{
 const cases=new Map(history.cases.map(c=>[c.caseId,c]));
 const accepted=new Map(outcomes.accepted.map(c=>[c.caseId,c]));
 const valid:{metricId:string;stage:RaasStage;caseId:string;program:string;returnPct:number;score:number;
  entryDate:string;exitDate:string;benchmarkId:string;ruleVersion:string}[]=[];
 for(const r of rated.records){
  const c=cases.get(r.caseId),outcome=accepted.get(r.caseId);
  if(!c||!outcome||r.stage!==c.stage||r.ticker.trim().toLowerCase()!==c.ticker.trim().toLowerCase()||
   id(r)!==id(c)||!c.nctIds.includes(r.nctId)||
   r.sourcePublishedAt>c.featureAsOf||r.assessedAt>c.predictionPublishedAt||
   r.assessedAt>c.entryDate||r.assessedAt>rated.sourceAsOf)continue;
  valid.push({metricId:r.metricId,stage:r.stage,caseId:r.caseId,
   program:outcome.programKey,returnPct:outcome.realizedReturnPercent,
   score:r.score,entryDate:outcome.entryDate,exitDate:outcome.exitDate,
   benchmarkId:r.benchmarkId,ruleVersion:r.ruleVersion});
 }
 const threshold=30;
 return (["pre","post"] as const).flatMap(stage=>
  RAAS_METRIC_CATALOG[stage].flatMap(cat=>cat.metrics.map(metric=>{
   const candidates=valid.filter(x=>x.stage===stage&&x.metricId===metric.id)
    .sort((a,b)=>a.entryDate.localeCompare(b.entryDate));
   const independent=new Map<string,typeof candidates[number]>();
   for(const c of candidates)if(!independent.has(c.program))independent.set(c.program,c);
   const p=[...independent.values()];
   // Never pool incompatible scoring definitions into a single correlation.
   const protocols=new Set(p.map(x=>x.benchmarkId+"|"+x.ruleVersion));
   const protocolConsistent=protocols.size===1;
   const low=p.filter(x=>x.score<=25),high=p.filter(x=>x.score>=75);
   const avg=(v:typeof p)=>v.reduce((s,x)=>s+x.returnPct,0)/v.length;
   const positive=(v:typeof p)=>round(v.filter(x=>x.returnPct>0).length/v.length*100);
   // Purged, chronological holdout: a training exit must be strictly before
   // the first test entry. Deduplicate company/therapy/indication first.
   let holdoutTrainPrograms=0,holdoutTestPrograms=0;
   for(const cutoff of new Set(p.map(x=>x.entryDate))){
    const train=p.filter(x=>x.exitDate<cutoff).length;
    const test=p.filter(x=>x.entryDate>=cutoff).length;
    if(Math.min(train,test)>Math.min(holdoutTrainPrograms,holdoutTestPrograms)){
     holdoutTrainPrograms=train;holdoutTestPrograms=test;
    }
   }
   const adequateCounts=p.length>=threshold&&low.length>=5&&high.length>=5;
   const enough=adequateCounts&&protocolConsistent&&
    holdoutTrainPrograms>=threshold&&holdoutTestPrograms>=threshold;
   return {stage,metricId:metric.id,name:metric.name,
    independentPrograms:p.length,observedReturnPairs:p.length,
    benchmarkId:protocolConsistent&&p.length?p[0].benchmarkId:null,
    ruleVersion:protocolConsistent&&p.length?p[0].ruleVersion:null,
    protocolConsistent,holdoutTrainPrograms,holdoutTestPrograms,
    spearmanScoreToReturn:protocolConsistent?spearman(p.map(x=>x.score),p.map(x=>x.returnPct)):null,
    meanHighMinusLowPercent:protocolConsistent&&low.length&&high.length?round(avg(high)-avg(low)):null,
    positiveReturnRateHigh:protocolConsistent&&high.length?positive(high):null,
    positiveReturnRateLow:protocolConsistent&&low.length?positive(low):null,
    status:enough?"REVIEW_ELIGIBLE_NOT_APPROVED" as const:"INSUFFICIENT_EVIDENCE" as const,
    reason:!protocolConsistent&&p.length>0?
      "Mixed benchmark or rule versions: metric returns cannot be pooled for validation.":
      !adequateCounts?"Insufficient unique, source-dated before-entry programs or high/low grade cohorts.":
      !enough?"No purged chronological 30-program training and 30-program holdout split is available.":
      "Comparable scoring protocol and chronological sample floors met; independent audit, statistical uncertainty and calibration approval are still required."
   };
  })));
}
