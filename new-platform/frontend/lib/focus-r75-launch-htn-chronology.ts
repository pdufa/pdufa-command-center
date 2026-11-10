/** MAIN R75: literal publisher-PDF-page research evidence, never a qualified SAP signoff. */
import raw from "../data/focus-r75-launch-htn-source-date-reconciliation.json";
import {FOCUS_R73_LAUNCH_HTN_DOCUMENT_INDEX} from "./focus-r73-launch-htn-document-index";

const OBSERVED=[
 {version:"NOT_STATED",date:null,sig:null,conflict:false,pages:37,role:"METHODS_SUPPLEMENT",read:[1]},
 {version:"3.1 EU",date:"2024-06-11",sig:null,conflict:false,pages:80,role:"PROTOCOL_VERSION",read:[1]},
 {version:"3.0",date:"2024-06-11",sig:null,conflict:false,pages:81,role:"PROTOCOL_VERSION",read:[1]},
 {version:"2.1 UK",date:"2024-01-08",sig:null,conflict:false,pages:78,role:"PROTOCOL_VERSION",read:[1]},
 {version:"SAP 3.0 windowing addendum 1.0",date:"2025-02-22",sig:"2025-02-23",conflict:true,pages:5,role:"SAP_ADDENDUM",read:[1,2]},
 {version:"SAP version 3.0 Amendment 2",date:"2025-02-13",sig:"2025-02-13",conflict:false,pages:70,role:"SAP_AMENDMENT",read:[1,2]},
 {version:"SAP 3.0 multiple imputation addendum 1.0",date:"2025-02-13",sig:"2025-02-13",conflict:true,pages:10,role:"SAP_ADDENDUM",read:[1,2]}
] as const;

export function buildR75LaunchHtnChronology(input:unknown=raw){
 const upstream=FOCUS_R73_LAUNCH_HTN_DOCUMENT_INDEX;
 if(!upstream||upstream.indexedDocumentCount!==7||
    upstream.independentlySignedSAPs!==0||
    upstream.officialFutureFDAOutcome!=="ABSTAIN"||
    !input||typeof input!=="object"||Array.isArray(input))return null;
 const d=input as typeof raw;
 if(d.schema!=="MAIN_R75_LAUNCH_HTN_ORIGINAL_PUBLISHER_PDF_PRINTED_DATE_CHRONOLOGY_RESEARCH_ONLY"||
    d.asOf!=="2026-11-09"||d.nct!=="NCT06153693"||d.ticker!=="MLYS"||
    d.pmid!=="40587141"||d.doi!=="10.1001/jama.2025.9413"||
    d.journalPage!=="https://jamanetwork.com/journals/jama/fullarticle/2835763"||
    d.pmcPublicIndex!=="https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/"||
    d.publisherSupplementsLinked!==7||d.originalPublicSourcePdfPagesVisuallyRead!==10||
    d.originalSourcePdfByteHashesCaptured!==0||
    d.observedLastParticipantFollowUpDate!=="2025-01-24"||
    d.originalJournalOnlinePublicationDate!=="2025-06-30"||
    d.printedOnlyEfilingSignatureDatesNotCryptographicallyVerified!==3||
    d.sameSourcePrintedYearDiscrepancies!==2||
    d.signedOriginalProspectiveStatisticalPlansIndependentlyAuthenticated!==0||
    d.databaseLockDateAuthenticated!==false||d.firstUnblindingDateAuthenticated!==false||
    d.originalPlansInEffectAtUnblindingAuthenticated!==false||
    d.originalPdfFirstPublicPublicationDatesAuthenticated!==false||
    d.originalSignedScienceReviewerAssessed!==false||d.clinicalScienceGrade!==null||
    d.validatedFutureFDAForecasts!==0||d.futureFDAOutcome!=="ABSTAIN"||
    d.reviewTimingForecast!=="UNKNOWN"||d.noHistoricalOutcomeLookups!==true||
    d.noTrainingOrProductionWrites!==true||d.docs.length!==7)return null;
 let pages=0,conflicts=0,signatures=0;
 for(let i=0;i<7;i++){
  const doc=d.docs[i],expected=OBSERVED[i],fromIndex=upstream.documents[i];
  if(doc.supplementNumber!==i+1||doc.filename!==fromIndex.filename||
     doc.role!==expected.role||doc.role!==fromIndex.role||
     doc.documentVersion!==expected.version||
     doc.printedEffectiveOrHeaderDate!==expected.date||
     doc.printedSignatureDate!==expected.sig||
     doc.printedDateConflict!==expected.conflict||
     doc.sourceRenderedPages!==expected.pages||
     JSON.stringify(doc.observedPageNumbers)!==JSON.stringify(expected.read)||
     typeof doc.notes!=="string"||doc.notes.length<60)return null;
  pages+=doc.observedPageNumbers.length;
  conflicts+=Number(doc.printedDateConflict);
  signatures+=Number(doc.printedSignatureDate!==null);
 }
 if(pages!==10||conflicts!==2||signatures!==3||
    d.disclaimer.length<130)return null;
 return {...d,recordedSourceDatePairs:7,
   clinicalReviewerSignatureAuthenticated:false as const,
   independentEvidenceGrade:null,
   FDAForecast:"ABSTAIN" as const};
}
export const FOCUS_R75_LAUNCH_HTN_CHRONOLOGY=buildR75LaunchHtnChronology();
