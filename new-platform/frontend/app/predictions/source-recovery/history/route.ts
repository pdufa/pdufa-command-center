import {R89_HISTORICAL_SOURCE_RECOVERY} from
 "../../../../lib/focus-r89-historical-source-recovery";

/** Official ClinicalTrials.gov public historical registry versions (non-v2
 * UI history API used in original ACACIA source research). History access can
 * fail independently of the current v2 API: never report blocked as missing.
 * No untrusted host or PDF path; no source, trial, model or reviewer writes.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const HEADERS={
 "Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"
} as const;
const MAX_BYTES=2_500_000;
type AnyRecord=Record<string,unknown>;
function obj(x:unknown):AnyRecord|null{
 return x!==null&&typeof x==="object"&&!Array.isArray(x)?x as AnyRecord:null;
}
function text(x:unknown,limit=500):string|null{
 return typeof x==="string"&&x.length>0&&x.length<=limit?x:null;
}
function fail(code:string,status:number):Response{
 return Response.json({
  error:code,
  unknownHistoricalSourceNotAbsent:true,
  verifiedSignedProspectiveSAPs:0,qualifiedScientificReviews:0,
  FDAForecast:"ABSTAIN"
 },{status,headers:HEADERS});
}
async function fetchOfficial(url:string):Promise<unknown>{
 const r=await fetch(url,{
  method:"GET",cache:"no-store",redirect:"error",
  headers:{"Accept":"application/json"},signal:AbortSignal.timeout(11000)
 });
 if(!r.ok)throw new Error("UPSTREAM_STATUS_"+r.status);
 const contentType=r.headers.get("content-type")??"";
 if(!contentType.includes("json"))throw new Error("UPSTREAM_NON_JSON");
 const headerSize=Number(r.headers.get("content-length")??0);
 if(!Number.isFinite(headerSize)||headerSize>MAX_BYTES)
  throw new Error("UPSTREAM_OVERSIZE");
 const raw=await r.text();
 if(raw.length>MAX_BYTES)throw new Error("UPSTREAM_OVERSIZE");
 return JSON.parse(raw) as unknown;
}
function identityOf(study:unknown):string|null{
 const p=obj(obj(study)?.protocolSection);
 return text(obj(p?.identificationModule)?.nctId,30);
}
function historyIndex(raw:unknown,nct:string){
 const record=obj(raw),body=record?.study;
 if(identityOf(body)!==nct)return null;
 const history=obj(record?.history),items=history?.changes;
 if(!Array.isArray(items)||items.length<1||items.length>500)return null;
 const seen=new Set<number>();
 const entries=[];
 for(const item of items){
  const x=obj(item);
  if(!x||typeof x.version!=="number"||!Number.isSafeInteger(x.version)||
     x.version<0||x.version>499||seen.has(x.version)||
     typeof x.date!=="string"||!/^20\d{2}-\d{2}-\d{2}$/u.test(x.date))
   return null;
  seen.add(x.version);
  entries.push({apiIndex:x.version,uiVersion:x.version+1,submittedDate:x.date});
 }
 entries.sort((a,b)=>a.apiIndex-b.apiIndex);
 return entries;
}
function inspectVersion(raw:unknown,nct:string,version:number,submittedDate:string){
 const outer=obj(raw);
 if(!outer||outer.studyVersion!==version||identityOf(outer.study)!==nct)return null;
 const p=obj(obj(outer.study)?.protocolSection);
 const status=obj(p?.statusModule);
 const submitted=text(status?.lastUpdateSubmitDate,20);
 if(submitted!==submittedDate)return null;
 const outcomes=obj(p?.outcomesModule);
 const primary=outcomes?.primaryOutcomes;
 if(primary!==undefined&&!Array.isArray(primary))return null;
 if(Array.isArray(primary)&&primary.length>50)return null;
 const docs=obj(obj(outer.study)?.documentSection);
 const large=obj(docs?.largeDocumentModule);
 const original=large?.largeDocs??[];
 if(!Array.isArray(original)||original.length>100)return null;
 const listed=[];
 for(const value of original){
  const x=obj(value);
  const name=text(x?.filename,160);
  if(!x||!name||/[/\\]|\.\./u.test(name))return null;
  listed.push({
   filename:name,typeAbbrev:text(x.typeAbbrev,30),
   documentDate:text(x.date,30),registryUploadDate:text(x.uploadDate,40),
   hasProtocol:x.hasProtocol===true,hasSAP:x.hasSap===true,
   reportedSize:typeof x.size==="number"&&Number.isSafeInteger(x.size)&&x.size>0?x.size:null
  });
 }
 return {
  nct,
  apiIndex:version,uiVersion:version+1,submittedDate,
  officialSourceUrl:"https://clinicaltrials.gov/api/int/studies/"+nct+"/history/"+version,
  registryReportedStatus:text(status?.overallStatus,100),
  originalPrimaryOutcomeCount:Array.isArray(primary)?primary.length:null,
  originalPublicDocumentListingCount:listed.length,
  listedProtocolOrSapDocuments:listed.filter(x=>x.hasProtocol||x.hasSAP),
  historicalOriginalSourceByteSha256:null,
  documentContentRead:false as const,
  prospectivelyAuthenticatedSignedSAP:false as const,
  independentScientificReview:false as const,
  FDAForecast:"ABSTAIN" as const,
  notice:"Dated original registry-version metadata only: no authenticated original protocol/SAP approval or unblinding history."
 };
}
export async function GET(request:Request):Promise<Response>{
 const manifest=R89_HISTORICAL_SOURCE_RECOVERY;
 if(!manifest)return fail("EXACT_FOCUS_RESEARCH_CROSSWALK_INVALID",503);
 const query=new URL(request.url).searchParams;
 const nct=query.get("nct")??"";
 if(!/^NCT\d{8}$/u.test(nct))return fail("EXACT_NCT_REQUIRED",400);
 const row=manifest.rows.find(x=>x.nct===nct);
 if(!row)return fail("NCT_NOT_IN_17_MISSING_CURRENT_ORIGINALS",404);
 const versionParam=query.get("version");
 if(versionParam!==null&&!/^(?:0|[1-9]\d{0,2})$/u.test(versionParam))
  return fail("VALID_HISTORY_VERSION_INDEX_REQUIRED",400);
 const version=versionParam===null?null:Number(versionParam);
 if(version!==null&&version>499)return fail("HISTORY_VERSION_OUT_OF_BOUNDS",400);
 const base="https://clinicaltrials.gov/api/int/studies/"+row.nct;
 let original:unknown;
 try{original=await fetchOfficial(base+"?history=true");}
 catch{return fail("OFFICIAL_HISTORY_NOT_ACCESSIBLE_CHECK_PUBLIC_UI_OR_RETRY",502);}
 const index=historyIndex(original,row.nct);
 if(!index)return fail("HISTORY_ORIGINAL_IDENTITY_OR_INDEX_INVALID",502);
 if(version===null){
  return Response.json({
   nct:row.nct,ticker:row.ticker,
   sourceUrl:base+"?history=true",
   historyVersionCount:index.length,
   versions:index,
   publiclyListedOriginalsOnly:true,
   authenticatedSignedSAPs:0,qualifiedReviews:0,FDAForecast:"ABSTAIN",
   note:"Official submitted-date history is not an independently certified SAP chronology. For public availability use posting date, which can follow submission."
  },{headers:HEADERS});
 }
 const selected=index.find(x=>x.apiIndex===version);
 if(!selected)return fail("HISTORY_VERSION_NOT_IN_OFFICIAL_INDEX",404);
 try{
  const exact=await fetchOfficial(base+"/history/"+version);
  const result=inspectVersion(exact,row.nct,version,selected.submittedDate);
  if(!result)return fail("ORIGINAL_HISTORY_VERSION_ID_OR_SUBMISSION_DATE_MISMATCH",502);
  return Response.json(result,{headers:HEADERS});
 }catch{return fail("OFFICIAL_EXACT_HISTORY_VERSION_NOT_ACCESSIBLE",502);}
}
