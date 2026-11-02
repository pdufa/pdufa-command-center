/** Verified-date source inputs captured before an unresolved Phase 3 readout.
 * A source baseline is NOT a numeric RAAS grade, trade entry, forecast, or
 * validated historical case. A Git commit provides inspectable history only.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
export type ProspectiveSourceFact={
 id:string;metricIds:string[];kind:"PRIOR_PHASE2B_EFFICACY"|"PHASE3_TRIAL_DESIGN"|
 "PHASE3_READOUT_GUIDANCE"|"ISSUER_CASH_DISCLOSURE";
 observedAsOf:string;sourcePublishedAt:string;sourceUrl:string;
 valueText:string;limitation:string;
};
export type ProspectiveSourceBaseline={
 id:string;ticker:string;nctId:string;drug:string;indication:string;
 stage:RaasStage;capturedOn:string;readoutAtCapture:"NOT_YET_REPORTED";
 sourceBaselineStatus:"PROSPECTIVE_SOURCE_RESEARCH_ONLY";
 archivedRaasPrediction:false;predictedRaas:null;predictedReturnPercent:null;
 entryExecutionPrice:null;
 marketCap:{usdMillions:number;observedAsOf:string;sourceUrl:string;
 verification:"VENDOR_REPORTED_NOT_INDEPENDENTLY_AUDITED";note:string};
 observations:ProspectiveSourceFact[];
};
export type ProspectiveSourceFeed={
 schemaVersion:1;scope:"RAAS_PROSPECTIVE_SOURCE_BASELINES";
 sourceAsOf:string;note:string;records:ProspectiveSourceBaseline[];
};
const dateOk=(s:unknown):s is string=>typeof s==="string"&&
 /^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const secureUrl=(s:unknown):s is string=>typeof s==="string"&&
 /^https:\/\/[^\s/@:?#]+(?:\:[0-9]+)?\/\S+$/.test(s)&&!s.includes("@");
const present=(s:unknown):s is string=>typeof s==="string"&&s.trim().length>0&&s.length<1500;
const key=(r:{nctId:string;ticker:string;drug:string;indication:string})=>
 [r.nctId,r.ticker,r.drug,r.indication].map(s=>s.trim().toLowerCase()).join("|");
export function parseProspectiveSourceBaselines(input:unknown):ProspectiveSourceFeed{
 if(!input||typeof input!=="object"||Array.isArray(input))
  throw Error("RAAS_PROSPECTIVE_FEED_INVALID");
 const f=input as ProspectiveSourceFeed;
 if(f.schemaVersion!==1||f.scope!=="RAAS_PROSPECTIVE_SOURCE_BASELINES"||
   !dateOk(f.sourceAsOf)||!present(f.note)||!Array.isArray(f.records)||
   f.records.length>2000)throw Error("RAAS_PROSPECTIVE_FEED_INVALID");
 const ids=new Set<string>(),unique=new Set<string>();
 for(const r of f.records){
  if(!r||!present(r.id)||ids.has(r.id)||!/^NCT\d{8}$/.test(r.nctId)||
   !present(r.ticker)||!present(r.drug)||!present(r.indication)||
   (r.stage!=="pre"&&r.stage!=="post")||
   !dateOk(r.capturedOn)||r.capturedOn>f.sourceAsOf||
   r.readoutAtCapture!=="NOT_YET_REPORTED"||
   r.sourceBaselineStatus!=="PROSPECTIVE_SOURCE_RESEARCH_ONLY"||
   r.archivedRaasPrediction!==false||r.predictedRaas!==null||
   r.predictedReturnPercent!==null||r.entryExecutionPrice!==null||
   !r.marketCap||!Number.isFinite(r.marketCap.usdMillions)||
   r.marketCap.usdMillions<300||r.marketCap.usdMillions>10000||
   !dateOk(r.marketCap.observedAsOf)||r.marketCap.observedAsOf>r.capturedOn||
   !secureUrl(r.marketCap.sourceUrl)||!present(r.marketCap.note)||
   r.marketCap.verification!=="VENDOR_REPORTED_NOT_INDEPENDENTLY_AUDITED"||
   !Array.isArray(r.observations)||r.observations.length<1||r.observations.length>50)
   throw Error("RAAS_PROSPECTIVE_BASELINE_INVALID");
  ids.add(r.id);
  const identity=key(r)+"|"+r.stage+"|"+r.capturedOn;
  if(unique.has(identity))throw Error("RAAS_PROSPECTIVE_DUPLICATE_SNAPSHOT");
  unique.add(identity);
  const validMetricIds=new Set(RAAS_METRIC_CATALOG[r.stage].flatMap(g=>g.metrics.map(m=>m.id)));
  const factIds=new Set<string>();
  for(const o of r.observations){
   if(!o||!present(o.id)||factIds.has(o.id)||!present(o.valueText)||
    !present(o.limitation)||!Array.isArray(o.metricIds)||!o.metricIds.length||
    new Set(o.metricIds).size!==o.metricIds.length||
    o.metricIds.some(x=>!validMetricIds.has(x))||
    !["PRIOR_PHASE2B_EFFICACY","PHASE3_TRIAL_DESIGN","PHASE3_READOUT_GUIDANCE","ISSUER_CASH_DISCLOSURE"].includes(o.kind)||
    !dateOk(o.observedAsOf)||!dateOk(o.sourcePublishedAt)||
    o.observedAsOf>o.sourcePublishedAt||o.sourcePublishedAt>r.capturedOn||
    !secureUrl(o.sourceUrl))throw Error("RAAS_PROSPECTIVE_FACT_INVALID");
   factIds.add(o.id);
  }
 }
 return f;
}
export function prospectiveSourceSummary(feed:ProspectiveSourceFeed){
 return {baselines:feed.records.length,
  distinctPrograms:new Set(feed.records.map(x=>[x.ticker,x.drug,x.indication].map(s=>s.trim().toLowerCase()).join("|"))).size,
  distinctIssuers:new Set(feed.records.map(x=>x.ticker.trim().toUpperCase())).size,
  recordedSourceFacts:feed.records.reduce((sum,r)=>sum+r.observations.length,0),
  numericRaasScores:0,validatedHistoricalOutcomes:0} as const;
}
