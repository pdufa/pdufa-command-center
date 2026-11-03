/** Read-only, exact-program worklist for TOP/BOTTOM's 60 RAAS scoring metrics.
 * Every metric remains unscored unless the separate approved calibration and
 * reviewed exact-identity records actually support a composite. One dated
 * research source is not evidence of clinical success or a numeric grade.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {executeRaasReadinessScan} from "./raas-readiness-scan";
import {parseRaasPilotFeed,type RaasPilotRecord} from "./raas-score-engine";
import {parseProspectiveSourceBaselines,type ProspectiveSourceBaseline} from "./raas-prospective-source-baselines";
import pilotData from "../data/raas-pilot-observations.json";
import prospectiveData from "../data/raas-prospective-source-baselines.json";

const pilot=parseRaasPilotFeed(pilotData);
const prospective=parseProspectiveSourceBaselines(prospectiveData);
const equals=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
export type RaasWorklistTrial={nctId:string;ticker:string;drug?:string;indication?:string;stage?:RaasStage};
export type RaasWorklistSource={
 id:string;origin:"PILOT"|"PROSPECTIVE";nctId:string;ticker:string;
 date:string;title:string;sourceUrl:string;note:string;
};
export type RaasWorklistItem={
 stage:RaasStage;groupId:string;group:string;groupWeight:number;id:string;name:string;
 requiredEvidence:string;scoreRule:string;criticalRisk:string;
 sourceLeads:readonly RaasWorklistSource[];sourceCount:number;
 evidenceState:"RESEARCH_SOURCE_LEADS_NOT_GRADED"|"NO_METRIC_SOURCE_LEADS";
 calibrationApproved:boolean;trialMetricApproved:false;
 historicalTrainIssuers:number;historicalHoldoutIssuers:number;
 historicalHighHoldoutIssuers:number;historicalLowHoldoutIssuers:number;
 historicalReviewEligible:boolean;globalProspectiveSourceFacts:number;
 missingRequirements:readonly string[];
 readinessReason:string;
};
export type RaasValidationWorklist={
 schemaVersion:1;scope:"RAAS_60_METRIC_TRIAL_VALIDATION_WORKLIST_READ_ONLY";
 sourceAsOf:string;trial:RaasWorklistTrial|null;
 displayedContext:"EXACT_TRIAL_SOURCE_LEADS"|"GLOBAL_RESEARCH_SOURCES";
 totalMetrics:60;approvedCalibrations:number;approvedTrialMetricGrades:0;
 sourceMappedMetrics:number;missingSourceMetrics:number;
 byStage:{pre:{total:30;mapped:number;calibrated:number};post:{total:30;mapped:number;calibrated:number}};
 items:readonly RaasWorklistItem[];
};
function safeTrial(t:RaasWorklistTrial|null):RaasWorklistTrial|null{
 if(t===null)return null;
 if(!/^NCT\d{8}$/.test(t.nctId)||!/^[A-Z0-9.\-]{1,12}$/.test(t.ticker)||
   (t.stage!==undefined&&t.stage!=="pre"&&t.stage!=="post")||
   (t.drug!==undefined&&(t.drug.length>200||t.drug.includes("\u0000")))||
   (t.indication!==undefined&&(t.indication.length>200||t.indication.includes("\u0000"))))
  throw Error("RAAS_WORKLIST_INVALID_TRIAL_CONTEXT");
 return t;
}
const sameTrial=(r:{nctId:string;ticker:string;drug:string;indication:string;stage:RaasStage},
 t:RaasWorklistTrial|null)=>
 t===null||
 (r.nctId===t.nctId&&equals(r.ticker,t.ticker)&&
  (t.stage===undefined||r.stage===t.stage)&&
  (!t.drug?.trim()||equals(r.drug,t.drug))&&
  (!t.indication?.trim()||equals(r.indication,t.indication)));
function collectSources(trial:RaasWorklistTrial|null):Map<string,RaasWorklistSource[]>{
 if(pilot.sourceAsOf!==prospective.sourceAsOf)
  throw Error("RAAS_WORKLIST_SOURCE_SNAPSHOT_MISMATCH");
 const byMetric=new Map<string,RaasWorklistSource[]>();
 const put=(stage:RaasStage,metricIds:readonly string[],source:RaasWorklistSource)=>{
  for(const id of metricIds){
   const key=stage+"|"+id,old=byMetric.get(key)||[];
   if(old.some(x=>x.id===source.id&&x.origin===source.origin&&x.nctId===source.nctId))
    throw Error("RAAS_WORKLIST_DUPLICATED_METRIC_SOURCE");
   byMetric.set(key,[...old,source]);
  }
 };
 for(const r of pilot.records){
  if(!sameTrial(r,trial))continue;
  const record=r as RaasPilotRecord;
  for(const o of record.observations){
   if(o.assessmentDate>pilot.sourceAsOf||o.measurementDate>o.assessmentDate)continue;
   put(r.stage,o.metricIds,{id:o.id,origin:"PILOT",nctId:r.nctId,ticker:r.ticker,
    date:o.assessmentDate,title:o.title,sourceUrl:o.sourceUrl,note:o.note});
  }
 }
 for(const r of prospective.records){
  if(!sameTrial(r,trial))continue;
  const record=r as ProspectiveSourceBaseline;
  if(record.capturedOn>prospective.sourceAsOf)continue;
  for(const o of record.observations){
   if(o.sourcePublishedAt>record.capturedOn||o.sourcePublishedAt>prospective.sourceAsOf)continue;
   put(r.stage,o.metricIds,{id:o.id,origin:"PROSPECTIVE",nctId:r.nctId,ticker:r.ticker,
    date:o.sourcePublishedAt,title:o.kind.replaceAll("_"," ").toLowerCase(),
    sourceUrl:o.sourceUrl,note:o.limitation});
  }
 }
 return byMetric;
}
export function raasDocumentedTrialOptions():readonly RaasWorklistTrial[]{
 const found=new Map<string,RaasWorklistTrial>();
 for(const r of [...pilot.records,...prospective.records]){
  const key=[r.stage,r.nctId,r.ticker,r.drug,r.indication].map(x=>x.toLowerCase()).join("|");
  if(!found.has(key))found.set(key,{stage:r.stage,nctId:r.nctId,ticker:r.ticker,drug:r.drug,indication:r.indication});
 }
 return [...found.values()].sort((a,b)=>(a.stage||"").localeCompare(b.stage||"")||
  a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId));
}
export function buildRaasMetricValidationWorklist(rawTrial:RaasWorklistTrial|null=null):RaasValidationWorklist{
 const trial=safeTrial(rawTrial);
 const report=executeRaasReadinessScan();
 if(report.finalScoring!=="NOT_VALIDATED"||report.summary.metricsInspected!==60||
  report.metrics.length!==60||report.scanExecution!=="COMPLETED_READ_ONLY_SOURCE_AUDIT")
  throw Error("RAAS_WORKLIST_SCAN_SOURCE_UNEXPECTED");
 const sources=collectSources(trial);
 const scanById=new Map(report.metrics.map(m=>[m.stage+"|"+m.id,m]));
 if(scanById.size!==60)throw Error("RAAS_WORKLIST_DUPLICATE_SCAN_METRIC");
 const items:RaasWorklistItem[]=[];
 for(const stage of ["pre","post"] as const){
  const groups=RAAS_METRIC_CATALOG[stage];
  if(groups.length!==6||groups.reduce((sum,g)=>sum+g.metrics.length,0)!==30)
   throw Error("RAAS_WORKLIST_CATALOG_INCOMPLETE");
  for(const group of groups)for(const m of group.metrics){
   const scan=scanById.get(stage+"|"+m.id);
   if(!scan||scan.name!==m.name||scan.requiredEvidence!==m.requiredEvidence)
    throw Error("RAAS_WORKLIST_SCAN_METRIC_MISMATCH");
   const links=sources.get(stage+"|"+m.id)||[];
   const missing:string[]=[];
   if(!links.length)missing.push("Find a dated, exact-NCT and exact-issuer primary source covering this metric.");
   else missing.push("Independently review the source facts, uncertainty and relevance; a mapped link is not an accepted grade.");
   if(!scan.historicalReviewEligible||!scan.approvedCalibration){
    missing.push("Validate a precommitted scoring benchmark with at least 30 issuer-disjoint training and 30 later holdout cases, including high/low cohorts and adjusted returns.");
   }
   missing.push("Verify critical-risk and eligibility gates: "+m.criticalRisk);
   missing.push("Record and approve a sourced, exact-trial metric grade at the correct timepoint before including it in overall RAAS.");
   items.push({stage,groupId:group.id,group:group.name,groupWeight:group.weight,
    id:m.id,name:m.name,requiredEvidence:m.requiredEvidence,
    scoreRule:m.scoreRule,criticalRisk:m.criticalRisk,sourceLeads:links,
    sourceCount:links.length,evidenceState:links.length?
     "RESEARCH_SOURCE_LEADS_NOT_GRADED":"NO_METRIC_SOURCE_LEADS",
    calibrationApproved:scan.approvedCalibration,trialMetricApproved:false,
    historicalTrainIssuers:scan.holdoutTrainIssuers,
    historicalHoldoutIssuers:scan.holdoutTestIssuers,
    historicalHighHoldoutIssuers:scan.heldOutHighIssuers,
    historicalLowHoldoutIssuers:scan.heldOutLowIssuers,
    historicalReviewEligible:scan.historicalReviewEligible,
    globalProspectiveSourceFacts:scan.prospectiveSourceFacts,
    missingRequirements:missing,readinessReason:scan.reason});
  }
 }
 if(items.length!==60||new Set(items.map(x=>x.stage+"|"+x.id)).size!==60)
  throw Error("RAAS_WORKLIST_SIXTY_METRICS_REQUIRED");
 const tally=(stage:RaasStage)=>({
  total:30 as const,mapped:items.filter(x=>x.stage===stage&&x.sourceCount>0).length,
  calibrated:items.filter(x=>x.stage===stage&&x.calibrationApproved).length});
 const mapped=items.filter(x=>x.sourceCount>0).length;
 return {schemaVersion:1,scope:"RAAS_60_METRIC_TRIAL_VALIDATION_WORKLIST_READ_ONLY",
  sourceAsOf:pilot.sourceAsOf,trial,
  displayedContext:trial?"EXACT_TRIAL_SOURCE_LEADS":"GLOBAL_RESEARCH_SOURCES",
  totalMetrics:60,approvedCalibrations:report.summary.approvedMetricCalibrations,
  approvedTrialMetricGrades:0,sourceMappedMetrics:mapped,missingSourceMetrics:60-mapped,
  byStage:{pre:tally("pre"),post:tally("post")},items};
}
