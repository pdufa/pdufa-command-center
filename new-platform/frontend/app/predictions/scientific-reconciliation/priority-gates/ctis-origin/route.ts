import {createHash} from "node:crypto";
import {R95_EU_ACACIA_PROTOCOL_IDENTITY} from
 "../../../../../lib/focus-r95-eu-protocol-identity-gates";

/** MAIN R96: source-only diagnostic of exact public EU CTIS original document
 * manifest. Fixed public EUCT record, no arbitrary host, URL or trial input.
 * Document UUIDs are references, not authenticated PDF bytes or signed SAPs.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const HOST="https://euclinicaltrials.eu";
const CT="2023-505797-15-00";
const NCT="NCT06081894";
const CODE="CY 6033";
const API=HOST+"/ctis-public-api/retrieve/"+CT;
const HEADERS={"Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"} as const;
const MAX_BYTES=8_000_000;
type Dict=Record<string,unknown>;
function obj(v:unknown):Dict|null{
 return v!==null&&typeof v==="object"&&!Array.isArray(v)?v as Dict:null;
}
function value(v:unknown):string|null{
 return typeof v==="string"&&v.length>0&&v.length<250?v:null;
}
function fail(reason:string,status=502){
 return Response.json({
  error:reason,originalPdfByteCountVerified:0,
  finalSignedSAPVerified:false,independentScienceReviewSigned:false,
  FDAForecast:"ABSTAIN"
 },{status,headers:HEADERS});
}
export async function GET():Promise<Response>{
 const audit=R95_EU_ACACIA_PROTOCOL_IDENTITY;
 if(!audit||audit.exactNct!==NCT||audit.euTrialNumber!==CT||
   audit.sponsorProtocolCode!==CODE||
   audit.originalAcaciaGatesUnresolved!==4||
   audit.originalLaunchGatesUnresolved!==7||
   audit.signedFinalSapVersionsVerified!==0||
   audit.exactOriginalPdfBytesCaptured!==0||
   audit.FDAForecast!=="ABSTAIN")
  return fail("EXACT_ACACIA_CTIS_SOURCE_GUARD_FAILED",503);
 try{
  const response=await fetch(API,{
   cache:"no-store",redirect:"error",method:"GET",
   headers:{"Accept":"application/json"},
   signal:AbortSignal.timeout(12000)
  });
  if(!response.ok)return fail("OFFICIAL_CTIS_SOURCE_NOT_ACCESSIBLE_"+response.status);
  const sz=Number(response.headers.get("content-length")??0);
  if(!Number.isFinite(sz)||sz>MAX_BYTES)return fail("CTIS_SOURCE_OVERSIZE");
  const raw=await response.text();
  if(raw.length>MAX_BYTES)return fail("CTIS_SOURCE_OVERSIZE");
  const sha=createHash("sha256").update(raw,"utf8").digest("hex");
  const json:unknown=JSON.parse(raw);
  const root=obj(json);
  if(!root)return fail("CTIS_SOURCE_NOT_JSON_OBJECT");
  // Do not count text presence as signed version proof: guard only the
  // exact official EUCT identity, then inspect document metadata cautiously.
  if(!raw.includes(CT)||!raw.includes(CODE))
   return fail("CTIS_RECORD_EUCT_PROTOCOL_IDENTITY_MISMATCH");
  const found:Array<{
   treePath:string;
   fieldNames:string[];
   title:string|null;
   version:string|null;
   uuid:string|null;
   id:string|null;
   associatedEntityId:string|null;
   manualVersion:string|null;
   systemVersion:string|null;
   fileType:string|null;
  }>=[];
  let nodes=0;
  const seen=new WeakSet<object>();
  function walk(item:unknown,path:string,depth:number){
   if(depth>16||nodes++>120_000||found.length>=70||!item||
     typeof item!=="object"||seen.has(item as object))return;
   seen.add(item as object);
   if(Array.isArray(item)){
    for(let i=0;i<Math.min(item.length,3000);i++)walk(item[i],path+"["+i+"]",depth+1);
    return;
   }
   const x=obj(item);
   if(!x)return;
   const candidates=["title","documentTitle","documentName","name",
    "fileName","filename","uploadedFileName","originalFileName",
    "label","docTitle","documentTypeName"];
   const titles=candidates.map(k=>value(x[k])).filter((s):s is string=>Boolean(s));
   const target=titles.find(s=>
     /2023-505797-15-00.*(?:Protocol|Synopsis)|CY.?6033|Protocol_FP|Synopsis_EN_FP/i.test(s));
   if(target){
    const version=["version","documentVersion","versionNumber","versionLabel"]
     .map(k=>value(x[k])??(typeof x[k]==="number"?String(x[k]):null))
     .find(Boolean)??null;
    const uuid=["uuid","documentUuid","documentUUID","fileUuid","documentId","fileId"]
     .map(k=>value(x[k])).find(Boolean)??null;
    found.push({
     treePath:path.slice(0,400),fieldNames:Object.keys(x).slice(0,45),
     title:target.slice(0,250),version,uuid,
     id:value(x.id)??value(x._id),
     associatedEntityId:value(x.associatedEntityId),
     manualVersion:value(x.manualVersion),
     systemVersion:value(x.systemVersion),
     fileType:value(x.fileType)
    });
   }
   for(const [k,v] of Object.entries(x)){
    if(v&&typeof v==="object"&&depth<16)walk(v,path+"."+k,depth+1);
   }
  }
  walk(root,"root",0);
  return Response.json({
   schema:"MAIN_R96_CTIS_ACACIA_ORIGINAL_DOCUMENT_INDEX_RETRIEVAL_NOT_SIGNED_SAP",
   exactEuct:CT,exactNct:NCT,exactProtocol:CODE,
   officialPublicSourceUrl:API,
   originalSourceResponseSha256:sha,rawResponseCharacters:raw.length,
   recordKeys:Object.keys(root).slice(0,45),
   trialIdCandidates:["id","_id","trialId","trialID","ctId"].map(k=>
    ({field:k,value:value(root[k])})),
   authorizedApplicationKeys:Object.keys(obj(root.authorizedApplication)??{}).slice(0,55),
   documentObjectCount:Array.isArray(root.documents)?root.documents.length:null,
   protocolRecordMatches:found,
   discoveredProtocolRecordCount:found.length,
   nodesVisited:nodes,
   isOriginalPublicDocumentBytes:false,
   independentlyAuthenticatedSignedSAPs:0,
   firstUnblindedAccessAuditsVerified:0,
   qualifiedClinicalReviewsSigned:0,
   FDAForecast:"ABSTAIN"
  },{headers:HEADERS});
 }catch{
  return fail("CTIS_OFFICIAL_JSON_RETRIEVAL_OR_SHAPE_FAILED");
 }
}
