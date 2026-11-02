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
 holdoutCutoffDate:string|null;holdoutIssuerPurgedPrograms:number;
 holdoutHighPrograms:number;holdoutLowPrograms:number;
 holdoutSpearmanScoreToReturn:number|null;holdoutHighMinusLowPercent:number|null;
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
  entryDate:string;exitDate:string;benchmarkId:string;ruleVersion:string;ticker:string}[]=[];
 for(const r of rated.records){
  const c=cases.get(r.caseId),outcome=accepted.get(r.caseId);
  if(!c||!outcome||r.stage!==c.stage||r.ticker.trim().toLowerCase()!==c.ticker.trim().toLowerCase()||
   id(r)!==id(c)||!c.nctIds.includes(r.nctId)||
   r.sourcePublishedAt>c.featureAsOf||r.assessedAt>c.predictionPublishedAt||
   r.assessedAt>c.entryDate||r.assessedAt>rated.sourceAsOf)continue;
  valid.push({metricId:r.metricId,stage:r.stage,caseId:r.caseId,
   program:outcome.programKey,returnPct:outcome.realizedReturnPercent,
   score:r.score,entryDate:outcome.entryDate,exitDate:outcome.exitDate,
   benchmarkId:r.benchmarkId,ruleVersion:r.ruleVersion,ticker:r.ticker.trim().toUpperCase()});
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
   // Choose the fold solely from timestamp and issuer counts, never from
   // returns. All prior positions for an issuer in the test set are purged
   // from training. Within each fold a ticker counts once, even when its
   // different drugs / indications have distinct program IDs.
   const distinctIssuers=(rows:typeof p):typeof p=>{
    const seen=new Set<string>();
    return rows.filter(x=>{
     if(seen.has(x.ticker))return false;
     seen.add(x.ticker);return true;
    });
   };
   let chosen:{cutoff:string;train:typeof p;test:typeof p;purged:number}|null=null;
   for(const cutoff of new Set(p.map(x=>x.entryDate))){
    const testCandidates=p.filter(x=>x.entryDate>=cutoff);
    const testIssuers=new Set(testCandidates.map(x=>x.ticker));
    const trainBeforeCutoff=p.filter(x=>x.exitDate<cutoff);
    const train=distinctIssuers(trainBeforeCutoff.filter(x=>!testIssuers.has(x.ticker)));
    const test=distinctIssuers(testCandidates);
    const purged=trainBeforeCutoff.filter(x=>testIssuers.has(x.ticker)).length;
    if(!train.length||!test.length)continue;
    if(!chosen||
       Math.min(train.length,test.length)>Math.min(chosen.train.length,chosen.test.length)||
       (Math.min(train.length,test.length)===Math.min(chosen.train.length,chosen.test.length)&&
        train.length+test.length>chosen.train.length+chosen.test.length)){
     chosen={cutoff,train,test,purged};
    }
   }
   const holdoutTrainPrograms=chosen?.train.length??0;
   const holdoutTestPrograms=chosen?.test.length??0;
   const heldOut=chosen?.test??[];
   const holdoutLow=heldOut.filter(x=>x.score<=25);
   const holdoutHigh=heldOut.filter(x=>x.score>=75);
   const holdoutSpearman=protocolConsistent?
     spearman(heldOut.map(x=>x.score),heldOut.map(x=>x.returnPct)):null;
   const holdoutSpread=protocolConsistent&&holdoutLow.length&&holdoutHigh.length?
     round(avg(holdoutHigh)-avg(holdoutLow)):null;
   const adequateCounts=p.length>=threshold&&low.length>=5&&high.length>=5;
   const adequateHoldoutCohorts=holdoutLow.length>=5&&holdoutHigh.length>=5;
   // Positive in-sample associations alone are not validation. The only
   // evidence accepted for review must work on untouched later issuers.
   const holdoutSupportsDirection=holdoutSpearman!==null&&
     holdoutSpearman>0&&holdoutSpread!==null&&holdoutSpread>0;
   const enough=adequateCounts&&protocolConsistent&&
    holdoutTrainPrograms>=threshold&&holdoutTestPrograms>=threshold&&
    adequateHoldoutCohorts&&holdoutSupportsDirection;
   return {stage,metricId:metric.id,name:metric.name,
    independentPrograms:p.length,observedReturnPairs:p.length,
    benchmarkId:protocolConsistent&&p.length?p[0].benchmarkId:null,
    ruleVersion:protocolConsistent&&p.length?p[0].ruleVersion:null,
    protocolConsistent,holdoutTrainPrograms,holdoutTestPrograms,
    holdoutCutoffDate:chosen?.cutoff??null,
    holdoutIssuerPurgedPrograms:chosen?.purged??0,
    holdoutHighPrograms:holdoutHigh.length,holdoutLowPrograms:holdoutLow.length,
    holdoutSpearmanScoreToReturn:holdoutSpearman,
    holdoutHighMinusLowPercent:holdoutSpread,
    spearmanScoreToReturn:protocolConsistent?spearman(p.map(x=>x.score),p.map(x=>x.returnPct)):null,
    meanHighMinusLowPercent:protocolConsistent&&low.length&&high.length?round(avg(high)-avg(low)):null,
    positiveReturnRateHigh:protocolConsistent&&high.length?positive(high):null,
    positiveReturnRateLow:protocolConsistent&&low.length?positive(low):null,
    status:enough?"REVIEW_ELIGIBLE_NOT_APPROVED" as const:"INSUFFICIENT_EVIDENCE" as const,
    reason:!protocolConsistent&&p.length>0?
      "Mixed benchmark or rule versions: metric returns cannot be pooled for validation.":
      !adequateCounts?"Insufficient unique, source-dated before-entry programs or high/low grade cohorts.":
      holdoutTrainPrograms<threshold||holdoutTestPrograms<threshold?
       "No issuer-disjoint, purged chronological 30-issuer training and 30-issuer holdout split is available.":
      !adequateHoldoutCohorts?
       "Held-out issuer cohort lacks at least five low and five high pre-entry metric ratings.":
      !holdoutSupportsDirection?
       "Held-out issuer scores do not demonstrate both positive rank association and positive high-minus-low returns.":
      "Issuer-disjoint chronological holdout shows a positive descriptive association; independent audit, statistical uncertainty, multiple-testing controls and calibration approval remain required."
   };
  })));
}
