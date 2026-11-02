/** ClinicalTrials.gov results-posting audit. NOT company announcement status.
 * v1 = October 18 saved static baseline. v2 = an exact-NCT full registry
 * recheck after the clinical scan. Never accept partial or duplicate rows.
 */
export type RegistryPostingRow={
  nctId:string;ticker:string;company:string;
  registryStatus:string;resultsCount:number;sourceUrl:string;
  resultsFirstPostedDate:string|null;
};
export type RegistryPostingSnapshot={
  date:string;sourceAsOf:string;sourceFile:string;total:number;fresh:boolean;
  before:RegistryPostingRow[];after:RegistryPostingRow[];
};
const BASE="https://clinicaltrials.gov/study/";
const MEASURE="CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT";
const SOURCE_V1="data/phase3_730_full_assessment.csv";
const SOURCE_V2="data/phase3_all_years_300m_10b_trials.csv";
const KIND_V2="OFFICIAL_CLINICALTRIALS_GOV_API_EXACT_NCT";
const COHORT_V2="DATED_300M_10B_PHASE3_CENSUS_EXACT_NCTS";
const fail=():never=>{throw Error("Registry results-posting source is incomplete, stale-format, or identity inconsistent.");};
const isoDay=(day:unknown):day is string=>
  typeof day==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(day)&&
  !Number.isNaN(Date.parse(day+"T00:00:00Z"))&&
  new Date(day+"T00:00:00Z").toISOString().slice(0,10)===day;
export function parseRegistryPostingSnapshot(raw:unknown):RegistryPostingSnapshot{
  if(!raw||typeof raw!=="object"||Array.isArray(raw))return fail();
  const data=raw as Record<string,unknown>;
  const live=data.schemaVersion===2;
  const v1=data.schemaVersion===1;
  if((!v1&&!live)||data.measure!==MEASURE||
     !isoDay(data.snapshotDate)||typeof data.total!=="number"||
     !Number.isSafeInteger(data.total)||data.total<700||data.total>20000||
     typeof data.noResultsPosted!=="number"||typeof data.resultsPosted!=="number"||
     !Number.isSafeInteger(data.noResultsPosted)||!Number.isSafeInteger(data.resultsPosted)||
     data.noResultsPosted<0||data.resultsPosted<0||
     data.noResultsPosted+data.resultsPosted!==data.total||
     !Array.isArray(data.records)||data.records.length!==data.total)return fail();
  if(live && (data.sourceFile!==SOURCE_V2||data.sourceKind!==KIND_V2||
      data.cohort!==COHORT_V2||typeof data.sourceAsOf!=="string"||
      !Number.isFinite(Date.parse(data.sourceAsOf))||
      data.snapshotDate!==data.sourceAsOf.slice(0,10)))return fail();
  if(v1 && (data.sourceFile!==SOURCE_V1||
      data.cohort!=="HISTORICAL_PHASE3_730_RESEARCH_SNAPSHOT_US_LISTED_300M_10B"||
      data.snapshotDate!=="2026-10-18"||data.total!==730||
      data.noResultsPosted!==404||data.resultsPosted!==326))return fail();
  const before:RegistryPostingRow[]=[],after:RegistryPostingRow[]=[];
  const ids=new Set<string>();
  for(const entry of data.records as unknown[]){
    if(!entry||typeof entry!=="object"||Array.isArray(entry))return fail();
    const row=entry as Record<string,unknown>;
    const id=row.nctId,ticker=row.ticker,company=row.company,status=row.registryStatus,n=row.resultsCount;
    const posted=live?row.resultsFirstPostedDate:null;
    if(typeof id!=="string"||!/^NCT\d{8}$/.test(id)||ids.has(id)||
      typeof ticker!=="string"||!/^[A-Z0-9.-]{1,15}$/.test(ticker)||
      typeof company!=="string"||!company||company.length>250||
      typeof status!=="string"||!/^[A-Z_]{3,50}$/.test(status)||
      typeof n!=="number"||!Number.isSafeInteger(n)||n<0||n>20||
      (live && (n>1||typeof posted!=="string"||
        (!!posted&&!isoDay(posted))||
        Boolean(posted)!==Boolean(n)||
        (!!posted && posted>data.snapshotDate))))return fail();
    ids.add(id);
    const record:RegistryPostingRow={
      nctId:id,ticker,company,registryStatus:status,
      resultsCount:n,sourceUrl:BASE+id,
      resultsFirstPostedDate:live?(posted as string)||null:null,
    };
    (n===0?before:after).push(record);
  }
  if(ids.size!==data.total||
    before.length!==data.noResultsPosted||after.length!==data.resultsPosted)return fail();
  const sort=(a:RegistryPostingRow,b:RegistryPostingRow)=>
    a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId);
  before.sort(sort);after.sort(sort);
  return {
    date:data.snapshotDate as string,
    sourceAsOf:live?data.sourceAsOf as string:data.snapshotDate as string,
    sourceFile:live?SOURCE_V2:SOURCE_V1,total:data.total as number,
    fresh:live,before,after,
  };
}
