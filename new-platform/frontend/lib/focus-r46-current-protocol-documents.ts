/** MAIN R46: pinned public protocol/SAP metadata only; no clinical grade/prediction. */
import pinned from "../data/focus-r46-current-protocol-document-index.json";
import {FOCUS_PRELIMINARY_R39} from "./focus-preliminary-application-research";

const SHA="05e7dbe734795018503e7b3751ff1b0b93fa34311ba5183d6c96ab9f0cac0614";
const NCT=/^NCT\d{8}$/;
const DOC=/^[A-Za-z0-9][A-Za-z0-9_.-]{0,190}\.pdf$/;
export function validateR46CurrentDocuments(raw:unknown=pinned){
 if(!raw||typeof raw!=="object"||Array.isArray(raw))return null;
 const d=raw as typeof pinned,c=d.counts;
 if(d.schema!=="MAIN_R46_PUBLIC_CURRENT_PROTOCOL_SAP_DOCUMENT_INDEX_PIN"||
   d.asOf!=="2026-11-09"||d.capturedAtUtc!=="2026-11-09T17:50:01+00:00"||
   d.sourceRunId!==42668393809||d.sourceArtifactId!==13697642476||
   d.sourceArtifactExpiresAt!=="2027-02-07T17:49:44Z"||
   d.originalResearchReceiptSha256!==SHA||
   c.sourceNcts!==29||c.provisionalApplications!==23||c.registryNctsRetrieved!==29||
   c.withCurrentProtocolAndSapAttachments!==12||c.withoutCurrentRegistryAttachments!==17||
   c.protocolDocumentsPresentForNcts!==12||c.sapDocumentsPresentForNcts!==12||
   c.documentEntries!==23||c.independentlyVerifiedLockedSap!==0||
   c.qualifiedIndependentScientificGrades!==0||c.independentlyValidatedFdaForecasts!==0||
   c.historicalIndependentBacktests!==0||
   d.originalFirstPublicDocumentDateVerified!==false||
   d.originalLockedSapAndMultiplicityVerified!==false||
   d.documentBodiesReviewed!==false||
   d.currentlyRegisteredDocumentMetadataOnly!==true||
   d.clinicalReviewerSigned!==false||
   d.officialFutureFdaPrediction!=="ABSTAIN"||
   d.officialFutureDelayPrediction!=="ABSTAIN"||
   d.numericalFdaProbability!==null||d.calibratedAccuracy!==null||
   !Array.isArray(d.attached)||d.attached.length!==12||
   FOCUS_PRELIMINARY_R39.trials.length!==29||
   FOCUS_PRELIMINARY_R39.applications.length!==23)return null;
 const byNct=new Map(FOCUS_PRELIMINARY_R39.trials.map(t=>[t.nct,t]));
 const seen=new Set<string>();let files=0;
 for(const item of d.attached){
   const trial=byNct.get(item.nct);
   if(!trial||seen.has(item.nct)||!NCT.test(item.nct)||
     trial.applicationCycleIds.length!==1||
     trial.applicationCycleIds[0]!==item.applicationCycleId||
     !Array.isArray(item.documents)||item.documents.length<1||item.documents.length>20)return null;
   let protocol=false,sap=false;
   const unique=new Set<string>();
   for(const doc of item.documents){
      if(!["Prot","SAP","Prot_SAP"].includes(doc.kind)||!DOC.test(doc.filename)||
        !/^20\d{2}-\d{2}-\d{2}$/.test(doc.registryDocumentDate)||
        unique.has(doc.filename))return null;
      unique.add(doc.filename);
      if(doc.kind==="Prot"||doc.kind==="Prot_SAP")protocol=true;
      if(doc.kind==="SAP"||doc.kind==="Prot_SAP")sap=true;
      files++;
   }
   if(!protocol||!sap)return null;
   seen.add(item.nct);
 }
 if(files!==23||seen.size!==12)return null;
 const lookup=new Map(d.attached.map(a=>[a.nct,a] as const));
 const rows=FOCUS_PRELIMINARY_R39.trials.map(t=>({
   ticker:t.ticker,nct:t.nct,
   applicationCycleIds:[...t.applicationCycleIds],
   attachments:lookup.get(t.nct)?.documents??null,
   registrySource:"https://clinicaltrials.gov/study/"+t.nct,
   firstPublicationVerified:false,lockedSapVerified:false,
   scientificGrade:null,FDAForecast:"ABSTAIN" as const
 }));
 return {...d,rows};
}
export const FOCUS_R46_DOCUMENTS=validateR46CurrentDocuments();
