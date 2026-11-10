import {createHash} from "node:crypto";
import {inflateSync} from "node:zlib";
import {GET as originalPdf} from "../ctis-pdf-check/route";
import {R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS} from "../../../../../lib/focus-r98-ctis-original-pdf-receipts";
/** MAIN R104: conservative, page-linked PDF content-stream inspection.
 * This is NOT a full PDF parser: compressed object streams, font glyph maps,
 * inherited resources, XObjects, and nonliteral TJ text may be missed.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const H={"Cache-Control":"private, no-store","X-Content-Type-Options":"nosniff"} as const;
const TERMS=["kccq","peak vo2","primary endpoint","statistical analysis plan",
 "multiplicity","randomization","blinding","unblinding","heart failure",
 "safety","adverse event","analysis population","missing data"];
function fail(error:string,status=502){
 return Response.json({error,scientificPageCitationsCertified:false,
  signedProspectiveSAPAuthenticated:false,FDAForecast:"ABSTAIN"},{status,headers:H});
}
function decodeLiteral(v:string):string{
 return v.replace(/\\([nrtbf()\\])/g,(_,x:string)=>
  ({n:" ",r:" ",t:" ",b:" ",f:" ","(":"(",")":")","\\":"\\"} as Record<string,string>)[x]??x)
  .replace(/\\([0-7]{1,3})/g,(_,x:string)=>String.fromCharCode(parseInt(x,8)));
}
function stringsFromOperators(data:string):string[]{
 const result:string[]=[];
 for(const block of (data.match(/BT\b[\s\S]*?\bET\b/g)??[]).slice(0,3000)){
  const literal=/\(((?:\\.|[^\\)]){1,2000})\)/g;
  let m:RegExpExecArray|null;
  while((m=literal.exec(block))!==null&&result.length<5000){
   const text=decodeLiteral(m[1]).replace(/[\x00-\x1f]/g," ").trim();
   if(/[A-Za-z]{3}/.test(text))result.push(text.slice(0,300));
  }
 }
 return result;
}
export async function GET(req:Request):Promise<Response>{
 const key=new URL(req.url).searchParams.get("doc");
 const source=R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS;
 const item=source?.originalDocuments.find(x=>x.key===key);
 if(!item||source?.FDAForecast!=="ABSTAIN")return fail("DOCUMENT_NOT_ALLOWLISTED",404);
 const url=new URL(req.url);
 url.pathname="/predictions/scientific-reconciliation/priority-gates/ctis-pdf-check";
 url.search="?doc="+encodeURIComponent(item.key)+"&download=1";
 const res=await originalPdf(new Request(url.toString()));
 if(!res.ok)return fail("SOURCE_PDF_NOT_VERIFIED_"+res.status);
 const bytes=Buffer.from(await res.arrayBuffer());
 const sha=createHash("sha256").update(bytes).digest("hex");
 if(sha!==item.sha256||bytes.length!==item.byteCount)return fail("SOURCE_PDF_MISMATCH",409);
 const raw=bytes.toString("latin1");
 const objectMap=new Map<string,string>();
 for(const m of raw.matchAll(/(?:^|\r?\n)(\d{1,9})\s+(\d{1,5})\s+obj\b([\s\S]*?)\bendobj\b/g)){
  objectMap.set(m[1]+" "+m[2]+" R",m[3].slice(0,1000000));
  if(objectMap.size>6000)break;
 }
 const pageTreeNodeCount=[...objectMap.values()].filter(body=>/\/Type\s*\/Pages\b/.test(body)).length;
 const pageTreeNodeRefs=[...objectMap.entries()].filter(([,body])=>/\/Type\s*\/Pages\b/.test(body)).map(([id])=>id);
 const pageTreeNodesWithKids=pageTreeNodeRefs.filter(id=>/\/Kids\s*\[/.test(objectMap.get(id)??"")).length;
 const pageTreeNodesWithUnresolvedKids=pageTreeNodeRefs.filter(id=>{
  const body=objectMap.get(id)??"";
  const kids=body.match(/\/Kids\s*\[([\s\S]{0,10000}?)\]/)?.[1];
  if(!kids)return true;
  return (kids.match(/\d+\s+\d+\s+R/g)??[]).some(ref=>!objectMap.has(ref));
 }).length;
 const pageTreeDirectKidRefs=pageTreeNodeRefs.flatMap(id=>{
  const kids=(objectMap.get(id)??"").match(/\/Kids\s*\[([\s\S]{0,10000}?)\]/)?.[1]??"";
  return (kids.match(/\d+\s+\d+\s+R/g)??[]).slice(0,500);
 });
 const pageTreeDirectKidsDetected=pageTreeDirectKidRefs.length;
 const pageTreeDirectKidsMatchingPageDictionaries=pageTreeDirectKidRefs.filter(id=>/\/Type\s*\/Page\b(?!s)/.test(objectMap.get(id)??"")).length;
 const pageTreeDirectKidsMatchingNestedPageNodes=pageTreeDirectKidRefs.filter(id=>/\/Type\s*\/Pages\b/.test(objectMap.get(id)??"")).length;
 const directLeafPageOrder=pageTreeNodeRefs.length===1&&pageTreeDirectKidRefs.length>0&&
  pageTreeNodesWithUnresolvedKids===0&&
  pageTreeDirectKidRefs.every(id=>/\/Type\s*\/Page\b(?!s)/.test(objectMap.get(id)??""))&&
  new Set(pageTreeDirectKidRefs).size===pageTreeDirectKidRefs.length
  ?pageTreeDirectKidRefs:[];
 // R119: bounded, fail-closed traversal of visible /Pages -> /Kids references only.
 const nestedPageTreeOrder:string[]=[];
 let nestedPageTreeTraversalError:string|null=null;
 const rootCandidates=pageTreeNodeRefs.filter(id=>!pageTreeNodeRefs.some(parent=>{
  if(parent===id)return false;
  const kids=(objectMap.get(parent)??"").match(/\\/Kids\\s*\\[([\\s\\S]{0,10000}?)\\]/)?.[1]??"";
  return (kids.match(/\\d+\\s+\\d+\\s+R/g)??[]).includes(id);
 }));
 if(rootCandidates.length===1){
  const seen=new Set<string>();
  const walk=(id:string,depth:number):void=>{
   if(nestedPageTreeTraversalError)return;
   if(depth>16||seen.size>=500||seen.has(id)){
    nestedPageTreeTraversalError="TREE_CYCLE_OR_BOUNDS";return;
   }
   seen.add(id);
   const body=objectMap.get(id);
   if(!body){nestedPageTreeTraversalError="MISSING_TREE_OBJECT";return;}
   if(/\\/Type\\s*\\/Page\\b(?!s)/.test(body)){
    nestedPageTreeOrder.push(id);return;
   }
   if(!/\\/Type\\s*\\/Pages\\b/.test(body)){
    nestedPageTreeTraversalError="UNSUPPORTED_TREE_OBJECT";return;
   }
   const kids=body.match(/\\/Kids\\s*\\[([\\s\\S]{0,10000}?)\\]/)?.[1];
   if(!kids){nestedPageTreeTraversalError="KIDS_NOT_DIRECT_ARRAY";return;}
   const refs=kids.match(/\\d+\\s+\\d+\\s+R/g)??[];
   if(refs.length===0||refs.length>500){nestedPageTreeTraversalError="KIDS_EMPTY_OR_TOO_LARGE";return;}
   for(const child of refs)walk(child,depth+1);
  };
  walk(rootCandidates[0],0);
 }else nestedPageTreeTraversalError="ROOT_NOT_UNIQUELY_DETECTABLE";
 const provisionalNestedPageTreeOrder=nestedPageTreeTraversalError===null?nestedPageTreeOrder:[];
 const pages:Array<{pdfPageDictionaryIndex:number,pageObject:string,
  referencedContentStreams:number,decodedContentStreams:number,
  textFragments:number,termHits:Array<{term:string,fragment:string}>}>=[];
 let unsupportedFilters=0;
 for(const [id,body] of objectMap){
  if(!/\/Type\s*\/Page\b(?!s)/.test(body))continue;
  const contents=body.match(/\/Contents\s*(?:\[([\s\S]{0,10000}?)\]|(\d+\s+\d+\s+R))/);
  const refs=(contents?.[1]??contents?.[2]??"").match(/\d+\s+\d+\s+R/g)??[];
  const fragments:string[]=[];
  let decoded=0;
  for(const ref of refs.slice(0,50)){
   const obj=objectMap.get(ref);
   if(!obj)continue;
   const start=obj.search(/stream\r?\n/);
   if(start<0)continue;
   const at=start+(obj.slice(start).match(/^stream\r?\n/)?.[0].length??7);
   const end=obj.indexOf("endstream",at);
   if(end<0)continue;
   let stream=obj.slice(at,end).replace(/\r?\n$/,"");
   if(/\/Filter\b/.test(obj.slice(0,start))&&!/\/FlateDecode\b/.test(obj.slice(0,start))){
    unsupportedFilters++;continue;
   }
   if(/\/FlateDecode\b/.test(obj.slice(0,start))){
    try{stream=inflateSync(Buffer.from(stream,"latin1"),
     {maxOutputLength:2_000_000}).toString("latin1");}
    catch{continue;}
   }
   decoded++;
   fragments.push(...stringsFromOperators(stream).slice(0,1000));
  }
  const joined=fragments.join(" ").toLowerCase();
  const hits=TERMS.filter(term=>joined.includes(term)).map(term=>{
   const at=joined.indexOf(term);
   return {term,fragment:fragments.join(" ").slice(Math.max(0,at-100),at+160)};
  });
  pages.push({pdfPageDictionaryIndex:pages.length+1,pageObject:id,
   referencedContentStreams:refs.length,decodedContentStreams:decoded,
   textFragments:fragments.length,termHits:hits});
  if(pages.length>=500)break;
 }
 return Response.json({
  schema:"MAIN_R104_PARTIAL_PDF_PAGE_LINKED_TEXT_OPERATORS_NOT_SCIENTIFIC_CITATIONS",
  docKey:item.key,nct:"NCT06081894",protocol:"CY 6033",
  sha256:sha,sourceOriginalPdfBytes:bytes.length,
  detectedPageDictionaries:pages.length,
  detectedUncompressedPageTreeNodes:pageTreeNodeCount,
  detectedPageTreeNodesWithDirectKidsArray:pageTreeNodesWithKids,
  detectedPageTreeNodesWithMissingOrUnresolvedKids:pageTreeNodesWithUnresolvedKids,
  detectedDirectPageTreeKids:pageTreeDirectKidsDetected,
  detectedDirectKidsMatchingPageDictionaries:pageTreeDirectKidsMatchingPageDictionaries,
  detectedDirectKidsMatchingNestedPageNodes:pageTreeDirectKidsMatchingNestedPageNodes,
  provisionalNestedPageTreeOrder,
  provisionalNestedPageTreeTraversalError:nestedPageTreeTraversalError,
  provisionalNestedPageTreeOrderNotScientificallyCertified:true,
  provisionalDirectLeafKidsInArrayOrder:directLeafPageOrder,
  provisionalDirectLeafOrderToObjectScanIndex:directLeafPageOrder.map((ref,index)=>({
   provisionalPageTreePosition:index+1,
   pageObject:ref,
   pdfPageDictionaryObjectScanIndex:pages.find(p=>p.pageObject===ref)?.pdfPageDictionaryIndex??null
  })),
  provisionalDirectLeafKidsOrderNotScientificallyCertified:true,
  verifiedPageTreeTraversalPerformed:false,
  pagesWithTextFragments:pages.filter(p=>p.textFragments>0).length,
  unsupportedFilters,
  pages:pages.map(p=>({...p,termHits:p.termHits.slice(0,13)})),
  pdfPageDictionaryIndexIsNotCertifiedPrintedPageNumber:true,
  pageDictionaryIndexIsObjectScanOrderNotVerifiedPageTreeOrder:true,
  completePageTextExtraction:false,
  sourcePageCitationsScientificallyCertified:false,
  signedProspectiveSAPAuthenticated:false,
  independentScientificReviewSigned:false,
  FDAForecast:"ABSTAIN",
  limitations:"Page-tree node count is an uncompressed-object structural diagnostic, not a traversed or certified page tree. Page dictionary indices reflect object scan order, NOT verified PDF page-tree order or viewer page numbers. Uncompressed page dictionaries and directly referenced content streams only. Compressed object streams, font ToUnicode mappings, embedded text and inherited page content may be missing. Diagnostic snippets are not verified endpoint or SAP evidence."
 },{headers:H});
}
