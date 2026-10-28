import {normalizeDrugsFdaApplication,type OpenFdaApplication,type FdaApplicationEvidence} from "./decision-openfda-normalizer";
import {buildFdaReviewCycleLedger,type FdaReviewCycleLedger} from "./decision-fda-review-cycles";
/** Retrieval metadata describes this request, not independent verification of the returned documents. */
export type FdaRetrievalProvenance={sourceUrl:string;retrievedAt:string;sourceLastUpdated:string|null;applicationNumber:string};
/** Read-only FDA retrieval. No persistence, no automatic decision classification, no live trading. */
export type FdaFetchResult={status:"AVAILABLE_FOR_REVIEW"|"NOT_READY";application:FdaApplicationEvidence|null;provenance:FdaRetrievalProvenance|null;reviewCycleLedger:FdaReviewCycleLedger|null;issues:string[]};
export async function retrieveDrugsFdaApplication(applicationNumber:string,fetcher:typeof fetch=fetch):Promise<FdaFetchResult>{
 const fail=(issue:string):FdaFetchResult=>({status:"NOT_READY",application:null,provenance:null,reviewCycleLedger:null,issues:[issue]});
 if(!/^(NDA|BLA|ANDA)\d{6}$/i.test(applicationNumber))return fail("Invalid FDA application number");
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),10000);
 try{
  const url=new URL("https://api.fda.gov/drug/drugsfda.json");
  url.searchParams.set("search",'application_number:"'+applicationNumber.toUpperCase()+'"');url.searchParams.set("limit","1");
  const response=await fetcher(url.toString(),{signal:controller.signal,headers:{Accept:"application/json"},cache:"no-store",redirect:"error"});
  if(!response.ok)return fail("FDA request failed (HTTP "+response.status+")");
  const body:unknown=await response.json();
  if(!body||typeof body!=="object"||!("results" in body)||!Array.isArray(body.results)||body.results.length!==1)return fail("FDA returned no unique application record");
  const raw=body.results[0] as OpenFdaApplication;
  if(raw.application_number?.toUpperCase()!==applicationNumber.toUpperCase())return fail("FDA application identity mismatch");
  const application=normalizeDrugsFdaApplication(raw);
  const retrievedAt=new Date().toISOString();
  const meta="meta" in body&&body.meta&&typeof body.meta==="object"?body.meta:null;
  const sourceLastUpdated=meta&&"last_updated" in meta&&typeof meta.last_updated==="string"?meta.last_updated:null;
  const provenance={sourceUrl:url.toString(),retrievedAt,sourceLastUpdated,applicationNumber:application.applicationNumber};
  const reviewCycleLedger=buildFdaReviewCycleLedger(application,[],retrievedAt);
  return {status:"AVAILABLE_FOR_REVIEW",application,provenance,reviewCycleLedger,issues:[...application.warnings,...reviewCycleLedger.issues]};
 }catch{return fail("FDA retrieval unavailable or invalid response");}finally{clearTimeout(timeout);}
}
