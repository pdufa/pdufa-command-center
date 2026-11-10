import {inflateSync} from "node:zlib";
import {createHash} from "node:crypto";
import {GET as originalPdf} from "../ctis-pdf-check/route";
import {R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS} from "../../../../../lib/focus-r98-ctis-original-pdf-receipts";
/** MAIN R100: bounded diagnostic index of original source PDF text operators.
 * Not full text extraction, not page citations, and never a signed SAP audit.
 * Only R99 hash-checked, exact-allowlisted CTIS public original PDFs.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const MAX_STREAMS=3000,MAX_DECOMPRESSED=20_000_000;
const TERMS=["statistical analysis plan","primary endpoint","secondary endpoint",
 "kccq","peak vo2","multiplicity","alpha","randomization","blinding",
 "unblinding","analysis population","heart failure","adverse event",
 "intercurrent","missing data","version","amendment"];
const HEADERS={"Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"} as const;
function fail(error:string,status=502){
 return Response.json({error,originalDocumentTextScientificallyReviewed:false,
  finalSignedProspectiveSAPAuthenticated:false,FDAForecast:"ABSTAIN"},
  {status,headers:HEADERS});
}
function decodePdfLiteral(value:string):string{
 return value.replace(/\\([nrtbf()\\])/g,(_,v:string)=>({
  n:"\n",r:"\r",t:"\t",b:" ",f:" ","(":"(",")":")","\\":"\\"
 } as Record<string,string>)[v]??v)
 .replace(/\\([0-7]{1,3})/g,(_,v:string)=>
  String.fromCharCode(parseInt(v,8)))
 .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g," ");
}
function operatorsFromText(content:string):string[]{
 const found:string[]=[];
 // This intentionally ignores page maps, fonts, glyph mapping and graphics.
 // It can miss most or all original text; do not use for scientific decisions.
 const blocks=content.match(/BT\b[\s\S]*?\bET\b/g)??[];
 for(const block of blocks.slice(0,3000)){
  const pieces:string[]=[];
  const pattern=/\(((?:\\.|[^\\)]){1,2000})\)\s*(?:Tj|'|")|<([0-9a-fA-F]{2,4000})>\s*Tj/g;
  let m:RegExpExecArray|null;
  while((m=pattern.exec(block))!==null&&pieces.length<200){
   if(m[1])pieces.push(decodePdfLiteral(m[1]));
   else if(m[2]){
    const decoded=Buffer.from(m[2],"hex");
    const str=decoded.toString("latin1");
    if(/[a-zA-Z]{3}/.test(str))pieces.push(str);
   }
  }
  if(pieces.length)found.push(pieces.join(" "));
 }
 return found;
}
export async function GET(req:Request):Promise<Response>{
 const key=new URL(req.url).searchParams.get("doc");
 const evidence=R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS;
 const item=evidence?.originalDocuments.find(x=>x.key===key);
 if(!item||evidence?.FDAForecast!=="ABSTAIN")return fail("ORIGINAL_CTIS_DOCUMENT_NOT_ALLOWLISTED",404);
 const url=new URL(req.url);
 url.pathname="/predictions/scientific-reconciliation/priority-gates/ctis-pdf-check";
 url.search="?doc="+encodeURIComponent(item.key)+"&download=1";
 const source=await originalPdf(new Request(url.toString()));
 if(!source.ok)return fail("ORIGINAL_PDF_NOT_VERIFIED_"+source.status,502);
 const bytes=Buffer.from(await source.arrayBuffer());
 const sha=createHash("sha256").update(bytes).digest("hex");
 if(sha!==item.sha256||bytes.length!==item.byteCount)
  return fail("SOURCE_PDF_SHA256_MISMATCH",409);
 const raw=bytes.toString("latin1");
 const found:string[]=[];
 let attempted=0,inflated=0,failed=0;
 const re=/stream\r?\n/g;
 let match:RegExpExecArray|null;
 while((match=re.exec(raw))!==null&&attempted<MAX_STREAMS){
  const start=re.lastIndex;
  const end=raw.indexOf("endstream",start);
  if(end<0)break;
  attempted++;
  const dict=raw.slice(Math.max(0,match.index-400),match.index);
  let content=raw.slice(start,end).replace(/\r?\n$/,"");
  if(/\/FlateDecode\b/.test(dict)){
   try{
    const data=inflateSync(Buffer.from(content,"latin1"),{
     maxOutputLength:Math.min(MAX_DECOMPRESSED-inflated,5_000_000)
    });
    inflated+=data.length;
    content=data.toString("latin1");
   }catch{failed++;re.lastIndex=end+9;continue;}
  }
  if(inflated>MAX_DECOMPRESSED)break;
  const chunks=operatorsFromText(content);
  for(const chunk of chunks){
   if(found.length>=2000)break;
   if(/[A-Za-z]{3}/.test(chunk))found.push(chunk.slice(0,2000));
  }
  re.lastIndex=end+9;
 }
 const indexed=found.join("\n");
 const matches=TERMS.map(term=>{
  const i=indexed.toLowerCase().indexOf(term);
  return {term,found:i>=0,operatorExcerpt:i>=0?
   indexed.slice(Math.max(0,i-140),Math.min(indexed.length,i+230)):null};
 });
 return Response.json({
  schema:"MAIN_R100_CTIS_PDF_TEXT_OPERATOR_DIAGNOSTIC_UNREVIEWED_NO_PAGE_MAPPING",
  nct:"NCT06081894",protocol:"CY 6033",euct:"2023-505797-15-00",
  document:item.title,version:item.manualVersion,
  sha256:sha,originalPdfBytes:bytes.length,
  originalPdfSourceUrl:item.originalSourceUrl,
  extractionTechnique:"BOUNDED_PDF_TEXT_OPERATORS_WITH_FLATE_ONLY",
  attemptedPdfStreams:attempted,failedFlateStreams:failed,
  extractedTextOperatorChunks:found.length,
  keywordDiagnostics:matches,
  previewOnly:found.slice(0,35),
  scientificPageReferencesCertified:false,
  completePdfTextExtracted:false,
  originalDocumentTextScientificallyReviewed:false,
  controlledSignedFinalSAPAuthenticated:false,
  independentScienceSignoff:false,
  FDAForecast:"ABSTAIN"
 },{headers:HEADERS});
}
