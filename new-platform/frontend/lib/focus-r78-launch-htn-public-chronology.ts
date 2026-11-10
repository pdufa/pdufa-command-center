/** R78: public first-disclosure chronology; NOT original blinded database-lock proof. */
import raw from "../data/focus-r78-launch-htn-public-chronology.json";
import {FOCUS_R75_LAUNCH_HTN_CHRONOLOGY} from "./focus-r75-launch-htn-chronology";
import {FOCUS_R77_LAUNCH_HTN_PUBLISHED_METHODS} from "./focus-r77-launch-htn-published-methods";

const URLS={
 journal:"https://jamanetwork.com/journals/jama/fullarticle/2835763",
 sec20250310:"https://ir.mineralystx.com/sec-filings/all-sec-filings/content/0001628280-25-011459/mlys-20250310.htm",
 issuer20250307:"https://ir.mineralystx.com/news-events/press-releases/detail/59/mineralys-therapeutics-to-announce-topline-data-from",
 issuer20260309:"https://ir.mineralystx.com/news-events/press-releases/detail/93/mineralys-therapeutics-announces-fda-acceptance-of-nda-for",
 sec20261104:"https://www.sec.gov/Archives/edgar/data/1933414/000193341426000142/mlys2026q38kex991.htm"
} as const;

const EVENTS=[
 ["LAST_PARTICIPANT_FOLLOWUP_REPORTED","2025-01-24","REPORTED_TRIAL_CONDUCT","journal","2025-06-30"],
 ["MAIN_SAP_3_0_PRINTED_SIGNATURE_IMPRINT","2025-02-13","PUBLISHED_DOCUMENT_PRINTED_DATE_NOT_AUTHENTICATED","journal","2025-06-30"],
 ["MULTIPLE_IMPUTATION_ADDENDUM_PRINTED_SIGNATURE_IMPRINT","2025-02-13","PUBLISHED_DOCUMENT_PRINTED_DATE_NOT_AUTHENTICATED","journal","2025-06-30"],
 ["WINDOWING_ADDENDUM_PRINTED_SIGNATURE_IMPRINT","2025-02-23","PUBLISHED_DOCUMENT_PRINTED_DATE_NOT_AUTHENTICATED","journal","2025-06-30"],
 ["SPONSOR_ANNOUNCED_TOPLINE_DISCLOSURE_SCHEDULE","2025-03-07","PUBLIC_ISSUER_SCHEDULE_ANNOUNCEMENT_NOT_RESULTS","issuer20250307","2025-03-07"],
 ["SPONSOR_DISCLOSED_TOPLINE_IN_SEC_8K","2025-03-10","PUBLIC_SEC_SPONSOR_EFFICACY_READOUT","sec20250310","2025-03-10"],
 ["JAMA_PUBLISHED_FULL_PRIMARY_REPORT_AND_SUPPLEMENTS","2025-06-30","PUBLIC_JOURNAL_REPORT_NOT_PROSPECTIVE_SAP","journal","2025-06-30"],
 ["SPONSOR_ANNOUNCED_NDA_ACCEPTANCE","2026-03-09","ISSUER_REPORTED_FDA_NDA_ACCEPTANCE","issuer20260309","2026-03-09"],
 ["SEC_EXHIBIT_REPORTED_REVIEW_CONTINUING","2026-11-04","ISSUER_SEC_8K_PENDING_REVIEW","sec20261104","2026-11-04"]
] as const;

export function buildR78LaunchHtnChronology(input:unknown=raw){
 const r75=FOCUS_R75_LAUNCH_HTN_CHRONOLOGY;
 const r77=FOCUS_R77_LAUNCH_HTN_PUBLISHED_METHODS;
 if(!r75||!r77||r75.nct!=="NCT06153693"||r77.nct!=="NCT06153693"||
    r75.futureFDAOutcome!=="ABSTAIN"||
    r75.signedOriginalProspectiveStatisticalPlansIndependentlyAuthenticated!==0||
    r77.reviewSafety.signedClinicalReviewerCount!==0||
    !input||typeof input!=="object"||Array.isArray(input))return null;
 const d=input as typeof raw;
 if(d.schema!=="MAIN_R78_LAUNCH_HTN_PUBLIC_DISCLOSURE_CHRONOLOGY_NOT_DATABASE_LOCK_PROOF"||
    d.asOf!=="2026-11-09"||d.nct!=="NCT06153693"||d.ticker!=="MLYS"||
    d.drug!=="Lorundrostat"||d.cycleId!=="mlys-lorundrostat"||
    d.applicationType!=="NDA"||
    d.focusTrialCountUnchanged!==29||d.provisionalApplicationCycleCountUnchanged!==23||
    JSON.stringify(d.sources)!==JSON.stringify(URLS)||
    d.sourceEvents.length!==9||d.blockingTasks.length!==6)return null;
 for(let i=0;i<EVENTS.length;i++){
   const event=d.sourceEvents[i],e=EVENTS[i];
   if(event.eventId!==e[0]||event.date!==e[1]||event.eventKind!==e[2]||
      event.sourceUrl!==URLS[e[3]]||event.sourceDate!==e[4]||
      event.evidenceOnly!==true||event.provesUnblinding!==false||
      typeof event.summary!=="string"||event.summary.length<75)return null;
 }
 const o=d.observation,g=d.regulatory;
 if(o.lastFollowupReportedDate!=="2025-01-24"||
    o.mainSapPrintedSignatureImprint!=="2025-02-13"||
    o.windowingAddendumPrintedSignatureImprint!=="2025-02-23"||
    o.publicScheduledResultsAnnouncementDate!=="2025-03-07"||
    o.publicIssuerToplineSECDisclosureDate!=="2025-03-10"||
    o.publicationOnlineDate!=="2025-06-30"||
    o.journalDescribesMaskingUntilFinalDatabaseLock!==true||
    o.journalDisclosesFinalDatabaseLockCalendarDate!==false||
    o.originalActualDatabaseLockDate!==null||
    o.originalActualUnblindingDate!==null||
    o.originalSAPAuthenticPreUnblindingSignatureVerified!==false||
    o.twoPrintedSAPCoverDateDiscrepanciesUnresolved!==true||
    o.originalPdfSourceByteHashesAvailable!==0||
    o.noAuthenticatedOriginalArchive!==true||
    o.interpretation!=="THE_SEQUENCE_IS_CONSISTENT_WITH_BUT_DOES_NOT_ESTABLISH_PRE_UNBLINDING_SAP_SIGNOFF"||
    typeof o.sourceDisclaimer!=="string"||o.sourceDisclaimer.length<120)return null;
 if(g.reportedNdaAcceptanceDate!=="2026-03-09"||
    g.acceptanceEvidenceKind!=="SPONSOR_ANNOUNCEMENT_NOT_PUBLIC_FDA_ACCEPTANCE_LETTER"||
    g.latestSourceDate!=="2026-11-04"||
    g.asReportedRegulatoryStatus!=="SPONSOR_REPORTS_FDA_REVIEW_ONGOING"||
    g.pdufaTargetDate!=="2026-12-22"||
    g.pdufaSourceUrl!==URLS.sec20261104||
    g.fdaIssuedDecisionDocumentIndependentlyVerified!==false||
    g.officialOutcomeForecast!=="ABSTAIN"||
    g.officialTimingForecast!=="UNKNOWN"||
    g.signedQualifiedReviewerCount!==0||
    g.validatedApplicationForecasts!==0||
    g.noModelTrainingOrProductionWrites!==true)return null;
 if(d.blockingTasks.some(x=>typeof x!=="string"||x.length<60))return null;
 return {...d,
   actualUnblindingDateVerified:false as const,
   prospectivelySignedPlanVerified:false as const,
   regulatoryDateSourceVerifiedOnly:true as const,
   medicalGradeAllowed:false as const,
   validatedFDAOutcome:"ABSTAIN" as const};
}
export const FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY=buildR78LaunchHtnChronology();
