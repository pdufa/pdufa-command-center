/** Live, per-exact-NCT scientific source review across every issuer-classified
 * TOP/BOTTOM spreadsheet trial. Current evidence availability is NOT an
 * independently calibrated investment or FDA probability score.
 */
import type {ReadoutClassification,ReadoutRow} from "./phase3-public-readout";
import type {RaasLiveRegistryAudit} from "./raas-live-registry-audit";
export type RaasClassifiedTrial={
 nctId:string;ticker:string;company:string;stage:"pre"|"post";
 evidenceDate:string;evidenceUrl:string;
};
export type RaasBulkRow={
 trial:RaasClassifiedTrial;
 result:RaasLiveRegistryAudit|null;
 state:"READY"|"SOURCE_UNAVAILABLE";
 problem:string|null;
};
export type RaasBulkSummary={
 totalCensus:number;classified:number;top:number;bottom:number;
 unverified:number;fetched:number;failed:number;
 registryPosted:number;registryProtocolOnly:number;
 withPrimaryMeasurements:number;withSAECounts:number;
 sourceLeadCount:number;
 approvedRaasScores:0;
 complete:boolean;
};
const nct=(v:string)=>/^NCT\d{8}$/.test(v);
const goodDate=(v:string)=>/^\d{4}-\d{2}-\d{2}$/.test(v)&&
 !Number.isNaN(Date.parse(v+"T00:00:00Z"))&&
 new Date(v+"T00:00:00Z").toISOString().slice(0,10)===v;
const url=(v:string)=>/^https:\/\/[^\s/]+\/\S+/.test(v);
function knownRows(rows:readonly ReadoutRow[],stage:"pre"|"post"):RaasClassifiedTrial[]{
 const kind=stage==="pre"?"PRE_AS_OF_CHECK":"POST_PUBLIC_READOUT";
 return rows.map(r=>{
  const e=r.evidence;
  if(!nct(r.nctId)||!r.ticker?.trim()||!r.company?.trim()||!e||
     e.kind!==kind||e.nctId!==r.nctId||e.ticker!==r.ticker||
     !goodDate(e.evidenceDate)||!url(e.evidenceUrl))
   throw Error("RAAS_BULK_ISSUER_SOURCE_CLASSIFICATION_INVALID");
  return {nctId:r.nctId,ticker:r.ticker,company:r.company,stage,
   evidenceDate:e.evidenceDate,evidenceUrl:e.evidenceUrl};
 });
}
export function classifiedRaasTrials(
 data:ReadoutClassification
):RaasClassifiedTrial[]{
 if(!data||!Array.isArray(data.pre)||!Array.isArray(data.post)||
  !Array.isArray(data.unverified)||!Number.isSafeInteger(data.total)||
  data.total!==data.pre.length+data.post.length+data.unverified.length)
  throw Error("RAAS_BULK_CENSUS_INVALID");
 const trials=[...knownRows(data.pre,"pre"),...knownRows(data.post,"post")];
 const seen=new Set<string>();
 for(const r of trials){
  if(seen.has(r.nctId))throw Error("RAAS_BULK_DUPLICATE_NCT");
  seen.add(r.nctId);
 }
 for(const r of data.unverified){
  if(!nct(r.nctId)||seen.has(r.nctId)||r.evidence!==null)
   throw Error("RAAS_BULK_UNVERIFIED_CONFLICT");
  seen.add(r.nctId);
 }
 if(seen.size!==data.total)throw Error("RAAS_BULK_CENSUS_INVALID");
 return trials;
}
export function summarizeBulkRaasSources(
 data:ReadoutClassification,rows:readonly RaasBulkRow[]
):RaasBulkSummary{
 const expected=classifiedRaasTrials(data);
 if(rows.length>expected.length)throw Error("RAAS_BULK_RESULT_COUNT_INVALID");
 const byNct=new Map(expected.map(x=>[x.nctId,x]));
 const seen=new Set<string>();
 for(const row of rows){
  const e=byNct.get(row.trial?.nctId);
  if(!e||seen.has(e.nctId)||e.stage!==row.trial.stage||
   e.ticker!==row.trial.ticker||
   row.state==="READY"&&(!row.result||row.result.nctId!==e.nctId||
    row.result.sourceNotValidated!==true)||
   row.state==="SOURCE_UNAVAILABLE"&&row.result!==null||
   !["READY","SOURCE_UNAVAILABLE"].includes(row.state))
    throw Error("RAAS_BULK_INVALID_RESEARCH_ROW");
  seen.add(e.nctId);
 }
 const valid=rows.filter(r=>r.state==="READY"&&r.result);
 return {totalCensus:data.total,classified:expected.length,
  top:data.pre.length,bottom:data.post.length,
  unverified:data.unverified.length,
  fetched:valid.length,failed:rows.filter(x=>x.state==="SOURCE_UNAVAILABLE").length,
  registryPosted:valid.filter(x=>x.result?.resultsPosted===true).length,
  registryProtocolOnly:valid.filter(x=>x.result?.resultsPosted===false).length,
  withPrimaryMeasurements:valid.filter(x=>(x.result?.primaryMeasurements??0)>0).length,
  withSAECounts:valid.filter(x=>(x.result?.seriousAdverseEventArms??0)>0).length,
  sourceLeadCount:valid.reduce((n,x)=>n+(x.result?.preliminaryMetricLeads.length??0),0),
  approvedRaasScores:0,complete:rows.length===expected.length};
}
