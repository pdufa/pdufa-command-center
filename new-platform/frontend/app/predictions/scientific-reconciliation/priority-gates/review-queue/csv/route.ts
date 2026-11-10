import QUEUE from "../../../../../../data/focus-r106-acacia-source-evidence-review-queue-20261110.json";
import READBACK from "../../../../../../data/focus-r105-acacia-page-linked-diagnostic-readback-20261110.json";
import {R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS} from "../../../../../../lib/focus-r98-ctis-original-pdf-receipts";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"} as const;
/** R109 reviewer worksheet export. Never a scientific evidence signoff. */
export async function GET(){
 const original=R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS?.originalDocuments.find(x=>x.key==="am4-protocol");
 const diagnostic=READBACK.documents.find(x=>x.key==="am4-protocol");
 if(!original||!diagnostic||QUEUE.nct!=="NCT06081894"||QUEUE.protocol!=="CY 6033"||
  QUEUE.sourceSha256!==original.sha256||diagnostic.sha256!==original.sha256||
  JSON.stringify(QUEUE.candidatePageObjectIndices)!==JSON.stringify(diagnostic.pageObjectIndices)||
  QUEUE.FDAForecast!=="ABSTAIN"||READBACK.FDAForecast!=="ABSTAIN"||
  QUEUE.openScienceGates!==11||READBACK.openScienceGates!==11)
  return Response.json({error:"REVIEW_QUEUE_PROVENANCE_MISMATCH",FDAForecast:"ABSTAIN"},{status:409,headers});
 const escape=(v:string|number)=>'"'+String(v).replace(/"/g,'""')+'"';
 const columns=["nct","protocol","document","source_sha256","candidate_keyword","pdf_page_object_index","printed_page_verified","complete_page_text_verified","scientific_citation_certified","review_status","fda_forecast"];
 const rows=QUEUE.candidatePageObjectIndices.map(index=>[
  QUEUE.nct,QUEUE.protocol,QUEUE.sourceDocument,QUEUE.sourceSha256,QUEUE.candidateKeyword,index,
  "false","false","false","PENDING_PRIMARY_PAGE_REVIEW","ABSTAIN"].map(escape).join(","));
 const csv=[columns.join(","),...rows].join("\r\n")+"\r\n";
 return new Response(csv,{headers:{...headers,"Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":"attachment; filename=acacia-hcm-kccq-original-page-review-queue-r109.csv"}});
}
