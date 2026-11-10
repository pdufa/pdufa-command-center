/** MAIN R88 — timeline triage of public ClinicalTrials.gov document metadata.
 * Public document/upload dates, even against actual primary completion, do NOT
 * establish a prospectively signed plan, database lock, first access to the
 * randomization code, an efficacy conclusion or a calibrated FDA forecast.
 */
import raw from "../data/focus-r88-source-chronology-triage-20261110.json";
import receipt from "../data/focus-r87-public-pdf-byte-receipts-20261110.json";
import {R85_PHASE_MANIFEST} from "./focus-r85-registry-phase-crosscheck";

const NCT=/^NCT\d{8}$/u;
const SHA=/^[a-f0-9]{64}$/u;
const DAY=/^\d{4}-\d{2}-\d{2}$/u;
const UPLOAD=/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d$/u;
type Source=typeof raw;
function validDay(s:string):boolean {
 if(!DAY.test(s))return false;
 const d=new Date(s+"T00:00:00Z");
 return !Number.isNaN(d.getTime())&&d.toISOString().slice(0,10)===s;
}
export const R88_EXPLANATION=
 "Public document/upload dates are compared with registry primary completion, NOT actual blind-break or database lock. These differences are questions for the original signed amendment and unblinding chronology, never statistical misconduct findings, signed scientific assessments, or FDA predictions.";

export function buildR88SourceChronology(input:Source|null=raw){
 const phase=R85_PHASE_MANIFEST;
 if(!phase||!input||
    phase.exactTrials!==29||phase.provisionalCycles!==23||
    phase.rows.length!==29||phase.independentlySignedPhaseReviews!==0||
    phase.authenticatedSignedSAPs!==0||phase.validatedFutureFDAPredictions!==0||
    receipt.records.length!==23||receipt.distinctNctsWithFingerprintedPdf!==12||
    receipt.originalSignedProspectiveSAPVersionsAuthenticated!==0||
    receipt.qualifiedIndependentScientificReviews!==0||
    input.schema!=="MAIN_R88_PUBLIC_PROTOCOL_SAP_REGISTRY_CHRONOLOGY_TRIAGE_NOT_SAP_AUTHENTICATION"||
    input.snapshotDateUtc!=="2026-11-10"||input.datePrecision!=="DAY_ONLY"||
    input.sources.archivedTrialPhase!=="new-platform/frontend/data/focus-r67-original-phase-source.json"||
    input.sources.publicPdfByteAudit!=="new-platform/frontend/data/focus-r87-public-pdf-byte-receipts-20261110.json"||
    input.sources.archivedTrialPhaseBlobSha!=="5fb99510f7d71ac4d1cca08b3ca791b882990823"||
    input.sources.publicPdfAuditBlobSha!=="75a04d181b96c968b740e8fe3534d0f9bab347c2"||
    input.normalization.comparisonMilestone!==
      "ARCHIVED_REGISTRY_PRIMARY_COMPLETION_DATE_NOT_UNBLINDING_OR_FINAL_DATABASE_LOCK"||
    input.normalization.oneDocumentCanListBothProtocolAndSap!==true||
    input.files.length!==23||
    input.nctsWithoutCurrentRegistryProtocolSapFiles.length!==17||
    input.clinicalGradesAssigned!==0||input.officialFDAOutcome!=="ABSTAIN"||
    input.noProductionWrites!==true||
    input.counts.qualifiedSignedScientificReviews!==0||
    input.counts.prospectivelyAuthenticatedSignedSAPs!==0||
    input.counts.independentlyValidatedFDAForecasts!==0)return null;

 const byNct=new Map(phase.rows.map(r=>[r.nct,r]));
 const byPdf=new Map(receipt.records.map(r=>[r.nct+"|"+r.filename,r]));
 if(byNct.size!==29||byPdf.size!==23)return null;
 const seenFiles=new Set<string>();
 const byTrial=new Map<string,Array<{
   filename:string;sha256:string;sizeBytes:number;sourcePdfUrl:string;
   documentDate:string;registryUploadDate:string;
   printedDateComparedToCompletion:"AFTER"|"ON_OR_BEFORE";
   uploadComparedToCompletion:"AFTER"|"ON_OR_BEFORE";
   listsProtocol:boolean;listsSAP:boolean;
 }>>();
 let laterDoc=0,laterSap=0,notLaterSap=0,laterUpload=0;
 for(const d of input.files){
  const baseline=byNct.get(d.nct);
  const actual=byPdf.get(d.nct+"|"+d.filename);
  const id=d.nct+"|"+d.filename;
  if(!NCT.test(d.nct)||seenFiles.has(id)||!baseline||!actual||
     !SHA.test(d.observedPdfSha256)||d.observedPdfSha256!==actual.sha256||
     d.observedPdfByteCount!==actual.byteCount||
     d.sourcePdfUrl!==actual.publicSourceUrl||
     d.listsProtocol!==actual.listsProtocol||d.listsSAP!==actual.listsSap||
     (!d.listsSAP&&!d.listsProtocol)||
     !validDay(d.reportedDocumentDate)||!UPLOAD.test(d.registryUploadDate)||
     !validDay(d.registryUploadDate.slice(0,10))||
     !validDay(d.registryPrimaryCompletionDate)||
     d.registryPrimaryCompletionDate!==baseline.primaryCompletionDate||
     d.primaryCompletionDateType!==baseline.primaryCompletionType||
     d.registryReportedStatus.replaceAll("_"," ")!==baseline.registryReportedStatus||
     d.documentDateAfterPrimaryCompletion!==(d.reportedDocumentDate>d.registryPrimaryCompletionDate)||
     d.publicUploadAfterPrimaryCompletion!==(d.registryUploadDate.slice(0,10)>d.registryPrimaryCompletionDate)||
     d.prospectiveSignedSAPVerified!==false||
     d.sourceCustodianSigned!==false||
     d.independentStatisticianApproved!==false||d.observationalOnly!==true)return null;
  seenFiles.add(id);
  if(d.documentDateAfterPrimaryCompletion)laterDoc++;
  if(d.publicUploadAfterPrimaryCompletion)laterUpload++;
  if(d.listsSAP){
   if(d.documentDateAfterPrimaryCompletion)laterSap++;
   else notLaterSap++;
  }
  const rows=byTrial.get(d.nct)??[];
  rows.push({
   filename:d.filename,sha256:d.observedPdfSha256,
   sizeBytes:d.observedPdfByteCount,sourcePdfUrl:d.sourcePdfUrl,
   documentDate:d.reportedDocumentDate,registryUploadDate:d.registryUploadDate,
   printedDateComparedToCompletion:d.documentDateAfterPrimaryCompletion?"AFTER":"ON_OR_BEFORE",
   uploadComparedToCompletion:d.publicUploadAfterPrimaryCompletion?"AFTER":"ON_OR_BEFORE",
   listsProtocol:d.listsProtocol,listsSAP:d.listsSAP
  });
  byTrial.set(d.nct,rows);
 }
 if(seenFiles.size!==23||[...byPdf.keys()].some(id=>!seenFiles.has(id))||
    byTrial.size!==12||laterDoc!==16||laterSap!==11||
    notLaterSap!==1||laterUpload!==23)return null;
 const missing=phase.rows.filter(r=>!byTrial.has(r.nct)).map(r=>r.nct).sort();
 if(missing.length!==17||
    JSON.stringify(missing)!==JSON.stringify([...input.nctsWithoutCurrentRegistryProtocolSapFiles].sort()))return null;
 const counts=input.counts;
 if(counts.exactFocusTrials!==29||counts.provisionalApplicationCycles!==23||
    counts.withCurrentProtocolOrSapFiles!==12||
    counts.withoutCurrentProtocolOrSapFiles!==17||
    counts.pdfDocuments!==23||
    counts.filesWithDocumentDateAfterPrimaryCompletion!==laterDoc||
    counts.sapFilesWithDocumentDateAfterPrimaryCompletion!==laterSap||
    counts.sapFilesWithDocumentDateOnOrBeforePrimaryCompletion!==notLaterSap||
    counts.filesPubliclyUploadedAfterPrimaryCompletion!==laterUpload)return null;

 const rows=phase.rows.map(phaseRow=>{
  const files=[...(byTrial.get(phaseRow.nct)??[])].sort((a,b)=>a.filename.localeCompare(b.filename));
  const saps=files.filter(f=>f.listsSAP);
  const state=files.length===0?"NO_CURRENT_REGISTRY_PROTOCOL_SAP_FILES":
    saps.some(f=>f.printedDateComparedToCompletion==="AFTER")?
      "LISTED_SAP_DATE_AFTER_PRIMARY_COMPLETION_RECONCILE_VERSION":
      "SAP_DATE_NOT_AFTER_PRIMARY_COMPLETION_STILL_REQUIRE_SIGNED_LOCK_PROOF";
  const originalPilot=phaseRow.nct==="NCT06081894"?"ACACIA_HCM":
    phaseRow.nct==="NCT06153693"?"LAUNCH_HTN":null;
  return {
   nct:phaseRow.nct,ticker:phaseRow.ticker,
   cycleIds:[...phaseRow.cycleIds],
   originalPilot,
   archivedPrimaryCompletionDate:phaseRow.primaryCompletionDate,
   archivedPrimaryCompletionType:phaseRow.primaryCompletionType,
   reportedPhase:phaseRow.registryReportedPhase,
   registryStudyUrl:phaseRow.sourceUrl,
   sourcePdfFiles:files,
   sapDateChronologyState:state,
   nextRequiredProof:files.length?
    "Original signed SAP and amendment approvals, first unblinding access, final database lock, analysis-set and patient safety reconciliation":
    "Recover original dated protocols, SAP and other sponsor/journal/CSR/regulator or historical-registry sources; absence here is not clinical failure",
   originallySignedPlanVerified:false as const,
   actualBlindBreakDateIndependentlyVerified:false as const,
   qualifiedClinicalReviewerSignoff:false as const,
   clinicalGrade:null,
   FDAForecast:"ABSTAIN" as const
  };
 });
 rows.sort((a,b)=>{
  const priority=(x:typeof rows[number])=>
   x.originalPilot?0:x.sapDateChronologyState==="LISTED_SAP_DATE_AFTER_PRIMARY_COMPLETION_RECONCILE_VERSION"?1:
   x.sourcePdfFiles.length?2:3;
  return priority(a)-priority(b)||a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct);
 });
 return {
  schema:"MAIN_R88_RECONCILE_REGISTRY_DOCUMENT_DATES_NO_PROSPECTIVE_SAP_CLAIM" as const,
  observationDateUtc:input.snapshotDateUtc,
  notice:R88_EXPLANATION,
  trialCount:29 as const,applicationCycles:23 as const,
  listedPdfFiles:23 as const,
  trialsWithPublicListedPdf:12 as const,
  trialsWithoutListedPdf:17 as const,
  sapListedDocumentDatesAfterPrimaryCompletion:11 as const,
  sapListedDocumentDatesOnOrBeforePrimaryCompletion:1 as const,
  filesUploadedAfterPrimaryCompletion:23 as const,
  authenticatedProspectiveSAPs:0 as const,
  independentSignedMedicalReviews:0 as const,
  independentlyValidatedFDAForecasts:0 as const,
  researchOnly:true as const,
  rows
 };
}
export const R88_SOURCE_CHRONOLOGY=buildR88SourceChronology();
