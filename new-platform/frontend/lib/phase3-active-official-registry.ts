import part01 from "../data/phase3ActiveOfficialRegistry20261106Part01.json";
import part02 from "../data/phase3ActiveOfficialRegistry20261106Part02.json";
import part03 from "../data/phase3ActiveOfficialRegistry20261106Part03.json";

/**
 * Persisted ClinicalTrials.gov v2 protocol and results evidence for the active
 * 258 exact-NCT research group. This data is NOT an FDA-eligible Pipeline set.
 * Facts document a registry statement; efficacy, risk, power and RAAS still
 * require separate substantive review. Legacy census source is untouched.
 */
const parts=[part01,part02,part03] as const;
export const ACTIVE_OFFICIAL_REGISTRY_AS_OF=part01.asOf;
export const activeOfficialRegistryRecords=parts.flatMap(p=>p.records);
const byNct=new Map(activeOfficialRegistryRecords.map(r=>[r.nctId,r] as const));
export function activeOfficialRegistryRecord(nctId:string){return byNct.get(nctId)??null;}
export function activeOfficialRegistryIntegrity(activeIds:ReadonlySet<string>):boolean{
 return parts.length===3&&
  parts.every((p,i)=>p.schemaVersion===1&&p.part===i+1&&p.partCount===3&&
   p.total===258&&p.records.length===86&&p.asOf===ACTIVE_OFFICIAL_REGISTRY_AS_OF&&
   p.sourceSummary.census===258&&p.sourceSummary.studiesFetched===258&&
   p.sourceSummary.studiesNotFetched===0&&p.sourceSummary.failedBatches===0)&&
  activeIds.size===258&&activeOfficialRegistryRecords.length===258&&byNct.size===258&&
  activeOfficialRegistryRecords.every(r=>activeIds.has(r.nctId)&&
   r.sourceState==="FETCHED"&&r.registryUrl==="https://clinicaltrials.gov/study/"+r.nctId&&
   /^NCT\d{8}$/.test(r.nctId)&&
   /^\d{4}-\d{2}-\d{2}T/.test(ACTIVE_OFFICIAL_REGISTRY_AS_OF));
}
