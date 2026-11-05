/** ClinicalTrials.gov source facts, exact NCT and ticker, mapped to RAAS
 * metric *research requirements* only. This mapping is NOT a metric grade.
 * ClinicalTrials.gov results do NOT independently verify the date or
 * direction of a public Phase 3 readout, FDA outcome or PIPELINE eligibility.
 * Original source values remain unadjusted and are never backdated.
 */
import {parseRegistryEvidenceIndex,registryMetricLeads,
 type RegistryEvidenceIndex} from "./raas-registry-evidence";
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";

export type RaasRegistryClinicalFact={
 id:string;nctId:string;ticker:string;sourceUrl:string;sourceHash:string;
 sourceAsOf:string;sourceDate:string;resultsFirstPosted:string|null;
 candidateStage:RaasStage;
 /** Exact metric IDs are research routing tags, NOT approved RAAS grades. */
 metricIds:string[];
 kind:string;description:string;
 measurementLabel:string|null;measurementValue:number|null;
 measurementUnit:string|null;
 metricGrade:null;approvedOverallRaasScore:null;fdaProbability:null;
};
export type RaasRegistryClinicalFactLedger={
 scope:"RAAS_EXACT_NCT_REGISTRY_SOURCE_FACTS_UNGRADED";
 sourceAsOf:string;registryNcts:number;
 trialsWithLeads:number;totalSourceFacts:number;
 rawNumericFacts:number;rawContrastFacts:number;rawConfidenceIntervalFacts:number;
 rawPValueFacts:number;rawSeriousEventAffectedRates:number;
 registryPostedResults:number;independentlyValidatedMetricGrades:0;
 approvedOverallRaasScores:0;calibratedFdaPredictions:0;
 facts:RaasRegistryClinicalFact[];
};
const allowed=new Set(
 (["pre","post"] as const).flatMap(stage=>
  RAAS_METRIC_CATALOG[stage].flatMap(c=>c.metrics.map(m=>m.id))));
export function buildRaasRegistryClinicalFactLedger(index:unknown):RaasRegistryClinicalFactLedger{
 const saved:RegistryEvidenceIndex=parseRegistryEvidenceIndex(index);
 const facts:RaasRegistryClinicalFact[]=[];
 const seen=new Set<string>(),withLeads=new Set<string>();
 for(const registry of saved.records){
  for(const stage of ["pre","post"] as const){
   const leads=registryMetricLeads(registry,stage,{
    nctId:registry.nctId,ticker:registry.ticker
   });
   for(const lead of leads){
    const id=stage+"|"+registry.nctId+"|"+lead.id;
    if(seen.has(id)||!lead.metricIds.length||
     lead.metricIds.some(m=>!allowed.has(m)||!m.startsWith(stage+"-"))||
     lead.sourceUrl!==registry.sourceUrl||
     (stage==="post"&&!registry.postedResults)||
     (lead.measurement&&!Number.isFinite(lead.measurement.value)))
     throw Error("RAAS_REGISTRY_CLINICAL_FACT_SOURCE_INVALID");
    seen.add(id);withLeads.add(registry.nctId);
    facts.push({
     id,nctId:registry.nctId,ticker:registry.ticker,
     sourceUrl:registry.sourceUrl,sourceHash:registry.sourceHash,
     sourceAsOf:saved.sourceAsOf,sourceDate:lead.sourceDate,
     resultsFirstPosted:registry.resultsFirstPosted,
     candidateStage:stage,metricIds:lead.metricIds,
     kind:lead.kind,description:lead.description,
     measurementLabel:lead.measurement?.label??null,
     measurementValue:lead.measurement?.value??null,
     measurementUnit:lead.measurement?.unit??null,
     metricGrade:null,approvedOverallRaasScore:null,fdaProbability:null
    });
   }
  }
 }
 const count=(kind:string)=>facts.filter(x=>x.kind===kind).length;
 const result={
  scope:"RAAS_EXACT_NCT_REGISTRY_SOURCE_FACTS_UNGRADED" as const,
  sourceAsOf:saved.sourceAsOf,registryNcts:saved.records.length,
  trialsWithLeads:withLeads.size,totalSourceFacts:facts.length,
  rawNumericFacts:facts.filter(x=>x.measurementValue!==null).length,
  rawContrastFacts:count("POSTED_PRIMARY_CONTRAST_RAW_MEASUREMENT"),
  rawConfidenceIntervalFacts:count("POSTED_PRIMARY_CI_WIDTH_RAW_MEASUREMENT"),
  rawPValueFacts:count("POSTED_PRIMARY_P_VALUE_RAW_MEASUREMENT"),
  rawSeriousEventAffectedRates:count("POSTED_SAE_AFFECTED_RATE_RAW_MEASUREMENT"),
  registryPostedResults:saved.summary.postedRegistryResults,
  independentlyValidatedMetricGrades:0 as const,
  approvedOverallRaasScores:0 as const,calibratedFdaPredictions:0 as const,
  facts
 };
 return result;
}
