/** MAIN R93 — phase-first scientific SOURCE handoff for two priority FOCUS
 * studies. Preserves all R86 / R79 blocker identities; no fake signatures.
 * This module is a read-only document-recovery queue, not a medical grade.
 */
import {R86_ORIGINAL_DOCUMENT_MANIFEST} from "./focus-r86-original-document-inventory";
import {FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES} from "./focus-r79-launch-htn-sap-lock-evidence-gates";
import {FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY} from "./focus-r78-launch-htn-public-chronology";
import {R89_ARCHIVED_ACACIA_SOURCE_HISTORY} from "./focus-r89-acacia-prior-original-history";
import {R89_HISTORICAL_SOURCE_RECOVERY} from "./focus-r89-historical-source-recovery";

export const R93_QUALIFICATION_NOTICE=
 "Research leads and original public registry versions are documented evidence, not authenticated final prospectively approved SAPs, first unblinded-access or database-lock logs, qualified medical signoffs, regulatory decisions, or calibrated FDA probabilities.";

const ACACIA="NCT06081894";
const LAUNCH="NCT06153693";
const GH="https://github.com/pdufa/pdufa-command-center/blob/feature/main-r83-evidence-gap-export-20261109/";
const JAMA="https://jamanetwork.com/journals/jama/fullarticle/2835763";
const CTIS="https://euclinicaltrials.eu/ctis-public/view/2023-505797-15-00?lang=en";
const ACACIA_REVIEW=GH+"docs/medical-review-pilot-20261108/revision36-protocol-safety/reviewer-packet.json";
const ACACIA_HISTORY=GH+"docs/medical-review-pilot-20261108/revision36-original-history/validated_comparison.json";
const LAUNCH_GATES=GH+"new-platform/frontend/data/focus-r79-launch-htn-sap-lock-evidence-gates.json";
const LAUNCH_TIMELINE=GH+"new-platform/frontend/data/focus-r78-launch-htn-public-chronology.json";

const META:Record<string,{
 title:string;proof:string;scientificQuestion:string;
 sourceLabel:string;sourceUrl:string;sourceRecord:string;
 priority:1|2|3;
}>={
 "ACACIA_HCM:FINAL_LOCKED_SAP":{
  title:"Find final prospectively approved signed SAP",
  proof:"Controlled sponsor final SAP, signature/effective-version audit, final database lock and first assignment-access log",
  scientificQuestion:"Which version governed H1–H7 at first unblinded access, including missingness and alpha recycling?",
  sourceLabel:"CTIS publicly posted Amendment 04 protocol",
  sourceUrl:CTIS,sourceRecord:ACACIA_REVIEW,priority:1
 },
 "ACACIA_HCM:DUAL_PRIMARY_HISTORY":{
  title:"Reconcile one-to-two registered primary outcomes",
  proof:"Approved original amendment history with effective dates, signed SAP endpoint hierarchy and first unblinding record",
  scientificQuestion:"Was pVO2 an approved additional primary outcome before any access to relevant unblinded data?",
  sourceLabel:"Four original registry source versions (v26, v27, v29, v30)",
  sourceUrl:ACACIA_HISTORY,sourceRecord:ACACIA_HISTORY,priority:1
 },
 "ACACIA_HCM:CONSORT_SETS":{
  title:"Reconcile 516 versus 517 and population definitions",
  proof:"Original dated participant CONSORT flow, actual randomized/FAS/safety listings, arm denominators and cutoff dates",
  scientificQuestion:"Which denominator is randomized, analysis eligible, or treated, and why do reported participant figures differ?",
  sourceLabel:"Re-examined source protocol and safety reviewer packet",
  sourceUrl:ACACIA_REVIEW,sourceRecord:ACACIA_REVIEW,priority:2
 },
 "ACACIA_HCM:HEART_FAILURE_WINDOWS":{
  title:"Reconcile heart-failure and LVEF adverse-event reporting",
  proof:"Original AE case listings by cutoff, exposure, coding, severity, safety arm and blinded adjudication records",
  scientificQuestion:"Do the reported HF 11/1 and 12/3 figures use different case definitions, windows, or populations? Reconcile 14 reported interruptions and source denominator.",
  sourceLabel:"HFSA public sponsor dosing and safety presentation (bytes uncaptured)",
  sourceUrl:"https://cytokinetics.com/wp-content/uploads/2026/10/HFSA26-ACACIA-Dosing-and-Safety-Rapid-Fire-Presentation_FINAL_V3.pdf",
  sourceRecord:ACACIA_REVIEW,priority:2
 },
 "LAUNCH_HTN:CONTROLLED_ORIGINAL_SAP_BYTES":{
  title:"Authenticate original SAP 3.0 source file and custody",
  proof:"Sponsor-controlled exact SAP 3.0/Amendment 2 bytes, signer identities, approved date and immutable SHA receipt",
  scientificQuestion:"Are the published JAMA supplement signature imprints equivalent to the approved final sponsor SAP version?",
  sourceLabel:"Original JAMA Launch-HTN paper and supplements",sourceUrl:JAMA,
  sourceRecord:LAUNCH_GATES,priority:1
 },
 "LAUNCH_HTN:FORMAL_SAP_FINALIZATION_RECORD":{
  title:"Authenticate controlled SAP final approval",
  proof:"Original source-controlled approvals, accountable statistician signature audit and amendment effective-version history",
  scientificQuestion:"Was the governing SAP approved and locked before first unblinded treatment access?",
  sourceLabel:"Original JAMA SAP version 3.0 imprint",sourceUrl:JAMA,sourceRecord:LAUNCH_GATES,priority:1
 },
 "LAUNCH_HTN:FINAL_DATABASE_LOCK_AUDIT":{
  title:"Recover actual final database-lock timestamp",
  proof:"Immutable original final database lock certificate, approvals, query-close evidence and timestamped change audit",
  scientificQuestion:"What exact date/time was the final analysis database locked and were subsequent changes controlled?",
  sourceLabel:"JAMA primary report masking description",sourceUrl:JAMA,sourceRecord:LAUNCH_TIMELINE,priority:1
 },
 "LAUNCH_HTN:FIRST_UNBLINDED_ACCESS_AUDIT":{
  title:"Recover first unblinding and analysis access audit",
  proof:"Treatment-assignment blind-break authorization, first access log, user/time, statistical-program checksum",
  scientificQuestion:"Can SAP approval be independently ordered before all unblinded data access, not merely before topline announcement?",
  sourceLabel:"March 10, 2025 public SEC results disclosure",
  sourceUrl:"https://ir.mineralystx.com/sec-filings/all-sec-filings/content/0001628280-25-011459/mlys-20250310.htm",
  sourceRecord:LAUNCH_TIMELINE,priority:1
 },
 "LAUNCH_HTN:SAP_AMENDMENT_CONTROLLED_CHAIN":{
  title:"Reconcile protocol and SAP 2.1 / 3.0 / 3.1 version chain",
  proof:"Sponsor original approval trail linking every protocol amendment, SAP revision, analysis set, and H1–H7 gate to effective time",
  scientificQuestion:"Which version's hierarchy, missing data handling and multiplicity rules governed the primary analysis?",
  sourceLabel:"JAMA original protocol and SAP supplement index",sourceUrl:JAMA,
  sourceRecord:LAUNCH_GATES,priority:2
 },
 "LAUNCH_HTN:CONFLICTED_ADDENDUM_YEAR_RECONCILIATION":{
  title:"Resolve imputation and windowing addendum year conflicts",
  proof:"Dated issuer/sponsor signed controlled addendum versions plus original release and approval timestamps",
  scientificQuestion:"Why do two published addendum covers contain 2024 versus 2025 date discrepancies?",
  sourceLabel:"Published JAMA supplements 5 and 7",sourceUrl:JAMA,
  sourceRecord:LAUNCH_GATES,priority:2
 },
 "LAUNCH_HTN:TWO_TRUSTED_INDEPENDENT_ATTESTATIONS":{
  title:"Obtain authorized independent source and science attestations",
  proof:"Owner-authorized source-custodian authentication and qualified independent statistician/clinical reviewer signed assessment",
  scientificQuestion:"Can a separate trusted reviewer certify the exact original files, analysis and timeline without reusing automated labels?",
  sourceLabel:"Recorded evidence authentication gate",sourceUrl:LAUNCH_GATES,
  sourceRecord:LAUNCH_GATES,priority:3
 }
};

const SOURCE_GATE_STATES:Record<string,string>={
 "ACACIA_HCM:FINAL_LOCKED_SAP":"NOT_AUTHENTICATED",
 "ACACIA_HCM:DUAL_PRIMARY_HISTORY":"NEEDS_ADJUDICATION",
 "ACACIA_HCM:CONSORT_SETS":"UNRESOLVED",
 "ACACIA_HCM:HEART_FAILURE_WINDOWS":"UNRESOLVED",
 "LAUNCH_HTN:CONTROLLED_ORIGINAL_SAP_BYTES":"PUBLISHED_IMPRINT_ONLY",
 "LAUNCH_HTN:FORMAL_SAP_FINALIZATION_RECORD":"NOT_OBTAINED",
 "LAUNCH_HTN:FINAL_DATABASE_LOCK_AUDIT":"NOT_OBTAINED",
 "LAUNCH_HTN:FIRST_UNBLINDED_ACCESS_AUDIT":"NOT_OBTAINED",
 "LAUNCH_HTN:SAP_AMENDMENT_CONTROLLED_CHAIN":"NOT_OBTAINED",
 "LAUNCH_HTN:CONFLICTED_ADDENDUM_YEAR_RECONCILIATION":"UNRESOLVED_PRINTED_YEAR_CONFLICT",
 "LAUNCH_HTN:TWO_TRUSTED_INDEPENDENT_ATTESTATIONS":"NOT_OBTAINED"
};
export function buildR93PriorityScientificGates(
 inventory:typeof R86_ORIGINAL_DOCUMENT_MANIFEST=R86_ORIGINAL_DOCUMENT_MANIFEST,
 launch:typeof FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES=FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES,
 history:typeof R89_ARCHIVED_ACACIA_SOURCE_HISTORY=R89_ARCHIVED_ACACIA_SOURCE_HISTORY,
 publicTime:typeof FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY=FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY,
 recovery:typeof R89_HISTORICAL_SOURCE_RECOVERY=R89_HISTORICAL_SOURCE_RECOVERY
){
 if(!inventory||!launch||!publicTime||!recovery||
  inventory.exactTrials!==29||inventory.provisionalApplications!==23||
  inventory.rows.length!==29||
  inventory.knownAcaciaDocumentaryBlockers!==4||
  inventory.knownLaunchDocumentaryBlockers!==7||
  inventory.independentSignedSAPsAuthenticated!==0||
  inventory.qualifiedIndependentScientificReviews!==0||
  inventory.validatedFutureFDAPredictions!==0||
  launch.nct!==LAUNCH||launch.sourceRequirements.length!==7||
  launch.requirementsIndependentlyVerified!==0||
  launch.qualifiedIndependentReviewersSigned!==0||
  launch.originalSourceAttestationsVerified!==false||
  launch.scientificGrade!==null||launch.FDAOutcome!=="ABSTAIN"||
  history.nct!==ACACIA||history.exactOriginalVersionsCaptured!==4||
  history.scientificReviewSigned!==false||
  history.prospectiveSAPFinalSignatureAuthenticated!==false||
  history.actualUnblindingDateIndependentlyVerified!==false||
  JSON.stringify(history.previousVersionFiles.map(x=>x.primaryEndpointsListed))!==
    JSON.stringify([1,2,2,2])||
  JSON.stringify(history.previousVersionFiles.map(x=>x.publiclyPostedDate))!==
    JSON.stringify(["2025-01-14","2025-05-20","2026-02-02","2026-08-05"])||
  publicTime.nct!==LAUNCH||
  publicTime.observation.mainSapPrintedSignatureImprint!=="2025-02-13"||
  publicTime.observation.windowingAddendumPrintedSignatureImprint!=="2025-02-23"||
  publicTime.observation.publicIssuerToplineSECDisclosureDate!=="2025-03-10"||
  publicTime.observation.originalActualDatabaseLockDate!==null||
  publicTime.observation.originalActualUnblindingDate!==null||
  publicTime.observation.originalSAPAuthenticPreUnblindingSignatureVerified!==false||
  publicTime.observation.twoPrintedSAPCoverDateDiscrepanciesUnresolved!==true||
  publicTime.regulatory.officialOutcomeForecast!=="ABSTAIN"||
  recovery.rows.length!==17)return null;

 const cases=[];
 for(const [nct,kind] of [[ACACIA,"ACACIA_HCM"],[LAUNCH,"LAUNCH_HTN"]] as const){
  const m=inventory.rows.find(x=>x.nct===nct);
  const r=recovery.rows.find(x=>x.nct===nct);
  if(!m||!r||m.focusCase!==kind||r.researchPilot!==kind||
     m.knownBlockers.length!==(kind==="ACACIA_HCM"?4:7)||
     m.authenticatedSignedProspectiveSAP!==false||
     m.signedIndependentScientificReview!==false||
     m.scientificGrade!==null||m.FDAOutcome!=="ABSTAIN"||
     r.prospectivelyAuthenticatedSignedSAP!==false||
     r.independentQualifiedScienceReview!==false||
     r.validatedFDAOutcome!=="ABSTAIN")return null;
  const rows=kind==="ACACIA_HCM"?m.knownBlockers:launch.sourceRequirements;
  const gates=[];
  for(const gate of rows){
   const id=gate.id,meta=META[kind+":"+id];
   if(!meta||SOURCE_GATE_STATES[kind+":"+id]!==gate.status||
      !gate.label||!gate.evidence||
      ("verified" in gate&&gate.verified!==false)||
      ("independentReceipt" in gate&&gate.independentReceipt!==null))return null;
   gates.push({
    id,clinicalStudy:kind,sourceStatus:gate.status,
    existingEvidence:gate.evidence,
    sourceEvidenceLabel:meta.sourceLabel,
    sourceUrl:meta.sourceUrl,storedResearchReceiptUrl:meta.sourceRecord,
    scientificQuestion:meta.scientificQuestion,
    originalProofRequired:meta.proof,
    reviewPriority:meta.priority,
    provenanceClass:"PUBLISHED_RESEARCH_LEAD_REQUIRES_CONTROLLED_ORIGINAL_PROOF" as const,
    resolvedByAuthenticatedOriginals:false as const,
    signedQualifiedReviewerApproved:false as const,
    permissibleConclusion:"SOURCE_RECONCILIATION_PENDING_NOT_APPROVAL_PROBABILITY" as const
   });
  }
  if(gates.length!==(kind==="ACACIA_HCM"?4:7))return null;
  const gateIds=new Set(gates.map(x=>x.id));
  if(gateIds.size!==gates.length||
     Object.keys(META).filter(x=>x.startsWith(kind+":")).some(x=>!gateIds.has(x.split(":")[1])))return null;
  gates.sort((a,b)=>a.reviewPriority-b.reviewPriority||a.id.localeCompare(b.id));
  cases.push({
   nct,ticker:m.ticker,trial:kind,phase:m.registryReportedPhase,
   applicationCycles:[...m.cycleIds],
   originalRegistryUrl:m.registryUrl,
   originalJournalLead:m.publishedMainReportLead,
   protocolOrSapPdfListedInCurrentRegistry:false as const,
   historicalOriginalRegistryVersionsCaptured:kind==="ACACIA_HCM"?4:0,
   currentRegistryAggregateResultsPosted:false as const,
   timelineSummary:kind==="ACACIA_HCM"?
     "Registry source v26 posted Jan 14 2025 lists one primary; v27 posted May 20 2025 lists two. SAP signature and first-unblinding chronology are NOT independently authenticated.":
     "Published SAP main imprint Feb 13 2025 and windowing addendum imprint Feb 23 2025 precede the Mar 10 2025 public topline, but real database-lock and first-unblinded-access timestamps remain unknown.",
   gates,
   signedOriginalSAPAuthenticated:false as const,
   independentScienceApproved:false as const,
   methodGrade:null,
   FDAForecast:"ABSTAIN" as const
  });
 }
 if(cases.reduce((n,x)=>n+x.gates.length,0)!==11||
    new Set(cases.map(x=>x.nct)).size!==2||cases.some(x=>x.applicationCycles.length===0))
   return null;
 return {
  schema:"MAIN_R93_PRIORITY_2_CASE_11_ORIGINAL_SCIENTIFIC_GATES_UNADJUDICATED" as const,
  datedSourceReview:"2026-11-10" as const,
  exactFOCUSTrialsUnaffected:29 as const,
  provisionalFDAApplicationCyclesUnaffected:23 as const,
  priorityOriginalTrialCases:2 as const,
  unresolvedAuthenticatedScienceRequirements:11 as const,
  acaciaOriginalHistoricalVersions:4 as const,
  acaciaRegistryPrimaryEndpointsVersion26:1 as const,
  acaciaRegistryPrimaryEndpointsVersion27:2 as const,
  launchPublishedSAPImprint:"2025-02-13" as const,
  launchPublicToplineDate:"2025-03-10" as const,
  independentlyVerifiedSignedProspectiveSAPs:0 as const,
  qualifiedIndependentScienceSignoffs:0 as const,
  validatedFDAPredictions:0 as const,
  FDAForecast:"ABSTAIN" as const,
  notice:R93_QUALIFICATION_NOTICE,
  cases
 };
}
export const R93_PRIORITY_SCIENTIFIC_GATES=buildR93PriorityScientificGates();
