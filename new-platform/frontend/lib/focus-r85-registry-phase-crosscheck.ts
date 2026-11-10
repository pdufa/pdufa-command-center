/** MAIN R85: strict, read-only ClinicalTrials.gov CURRENT versus dated R67 registry
 * fields. Registry-to-registry comparison is NOT independent clinical phase
 * adjudication, FDA review validation, statistical analysis, or prediction.
 */
import {FOCUS_R67_PHASE_SOURCE} from "./focus-r67-phase-source";
import {FOCUS_R81_SOURCE_READINESS} from "./focus-r81-all-focus-source-readiness";

type Phase=NonNullable<typeof FOCUS_R67_PHASE_SOURCE>;
type Readiness=NonNullable<typeof FOCUS_R81_SOURCE_READINESS>;
const NCT=/^NCT\d{8}$/u;
const SHA=/^[0-9a-f]{64}$/u;
export const R85_SOURCE_OBSERVED_ON="2026-11-09";
export const R85_VALIDATION_NOTICE=
 "Live ClinicalTrials.gov API fields are compared with the dated R67 original-source record; a match does not independently verify phase or authenticate a signed protocol/SAP.";

export function buildR85PhaseCrosscheckManifest(
 phase:Phase|null=FOCUS_R67_PHASE_SOURCE,
 source:Readiness|null=FOCUS_R81_SOURCE_READINESS
) {
 if(!phase || !source || phase.ncts!==29 || phase.applications!==23 ||
    phase.records.length!==29 || source.rows.length!==29 ||
    source.exactTrials!==29 || source.provisionalCycles!==23 ||
    phase.verifiedPhaseReviews!==0 ||phase.signedScienceReviews!==0 ||
    phase.independentlyValidatedFDAForecasts!==0 ||phase.futureFDAOutcome!=="ABSTAIN"||
    phase.productionOrClinicalWrites!==false||
    source.independentScientificSignoffs!==0||
    source.originalSignedProspectiveSAPsVerified!==0||
    source.validFutureFDAApplicationForecasts!==0||source.FDAOutcome!=="ABSTAIN")
  return null;
 const canonical=new Map(source.rows.map(x=>[x.nct,x]));
 if(canonical.size!==29)return null;
 const seen=new Set<string>();
 const rows=[];
 for(const r of phase.records) {
  const x=canonical.get(r.nct);
  if(!NCT.test(r.nct)||seen.has(r.nct)||!x||x.ticker!==r.ticker||
     !SHA.test(r.currentOriginalSourceSha256)||
     r.originalRegistryUrl!=="https://clinicaltrials.gov/study/"+r.nct||
     JSON.stringify(x.cycleIds)!==JSON.stringify(r.applicationCycles)||
     r.independentlyVerifiedTrialPhase!==false||r.independentPhaseReviewEventId!==null||
     r.independentlyCompletedScientificLevel!==null||
     r.scientificMethodScores!==0||r.verifiedFdaApplicationStatus!==null||
     r.predictedFDAOutcome!=="ABSTAIN"||r.predictionConfidence!==null||
     !["Phase 3","Combined Phase 2/3"].includes(r.sourcePhase)||
     !["COMPLETED","ACTIVE NOT RECRUITING","RECRUITING"].includes(r.sourceStatus)||
     !/^\d{4}-\d{2}-\d{2}$/u.test(r.sourceUpdatedDate)||
     !/^\d{4}-\d{2}$/u.test(r.registryVerifiedMonth)||
     !["RANDOMIZED","NA"].includes(r.allocation)||
     !["NONE","DOUBLE","TRIPLE","QUADRUPLE"].includes(r.masking)||
     !Number.isSafeInteger(r.enrollment)||r.enrollment<=0||
     !["ACTUAL","ESTIMATED"].includes(r.enrollmentType)||
     !/^\d{4}-\d{2}(?:-\d{2})?$/u.test(r.primaryCompletionDate)||
     !["ACTUAL","ESTIMATED"].includes(r.primaryCompletionType))return null;
  seen.add(r.nct);
  const exceptionalPhase=r.sourcePhase==="Combined Phase 2/3";
  const nonRandomized=r.allocation==="NA";
  const needsSourceResults=!x.currentRegistryPrimaryTable||!x.currentRegistrySafetyArms;
  rows.push({
   nct:r.nct,ticker:r.ticker,cycleIds:[...r.applicationCycles],
   sourceUrl:r.originalRegistryUrl,archivedRegistrySha256:r.currentOriginalSourceSha256,
   archivedSourceUpdatedDate:r.sourceUpdatedDate,
   archivedRegistryVerifiedMonth:r.registryVerifiedMonth,
   registryReportedPhase:r.sourcePhase,registryReportedStatus:r.sourceStatus,
   allocation:r.allocation,masking:r.masking,
   enrollment:r.enrollment,enrollmentType:r.enrollmentType,
   primaryCompletionDate:r.primaryCompletionDate,
   primaryCompletionType:r.primaryCompletionType,
   primaryTablePresentInRetainedSource:x.currentRegistryPrimaryTable,
   safetyArmsPresentInRetainedSource:x.currentRegistrySafetyArms,
   phaseFirstReviewPriority:exceptionalPhase||nonRandomized?"DESIGN_REQUIRES_SPECIAL_ADJUDICATION":
     r.sourceStatus!=="COMPLETED"?"STUDY_STATUS_RECONCILIATION":
     needsSourceResults?"RETRIEVE_ORIGINAL_RESULTS_AND_SAFETY":"VERIFY_ORIGINAL_DOCUMENT_TIMELINE",
   independentPhaseReview:"NOT_SIGNED" as const,
   signedProspectiveSAP:"NOT_AUTHENTICATED" as const,
   scientificGrade:null,FDAForecast:"ABSTAIN" as const,
  });
 }
 if(seen.size!==29||canonical.size!==29||
    source.rows.some(r=>!seen.has(r.nct))||
    rows.filter(r=>r.registryReportedPhase==="Combined Phase 2/3").length!==1||
    rows.filter(r=>r.registryReportedPhase==="Phase 3").length!==28||
    rows.filter(r=>r.allocation==="NA").length!==1||
    rows.filter(r=>r.registryReportedStatus==="COMPLETED").length!==19||
    rows.filter(r=>r.registryReportedStatus==="ACTIVE NOT RECRUITING").length!==8||
    rows.filter(r=>r.registryReportedStatus==="RECRUITING").length!==2)return null;
 const priorities={
   "DESIGN_REQUIRES_SPECIAL_ADJUDICATION":0,
   "STUDY_STATUS_RECONCILIATION":1,
   "RETRIEVE_ORIGINAL_RESULTS_AND_SAFETY":2,
   "VERIFY_ORIGINAL_DOCUMENT_TIMELINE":3
 };
 rows.sort((a,b)=>priorities[a.phaseFirstReviewPriority]-priorities[b.phaseFirstReviewPriority]||
   a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R85_PHASE_REGISTRY_CROSSCHECK_NOT_ADJUDICATED" as const,
  sourceObservedOn:R85_SOURCE_OBSERVED_ON,
  banner:R85_VALIDATION_NOTICE,
  exactTrials:29 as const,provisionalCycles:23 as const,
  sourceReportedPhase3:28 as const,sourceReportedCombinedPhase23:1 as const,
  sourceReportedCompleted:19 as const,sourceReportedActive:8 as const,
  sourceReportedRecruiting:2 as const,
  sourceReportedNonRandomized:1 as const,
  independentlySignedPhaseReviews:0 as const,authenticatedSignedSAPs:0 as const,
  validatedFutureFDAPredictions:0 as const,readOnly:true as const,
  rows
 };
}
export const R85_PHASE_MANIFEST=buildR85PhaseCrosscheckManifest();

type ManifestRow=NonNullable<typeof R85_PHASE_MANIFEST>["rows"][number];
type DiffItem={field:string;archived:string|number;current:string|number};
type JsonRecord=Record<string,unknown>;
function obj(value:unknown):JsonRecord|null{
 return value!==null&&typeof value==="object"&&!Array.isArray(value)?
   value as JsonRecord:null;
}
function str(value:unknown):string|null{
 return typeof value==="string"&&value.length<150?value:null;
}
function integer(value:unknown):number|null{
 return typeof value==="number"&&Number.isSafeInteger(value)&&value>0?
  value:null;
}
export function compareR85CurrentRegistry(
 row:ManifestRow, response:unknown
) {
 const root=obj(response),p=obj(root?.protocolSection),
  identity=obj(p?.identificationModule),s=obj(p?.statusModule),
  d=obj(p?.designModule),di=obj(d?.designInfo),mask=obj(di?.maskingInfo),
  enroll=obj(d?.enrollmentInfo),finish=obj(s?.primaryCompletionDateStruct),
  updated=obj(s?.lastUpdatePostDateStruct);
 const actualNct=str(identity?.nctId);
 if(!actualNct || actualNct!==row.nct)return null;
 const phases=d?.phases;
 const phase=Array.isArray(phases)&&phases.length>0&&
   phases.every(t=>t==="PHASE2"||t==="PHASE3")?
   [...phases].sort().join(","):null;
 const current={
  sourcePhase:phase==="PHASE3"?"Phase 3":
    phase==="PHASE2,PHASE3"?"Combined Phase 2/3":null,
  sourceStatus:str(s?.overallStatus)?.replaceAll("_"," ")??null,
  sourceUpdatedDate:str(updated?.date),
  registryVerifiedMonth:str(s?.statusVerifiedDate),
  allocation:str(di?.allocation),
  masking:str(mask?.masking),
  enrollment:integer(enroll?.count),
  enrollmentType:str(enroll?.type),
  primaryCompletionDate:str(finish?.date),
  primaryCompletionType:str(finish?.type)
 };
 const archived={
  sourcePhase:row.registryReportedPhase,
  sourceStatus:row.registryReportedStatus,
  sourceUpdatedDate:row.archivedSourceUpdatedDate,
  registryVerifiedMonth:row.archivedRegistryVerifiedMonth,
  allocation:row.allocation,masking:row.masking,enrollment:row.enrollment,
  enrollmentType:row.enrollmentType,
  primaryCompletionDate:row.primaryCompletionDate,
  primaryCompletionType:row.primaryCompletionType
 };
 const unavailable:string[]=[];
 const differences:DiffItem[]=[];
 for(const name of Object.keys(archived) as Array<keyof typeof archived>) {
  const oldValue=archived[name],newValue=current[name];
  if(newValue===null){unavailable.push(name);continue;}
  if(oldValue!==newValue)differences.push({field:name,archived:oldValue,current:newValue});
 }
 const status=unavailable.length?"INCOMPLETE_CURRENT_REGISTRY_FIELDS_REQUIRES_REVIEW":
   differences.length?"REGISTRY_CHANGED_REQUIRES_INDEPENDENT_REVIEW":
   "REGISTRY_FIELDS_MATCH_NOT_INDEPENDENTLY_VERIFIED";
 return {
  nct:row.nct,
  sourceUrl:"https://clinicaltrials.gov/api/v2/studies/"+row.nct,
  archiveSourceSha256:row.archivedRegistrySha256,
  archivedSourceUpdatedDate:row.archivedSourceUpdatedDate,
  currentSourceUpdatedDate:current.sourceUpdatedDate,
  checkedAgainst:"CLINICALTRIALS_GOV_PUBLIC_API_V2" as const,
  status,unavailableFields:unavailable,differences,
  currentRegistryFields:current,
  independentPhaseReview:"NOT_SIGNED" as const,
  prospectiveSAPAuthenticated:false as const,
  scientificGrade:null,FDAForecast:"ABSTAIN" as const,
  independentFDAApprovalForecastValidated:false as const,
  notice:R85_VALIDATION_NOTICE
 };
}
