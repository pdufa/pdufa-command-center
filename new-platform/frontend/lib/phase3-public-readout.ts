import type {Phase3CensusTrial} from "./phase3-census-rows";

/** Exact-NCT, dated release evidence. Registry results postings do not enter this gate. */
export type ReadoutKind="PRE_AS_OF_CHECK"|"POST_PUBLIC_READOUT";
export type ReadoutEvidence={
  nctId:string;ticker:string;kind:ReadoutKind;
  evidenceDate:string;evidenceUrl:string;drug:string;indication:string;
};
export type ReadoutRow=Phase3CensusTrial&{evidence:ReadoutEvidence|null};
export type ReadoutClassification={
  pre:ReadoutRow[];post:ReadoutRow[];unverified:ReadoutRow[];
  censusDate:string;sourceAsOf:string;sourceFiles:string[];
  total:number;
};
const SCOPE="HISTORICAL_US_LISTED_300M_10B_PHASE3_LEAD_SPONSOR_RESEARCH";
const sourceUrlOk=(s:unknown):s is string=>
  typeof s==="string"&&/^https:\/\/[^\s<>"']+$/.test(s);
const dayOk=(s:unknown):s is string=>
  typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
  !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
  new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const fail=():never=>{throw Error("Dated Phase 3 readout evidence did not pass identity or source verification.");};
export function classifyPhase3Readouts(raw:unknown,census:readonly Phase3CensusTrial[]):ReadoutClassification{
  if(!raw||typeof raw!=="object"||Array.isArray(raw))fail();
  const value=raw as Record<string,unknown>;
  const censusDate=value.censusDate,sourceAsOf=value.sourceAsOf;
  const sourceFiles=value.sourceFiles,entries=value.entries;
  if(value.schemaVersion!==1||value.scope!==SCOPE||
    !dayOk(censusDate)||!dayOk(sourceAsOf)||
    censusDate>sourceAsOf||
    !Array.isArray(sourceFiles)||
    sourceFiles.length!==2||
    !sourceFiles.includes("data/phase3_pre_readout_evidence.csv")||
    !sourceFiles.includes("data/post_phase3_discoveries.csv")||
    !Array.isArray(entries)||entries.length>census.length)fail();
  const censusIds=new Map(census.map(row=>[row.nctId,row]));
  if(censusIds.size!==741||census.length!==741)fail();
  const known=new Map<string,ReadoutEvidence>();
  for(const item of entries as unknown[]){
    if(!item||typeof item!=="object"||Array.isArray(item))fail();
    const row=item as Record<string,unknown>;
    const nctId=row.nctId,ticker=row.ticker,kind=row.kind;
    const evidenceDate=row.evidenceDate,evidenceUrl=row.evidenceUrl;
    const drug=row.drug,indication=row.indication;
    if(typeof nctId!=="string"||!/^NCT\d{8}$/.test(nctId)||
      typeof ticker!=="string"||known.has(nctId)||
      censusIds.get(nctId)?.ticker!==ticker||
      !["PRE_AS_OF_CHECK","POST_PUBLIC_READOUT"].includes(String(kind))||
      !dayOk(evidenceDate)||evidenceDate>sourceAsOf||
      !sourceUrlOk(evidenceUrl)||
      typeof drug!=="string"||typeof indication!=="string"||
      drug.length>300||indication.length>300)fail();
    known.set(nctId,{
      nctId,ticker,kind:kind as ReadoutKind,evidenceDate,evidenceUrl,drug,indication
    });
  }
  const pre:ReadoutRow[]=[],post:ReadoutRow[]=[],unverified:ReadoutRow[]=[];
  for(const row of census){
    const evidence=known.get(row.nctId)||null;
    const out={...row,evidence};
    if(evidence?.kind==="PRE_AS_OF_CHECK")pre.push(out);
    else if(evidence?.kind==="POST_PUBLIC_READOUT")post.push(out);
    else unverified.push(out);
  }
  if(pre.length+post.length+unverified.length!==census.length)fail();
  const byTicker=(a:ReadoutRow,b:ReadoutRow)=>a.ticker.localeCompare(b.ticker)||
    a.nctId.localeCompare(b.nctId);
  pre.sort(byTicker);post.sort(byTicker);unverified.sort(byTicker);
  return {
    pre,post,unverified,total:census.length,
    censusDate,sourceAsOf,sourceFiles:sourceFiles as string[]
  };
}
