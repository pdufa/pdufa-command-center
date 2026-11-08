import type {PhaseContext} from "./medical-intelligence-advanced";
const PHASES=["EARLY_PHASE1","PHASE1","PHASE2","PHASE3","PHASE4"] as const;
const record=(x:unknown):Record<string,unknown>=>x!==null&&typeof x==="object"&&!Array.isArray(x)?x as Record<string,unknown>:{};
const str=(x:unknown)=>typeof x==="string"?x:"";
export function parseExactRegistryPhase(study:unknown,nct:string):PhaseContext{
 if(!/^NCT\d{8}$/.test(nct))throw Error("Invalid exact NCT");
 const protocol=record(record(study).protocolSection);
 const actual=str(record(protocol.identificationModule).nctId);
 if(actual!==nct)throw Error("ClinicalTrials.gov NCT identity mismatch");
 const values=record(protocol.designModule).phases;
 const reported=Array.isArray(values)?values.filter((p):p is string=>typeof p==="string"):[];
 const accepted=PHASES.filter(phase=>reported.includes(phase));
 const verifiedPhase=accepted.length?accepted[accepted.length-1]:"UNKNOWN";
 const lastUpdate=str(record(protocol.statusModule).studyFirstPostDate)||
   str(record(protocol.statusModule).lastUpdatePostDate);
 return {nct,verifiedPhase,sourceUrl:"https://clinicaltrials.gov/study/"+nct,
   ...(lastUpdate?{verifiedAt:lastUpdate}:{})};
}
export async function getRegistryPhases(ncts:readonly string[]):Promise<PhaseContext[]>{
 const unique=[...new Set(ncts.filter(x=>/^NCT\d{8}$/.test(x)))].slice(0,8);
 const result=await Promise.all(unique.map(async nct=>{
  try{
   const response=await fetch("https://clinicaltrials.gov/api/v2/studies/"+nct,{
     headers:{Accept:"application/json"},next:{revalidate:21600},
     signal:AbortSignal.timeout(6500)
   });
   if(!response.ok||!response.headers.get("content-type")?.toLowerCase().includes("json"))
     throw Error("Registry unavailable");
   const raw=await response.text();
   if(raw.length>6000000)throw Error("Registry response exceeds size guard");
   return parseExactRegistryPhase(JSON.parse(raw) as unknown,nct);
  }catch{
   return {nct,verifiedPhase:"UNKNOWN" as const};
  }
 }));
 return result;
}
