/** A real, source-dated, *unscored* RAAS intake scan for TOP/BOTTOM spreadsheet rows.
 * Maps available specific evidence to 30 metric worklist slots. A mapped slot
 * is not a complete metric grade or a validated predictive 0-100 score.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import type {RaasPilotFeed,RaasObservation} from "./raas-score-engine";
import type {ProspectiveSourceFeed,ProspectiveSourceFact} from "./raas-prospective-source-baselines";
import {provisionalGradesForTrial,type ProvisionalMetricGrade} from "./raas-threshold-profiles";
export type RaasEvidenceTrial={nctId:string;ticker:string;drug?:string;indication?:string};
export type RaasCurrentEvidence={
 stage:RaasStage;asOf:string;totalMetrics:30;
 mappedMetrics:number;missingMetricCount:number;metricIds:string[];
 categories:{id:string;name:string;mapped:number;total:5;metricIds:string[]}[];
 pilotObservations:RaasObservation[];
 prospectiveFacts:ProspectiveSourceFact[];
 exploratoryTimingGrade:ProvisionalMetricGrade|null;
 approvedOverallScore:null;
 status:"SOURCE_LEADS_AVAILABLE_NOT_VALIDATED"|"NO_METRIC_SOURCE_LEADS";
};
const same=(a:string,b:string)=>a.trim().toUpperCase()===b.trim().toUpperCase();
const day=(s:string)=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
 !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
 new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
/** Ticker and NCT must BOTH match a documented trial. A stock symbol alone
 * cannot attach another program's evidence. Exact recorded drug/indication are
 * preserved in the underlying observation, not invented from the row label.
 */
export function scanRaasCurrentEvidence(
 pilot:RaasPilotFeed,prospective:ProspectiveSourceFeed,
 trial:RaasEvidenceTrial,stage:RaasStage,asOf:string
):RaasCurrentEvidence{
 if(!day(asOf)||asOf>pilot.sourceAsOf||asOf>prospective.sourceAsOf)
  throw Error("RAAS_EVIDENCE_SCAN_ASOF_INVALID");
 const matchingPilot=pilot.records.filter(x=>x.stage===stage&&x.nctId===trial.nctId&&same(x.ticker,trial.ticker));
 const matchingProspective=prospective.records.filter(x=>x.stage===stage&&x.nctId===trial.nctId&&
  same(x.ticker,trial.ticker)&&x.capturedOn<=asOf);
 // Ambiguous identity: do not merge competing records.
 const p=matchingPilot.length===1?matchingPilot[0]:null;
 const s=matchingProspective.length===1?matchingProspective[0]:null;
 const pilotObservations=p?p.observations.filter(o=>o.assessmentDate<=asOf):[];
 const prospectiveFacts=s?s.observations.filter(o=>o.sourcePublishedAt<=asOf):[];
 const catalog=RAAS_METRIC_CATALOG[stage];
 const validIds=new Set(catalog.flatMap(g=>g.metrics.map(m=>m.id)));
 const sourceMetricIds=new Set(
  [...pilotObservations,...prospectiveFacts].flatMap(x=>x.metricIds)
   .filter(id=>validIds.has(id))
 );
 const metricIds=[...validIds].filter(id=>sourceMetricIds.has(id));
 const categories=catalog.map(g=>({
  id:g.id,name:g.name,mapped:g.metrics.filter(m=>sourceMetricIds.has(m.id)).length,
  total:5 as const,metricIds:g.metrics.filter(m=>sourceMetricIds.has(m.id)).map(m=>m.id)
 }));
 // Historical calibration evidence is not available. Keep the ONE already
 // implemented exploratory timing-specificity grade separate from any final score.
 const existing=p?provisionalGradesForTrial(pilot,{
  nctId:p.nctId,ticker:p.ticker,drug:p.drug,indication:p.indication
 },stage,"CURRENT",asOf):[];
 const exploratoryTimingGrade=existing.find(g=>g.metricId==="pre-4-1")??null;
 return {stage,asOf,totalMetrics:30,mappedMetrics:metricIds.length,
  missingMetricCount:30-metricIds.length,metricIds,categories,
  pilotObservations,prospectiveFacts,exploratoryTimingGrade,
  approvedOverallScore:null,
  status:metricIds.length?"SOURCE_LEADS_AVAILABLE_NOT_VALIDATED":"NO_METRIC_SOURCE_LEADS"};
}
