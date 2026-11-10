/**
 * MAIN: research-only source acquisition handoff for the ACACIA-HCM pilot.
 * No email is sent, no confidential records are requested programmatically,
 * and no score, phase signoff, regulatory outcome or reviewer event is written.
 */
import type {Phase3ReviewQueue} from "./acacia-phase3-review-queue";

export type AcquisitionRequest={
  requestId:string;
  priority:1|2|3;
  category:"STATISTICAL"|"SAFETY"|"TRIAL_PROVENANCE"|"REGULATORY";
  title:string;
  preciseOriginalEvidenceNeeded:string;
  howToIndependentlyVerify:string;
  mappedMethodPositions:string[];
  evidenceState:"NOT_AUTHENTICATED_FOR_CURRENT_REVIEW";
  acquisitionState:"DRAFT_NOT_SENT";
  independentReviewerSigned:false;
  officialClinicalGrade:null;
};
export type AcquisitionPacket={
  schema:"MAIN_ACACIA_EVIDENCE_ACQUISITION_HANDOFF_V1";
  nct:"NCT06081894";
  trial:"ACACIA-HCM";
  protocol:"CY 6033";
  sourceSnapshotAsOf:"2026-11-08";
  sourceAuditRuns:{safetyAndSap:42555289486;alternativePublisher:42556948533};
  recipientForResearchEligibilityInquiry:"medicalaffairs@cytokinetics.com";
  dataAccessIsSubjectTo:"SPONSOR_ELIGIBILITY_TIMING_REVIEW_AND_AGREEMENT";
  requests:AcquisitionRequest[];
  requestCount:6;
  mappedMethodPositionsCovered:18;
  unmappedPositionsUnreviewed:782;
  requestDeliveryStatus:"DRAFT_ONLY_NOT_SENT";
  externallyAuthenticatedNewDocuments:0;
  approvedClinicalGrades:0;
  independentPhaseSignoffs:0;
  fdaPrediction:"ABSTAIN";
  accuracy:"NOT_CALIBRATED";
  noPatientLevelDataStored:true;
  disclaimer:string;
};
const methods:ReadonlyArray<Omit<AcquisitionRequest,"evidenceState"|"acquisitionState"|"independentReviewerSigned"|"officialClinicalGrade">>=[
  {
    requestId:"LOCKED_PRIMARY_SAP",priority:1,category:"STATISTICAL",
    title:"Final locked primary statistical analysis plan and signed amendment history",
    preciseOriginalEvidenceNeeded:"Identify the exact final dated/locked primary CY 6033 SAP, version history, approvals, lock/unblinding dates, prespecified co-primary hypotheses, estimands, multiplicity sequence, intercurrent-event strategy and all statistical amendments.",
    howToIndependentlyVerify:"Match source/version and lock dates against original registry, CTIS protocol amendment, database lock and peer-reviewed primary endpoints; independent statistical review required.",
    mappedMethodPositions:["4.2:L1","4.2:L2","4.3:L1","4.3:L4","5.1:L1","5.1:L12","5.2:L1","8.2:L1"]
  },
  {
    requestId:"PRIMARY_SENSITIVITY_AND_MISSINGNESS",priority:1,category:"STATISTICAL",
    title:"Original co-primary KCCQ-CSS and peak VO2 analysis and sensitivity tables",
    preciseOriginalEvidenceNeeded:"Request original arm-level analysis populations and denominator changes; prespecified model estimates and exact confidence intervals; missing observations, imputation, intercurrent events, sensitivity and tipping-point analyses, alpha allocations and confirmatory testing graph.",
    howToIndependentlyVerify:"Reproduce predeclared primary analyses and all sensitivity estimates from source-versioned methods/tables; do not substitute a secondary responder analysis.",
    mappedMethodPositions:["4.2:L1","4.3:L1","4.3:L4","5.1:L12","5.2:L1","5.4:L1"]
  },
  {
    requestId:"HF_SAE_EVENT_DEFINITION",priority:1,category:"SAFETY",
    title:"Serious heart-failure event definitions for reported 11/1 and 12/3 counts",
    preciseOriginalEvidenceNeeded:"Request redacted or aggregate reconciled event-code tables with original definitions, event dates relative to treatment, analysis population, observation windows, seriousness criteria, LVEF association, and rules distinguishing 11 treated/1 placebo from 12 treated/3 placebo.",
    howToIndependentlyVerify:"Create an independently reviewed matched-definition reconciliation, documenting whether counts represent different periods or case sets; 2+10=12 vs 3 does not by itself reconcile 11/1.",
    mappedMethodPositions:["5.3:L1","5.3:L19","8.1:L1","8.2:L1","8.2:L4"]
  },
  {
    requestId:"SAFETY_DENOMINATORS_EXPOSURE",priority:1,category:"SAFETY",
    title:"Treatment interruptions, safety denominators, exposure and causality",
    preciseOriginalEvidenceNeeded:"Request original arm-specific treatment-interruption numerator and eligible denominator, reasons, LVEF changes, exposure duration/time at risk, repeated events, coded severity, reversibility and independent medical event assessment.",
    howToIndependentlyVerify:"Reconcile published 7-versus-14 interruptions and reported percentages using exact source-defined analysis sets; do not infer causality from unadjusted randomized arm frequencies.",
    mappedMethodPositions:["5.3:L1","5.3:L19","8.1:L1","8.2:L4"]
  },
  {
    requestId:"CONSORT_AND_PROTOCOL_VERSIONS",priority:2,category:"TRIAL_PROVENANCE",
    title:"Exact trial conduct, CONSORT accounting and dated protocol amendments",
    preciseOriginalEvidenceNeeded:"Identify original amended protocols and version-effective dates; trial enrollment/randomization and 516-versus-517 accounting; missing follow-up, treatment deviations, analysis subsets, database lock, site monitoring and independently verifiable conduct records.",
    howToIndependentlyVerify:"Match patient-flow totals and every source version to exact NCT06081894 and CY 6033, with independent Phase III verification before grading.",
    mappedMethodPositions:["4.1:L1","4.4:L1","4.5:L1","5.4:L1","5.4:L4","8.1:L1"]
  },
  {
    requestId:"EXACT_NHCM_REGULATORY_STATUS",priority:2,category:"REGULATORY",
    title:"Source-verified FDA status for nonobstructive HCM, distinct from obstructive HCM label",
    preciseOriginalEvidenceNeeded:"Locate original dated FDA/issuer public confirmation, if any, of the nHCM supplement filing, FDA acceptance, designated action date, issued information requests and review decisions; distinguish from the separate obstructive-HCM approved indication.",
    howToIndependentlyVerify:"Require the correct drug/indication, date and authentic primary regulatory document. If absent, keep PDUFA action date and FDA prediction unverified/abstained.",
    mappedMethodPositions:["5.2:L1","8.2:L1","8.2:L4","8.2:L5"]
  }
];
const expected=new Set([
  "4.1:L1","4.2:L1","4.2:L2","4.3:L1","4.3:L4","4.4:L1","4.5:L1",
  "5.1:L1","5.1:L12","5.2:L1","5.3:L1","5.3:L19","5.4:L1","5.4:L4",
  "8.1:L1","8.2:L1","8.2:L4","8.2:L5"
]);

export function buildAcaciaAcquisitionHandoff(q:Phase3ReviewQueue|null):AcquisitionPacket|null{
  if(!q||q.schema!=="MAIN_ACACIA_PHASE3_REVIEW_QUEUE_V1"||
    q.nct!=="NCT06081894"||q.sourceSnapshotAsOf!=="2026-11-08"||
    q.status!=="RESEARCH_WORKLIST_NOT_CLINICAL_GRADE"||
    q.summary?.mappedSourceLeads!==18||q.summary?.positionsNotSourceMapped!==782||
    q.summary?.officialClinicalGrades!==0||q.summary?.qualifiedPhaseSignoffs!==0||
    q.fdaPrediction!=="ABSTAIN"||q.calibratedAccuracy!==null||
    q.alternativeSourceRecovery?.archivedAuditRun!==42556948533||
    q.alternativeSourceRecovery?.sponsorResearchContact!=="medicalaffairs@cytokinetics.com"||
    q.alternativeSourceRecovery?.automaticRequestSent!==false||
    q.alternativeSourceRecovery?.finalLockedPrimarySapAuthenticated!==false||
    !Array.isArray(q.positions)||q.positions.length!==18||
    q.positions.some(x=>x.clinicalGrade!==null||x.qualifiedReviewerSignoff!==false||
      x.fdaProbability!==null))return null;
  const ids=new Set(q.positions.map(p=>p.id));
  if(ids.size!==18||ids.size!==expected.size||[...ids].some(id=>!expected.has(id)))return null;
  const covered=new Set(methods.flatMap(x=>x.mappedMethodPositions));
  if(covered.size!==18||[...covered].some(id=>!ids.has(id))||
    methods.length!==6||new Set(methods.map(x=>x.requestId)).size!==6)return null;
  return {
    schema:"MAIN_ACACIA_EVIDENCE_ACQUISITION_HANDOFF_V1",
    nct:"NCT06081894",trial:"ACACIA-HCM",protocol:"CY 6033",
    sourceSnapshotAsOf:"2026-11-08",
    sourceAuditRuns:{safetyAndSap:42555289486,alternativePublisher:42556948533},
    recipientForResearchEligibilityInquiry:"medicalaffairs@cytokinetics.com",
    dataAccessIsSubjectTo:"SPONSOR_ELIGIBILITY_TIMING_REVIEW_AND_AGREEMENT",
    requests:methods.map(m=>({...m,mappedMethodPositions:[...m.mappedMethodPositions],
      evidenceState:"NOT_AUTHENTICATED_FOR_CURRENT_REVIEW",
      acquisitionState:"DRAFT_NOT_SENT",independentReviewerSigned:false,officialClinicalGrade:null})),
    requestCount:6,mappedMethodPositionsCovered:18,unmappedPositionsUnreviewed:782,
    requestDeliveryStatus:"DRAFT_ONLY_NOT_SENT",externallyAuthenticatedNewDocuments:0,
    approvedClinicalGrades:0,independentPhaseSignoffs:0,
    fdaPrediction:"ABSTAIN",accuracy:"NOT_CALIBRATED",noPatientLevelDataStored:true,
    disclaimer:"Research evidence request checklist only, not an application, transmission, disclosure approval, completion claim, original-data evaluation, scientific rating or FDA probability. Sponsor controls eligibility and timing; independent scientific review remains required."
  };
}

/** Standalone human-reviewed inquiry *draft* to copy or edit, never sent. */
export function acquisitionDraftText(packet:AcquisitionPacket):string{
  const lines=[
    "DRAFT — NOT SENT — research source eligibility inquiry",
    "To: "+packet.recipientForResearchEligibilityInquiry,
    "Subject: ACACIA-HCM / NCT06081894 / CY 6033 — original analysis and data-access eligibility",
    "",
    "I am inquiring about the eligibility process and availability of the following original trial documents or appropriately redacted aggregate research materials for independent methodological review.",
    "I recognize that access is governed by sponsor eligibility rules, timing and any required agreement, and am not asking for unauthorized participant-level data.",
    "",
    ...packet.requests.flatMap((x,i)=>[
      String(i+1)+". "+x.title,
      "   Requested: "+x.preciseOriginalEvidenceNeeded,
      "   Verification sought: "+x.howToIndependentlyVerify,
      ""
    ]),
    "Please advise which documents, published supplemental materials, data-sharing procedures and timelines may be available, and how a qualified researcher could apply.",
    "",
    "This draft has not been sent. Any scientific conclusions would require an independent review.",
  ];
  return lines.join("\n")+"\n";
}
