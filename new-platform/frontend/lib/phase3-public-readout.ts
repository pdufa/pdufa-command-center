import type {Phase3CensusTrial} from "./phase3-census-rows";
import * as addedSource from "../data/phase3_issuer_readout_additions_2026-11-05.json";

/** Exact-NCT, dated release evidence. Registry results postings do not enter this gate. */
export type ReadoutKind="PRE_AS_OF_CHECK"|"POST_PUBLIC_READOUT";
export type ReadoutEvidence={
  nctId:string;ticker:string;kind:ReadoutKind;
  evidenceDate:string;evidenceUrl:string;drug:string;indication:string;
  primaryEndpointP?:{display:string;endpoint:string;sourceUrl:string};
  issuerTrialName?:string;registryTrialUrl?:string;
};
export type ReadoutRow=Phase3CensusTrial&{evidence:ReadoutEvidence|null};
export type ReadoutClassification={
  pre:ReadoutRow[];post:ReadoutRow[];unverified:ReadoutRow[];
  censusDate:string;sourceAsOf:string;sourceFiles:string[];
  total:number;
};
const SCOPE="HISTORICAL_US_LISTED_300M_10B_PHASE3_LEAD_SPONSOR_RESEARCH";
const NEW_SOURCE="data/phase3_issuer_readout_additions_2026-11-05.json";
const sourceUrlOk=(s:unknown):s is string=>
  typeof s==="string"&&/^https:\/\/[^\s<>"']+$/.test(s);
const dayOk=(s:unknown):s is string=>
  typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&
  !Number.isNaN(Date.parse(s+"T00:00:00Z"))&&
  new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
const fail=():never=>{throw Error("Dated Phase 3 readout evidence did not pass identity or source verification.");};
export function classifyPhase3Readouts(raw:unknown,census:readonly Phase3CensusTrial[]):ReadoutClassification{
  if(!raw||typeof raw!=="object"||Array.isArray(raw))return fail();
  const value=raw as Record<string,unknown>;
  const censusDate=value.censusDate,sourceAsOf=value.sourceAsOf;
  const sourceFiles=value.sourceFiles,entries=value.entries;
  if(value.schemaVersion!==1||value.scope!==SCOPE||
    !dayOk(censusDate)||!dayOk(sourceAsOf)||
    censusDate>sourceAsOf||
    !Array.isArray(sourceFiles)||
    ![2,3].includes(sourceFiles.length)||
    !sourceFiles.includes("data/phase3_pre_readout_evidence.csv")||
    !sourceFiles.includes("data/post_phase3_discoveries.csv")||
    (sourceFiles.length===3&&!sourceFiles.includes(NEW_SOURCE))||
    !Array.isArray(entries)||entries.length>census.length)return fail();
  const censusIds=new Map(census.map(row=>[row.nctId,row]));
  if(censusIds.size!==741||census.length!==741)return fail();
  const hasManualReview=sourceFiles.includes(NEW_SOURCE);
  // New issuer/registry dual-source identities must never remain classifiable
  // if the provenance ledger was accidentally dropped from the manifest.
  if(!hasManualReview&&entries.some(item=>item&&typeof item==="object"&&
    ("issuerTrialName" in item||"registryTrialUrl" in item)))return fail();
  const provenance=addedSource.records;
  const expectedCrosswalk=new Map(provenance.map(x=>[x.nctId,x]));
  if(hasManualReview&&
     (entries.length!==10||
      addedSource.schemaVersion!==1||
      !addedSource.scope.endsWith("PHASE3_ISSUER_AND_REGISTRY_DUAL_SOURCE_READOUT_CROSSWALK_RESEARCH_ONLY")||
      addedSource.classifiedIssuerEvidenceSnapshotAsOf!==sourceAsOf||
      expectedCrosswalk.size!==5||
      addedSource.counts.newBottomReadoutRecords!==5||
      addedSource.counts.verifiedFdaRegulatoryOutcomes!==0))return fail();
  const matchedCrosswalk=new Set<string>();
  const known=new Map<string,ReadoutEvidence>();
  for(const item of entries as unknown[]){
    if(!item||typeof item!=="object"||Array.isArray(item))return fail();
    const row=item as Record<string,unknown>;
    const nctId=row.nctId,ticker=row.ticker,kind=row.kind;
    const evidenceDate=row.evidenceDate,evidenceUrl=row.evidenceUrl;
    const drug=row.drug,indication=row.indication;
    const rawP=row.primaryEndpointP;
    const trialName=row.issuerTrialName,registryTrialUrl=row.registryTrialUrl;
    const hasIdentity=trialName!==undefined||registryTrialUrl!==undefined;
    if(hasIdentity&&
      (kind!=="POST_PUBLIC_READOUT"||
       typeof trialName!=="string"||!/^[A-Za-z0-9 -]{3,90}$/.test(trialName)||
       registryTrialUrl!=="https://clinicaltrials.gov/study/"+nctId))
      return fail();
    if(hasManualReview&&expectedCrosswalk.has(String(nctId))){
     const verified=expectedCrosswalk.get(String(nctId))!;
     if(row.kind!==verified.kind||row.ticker!==verified.ticker||
      trialName!==verified.issuerTrialName||
      registryTrialUrl!==verified.registryTrialUrl||
      row.drug!==verified.drug||row.indication!==verified.indication||
      row.evidenceDate!==verified.evidenceDate||
      row.evidenceUrl!==verified.evidenceUrl)return fail();
     matchedCrosswalk.add(String(nctId));
    }
    if(hasManualReview&&!hasIdentity&&expectedCrosswalk.has(String(nctId)))return fail();
    let primaryEndpointP:ReadoutEvidence["primaryEndpointP"];
    if(rawP!==undefined){
      if(kind!=="POST_PUBLIC_READOUT"||!rawP||typeof rawP!=="object"||Array.isArray(rawP))return fail();
      const p=rawP as Record<string,unknown>;
      if(typeof p.display!=="string"||!/^p\s*(?:<|=|≤)\s*0?\.\d+$/.test(p.display)||
        typeof p.endpoint!=="string"||!p.endpoint.trim()||p.endpoint.length>400||
        !sourceUrlOk(p.sourceUrl)||p.sourceUrl!==evidenceUrl)return fail();
      primaryEndpointP={display:p.display,endpoint:p.endpoint,sourceUrl:p.sourceUrl};
    }
    if(typeof nctId!=="string"||!/^NCT\d{8}$/.test(nctId)||
      typeof ticker!=="string"||known.has(nctId)||
      censusIds.get(nctId)?.ticker!==ticker||
      !["PRE_AS_OF_CHECK","POST_PUBLIC_READOUT"].includes(String(kind))||
      !dayOk(evidenceDate)||evidenceDate>sourceAsOf||
      !sourceUrlOk(evidenceUrl)||
      typeof drug!=="string"||typeof indication!=="string"||
      drug.length>300||indication.length>300)return fail();
    known.set(nctId,{
      nctId,ticker,kind:kind as ReadoutKind,evidenceDate,evidenceUrl,drug,indication,primaryEndpointP,
      ...(hasIdentity?{issuerTrialName:trialName as string,registryTrialUrl:registryTrialUrl as string}:{})
    });
  }
  if(hasManualReview&&matchedCrosswalk.size!==expectedCrosswalk.size)return fail();
  const pre:ReadoutRow[]=[],post:ReadoutRow[]=[],unverified:ReadoutRow[]=[];
  for(const row of census){
    const evidence=known.get(row.nctId)||null;
    const out={...row,evidence};
    if(evidence?.kind==="PRE_AS_OF_CHECK")pre.push(out);
    else if(evidence?.kind==="POST_PUBLIC_READOUT")post.push(out);
    else unverified.push(out);
  }
  if(pre.length+post.length+unverified.length!==census.length)return fail();
  const byTicker=(a:ReadoutRow,b:ReadoutRow)=>a.ticker.localeCompare(b.ticker)||
    a.nctId.localeCompare(b.nctId);
  pre.sort(byTicker);post.sort(byTicker);unverified.sort(byTicker);
  return {
    pre,post,unverified,total:census.length,
    censusDate,sourceAsOf,sourceFiles:sourceFiles as string[]
  };
}
