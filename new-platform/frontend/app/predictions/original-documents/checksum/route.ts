import {R86_ORIGINAL_DOCUMENT_MANIFEST,inspectR86CurrentStudy} from
 "../../../../lib/focus-r86-original-document-inventory";
import {R87_MAX_SOURCE_PDF_BYTES,digestR87PublicPdf,selectR87PublicSourcePdf} from
 "../../../../lib/focus-r87-public-original-pdf-receipt";

export const runtime="nodejs";
export const dynamic="force-dynamic";
const HEADERS={"Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"} as const;
function fail(status:number,code:string):Response{
 return Response.json({error:code,originalSignedSAPAuthenticated:false,
  independentClinicalReview:false,FDAForecast:"ABSTAIN"},{status,headers:HEADERS});
}
async function readBoundedJson(response:Response):Promise<unknown>{
 const l=Number(response.headers.get("content-length")??0);
 if(!Number.isFinite(l)||l>2_000_000)return null;
 const raw=await response.text();
 if(raw.length>2_000_000)return null;
 return JSON.parse(raw) as unknown;
}
/** Bounded GET-only source-byte checksum, never a signed SAP or graded science. */
export async function GET(request:Request):Promise<Response>{
 const manifest=R86_ORIGINAL_DOCUMENT_MANIFEST;
 if(!manifest)return fail(503,"SOURCE_MANIFEST_INTEGRITY_FAILED");
 const q=new URL(request.url).searchParams;
 const nct=q.get("nct")??"",filename=q.get("filename")??"";
 if(!/^NCT\d{8}$/u.test(nct)||
    !/^[A-Za-z0-9][A-Za-z0-9_.() -]{0,129}\.pdf$/u.test(filename)||
    filename.includes(".."))return fail(400,"EXACT_NCT_AND_OFFICIAL_PDF_FILENAME_REQUIRED");
 const row=manifest.rows.find(r=>r.nct===nct);
 if(!row)return fail(404,"NCT_OUTSIDE_LOCKED_FOCUS_ROSTER");
 try{
  const registry=await fetch(
    "https://clinicaltrials.gov/api/v2/studies/"+row.nct+"?format=json",{
     method:"GET",redirect:"error",cache:"no-store",
     headers:{"Accept":"application/json"},signal:AbortSignal.timeout(12000)
    });
  if(!registry.ok)return fail(502,"OFFICIAL_REGISTRY_UNAVAILABLE");
  const study=await readBoundedJson(registry);
  const inventory=inspectR86CurrentStudy(row,study);
  const selection=selectR87PublicSourcePdf(row.nct,filename,inventory);
  if(!selection)return fail(422,"NOT_AN_ELIGIBLE_CURRENT_REGISTRY_PROTOCOL_OR_SAP_FILE");
  const pdf=await fetch(selection.publicCdnUrl,{
   method:"GET",redirect:"error",cache:"no-store",
   headers:{"Accept":"application/pdf"},signal:AbortSignal.timeout(15000)
  });
  if(!pdf.ok)return fail(502,"OFFICIAL_SOURCE_PDF_UNAVAILABLE");
  const sizeHeader=pdf.headers.get("content-length");
  if(sizeHeader!==null && Number(sizeHeader)!==selection.registryReportedSize)
    return fail(502,"PDF_DECLARED_BYTE_LENGTH_MISMATCH");
  if(selection.registryReportedSize>R87_MAX_SOURCE_PDF_BYTES)
    return fail(413,"SOURCE_PDF_EXCEEDS_BOUNDED_RETRIEVAL_SIZE");
  const body=await pdf.arrayBuffer();
  const result=digestR87PublicPdf(selection,new Uint8Array(body));
  if(!result)return fail(502,"SOURCE_PDF_BYTE_LENGTH_OR_MAGIC_MISMATCH");
  return Response.json({
    ...result,retrievedAtUtc:new Date().toISOString(),
    sourceAccessKind:"OFFICIAL_CDN_PUBLIC_PDF_BYTES_READ_ONLY" as const
  },{headers:HEADERS});
 }catch{
  return fail(502,"PUBLIC_SOURCE_BYTE_RETRIEVAL_FAILED");
 }
}
