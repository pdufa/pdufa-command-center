/** Source-gated historical ClinicalTrials.gov RESULTS-POSTING census.
 * Never interpret unposted results as proof that a company has not announced
 * Phase 3 data. This cohort is the October 18 730-study snapshot, not the
 * later October 26 741-study Phase 3 census.
 */
import {PHASE3_CENSUS_STATUS_VALUES,type Phase3CensusRegistryStatus} from "./phase3-census-rows";
export type RegistryPostingRow={
  nctId:string;ticker:string;company:string;
  registryStatus:Phase3CensusRegistryStatus;resultsCount:number;
  sourceUrl:string;
};
export type RegistryPostingSnapshot={
  date:string;sourceFile:string;total:number;
  before:RegistryPostingRow[];after:RegistryPostingRow[];
};
const BASE="https://clinicaltrials.gov/study/";
const SOURCE="data/phase3_730_full_assessment.csv";
const KIND="CLINICALTRIALS_GOV_RESULTS_POSTING_NOT_ISSUER_ANNOUNCEMENT";
const COHORT="HISTORICAL_PHASE3_730_RESEARCH_SNAPSHOT_US_LISTED_300M_10B";
const fail=():never=>{throw new Error("Historical registry-result snapshot failed completeness or identity verification.");};
export function parseRegistryPostingSnapshot(raw:unknown):RegistryPostingSnapshot{
  if(!raw||typeof raw!=="object"||Array.isArray(raw))return fail();
  const data=raw as Record<string,unknown>;
  if(data.schemaVersion!==1||data.snapshotDate!=="2026-10-18"||
    data.sourceFile!==SOURCE||data.measure!==KIND||data.cohort!==COHORT||
    data.total!==730||data.noResultsPosted!==404||data.resultsPosted!==326||
    !Array.isArray(data.records)||data.records.length!==730)return fail();
  const before:RegistryPostingRow[]=[],after:RegistryPostingRow[]=[];
  const ids=new Set<string>();
  for(const value of data.records as unknown[]){
    if(!value||typeof value!=="object"||Array.isArray(value))return fail();
    const row=value as Record<string,unknown>;
    const id=row.nctId,ticker=row.ticker,company=row.company,status=row.registryStatus,n=row.resultsCount;
    if(typeof id!=="string"||!/^NCT\d{8}$/.test(id)||ids.has(id)||
      typeof ticker!=="string"||!/^[A-Z0-9.-]{1,15}$/.test(ticker)||
      typeof company!=="string"||!company||company.length>250||
      !PHASE3_CENSUS_STATUS_VALUES.some(x=>x===status)||
      typeof n!=="number"||!Number.isSafeInteger(n)||n<0||n>20)return fail();
    ids.add(id);
    const record:RegistryPostingRow={
      nctId:id,ticker,company,
      registryStatus:status as Phase3CensusRegistryStatus,
      resultsCount:n,sourceUrl:BASE+id
    };
    if(n===0)before.push(record);else after.push(record);
  }
  if(ids.size!==730||before.length!==404||after.length!==326)return fail();
  const sort=(a:RegistryPostingRow,b:RegistryPostingRow)=>
    a.ticker.localeCompare(b.ticker)||a.nctId.localeCompare(b.nctId);
  before.sort(sort);after.sort(sort);
  return {date:"2026-10-18",sourceFile:SOURCE,total:730,before,after};
}
