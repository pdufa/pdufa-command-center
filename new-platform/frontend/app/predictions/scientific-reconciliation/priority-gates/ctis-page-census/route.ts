import {createHash} from "node:crypto";
import {GET as originalPdf} from "../ctis-pdf-check/route";
import {R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS} from "../../../../../lib/focus-r98-ctis-original-pdf-receipts";
/** MAIN R102: source-verified PDF structural page census, not a page-text parser.
 * Counts page dictionaries and content-stream references, flags unsupported
 * object-stream compression and deliberately does not attribute text to pages.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const HEADERS={"Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"} as const;
function fail(error:string,status=502){
 return Response.json({error,scientificPageReviewComplete:false,
  signedFinalSAPAuthenticated:false,FDAForecast:"ABSTAIN"},{status,headers:HEADERS});
}
export async function GET(req:Request):Promise<Response>{
 const key=new URL(req.url).searchParams.get("doc");
 const source=R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS;
 const item=source?.originalDocuments.find(x=>x.key===key);
 if(!item||source?.FDAForecast!=="ABSTAIN")
  return fail("UNAUTHORIZED_CTIS_ORIGINAL_DOCUMENT_KEY",404);
 const url=new URL(req.url);
 url.pathname="/predictions/scientific-reconciliation/priority-gates/ctis-pdf-check";
 url.search="?doc="+encodeURIComponent(item.key)+"&download=1";
 const verified=await originalPdf(new Request(url.toString()));
 if(!verified.ok)return fail("ORIGINAL_PDF_SOURCE_CHECK_FAILED_"+verified.status);
 const bytes=Buffer.from(await verified.arrayBuffer());
 const sha=createHash("sha256").update(bytes).digest("hex");
 if(sha!==item.sha256||bytes.length!==item.byteCount)
  return fail("ORIGINAL_PDF_CENSUS_SHA_MISMATCH",409);
 const raw=bytes.toString("latin1");
 const objects=[...raw.matchAll(/(?:^|\r?\n)(\d{1,9})\s+(\d{1,5})\s+obj\b([\s\S]*?)\bendobj\b/g)];
 const pages: Array<{pageObject:string,contentRefs:string[],mediaBox:string|null}>=[];
 let pagesTreeCountHints:number[]=[];
 let objectStreams=0;
 for(const m of objects){
  const id=m[1]+" "+m[2]+" R";
  const body=m[3].slice(0,100000);
  if(/\/Type\s*\/ObjStm\b/.test(body))objectStreams++;
  if(/\/Type\s*\/Pages\b/.test(body)){
   const count=body.match(/\/Count\s+(\d+)/);
   if(count)pagesTreeCountHints.push(Number(count[1]));
  }
  if(!/\/Type\s*\/Page\b(?!s)/.test(body))continue;
  const contents=body.match(/\/Contents\s*(?:\[((?:.|\n|\r)*?)\]|(\d+\s+\d+\s+R))/);
  const refs=(contents?.[1]??contents?.[2]??"").match(/\d+\s+\d+\s+R/g)??[];
  const mediaBox=body.match(/\/MediaBox\s*\[([^\]]{1,100})\]/)?.[1]??null;
  pages.push({pageObject:id,contentRefs:refs.slice(0,50),mediaBox});
  if(pages.length>=1000)break;
 }
 const structuralPageCount=pages.length;
 const pageTreeCountHint=Math.max(0,...pagesTreeCountHints);
 const reliableCount=objectStreams===0&&
  structuralPageCount>0&&
  (pageTreeCountHint===0||pageTreeCountHint===structuralPageCount);
 return Response.json({
  schema:"MAIN_R102_ORIGINAL_CTIS_PDF_PAGE_STRUCTURE_CENSUS_NOT_PAGE_TEXT_REVIEW",
  nct:"NCT06081894",protocol:"CY 6033",euct:"2023-505797-15-00",
  docKey:item.key,sourceSha256:sha,originalPdfBytes:bytes.length,
  structuralPdfObjectsFound:objects.length,
  structuralPageDictionariesFound:structuralPageCount,
  largestPageTreeCountHint:pageTreeCountHint,
  objectStreamContainersFound:objectStreams,
  pageCountStructurallyConsistent:reliableCount,
  samplePageObjectReferences:pages.slice(0,8),
  allPagesTextDecoded:false,
  pageLevelEndpointEvidenceExtracted:false,
  pageCitationsScientificallyValidated:false,
  signedFinalSAPAuthenticated:false,
  independentScientificReviewSigned:false,
  FDAForecast:"ABSTAIN",
  caution:"PDF structural page dictionaries do not prove visible page content or text. Encoded or compressed object streams can make this census incomplete. No clinical endpoint or SAP chronology is certified."
 },{headers:HEADERS});
}
