/** MAIN R87 — bounded SHA256 receipt for original publicly hosted PDF bytes.
 * The current registry lists documents; CDN URLs are derived using the observed
 * canonical ClinicalTrials.gov public CDN layout, not a documented v2 API URL
 * field. Never use digest receipt as proof of prospective signing, SAP lock or
 * independent clinical review. No storage or source-of-truth mutation.
 */
import {createHash} from "node:crypto";
import type {inspectR86CurrentStudy} from "./focus-r86-original-document-inventory";

type Inspection=NonNullable<ReturnType<typeof inspectR86CurrentStudy>>;
const NCT=/^NCT\d{8}$/u;
const NAME=/^[A-Za-z0-9][A-Za-z0-9_.() -]{0,129}\.pdf$/u;
export const R87_MAX_SOURCE_PDF_BYTES=15_000_000;
export const R87_SOURCE_CAVEAT=
 "Public CDN byte receipt, not an independently authenticated signed original, approval of statistical methods, proof of pre-unblinding SAP finalization, database-lock timeline, scientific assessment, or FDA forecast.";

export function selectR87PublicSourcePdf(
 nct:string,filename:string,inventory:Inspection|null
){
 if(!NCT.test(nct)||!NAME.test(filename)||filename.includes("..")||
    !inventory||inventory.nct!==nct||
    inventory.prospectivelyLockedSapAuthenticated!==false||
    inventory.qualifiedIndependentScientificReview!==false||
    inventory.independentFDAForecast!=="ABSTAIN")return null;
 const matches=inventory.documents.filter(d=>d.filename===filename);
 if(matches.length!==1)return null;
 const doc=matches[0];
 if(!doc.listsProtocol&&!doc.listsSap)return null;
 if(!Number.isSafeInteger(doc.sizeBytes)||doc.sizeBytes<6||
    doc.sizeBytes>R87_MAX_SOURCE_PDF_BYTES)return null;
 return {
  nct,filename,registryDocumentDate:doc.documentDate,
  registryUploadDate:doc.uploadDate,
  registryReportedSize:doc.sizeBytes,
  documentLabels:{protocol:doc.listsProtocol,sap:doc.listsSap},
  sourceStudyUrl:"https://clinicaltrials.gov/study/"+nct,
  // Official hosted CDN path observed in real public studies; not an API field.
  publicCdnUrl:"https://cdn.clinicaltrials.gov/large-docs/"+
    nct.slice(-2)+"/"+nct+"/"+encodeURIComponent(filename),
  originalClinicalSourceAuthenticated:false as const,
  independentHumanReviewSigned:false as const,
  FDAForecast:"ABSTAIN" as const
 };
}
export function digestR87PublicPdf(
 selection:NonNullable<ReturnType<typeof selectR87PublicSourcePdf>>,
 bytes:Uint8Array
){
 if(bytes.byteLength!==selection.registryReportedSize||
    bytes.byteLength<6||bytes.byteLength>R87_MAX_SOURCE_PDF_BYTES||
    bytes[0]!==37||bytes[1]!==80||bytes[2]!==68||
    bytes[3]!==70||bytes[4]!==45)return null;
 const sha256=createHash("sha256").update(bytes).digest("hex");
 return {
  schema:"MAIN_R87_PUBLIC_CDN_PDF_BYTE_RECEIPT_NOT_SIGNED_SOURCE" as const,
  nct:selection.nct,filename:selection.filename,
  sourceStudyUrl:selection.sourceStudyUrl,
  sourcePdfUrl:selection.publicCdnUrl,
  observedRegistryDocDate:selection.registryDocumentDate,
  observedRegistryUploadDate:selection.registryUploadDate,
  pdfByteLength:bytes.byteLength,
  registryReportedSize:selection.registryReportedSize,
  sha256,
  publiclyHostedPdfBytesRead:true as const,
  originalSignedSapChronologyVerified:false as const,
  originalClinicalSourceAuthenticated:false as const,
  independentHumanReviewSigned:false as const,
  FDAForecast:"ABSTAIN" as const,
  note:R87_SOURCE_CAVEAT
 };
}
