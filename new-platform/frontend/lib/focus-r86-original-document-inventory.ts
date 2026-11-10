/** MAIN R86 — exact-NCT source-document and posted-results inventory.
 * A current ClinicalTrials.gov largeDocs entry is a PUBLIC DOCUMENT LISTING,
 * never authenticated original bytes, a signed/SAP chronology, phase adjudication
 * or an FDA prediction. No guessed CDN document paths or reviewer writes.
 */
import {R85_PHASE_MANIFEST} from "./focus-r85-registry-phase-crosscheck";
import {FOCUS_R81_SOURCE_READINESS} from "./focus-r81-all-focus-source-readiness";
import {FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES} from "./focus-r79-launch-htn-sap-lock-evidence-gates";

type Phase=NonNullable<typeof R85_PHASE_MANIFEST>;
type Source=NonNullable<typeof FOCUS_R81_SOURCE_READINESS>;
type Launch=NonNullable<typeof FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES>;
export const R86_NOTICE=
 "Current ClinicalTrials.gov protocol/SAP document listings and posted results only. Listings do not authenticate signed prospective SAP versions, document bytes, database-lock or unblinding chronology; no independent clinical or FDA decision verification.";

export function buildR86OriginalDocumentManifest(
 phase:Phase|null=R85_PHASE_MANIFEST,
 source:Source|null=FOCUS_R81_SOURCE_READINESS,
 launch:Launch|null=FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES
){
 if(!phase||!source||!launch||phase.exactTrials!==29||
    phase.provisionalCycles!==23||source.exactTrials!==29||
    source.provisionalCycles!==23||phase.rows.length!==29||source.rows.length!==29||
    phase.independentlySignedPhaseReviews!==0||
    phase.authenticatedSignedSAPs!==0||
    phase.validatedFutureFDAPredictions!==0||
    source.independentScientificSignoffs!==0||
    source.validFutureFDAApplicationForecasts!==0||
    launch.nct!=="NCT06153693"||
    launch.cycleId!=="mlys-lorundrostat"||
    launch.requirementsIndependentlyVerified!==0||
    launch.requiredBeforeProspectiveSapChronologyCertified!==7||
    launch.sourceRequirements.length!==7||
    launch.originalSourceAttestationsVerified!==false||
    launch.qualifiedIndependentReviewersSigned!==0||
    launch.scientificGrade!==null||launch.FDAOutcome!=="ABSTAIN")return null;

 const bySource=new Map(source.rows.map(r=>[r.nct,r]));
 const originalManifestByNct=new Map(R85_PHASE_MANIFEST?.rows.map(r=>[r.nct,r]));
 const seen=new Set<string>();
 if(bySource.size!==29)return null;
 const rows=[];
 for(const r of phase.rows){
  const s=bySource.get(r.nct);
  if(!s||seen.has(r.nct)||r.ticker!==s.ticker||
      !originalManifestByNct.get(r.nct)||
      JSON.stringify(r)!==JSON.stringify(originalManifestByNct.get(r.nct))||
      JSON.stringify(r.cycleIds)!==JSON.stringify(s.cycleIds)||
      r.independentPhaseReview!=="NOT_SIGNED"||
      r.signedProspectiveSAP!=="NOT_AUTHENTICATED"||
      r.scientificGrade!==null||r.FDAForecast!=="ABSTAIN"||
      s.originalProspectiveSAPAuthenticated!==false||
      s.independentScienceReviewed!==false||
      s.scientificGrade!==null||s.officialFDAOutcome!=="ABSTAIN")return null;
  seen.add(r.nct);
  const focusCase=r.nct==="NCT06153693"?"LAUNCH_HTN":
                  r.nct==="NCT06081894"?"ACACIA_HCM":null;
  const knownBlockers=focusCase==="LAUNCH_HTN"?
   launch.sourceRequirements.map(x=>({
      id:x.id,label:x.label,status:x.status,evidence:x.evidence,
      verified:false as const
   })):
   focusCase==="ACACIA_HCM"?[
    {id:"FINAL_LOCKED_SAP",label:"Authenticate final prospectively locked SAP and control chain",
     status:"NOT_AUTHENTICATED",evidence:"Research packet retains historical registry versions 26/27/29/30, but no independently authenticated final signed SAP.",verified:false as const},
    {id:"DUAL_PRIMARY_HISTORY",label:"Reconcile pre-readout change from one to two primary endpoints",
     status:"NEEDS_ADJUDICATION",evidence:"Archived registry v26 listed one primary; v27, v29 and v30 listed two. The original dated approval hierarchy still requires verification.",verified:false as const},
    {id:"CONSORT_SETS",label:"Reconcile randomized/analysis populations and 516-versus-517 discrepancy",
     status:"UNRESOLVED",evidence:"Estimated enrollment in registry history cannot reconcile published randomized or analysis-set denominators.",verified:false as const},
    {id:"HEART_FAILURE_WINDOWS",label:"Reconcile heart-failure and LVEF event definitions, windows and exposure",
     status:"UNRESOLVED",evidence:"HF event counts and reporting windows are contradictory across source leads; an independent safety analysis is outstanding.",verified:false as const}
   ]:[];
  rows.push({
   nct:r.nct,ticker:r.ticker,cycleIds:[...r.cycleIds],
   registryUrl:r.sourceUrl,archivedOriginalRegistrySha256:r.archivedRegistrySha256,
   sourceUpdatedDate:r.archivedSourceUpdatedDate,
   registryReportedPhase:r.registryReportedPhase,
   currentPrimaryTableRetained:s.currentRegistryPrimaryTable,
   currentSafetyArmsRetained:s.currentRegistrySafetyArms,
   publishedMainReportLead:s.publisherOrPubmedUrl,
   publishedMainReportIndexedInFiveCaseSubset:s.indexedOriginalPivotalPublication,
   focusCase,
   sourceFirstPriority:focusCase!==null?0:
     (!s.currentRegistryPrimaryTable||!s.currentRegistrySafetyArms?1:2),
   knownBlockers,
   authenticatedSignedProspectiveSAP:false as const,
   signedIndependentScientificReview:false as const,
   scientificGrade:null,FDAOutcome:"ABSTAIN" as const
  });
 }
 if(seen.size!==29||source.rows.some(r=>!seen.has(r.nct))||
    rows.filter(r=>r.focusCase!==null).length!==2||
    rows.filter(r=>r.publishedMainReportIndexedInFiveCaseSubset).length!==5||
    rows.filter(r=>r.currentPrimaryTableRetained).length!==12||
    rows.filter(r=>r.currentSafetyArmsRetained).length!==12)return null;
 rows.sort((a,b)=>a.sourceFirstPriority-b.sourceFirstPriority||
   a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R86_CURRENT_DOCUMENT_REGISTRY_INVENTORY_SOURCE_ONLY" as const,
  datedSnapshot:"2026-11-09",
  notice:R86_NOTICE,
  exactTrials:29 as const,provisionalApplications:23 as const,
  knownPivotalReportSourceLeads:5 as const,
  knownLaunchDocumentaryBlockers:7 as const,
  knownAcaciaDocumentaryBlockers:4 as const,
  independentSignedSAPsAuthenticated:0 as const,
  qualifiedIndependentScientificReviews:0 as const,
  validatedFutureFDAPredictions:0 as const,
  readOnly:true as const,
  rows
 };
}
export const R86_ORIGINAL_DOCUMENT_MANIFEST=buildR86OriginalDocumentManifest();

type Row=NonNullable<typeof R86_ORIGINAL_DOCUMENT_MANIFEST>["rows"][number];
type RecordObject=Record<string,unknown>;
function obj(v:unknown):RecordObject|null{
 return v!==null&&typeof v==="object"&&!Array.isArray(v)?v as RecordObject:null;
}
function cleanStr(v:unknown,max=180):string|null{
 return typeof v==="string"&&v.length>0&&v.length<=max&&
 !/[\u0000-\u001f\u007f]/u.test(v)?v:null;
}
function pickCount(v:unknown):number|null{
 return Array.isArray(v)&&v.length<=10000?v.length:null;
}
type DocumentItem={
 type:string;label:string|null;documentDate:string|null;uploadDate:string|null;
 filename:string;sizeBytes:number;listsProtocol:boolean;listsSap:boolean;listsIcf:boolean;
};
function parseDocument(v:unknown):DocumentItem|null{
 const d=obj(v);
 if(!d)return null;
 const filename=cleanStr(d.filename,160);
 if(!filename||filename.includes("/")||filename.includes("\\")||
    filename==="."||filename===".."||filename.includes(".."))return null;
 const type=cleanStr(d.typeAbbrev,30);
 if(!type)return null;
 const label=d.label===undefined?null:cleanStr(d.label,300);
 const documentDate=d.date===undefined?null:cleanStr(d.date,20);
 const uploadDate=d.uploadDate===undefined?null:cleanStr(d.uploadDate,20);
 if(d.label!==undefined&&label===null||
    d.date!==undefined&&(documentDate===null||!/^\d{4}-\d{2}(?:-\d{2})?$/u.test(documentDate))||
    d.uploadDate!==undefined&&(uploadDate===null||!/^\d{4}-\d{2}-\d{2}(?:T(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?)?$/u.test(uploadDate))||
    typeof d.size!=="number"||!Number.isSafeInteger(d.size)||d.size<1||d.size>500_000_000||
    [d.hasProtocol,d.hasSap,d.hasIcf].some(x=>x!==undefined&&typeof x!=="boolean"))
    return null;
 return {
  type,label,documentDate,uploadDate,filename,sizeBytes:d.size,
  listsProtocol:d.hasProtocol===true,
  listsSap:d.hasSap===true,
  listsIcf:d.hasIcf===true
 };
}
export function inspectR86CurrentStudy(row:Row,body:unknown){
 const root=obj(body),p=obj(root?.protocolSection);
 const identity=obj(p?.identificationModule);
 if(cleanStr(identity?.nctId)!==row.nct)return null;
 if(typeof root?.hasResults!=="boolean")return null;
 const documents=obj(root?.documentSection);
 const docModule=documents?obj(documents.largeDocumentModule):null;
 const rawDocs=docModule?.largeDocs??[];
 if(!Array.isArray(rawDocs)||rawDocs.length>50)return null;
 const docs=rawDocs.map(parseDocument);
 if(docs.some(d=>d===null))return null;
 const knownDocs=docs as DocumentItem[];
 const results=obj(root?.resultsSection);
 if(root?.hasResults===true&&!results)return null;
 const flow=obj(results?.participantFlowModule);
 const outcomes=obj(results?.outcomeMeasuresModule);
 const adverse=obj(results?.adverseEventsModule);
 // Counts only; cannot establish original analysis populations or tolerability.
 const postedResultModules=root.hasResults===true?{
  participantFlowGroups:pickCount(flow?.groups),
  endpointMeasures:pickCount(outcomes?.outcomeMeasures),
  seriousAdverseEventTerms:pickCount(adverse?.seriousEvents),
  otherAdverseEventTerms:pickCount(adverse?.otherEvents)
 }:null;
 const documentsWithProtocol=knownDocs.filter(d=>d.listsProtocol).length;
 const documentsWithSAP=knownDocs.filter(d=>d.listsSap).length;
 return {
  nct:row.nct,sourceUrl:"https://clinicaltrials.gov/study/"+row.nct,
  checkedAgainst:"OFFICIAL_PUBLIC_CLINICALTRIALS_GOV_V2_CURRENT_RECORD" as const,
  docsInCurrentRegistry:knownDocs.length,
  listedProtocolDocuments:documentsWithProtocol,
  listedSapDocuments:documentsWithSAP,
  listedConsentDocuments:knownDocs.filter(d=>d.listsIcf).length,
  currentRegistryResultsPosted:root.hasResults,
  postedResultModules,
  documents:knownDocs,
  originalRegulatedSignedSourceAuthenticated:false as const,
  prospectivelyLockedSapAuthenticated:false as const,
  sourceChronologyAndUnblindingIndependentlyReconciled:false as const,
  analysisPopulationAndResultsIndependentlyReconciled:false as const,
  qualifiedIndependentScientificReview:false as const,
  independentFDAForecast:"ABSTAIN" as const,
  nextEvidenceAction:documentsWithProtocol+documentsWithSAP>0?
    "Retrieve actual original document bytes, verify digest, signed effective versions and prospective pre-unblinding SAP chain with authorized reviewers":
    "Search historical registry versions, publisher supplements, sponsor/CSR and regulator records for signed protocol/SAP; absence here does not imply documents do not exist",
  notice:R86_NOTICE
 };
}
