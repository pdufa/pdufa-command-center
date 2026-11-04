/** Verified source inventory used only as research leads, never numerical scores.
 * Registry results are independent of issuer-evidenced TOP/BOTTOM assignment.
 * Protocol fields cannot be promoted to clinical outcomes, and p-values do not
 * become effect sizes or 0–100 scoring grades.
 */
import type {RaasStage} from "./raas-metric-specs";
export type RegistryPrimaryResult={
 title:string;timeFrame:string;unit:string;analysisCount:number;pValues:string[];
};
export type RegistryTrialEvidence={
 nctId:string;ticker:string;sourceUrl:string;sourceHash:string;
 retrievedAt:string;registryLastUpdated:string|null;resultsFirstPosted:string|null;
 registryStatus:string;registeredPhases:string[];
 registeredConditions:string[];registeredInterventions:string[];
 primaryDefinitions:{measure:string;timeFrame:string}[];
 postedResults:boolean;postedPrimaryOutcomeCount:number;postedOtherOutcomeCount:number;
 primaryResults:RegistryPrimaryResult[];seriousAdverseEventTermCount:number;
 evidenceState:"PROTOCOL_ONLY"|"POSTED_RESULTS_UNGRADED";
};
export type RegistryEvidenceIndex={
 schemaVersion:1;scope:"RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX";source:string;
 sourceAsOf:string;summary:{
  researchNcts:number;registryRecords:number;postedRegistryResults:number;
  protocolOnly:number;approvedOverallRaasScores:0
 };records:RegistryTrialEvidence[];
};
export type RegistryMetricLead={
 id:string;kind:string;sourceDate:string;sourceUrl:string;
 description:string;measurement:null;metricIds:string[];
};
const exact=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
const nct=/^NCT\d{8}$/;
const hash=/^[0-9a-f]{64}$/;
const sameTrial=(e:RegistryTrialEvidence,t:{nctId:string;ticker:string;drug?:string})=>{
 if(e.nctId!==t.nctId||!exact(e.ticker,t.ticker))return false;
 const drug=t.drug?.trim().toLowerCase();
 if(!drug)return true;
 // Do not attach a source to a different drug in a multi-asset issuer.
 const names=drug.split(/[|;]/).map(x=>x.replace(/\([^)]*\)/g,"").trim()).filter(Boolean);
 if(!names.length)return false;
 return e.registeredInterventions.some(name=>{
  const actual=name.toLowerCase();
  return names.some(x=>actual.includes(x)||x.includes(actual));
 });
};
export function parseRegistryEvidenceIndex(raw:unknown):RegistryEvidenceIndex{
 if(!raw||typeof raw!=="object")throw Error("RAAS_REGISTRY_INDEX_INVALID");
 const j=raw as RegistryEvidenceIndex;
 if(j.schemaVersion!==1||j.scope!=="RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX"||
  !Array.isArray(j.records)||!j.summary||j.records.length!==j.summary.researchNcts||
  j.summary.researchNcts!==j.summary.registryRecords||
  j.summary.approvedOverallRaasScores!==0)
  throw Error("RAAS_REGISTRY_INDEX_INVALID");
 const ids=new Set<string>();let posted=0;
 for(const e of j.records){
  if(!nct.test(e.nctId)||ids.has(e.nctId)||!e.ticker?.trim()||
   e.sourceUrl!=="https://clinicaltrials.gov/study/"+e.nctId||
   !hash.test(e.sourceHash)||typeof e.postedResults!=="boolean"||
   !Array.isArray(e.primaryDefinitions)||!Array.isArray(e.primaryResults)||
   !Array.isArray(e.registeredInterventions)||!Array.isArray(e.registeredConditions)||
   !Number.isInteger(e.postedPrimaryOutcomeCount)||
   !Number.isInteger(e.seriousAdverseEventTermCount)||
   e.seriousAdverseEventTermCount<0||e.postedPrimaryOutcomeCount<0||
   e.postedResults!==(e.evidenceState==="POSTED_RESULTS_UNGRADED")||
   (!e.postedResults&&(e.primaryResults.length>0||e.postedPrimaryOutcomeCount>0)))
   throw Error("RAAS_REGISTRY_INDEX_ROW_INVALID");
  ids.add(e.nctId);if(e.postedResults)posted++;
 }
 if(posted!==j.summary.postedRegistryResults||
  posted+j.summary.protocolOnly!==j.summary.researchNcts)
  throw Error("RAAS_REGISTRY_INDEX_COUNT_INVALID");
 return j;
}
let cached:Promise<RegistryEvidenceIndex|null>|null=null;
export function loadRegistryEvidenceIndex():Promise<RegistryEvidenceIndex|null>{
 if(!cached){
  cached=fetch("/raas-registry-evidence-index.json",{cache:"no-store"})
   .then(async r=>{
    if(!r.ok)throw Error("REGISTRY_EVIDENCE_SNAPSHOT_NOT_PUBLISHED");
    return parseRegistryEvidenceIndex(await r.json());
   }).catch(()=>{cached=null;return null;});
 }
 return cached;
}
export function registryTrialFor(
 index:RegistryEvidenceIndex|null,
 trial:{nctId:string;ticker:string;drug?:string}
):RegistryTrialEvidence|null{
 if(!index)return null;
 const found=index.records.find(x=>x.nctId===trial.nctId);
 return found&&sameTrial(found,trial)?found:null;
}
export function registryMetricLeads(e:RegistryTrialEvidence|null,stage:RaasStage):RegistryMetricLead[]{
 if(!e)return [];
 const leads:RegistryMetricLead[]=[];
 const base={sourceUrl:e.sourceUrl,measurement:null as null};
 // A trial's registered design can inform the pre-readout DESIGN review,
 // but it cannot substantiate historical human efficacy or numerical scores.
 if(stage==="pre"&&e.primaryDefinitions.length){
  leads.push({...base,id:e.nctId+"-registered-design",kind:"REGISTERED_PHASE3_PROTOCOL",
   metricIds:["pre-1-2"],sourceDate:e.registryLastUpdated||e.retrievedAt.slice(0,10),
   description:"Registered Phase 3 primary endpoint: "+
    e.primaryDefinitions.slice(0,2).map(x=>x.measure+" ("+x.timeFrame+")").join("; ")+
    ". Protocol lead only; design power and prior results still need independent review."});
 }
 if(stage==="post"&&e.postedResults&&e.postedPrimaryOutcomeCount>0){
  leads.push({...base,id:e.nctId+"-posted-primary",kind:"POSTED_REGISTRY_RESULTS",
   metricIds:["post-1-1"],
   sourceDate:e.resultsFirstPosted||e.registryLastUpdated||e.retrievedAt.slice(0,10),
   description:"Registry reports "+e.postedPrimaryOutcomeCount+
    " primary outcome(s): "+
    e.primaryResults.slice(0,2).map(x=>x.title).join("; ")+
    ". Treatment effect, comparator, and clinical significance require review."});
  if(e.primaryResults.some(x=>x.analysisCount>0)){
   leads.push({...base,id:e.nctId+"-primary-statistics",kind:"POSTED_REGISTRY_STATISTICS",
    metricIds:["post-1-3"],
    sourceDate:e.resultsFirstPosted||e.registryLastUpdated||e.retrievedAt.slice(0,10),
    description:"Registry primary outcome includes statistical analyses; full confidence intervals, "+
     "multiplicity plan and missing-data sensitivity are not established by analysis presence."});
  }
 }
 if(stage==="post"&&e.postedResults&&e.seriousAdverseEventTermCount>0){
  leads.push({...base,id:e.nctId+"-posted-safety",kind:"POSTED_REGISTRY_SAFETY",
   metricIds:["post-1-5"],sourceDate:e.resultsFirstPosted||e.registryLastUpdated||e.retrievedAt.slice(0,10),
   description:"Registry lists "+e.seriousAdverseEventTermCount+
    " serious-adverse-event term(s). Matched exposure and adverse-event rates "+
    "remain required; this is not a safety rating."});
 }
 return leads;
}
