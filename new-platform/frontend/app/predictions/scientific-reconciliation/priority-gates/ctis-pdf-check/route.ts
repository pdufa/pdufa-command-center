import {createHash} from "node:crypto";
import {R95_EU_ACACIA_PROTOCOL_IDENTITY} from
 "../../../../../lib/focus-r95-eu-protocol-identity-gates";

/** MAIN R97 — original public CTIS document bytes fingerprint probe.
 * This is NOT a signed SAP certification. Fixed exact CTIS EUCT and document
 * UUIDs only; no arbitrary URL, redirect, user path, or NCT accepted.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const EUCT="2023-505797-15-00" as const;
const NCT="NCT06081894" as const;
const PROTOCOL="CY 6033" as const;
const BASE="https://euclinicaltrials.eu/ctis-public-api/documents/";
const LIMIT=24_000_000;
const DOCS={
 "am4-protocol":{
   uuid:"86e41e1d-b209-4209-bc83-b7e6ff3fcc69",
   title:"D1_2023-505797-15-00_Protocol_FP",
   manualVersion:"AM4",systemVersion:"6"
 },
 "am4-protocol-greek":{
   uuid:"effcac6a-5d31-4c95-9dbe-ed53df3a7fb8",
   title:"D1_2023-505797-15-00_Protocol_el_FP",
   manualVersion:"AM4",systemVersion:"6"
 },
 "am3-synopsis":{
   uuid:"bb5e0594-beed-427b-863a-5e27879c731a",
   title:"D1_2023-505797-15-00_Synopsis_EN_FP",
   manualVersion:"AM3",systemVersion:"5"
 },
 "protocol-addendum-a":{
   uuid:"777cdccb-1719-4488-8fde-67dcc03ad9d6",
   title:"D1_2023-505797-15-00_Protocol_add_A_FP",
   manualVersion:"A",systemVersion:"1"
 }
} as const;
function fail(error:string,status=502){
 return Response.json({
  error,originalPdfBytesAuthenticated:false,
  signedFinalProspectiveSAPAuthenticated:false,
  firstUnblindedAccessAuditVerified:false,
  qualifiedScientificReviewSigned:false,
  FDAForecast:"ABSTAIN"
 },{status,headers:{"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"}});
}
export async function GET(req:Request):Promise<Response>{
 const audit=R95_EU_ACACIA_PROTOCOL_IDENTITY;
 if(!audit||audit.exactNct!==NCT||audit.sponsorProtocolCode!==PROTOCOL||
   audit.euTrialNumber!==EUCT||
   audit.wrongProtocolCodeExcluded!=="CY 6032"||
   audit.signedFinalSapVersionsVerified!==0||audit.exactOriginalPdfBytesCaptured!==0||
   audit.FDAForecast!=="ABSTAIN")
  return fail("FOCUS_ACACIA_EXACT_TRIAL_IDENTITY_FAILED",503);
 const key=new URL(req.url).searchParams.get("doc")??"";
 if(!Object.prototype.hasOwnProperty.call(DOCS,key))
   return fail("DOCUMENT_KEY_OUTSIDE_ORIGINAL_CTIS_ACACIA_ROSTER",404);
 const doc=DOCS[key as keyof typeof DOCS];
 const url=BASE+EUCT+"/"+doc.uuid+"/download";
 try{
  const res=await fetch(url,{
   method:"GET",redirect:"error",cache:"no-store",
   headers:{"Accept":"application/pdf,application/octet-stream;q=0.9"},
   signal:AbortSignal.timeout(18000)
  });
  if(!res.ok)return fail("ORIGINAL_CTIS_PDF_SOURCE_HTTP_"+res.status);
  const claimed=Number(res.headers.get("content-length")??0);
  if(!Number.isFinite(claimed)||claimed>LIMIT)return fail("ORIGINAL_CTIS_PDF_TOO_LARGE");
  const bytes=new Uint8Array(await res.arrayBuffer());
  if(bytes.length<1024||bytes.length>LIMIT)
   return fail("ORIGINAL_CTIS_PDF_INVALID_SIZE");
  const prefix=String.fromCharCode(...bytes.slice(0,8));
  if(!prefix.startsWith("%PDF-"))return fail("ORIGINAL_CTIS_RESPONSE_NOT_PDF");
  const digest=createHash("sha256").update(bytes).digest("hex");
  const tail=String.fromCharCode(...bytes.slice(-2048));
  return Response.json({
   schema:"MAIN_R97_OFFICIAL_ACACIA_CTIS_ORIGINAL_PDF_BYTE_RECEIPT_NOT_SIGNED_SAP",
   exactNct:NCT,exactEUCT:EUCT,exactProtocol:PROTOCOL,
   docKey:key,ctisDocumentTitle:doc.title,
   manualVersion:doc.manualVersion,systemVersion:doc.systemVersion,
   ctisUuid:doc.uuid,originalOfficialUrl:url,
   responseType:res.headers.get("content-type"),
   originalPdfBytes:bytes.length,
   pdfMagicHeaderConfirmed:true,
   pdfEofMarkerVisible:tail.includes("%%EOF"),
   originalBytesSha256:digest,
   originalPdfContentsVisuallyInspected:false,
   originalPdfSourceAuthenticatedToTrialMetadata:true,
   originalControlledFinalProspectiveSAPSignatureAuthenticated:false,
   firstUnblindingTimeVerified:false,
   independentClinicalScienceReviewSigned:false,
   FDAForecast:"ABSTAIN"
  },{headers:{"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"}});
 }catch{
  return fail("ORIGINAL_CTIS_DOWNLOAD_NETWORK_OR_RESPONSE_FAILURE");
 }
}
