/**
 * MAIN ACACIA original evidence intake *precheck*, not document ingestion.
 * No source fetch, byte upload, database write, reviewer signoff or grade.
 * A supplied SHA-256 is a CLAIM until original file bytes are independently checked.
 */
import type {AcquisitionPacket,AcquisitionRequest} from "./acacia-evidence-acquisition-handoff";

export type IntakeDraft={
  nct:string;requestId:string;documentType:string;documentTitle:string;
  documentVersion:string;documentDate:string;sourceUrl:string;
  claimedSha256:string;
};
export type IntakeIssue=
  "WRONG_TRIAL"|"UNKNOWN_REQUEST"|"WRONG_DOCUMENT_TYPE"|"INVALID_DOCUMENT_TITLE"|
  "INVALID_VERSION"|"INVALID_DOCUMENT_DATE"|"UNSUPPORTED_OR_UNSAFE_SOURCE_URL"|
  "MISSING_OR_INVALID_CLAIMED_SHA256"|"UNEXPECTED_FIELDS";
export type IntakePrecheck={
  schema:"MAIN_ACACIA_EVIDENCE_INTAKE_PRECHECK_V1";
  nct:"NCT06081894";requestId:string;
  inputCheck:"METADATA_FORMAT_CHECKED_ONLY"|"REJECTED_METADATA";
  issueCodes:IntakeIssue[];
  expectedDocumentType:string|null;linkedMethodPositions:string[];
  sourceUrlHostAllowlisted:boolean;sourceContentRetrieved:false;
  claimedDocumentHashVerifiedFromOriginalBytes:false;
  documentVersionAuthenticated:false;
  sourceOwnershipIndependentlyVerified:false;
  sponsorDataSharingAuthorizationVerified:false;
  clinicalReviewerSignedOff:false;
  acceptedForClinicalScoring:false;
  clinicalGrade:null;
  gradeEventsWritten:0;
  persisted:false;
  uploadsReceived:0;
  emailSent:false;
  reviewerActionRequired:string[];
  nextStage:"NEEDS_ORIGINAL_BYTES_PROVENANCE_AND_INDEPENDENT_REVIEW";
  fdaPrediction:"ABSTAIN";accuracy:"NOT_CALIBRATED";
};
const categories:Readonly<Record<string,string>>={
  LOCKED_PRIMARY_SAP:"STATISTICAL_ANALYSIS_PLAN",
  PRIMARY_SENSITIVITY_AND_MISSINGNESS:"PRIMARY_ANALYSIS_TABLES",
  HF_SAE_EVENT_DEFINITION:"HF_ADVERSE_EVENT_TABLE",
  SAFETY_DENOMINATORS_EXPOSURE:"SAFETY_DENOMINATOR_TABLE",
  CONSORT_AND_PROTOCOL_VERSIONS:"PROTOCOL_CONSORT",
  EXACT_NHCM_REGULATORY_STATUS:"REGULATORY_SOURCE"
};
const allowedHosts=new Set([
  "clinicaltrials.gov","ctis.europa.eu","euclinicaltrials.eu",
  "www.nejm.org","nejm.org","pubmed.ncbi.nlm.nih.gov","pmc.ncbi.nlm.nih.gov",
  "www.ebi.ac.uk","www.sec.gov","www.fda.gov","www.accessdata.fda.gov",
  "accessdata.fda.gov","ir.cytokinetics.com","cytokinetics.com",
  "www.cytokinetics.com","github.com"
]);
function allowedPublicSource(value:unknown):boolean{
  if(typeof value!=="string"||value.length<14||value.length>320||
     /[\u0000-\u0020\u007f]/.test(value))return false;
  try{
    const u=new URL(value);
    return u.protocol==="https:" && !u.username && !u.password &&
      u.port==="" && u.search==="" && u.hash==="" &&
      allowedHosts.has(u.hostname) && u.pathname.startsWith("/") &&
      u.pathname.length>1 && !u.pathname.includes("\\") &&
      !/%2f|%5c|%00/i.test(u.pathname);
  }catch{return false;}
}
const validDate=(value:unknown):boolean=>{
  if(typeof value!=="string"||!/^(19|20)\d{2}-\d{2}-\d{2}$/.test(value))return false;
  const d=new Date(value+"T00:00:00Z");
  return !Number.isNaN(d.valueOf())&&d.toISOString().slice(0,10)===value;
};
const keys=new Set(["nct","requestId","documentType","documentTitle",
  "documentVersion","documentDate","sourceUrl","claimedSha256"]);
const sortedUnique=(x:IntakeIssue[])=>[...new Set(x)];
/** Does NOT confirm an actual document exists. It checks metadata format and
 * exact acquisition-request mapping, returning permanent review blockers.
 */
export function validateAcaciaIntakeCandidate(
  raw:unknown,packet:AcquisitionPacket|null
):IntakePrecheck|null{
  if(!packet||packet.schema!=="MAIN_ACACIA_EVIDENCE_ACQUISITION_HANDOFF_V1"||
     packet.nct!=="NCT06081894"||packet.requestDeliveryStatus!=="DRAFT_ONLY_NOT_SENT"||
     packet.requestCount!==6||packet.mappedMethodPositionsCovered!==18||
     packet.approvedClinicalGrades!==0||packet.independentPhaseSignoffs!==0||
     packet.externallyAuthenticatedNewDocuments!==0||
     packet.fdaPrediction!=="ABSTAIN"||packet.accuracy!=="NOT_CALIBRATED"||
     !Array.isArray(packet.requests)||packet.requests.length!==6||
     packet.requests.some(x=>x.acquisitionState!=="DRAFT_NOT_SENT"||
       x.independentReviewerSigned!==false||x.officialClinicalGrade!==null))
    return null;
  if(!raw||typeof raw!=="object"||Array.isArray(raw))return null;
  const input=raw as Record<string,unknown>;
  const issues:IntakeIssue[]=[];
  if(Object.keys(input).some(k=>!keys.has(k))||
     Object.keys(input).length!==keys.size||
     Object.keys(input).some(k=>typeof input[k]!=="string"))
    issues.push("UNEXPECTED_FIELDS");
  if(input.nct!=="NCT06081894")issues.push("WRONG_TRIAL");
  const found:AcquisitionRequest|undefined=packet.requests.find(
    x=>x.requestId===input.requestId
  );
  const requestId=found?.requestId??"UNIDENTIFIED";
  if(!found||typeof input.requestId!=="string"||
    !Object.hasOwn(categories,input.requestId))issues.push("UNKNOWN_REQUEST");
  const expected=found?categories[found.requestId]:null;
  if(input.documentType!==expected||!expected)issues.push("WRONG_DOCUMENT_TYPE");
  if(typeof input.documentTitle!=="string"||input.documentTitle.length<8||
     input.documentTitle.length>160||
     !/^[a-zA-Z0-9][a-zA-Z0-9 .,():_+\-/–—]*$/.test(input.documentTitle))
    issues.push("INVALID_DOCUMENT_TITLE");
  if(typeof input.documentVersion!=="string"||
     input.documentVersion.length<1||input.documentVersion.length>48||
     !/^[a-zA-Z0-9][a-zA-Z0-9._ \-/]*$/.test(input.documentVersion))
    issues.push("INVALID_VERSION");
  if(!validDate(input.documentDate))issues.push("INVALID_DOCUMENT_DATE");
  const publicSource=allowedPublicSource(input.sourceUrl);
  if(!publicSource)issues.push("UNSUPPORTED_OR_UNSAFE_SOURCE_URL");
  if(typeof input.claimedSha256!=="string"||
    !/^[a-f0-9]{64}$/.test(input.claimedSha256))
    issues.push("MISSING_OR_INVALID_CLAIMED_SHA256");
  const unique=sortedUnique(issues);
  return {
    schema:"MAIN_ACACIA_EVIDENCE_INTAKE_PRECHECK_V1",
    nct:"NCT06081894",requestId,inputCheck:unique.length===0?
      "METADATA_FORMAT_CHECKED_ONLY":"REJECTED_METADATA",
    issueCodes:unique,expectedDocumentType:expected,
    linkedMethodPositions:found?[...found.mappedMethodPositions]:[],
    sourceUrlHostAllowlisted:publicSource,
    sourceContentRetrieved:false,
    claimedDocumentHashVerifiedFromOriginalBytes:false,
    documentVersionAuthenticated:false,
    sourceOwnershipIndependentlyVerified:false,
    sponsorDataSharingAuthorizationVerified:false,
    clinicalReviewerSignedOff:false,
    acceptedForClinicalScoring:false,
    clinicalGrade:null,gradeEventsWritten:0,persisted:false,uploadsReceived:0,emailSent:false,
    reviewerActionRequired:[
      "Obtain original complete source bytes through authorized means and recompute SHA-256 independently.",
      "Verify exact NCT06081894, indication, protocol CY 6033, source issuer, version, effective date and original document provenance.",
      "Confirm public distribution rights or sponsor eligibility, access approval and relevant data-sharing agreement.",
      "Reconcile method-specific primary statistical analysis, population, event definitions and missing evidence against the source-locked rubric.",
      "Obtain qualified independent reviewer signoff in a separate authorized append-only clinical ledger; do not infer a grade or FDA probability from metadata."
    ],
    nextStage:"NEEDS_ORIGINAL_BYTES_PROVENANCE_AND_INDEPENDENT_REVIEW",
    fdaPrediction:"ABSTAIN",accuracy:"NOT_CALIBRATED"
  };
}
export function intakeDocumentTypes():Array<{requestId:string;documentType:string}>{
  return Object.entries(categories).map(([requestId,documentType])=>({requestId,documentType}));
}
