/** MAIN R98 original public PDF source-byte receipts. This does not
 * represent durable storage, detailed page inspection, signed SAP custody
 * or independent scientific/regulatory approval.
 */
import raw from "../data/focus-r98-ctis-original-pdf-byte-receipts-20261110.json";
import {R95_EU_ACACIA_PROTOCOL_IDENTITY} from "./focus-r95-eu-protocol-identity-gates";
type Source=typeof raw;
const expected=[
 {key:"am4-protocol",title:"D1_2023-505797-15-00_Protocol_FP",
  uuid:"86e41e1d-b209-4209-bc83-b7e6ff3fcc69",version:"AM4",sys:"6",
  bytes:701086,sha:"853ffd80a547df8a7b813b8985c7116dd6168a640f18521f61b95cf33a8ca5f8"},
 {key:"am4-protocol-greek",title:"D1_2023-505797-15-00_Protocol_el_FP",
  uuid:"effcac6a-5d31-4c95-9dbe-ed53df3a7fb8",version:"AM4",sys:"6",
  bytes:844512,sha:"1a6dc865104d89eb7643a6925074bb9c2df3a4dde92a892c0c6326c67a2c56e1"},
 {key:"am3-synopsis",title:"D1_2023-505797-15-00_Synopsis_EN_FP",
  uuid:"bb5e0594-beed-427b-863a-5e27879c731a",version:"AM3",sys:"5",
  bytes:112911,sha:"dbee10fa3570e6d27b04d88b4e6e498c0109f6bc10cebf1152d88e08369b67b8"},
 {key:"protocol-addendum-a",title:"D1_2023-505797-15-00_Protocol_add_A_FP",
  uuid:"777cdccb-1719-4488-8fde-67dcc03ad9d6",version:"A",sys:"1",
  bytes:71047,sha:"fa9def5b03df82e1d45671f5c1adabc8bb696948b5180d9d76cbd943dc392958"}
] as const;
export function buildR98AcaciaOriginalPdfReceipts(data:Source=raw){
 const earlier=R95_EU_ACACIA_PROTOCOL_IDENTITY;
 if(!earlier||earlier.exactNct!=="NCT06081894"||
  earlier.sponsorProtocolCode!=="CY 6033"||
  earlier.euTrialNumber!=="2023-505797-15-00"||
  earlier.originalAcaciaGatesUnresolved!==4||
  earlier.originalLaunchGatesUnresolved!==7||
  earlier.signedFinalSapVersionsVerified!==0||
  earlier.FDAForecast!=="ABSTAIN"||
  data.schema!=="MAIN_R98_ACACIA_EU_CTIS_FOUR_ORIGINAL_PUBLIC_PDF_BYTE_READBACKS_NOT_SIGNED_SAP"||
  data.dated!=="2026-11-10"||
  data.nct!=="NCT06081894"||
  data.originalEUCT!=="2023-505797-15-00"||
  data.sponsorProtocol!=="CY 6033"||
  data.originalCTISManifestSha256!=="c505e44f2eb556044ecbeaa9692b374b9704779671cd85537cb9cab42f996255"||
  data.originalReadbacksSucceeded!==4||
  data.originalPublicPdfFileBytesRetrievedInPreview!==1729556||
  data.exactDocuments.length!==4||
  data.sourceBytesPersistedInRepository!==false||
  data.sourcePdfTextExtractedAndReviewed!==false||
  data.trueSignatureOfFinalSAPAuthenticated!==false||
  data.qualifiedScienceReviewsSigned!==0||
  data.validatedFDAForecasts!==0||data.FDAForecast!=="ABSTAIN")return null;
 for(let i=0;i<expected.length;i++){
  const x=data.exactDocuments[i],e=expected[i];
  if(x.key!==e.key||x.title!==e.title||x.ctisUUID!==e.uuid||
   x.manualVersion!==e.version||x.systemVersion!==e.sys||
   x.originalPdfBytes!==e.bytes||x.originalPdfSha256!==e.sha||
   !/^[a-f0-9]{64}$/u.test(x.originalPdfSha256)||
   x.originalDocumentUrl!=="https://euclinicaltrials.eu/ctis-public-api/documents/2023-505797-15-00/"+e.uuid+"/download"||
   x.CTISPublicStorageProvenance!=="CTIS_SIGNED_PUBLIC_DOC_STORAGE"||
   x.verifiedPdfHeader!==true||x.verifiedPdfEofMarker!==true||
   x.archiveStatus!=="SOURCE_VERIFIED_RAW_BYTES_READABLE_BUT_NOT_PERSISTENTLY_ARCHIVED"||
   x.originalPdfPageTextInspected!==false||
   x.documentSignatureCryptographicallyAuthenticated!==false||
   x.preUnblindingAuthorizationVerified!==false)return null;
 }
 return {
  schema:"MAIN_R98_FOUR_ACACIA_ORIGINAL_CTIS_PUBLIC_PDF_RECEIPTS_RETRIEVED_NOT_SIGNED" as const,
  retrievalDate:data.dated,
  nct:data.nct,euct:data.originalEUCT,protocol:data.sponsorProtocol,
  originalPdfFilesAvailable:4 as const,
  originalTotalBytesSourceVerified:1729556 as const,
  originalPdfFilesPermanentlyArchived:0 as const,
  originalDocumentsScientificallyPageReviewed:0 as const,
  finalProspectiveSapSignaturesAuthenticated:0 as const,
  independentScienceSignoffs:0 as const,
  ACACIAOriginalGatesUnresolved:4 as const,
  launchOriginalGatesUnresolved:7 as const,
  FDAForecast:"ABSTAIN" as const,
  originalDocuments:data.exactDocuments.map(x=>({
   key:x.key,title:x.title,manualVersion:x.manualVersion,
   byteCount:x.originalPdfBytes,sha256:x.originalPdfSha256,
   originalSourceUrl:x.originalDocumentUrl,
   sourceStatus:x.archiveStatus,
   originalTextReviewed:false as const,
   independentSignedApproval:false as const
  }))
 };
}
export const R98_ACACIA_CTIS_ORIGINAL_PDF_RECEIPTS=buildR98AcaciaOriginalPdfReceipts();
