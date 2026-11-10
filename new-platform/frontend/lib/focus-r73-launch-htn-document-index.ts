/** R73: seven publication-listed PDF source leads, not authenticated original bytes.
 * Never promote source links into signed statistical methods or FDA forecasts.
 */
import raw from "../data/focus-r73-launch-htn-original-document-index.json";
import {FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE} from "./focus-r71-pivotal-evidence-intake";

const prefix="https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/";
const roles=[
 "METHODS_SUPPLEMENT","PROTOCOL_VERSION","PROTOCOL_VERSION","PROTOCOL_VERSION",
 "SAP_ADDENDUM","SAP_AMENDMENT","SAP_ADDENDUM"
] as const;
const titles=[
 "Published Supplement 1: eMethods, multiplicity figure, sensitivity and adverse-event tables",
 "Trial protocol version 3.1","Trial protocol version 3.0","Trial protocol version 2.1",
 "Statistical analysis plan, windowing addendum 1",
 "Statistical analysis plan, amendment 2",
 "Statistical analysis plan, multiple-imputation addendum 1"
] as const;

export function buildR73LaunchHtnDocumentIndex(input:unknown=raw){
 const upstream=FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE;
 if(!upstream||upstream.focusNcts!==29||upstream.applicationCycles!==23||
   upstream.scientificallyValidatedFutureFDAForecasts!==0||
   upstream.fiveRecords.find(x=>x.nct==="NCT06153693")?.futureFDAOutcome!=="ABSTAIN"||
   !input||typeof input!=="object"||Array.isArray(input))return null;
 const d=input as typeof raw;
 if(d.schema!=="MAIN_R73_LAUNCH_HTN_PUBLISHED_PROTOCOL_SAP_DOCUMENT_INDEX_NOT_LOCK_AUTHENTICATION"||
    d.asOf!=="2026-11-09"||d.nct!=="NCT06153693"||d.ticker!=="MLYS"||
    d.pmid!=="40587141"||d.doi!=="10.1001/jama.2025.9413"||
    d.originalPublicArticleIndex!=="https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/"||
    d.sourceDocumentBytesStored!==false||d.sourceDocumentHashesVerified!==0||
    d.originalPreunblindingSignaturesVerified!==0||d.earliestPublicReleaseDatesVerified!==0||
    d.originalLockChronologiesVerified!==0||d.originalFullPdfScientificReviewsSigned!==0||
    d.validatedFDAApplicationForecasts!==0||d.officialFutureFDAOutcome!=="ABSTAIN"||
    d.forecastTiming!=="UNKNOWN"||d.clinicalGrade!==null||
    d.trainingOrProductionWrites!==false||d.documents.length!==7||
    d.checksRemaining.length!==6)return null;
 for(let i=0;i<7;i++){
  const doc=d.documents[i],file=`jama-e259413-s${String(i+1).padStart(3,"0")}.pdf`;
  if(doc.supplementNumber!==i+1||doc.role!==roles[i]||doc.title!==titles[i]||
    doc.filename!==file||doc.publicOriginalIndexLink!==prefix+file||
    doc.originalPdfBytesIndependentVerification!==false||doc.sha256!==null||
    doc.documentInternalVersionDate!==null||doc.firstPublicAvailabilityDate!==null||
    doc.prospectivelySignedAndLockedBeforeUnblinding!==false||
    doc.independentMethodAdjudicationStatus!=="PENDING_ORIGINAL_VERSION_REVIEW")return null;
 }
 return {...d,indexedDocumentCount:7,protocolVersions:3,sapDocuments:3,
   independentlyAuthenticatedOriginalPdfBytes:0,
   independentlySignedSAPs:0,releaseOfClinicalGrades:false as const,
   officialFutureFDAOutcome:"ABSTAIN" as const};
}
export const FOCUS_R73_LAUNCH_HTN_DOCUMENT_INDEX=buildR73LaunchHtnDocumentIndex();
