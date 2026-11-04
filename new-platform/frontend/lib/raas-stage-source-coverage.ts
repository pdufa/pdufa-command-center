/** Full-research-population numeric SOURCE LEAD COVERAGE, explicitly NOT a RAAS
 * efficacy, valuation, clinical-success, regulatory, or investment rating.
 * Every number is the weight of catalog metrics with an exact-NCT public source
 * lead, not a quality judgment about missing/unpublished medical evidence.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {registryMetricLeads,type RegistryTrialEvidence} from "./raas-registry-evidence";

export type RaasStageSourceCoverage={
 stage:RaasStage;nctId:string;ticker:string;sourceUrl:string;
 mappedMetricIds:string[];unmappedMetricIds:string[];
 evidenceLeadCount:number;sourceWeightPct:number;metricCount:number;
 totalMetrics:30;kind:"PRIMARY_REGISTRY_LEAD_COVERAGE_NOT_RAAS";
 overallRaasScore:null;
};
export function raasRegistryCoverage(
 trial:{nctId:string;ticker:string;drug?:string},stage:RaasStage,
 registry:RegistryTrialEvidence|null
):RaasStageSourceCoverage|null{
 if(!registry)return null;
 const leads=registryMetricLeads(registry,stage,trial);
 // Failed identity check may not be represented as a numerical 0 (missing data).
 if(registry.nctId!==trial.nctId||
   registry.ticker.trim().toLowerCase()!==trial.ticker.trim().toLowerCase()||
   !/^NCT\d{8}$/.test(trial.nctId))return null;
 const catalog=RAAS_METRIC_CATALOG[stage];
 const ids=new Set(leads.flatMap(lead=>lead.metricIds));
 const all=catalog.flatMap(group=>group.metrics.map(metric=>({
  id:metric.id,weight:group.weight/group.metrics.length
 })));
 const expected=all.reduce((total,x)=>total+x.weight,0);
 if(all.length!==30||Math.abs(expected-100)>1e-6)
  throw Error("RAAS_SOURCE_COVERAGE_CATALOG_INVALID");
 const allowed=new Set(all.map(x=>x.id));
 if([...ids].some(x=>!allowed.has(x)))
  throw Error("RAAS_SOURCE_COVERAGE_UNKNOWN_METRIC");
 const mapped=all.filter(x=>ids.has(x.id));
 return {stage,nctId:trial.nctId,ticker:trial.ticker,sourceUrl:registry.sourceUrl,
  mappedMetricIds:mapped.map(x=>x.id),
  unmappedMetricIds:all.filter(x=>!ids.has(x.id)).map(x=>x.id),
  evidenceLeadCount:leads.length,
  sourceWeightPct:Math.round(mapped.reduce((total,x)=>total+x.weight,0)*100)/100,
  metricCount:mapped.length,totalMetrics:30,
  kind:"PRIMARY_REGISTRY_LEAD_COVERAGE_NOT_RAAS",overallRaasScore:null};
}
