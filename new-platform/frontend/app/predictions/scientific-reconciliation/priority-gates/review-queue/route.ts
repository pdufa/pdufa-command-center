import QUEUE from "../../../../../data/focus-r106-acacia-source-evidence-review-queue-20261110.json";
import READBACK from "../../../../../data/focus-r105-acacia-page-linked-diagnostic-readback-20261110.json";
import {R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS} from "../../../../../lib/focus-r98-ctis-original-pdf-receipts";
export const dynamic="force-dynamic";
const headers={"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"} as const;
/** R108 read-only, machine-readable primary-page review handoff.
 * Fail closed if candidate source hash or protocol identity diverges.
 */
export async function GET(){
 const source=R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS;
 const original=source?.originalDocuments.find(x=>x.key==="am4-protocol");
 const diagnostic=READBACK.documents.find(x=>x.key==="am4-protocol");
 if(!original||!diagnostic||
  QUEUE.nct!=="NCT06081894"||QUEUE.protocol!=="CY 6033"||
  QUEUE.sourceSha256!==original.sha256||
  diagnostic.sha256!==original.sha256||
  JSON.stringify(QUEUE.candidatePageObjectIndices)!==
   JSON.stringify(diagnostic.pageObjectIndices)||
  QUEUE.FDAForecast!=="ABSTAIN"||READBACK.FDAForecast!=="ABSTAIN"||
  QUEUE.openScienceGates!==11||READBACK.openScienceGates!==11)
  return Response.json({error:"REVIEW_QUEUE_PROVENANCE_MISMATCH",
   FDAForecast:"ABSTAIN"},{status:409,headers});
 return Response.json({
  schema:"MAIN_R108_SOURCE_PAGE_REVIEW_HANDOFF_NOT_SCIENTIFIC_SIGNOFF",
  nct:QUEUE.nct,protocol:QUEUE.protocol,euct:QUEUE.euct,
  sourceDocument:QUEUE.sourceDocument,sourceSha256:QUEUE.sourceSha256,
  candidateKeyword:QUEUE.candidateKeyword,
  candidatePageObjectIndices:QUEUE.candidatePageObjectIndices,
  reviewSteps:QUEUE.reviewSteps,
  pageEvidenceDiagnosticUrl:"/predictions/scientific-reconciliation/priority-gates/ctis-page-evidence?doc=am4-protocol",
  originalPdfDownloadUrl:"/predictions/scientific-reconciliation/priority-gates/ctis-pdf-check?doc=am4-protocol&download=1",
  status:"PENDING_PRIMARY_PAGE_REVIEW",
  printedPageNumbersVerified:false,
  completePageTextVerified:false,
  sourcePageCitationsCertified:false,
  originalSignedProspectiveSAPAuthenticated:false,
  independentScienceReviewSigned:false,
  openScienceGates:11,
  FDAForecast:"ABSTAIN",
  caution:"Read-only handoff. Candidate object indices are not verified printed pages or evidence of endpoint efficacy."
 },{headers});
}
