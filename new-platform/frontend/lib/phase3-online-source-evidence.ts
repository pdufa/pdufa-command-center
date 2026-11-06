import snapshot from "../public/phase3-source-coverage-20261105.json";
import {phase3DeepRegistryRecord,phase3DeepRegistrySourceFact,PHASE3_DEEP_REGISTRY_TRIAL_COUNT,PHASE3_DEEP_REGISTRY_UNIQUE_NCT_COUNT} from "./phase3-deep-registry-results";

/** Source facts are documentary observations only, NEVER numeric predictions or endpoint PASS/FAIL. */
const sourceByNct=new Map(snapshot.rows.map(r=>[r.nctId,r] as const));
export const PHASE3_ONLINE_SOURCE_DATE=snapshot.asOf;
export const PHASE3_ONLINE_TRIAL_COUNT=snapshot.trials;
export const PHASE3_DEEP_SOURCE_INTEGRITY=PHASE3_DEEP_REGISTRY_TRIAL_COUNT===762&&PHASE3_DEEP_REGISTRY_UNIQUE_NCT_COUNT===762;
export type OnlineSourceFact={description:string;sourceUrl:string;status:"SOURCE_FACT_ONLY"};

export function phase3OnlineRecord(nctId:string){return sourceByNct.get(nctId);}
export function phase3OnlineCoverageLabel(nctId:string):string{
 const r=sourceByNct.get(nctId);if(!r)return "NO_ONLINE_RECHECK";
 return [
  "CTGOV_REGISTRY_RECHECKED",
  phase3DeepRegistryRecord(nctId)?.hasPostedResults?"CTGOV_DEEP_PRIMARY_RESULTS_SAVED":"CTGOV_NO_POSTED_PRIMARY_RESULTS",
  r.resultsPosted?"CTGOV_RESULTS_POSTED":"CTGOV_RESULTS_NOT_POSTED",
  "REGISTRY_STATISTICAL_ANALYSES_"+r.resultsAnalysisCount,
  "REGISTRY_DOCUMENTS_"+r.documentCount,
  "PUBMED_EXACT_NCT_ARTICLE_LEADS_"+r.pubmedPMIDs.length,
  "SEC_EXACT_NCT_FILING_LEADS_"+(r.secFilingMentions??"ERROR")
 ].join("; ");
}
export function phase3OnlineSourceFact(nctId:string,question:number):OnlineSourceFact|null{
 const r=sourceByNct.get(nctId);if(!r)return null;
 const detailed=phase3DeepRegistrySourceFact(nctId,question);
 if(detailed)return detailed;
 const sourceUrl="https://clinicaltrials.gov/study/"+nctId;
 const fact=(description:string):OnlineSourceFact=>({description,sourceUrl,status:"SOURCE_FACT_ONLY"});
 switch(question){
  case 3:return r.resultsPosted&&r.resultsAnalysisCount>0?
   fact("Registry result analyses exist, but safety/tolerability has NOT been adjudicated; no safety prediction follows."):null;
  case 7:return r.primaryEndpoint?
   fact("Official registry first-listed primary outcome: "+r.primaryEndpoint):null;
  case 8:return r.primaryTimeFrame?
   fact("Official registry primary outcome timeframe: "+r.primaryTimeFrame):null;
  case 9:return r.allocation?
   fact("Official registry allocation field: "+r.allocation+"; statistical adequacy NOT assessed"):null;
  case 10:return r.masking?
   fact("Official registry masking field: "+r.masking+"; effectiveness of blinding NOT assessed"):null;
  case 12:return r.enrollment!==null&&r.enrollment!==undefined?
   fact("Official registry enrollment count: "+r.enrollment+"; estimated/actual design context not graded"):null;
  case 17:return r.secondaryEndpointCount>0?
   fact("Official registry lists "+r.secondaryEndpointCount+" secondary outcomes; efficacy NOT predicted"):null;
  case 25:return r.registryStatus?
   fact("Online registry recruitment status at source check: "+r.registryStatus+"; trial outcome separate"):null;
  case 27:return r.interventions.some(v=>/\bplacebo\b/i.test(v))?
   fact("Placebo named in registered interventions; comparator adequacy NOT assessed"):null;
  case 29:return r.resultsPosted?
   fact("ClinicalTrials.gov has posted trial results; public issuer readout and exact primary endpoint success are NOT inferred"):null;
  default:return null;
 }
}
export function phase3OnlineReviewLeads(nctId:string):{summary:string;urls:string[]}{
 const r=sourceByNct.get(nctId);
 if(!r)return {summary:"No online source snapshot for this trial",urls:[]};
 const leadParts:string[]=[];
 const urls:string[]=[];
 if(r.resultsPosted){leadParts.push("Registry results are posted and require endpoint review");urls.push("https://clinicaltrials.gov/study/"+nctId);}
 if(r.pubmedPMIDs.length){
  leadParts.push(r.pubmedPMIDs.length+" exact-NCT PubMed article lead(s), not yet readout-adjudicated");
  urls.push(...r.pubmedPMIDs.slice(0,3).map(id=>"https://pubmed.ncbi.nlm.nih.gov/"+id+"/"));
 }
 if((r.secFilingMentions||0)>0){
  leadParts.push(r.secFilingMentions+" indexed SEC filing mention(s); study outcome not independently adjudicated");
  urls.push("https://www.sec.gov/edgar/search/#/q="+nctId);
 }
 if(r.documentCount)leadParts.push(r.documentCount+" public registry document(s)");
 return {summary:leadParts.join("; "),urls};
}
