import {NextResponse} from "next/server";
import focusRoster from "../../../data/p3PostDataActive.json";

/**
 * Read-only COMPANY clinical phase evidence from nightly exact-NCT source receipts.
 * Phase comes only from the official ClinicalTrials.gov record in the source monitor.
 * FDA application stages and dates come from a separate source-linked cycle map.
 * Never infer that a clinical Phase 3 trial has an assigned FDA PDUFA date.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const SOURCE="https://raw.githubusercontent.com/pdufa/pdufa-command-center/main/data/focus_nightly_evidence_current.json";
const noStore={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
const knownPhases=new Set(["EARLY_PHASE1","PHASE1","PHASE2","PHASE3","PHASE4","NA"]);
const knownStatuses=new Set([
  "NOT_YET_RECRUITING","RECRUITING","ENROLLING_BY_INVITATION",
  "ACTIVE_NOT_RECRUITING","COMPLETED","SUSPENDED","TERMINATED","WITHDRAWN","UNKNOWN"
]);

type RegistryPhaseRecord = {
  nct:string; ticker:string; phase:string[]|null; registryStatus:string|null;
  sourceStatus:"OFFICIAL_REGISTRY_RETRIEVED"|"OFFICIAL_SOURCE_UNAVAILABLE";
  registryUpdated:string|null; sourceUrl:string;
};
function isRecord(value:unknown):value is Record<string,unknown>{
  return typeof value==="object" && value!==null && !Array.isArray(value);
}
function validIsoDate(s:unknown):s is string {
  if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;
  const d=new Date(s+"T00:00:00Z");
  return !Number.isNaN(d.valueOf())&&d.toISOString().slice(0,10)===s;
}
function parseSource(data:unknown){
  if(!isRecord(data)||data.schemaVersion!==1||
    data.kind!=="FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS"||
    !Array.isArray(data.trials)||data.trials.length>250||
    typeof data.runAtUTC!=="string"||!Number.isFinite(Date.parse(data.runAtUTC))||
    !isRecord(data.summary)||data.summary.focusTrials!==data.trials.length)
    throw Error("Nightly phase evidence format invalid");
  const canonical=new Map(focusRoster.records.map(t=>[t.nct,t.ticker]));
  const seen=new Set<string>();
  const records:RegistryPhaseRecord[]=[];
  for(const item of data.trials){
    if(!isRecord(item))throw Error("Source row invalid");
    const nct=item.nct, ticker=item.ticker;
    if(typeof nct!=="string"||!/^NCT\d{8}$/.test(nct)||
      typeof ticker!=="string"||canonical.get(nct)!==ticker||seen.has(nct)||
      !["OFFICIAL_REGISTRY_RETRIEVED","OFFICIAL_SOURCE_UNAVAILABLE"].includes(String(item.sourceStatus)))
      throw Error("Source exact-NCT roster or status mismatch");
    seen.add(nct);
    const available=item.sourceStatus==="OFFICIAL_REGISTRY_RETRIEVED";
    const phases=available&&Array.isArray(item.phase)&&
      item.phase.every(p=>typeof p==="string"&&knownPhases.has(p)) ? item.phase as string[] : null;
    const status=available&&typeof item.registryStatus==="string"&&
      knownStatuses.has(item.registryStatus)?item.registryStatus:null;
    const updated=available&&validIsoDate(item.registryUpdated)?item.registryUpdated:null;
    records.push({nct,ticker,phase:phases,registryStatus:status,
      sourceStatus:available?"OFFICIAL_REGISTRY_RETRIEVED":"OFFICIAL_SOURCE_UNAVAILABLE",
      registryUpdated:updated,sourceUrl:"https://clinicaltrials.gov/study/"+nct});
  }
  const ageMs=Date.now()-Date.parse(data.runAtUTC);
  return {schemaVersion:1,source:"ClinicalTrials.gov via nightly FOCUS public source monitor",
    checkedAt:data.runAtUTC,ageStatus:ageMs>=0&&ageMs<=72*60*60*1000?"RECENT":"STALE",
    records};
}
export async function GET(){
  try{
    const response=await fetch(SOURCE,{cache:"no-store",redirect:"error",
      headers:{Accept:"application/json"},signal:AbortSignal.timeout(12000)});
    if(!response.ok)throw Error("Nightly phase source not published");
    const body=await response.text();
    if(body.length>300000)throw Error("Nightly phase source too large");
    return NextResponse.json(parseSource(JSON.parse(body)),{headers:noStore});
  }catch{
    return NextResponse.json({error:"Verified clinical phases unavailable. No phase inferred."},
      {status:503,headers:noStore});
  }
}
