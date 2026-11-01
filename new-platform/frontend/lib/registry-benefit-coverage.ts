/** Display-only coverage of published ClinicalTrials.gov primary sources.
 * This NEVER certifies pivotal efficacy, FDA approval, Pipeline eligibility,
 * a safety advantage, or any of the 20 research assessment conclusions.
 */
export type RegistrySourceRow={
  nctId:string;retrievedAt:string;sourceUpdated:string|null;
  resultsPosted:boolean;primaryOutcomeCount:number;measuredPrimary:boolean;
  seriousEventTerms:number;measuredSeriousEvents:boolean;
  truncated:boolean;
};
export type RegistryCoverage={
  schemaVersion:1;scanned:number;successful:number;failed:number;
  sourceAsOf:string;records:RegistrySourceRow[];
  postedResults:number;withPrimaryMeasurements:number;withSeriousEventCounts:number;
  truncatedRecords:number;
};
const safeDateTime=(v:unknown):v is string=>
  typeof v==="string"&&/^\d{4}-\d{2}-\d{2}T/.test(v)&&Number.isFinite(Date.parse(v));
const sourceDate=(v:unknown):v is string=>
  typeof v==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v)
  &&Number.isFinite(Date.parse(v+"T00:00:00Z"))
  &&new Date(Date.parse(v+"T00:00:00Z")).toISOString().slice(0,10)===v;
const isObj=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==="object"&&!Array.isArray(v);
const count=(v:unknown):v is number=>Number.isSafeInteger(v)&&Number(v)>=0;
export function registryCoverageFromSnapshot(raw:unknown,now=Date.now()):RegistryCoverage{
  if(!isObj(raw)||raw.schemaVersion!==1||raw.censusAsOf!=="2026-10-26"
     ||!safeDateTime(raw.scanStartedAt)||!count(raw.scanned)||raw.scanned!==375
     ||!count(raw.successful)||!count(raw.failed)||!count(raw.reusedWithin72Hours)
     ||raw.successful>raw.scanned||raw.failed>raw.scanned||raw.successful+raw.failed!==raw.scanned
     ||!Array.isArray(raw.records)||raw.records.length>375)
    throw Error("INVALID_REGISTRY_SOURCE_ARCHIVE");
  const sourceTime=Date.parse(raw.scanStartedAt);
  if(!Number.isFinite(now)||sourceTime>now+300000||now-sourceTime>48*3600000)
    throw Error("STALE_REGISTRY_SOURCE_ARCHIVE");
  const seen=new Set<string>(),records:RegistrySourceRow[]=[];
  for(const item of raw.records){
    if(!isObj(item)||typeof item.nctId!=="string"||!/^NCT\d{8}$/.test(item.nctId)
       ||seen.has(item.nctId)||item.sourceUrl!=="https://clinicaltrials.gov/study/"+item.nctId
       ||!safeDateTime(item.retrievedAt)||Date.parse(item.retrievedAt)>now+300000
       ||Date.parse(item.retrievedAt)<sourceTime-86400000
       ||(item.sourceUpdated!==null&&!sourceDate(item.sourceUpdated))
       ||typeof item.resultsPosted!=="boolean"||!Array.isArray(item.primary)
       ||!Array.isArray(item.seriousAdverseEvents)||!isObj(item.truncatedEvidence)
       ||typeof item.truncatedEvidence.outcomes!=="boolean"
       ||typeof item.truncatedEvidence.seriousEvents!=="boolean"
       ||item.comparisonVerified!==false||item.benefitRank!==null
       ||item.fdaDecisionVerified!==false)
      throw Error("INVALID_REGISTRY_SOURCE_IDENTITY");
    seen.add(item.nctId);
    const primary=item.primary as unknown[];
    const adverse=item.seriousAdverseEvents as unknown[];
    if(primary.length>24||adverse.length>80)throw Error("UNBOUNDED_REGISTRY_SOURCE_RECORD");
    const measuredPrimary=primary.some(x=>isObj(x)&&Array.isArray(x.measurements)&&x.measurements.length>0);
    const measuredSeriousEvents=adverse.some(x=>isObj(x)&&Array.isArray(x.groups)&&x.groups.length>0);
    if(!item.resultsPosted&&(primary.length>0||adverse.length>0))throw Error("INCONSISTENT_REGISTRY_POSTING_STATE");
    records.push({nctId:item.nctId,retrievedAt:item.retrievedAt,
      sourceUpdated:item.sourceUpdated as string|null,resultsPosted:item.resultsPosted,
      primaryOutcomeCount:primary.length,measuredPrimary,
      seriousEventTerms:adverse.length,measuredSeriousEvents,
      truncated:item.truncatedEvidence.outcomes||item.truncatedEvidence.seriousEvents});
  }
  if(records.length>raw.successful+raw.reusedWithin72Hours)
    throw Error("UNRECONCILED_REGISTRY_SOURCE_ARCHIVE");
  return {schemaVersion:1,scanned:raw.scanned as number,successful:raw.successful as number,
    failed:raw.failed as number,sourceAsOf:raw.scanStartedAt,
    records,postedResults:records.filter(x=>x.resultsPosted).length,
    withPrimaryMeasurements:records.filter(x=>x.measuredPrimary).length,
    withSeriousEventCounts:records.filter(x=>x.measuredSeriousEvents).length,
    truncatedRecords:records.filter(x=>x.truncated).length};
}
export function sourceReviewHint(row:RegistrySourceRow|undefined,group:number):string|null{
  if(!row)return null;
  if(group===3){
    if(row.measuredPrimary)return "Registry primary measurements posted — review required";
    return row.resultsPosted?"No primary measurements extracted — review required":"Registry results not posted";
  }
  if(group===8){
    if(row.measuredSeriousEvents)return "Registry serious-event counts posted — review required";
    return row.resultsPosted?"No reliable serious-event counts extracted":"Registry results not posted";
  }
  return null;
}
