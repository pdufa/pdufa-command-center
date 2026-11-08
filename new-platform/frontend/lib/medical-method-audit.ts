/** Strict fail-closed decoder: 800 genuine SOURCE triage receipts, never clinical grades. */
export type PilotMethodAuditEvent = {
  position_index:number;assessment_index:number;method_index:number;
  source_class:string;source_count:number;observed_at:string;
};
export type PilotMethodAudit = {
  kind:"RUN";nct:"NCT06081894";runId:string;sourceSnapshotId:string;
  status:"PENDING"|"RUNNING"|"COMPLETE"|"FAILED";
  completedPositions:number;totalPositions:800;completedAssessmentGroups:number;
  currentAssessmentIndex:number|null;currentMethodIndex:number|null;
  createdAt:string;updatedAt:string;finishedAt:string|null;failureKind:string|null;
  recentEvents:PilotMethodAuditEvent[];
  auditKind:"SAVED_TRIAGE_SOURCE_CLASSIFICATION_VERIFICATION";
  scientificReviewEventsWritten:0;gradeEventsWritten:0;
  prediction:{APPROVAL:"ABSTAIN";CRL:"ABSTAIN";REVIEW_DELAY:"ABSTAIN"};
  accuracy:"NOT_CALIBRATED";
};
export type PilotMethodAuditObservation=PilotMethodAudit|
  {kind:"NO_RUN";nct:"NCT06081894";auditKind:"SAVED_TRIAGE_SOURCE_CLASSIFICATION_VERIFICATION"};

const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const states=new Set(["PENDING","RUNNING","COMPLETE","FAILED"]);
const classes=new Set(["SOURCE_RECORD_UNADJUDICATED","RESEARCH_LEADS_ONLY",
  "IDENTITY_ONLY_NO_CLINICAL_DATA","SOURCE_GAP","NO_MATCHING_SAVED_SOURCE"]);
function obj(value:unknown):Record<string,unknown>{
  if(!value||typeof value!=="object"||Array.isArray(value))throw Error("INVALID_SOURCE_AUDIT");
  return value as Record<string,unknown>;
}
function count(v:unknown):v is number{return typeof v==="number"&&Number.isSafeInteger(v)&&v>=0;}
function dated(v:unknown){return typeof v==="string"&&Number.isFinite(Date.parse(v));}
export function validatePilotMethodAudit(value:unknown):PilotMethodAudit{
  const x=obj(value),pred=obj(x.prediction);
  if(x.schema!=="MAIN_PILOT_800_SOURCE_AUDIT_V1"||x.nct!=="NCT06081894"||
    typeof x.runId!=="string"||!uuid.test(x.runId)||
    typeof x.sourceSnapshotId!=="string"||!uuid.test(x.sourceSnapshotId)||
    !states.has(String(x.status))||x.totalPositions!==800||
    !count(x.completedPositions)||x.completedPositions>800||
    x.completedAssessmentGroups!==Math.floor(x.completedPositions/20)||
    x.auditKind!=="SAVED_TRIAGE_SOURCE_CLASSIFICATION_VERIFICATION"||
    x.scientificReviewEventsWritten!==0||x.gradeEventsWritten!==0||
    x.accuracy!=="NOT_CALIBRATED"||
    Object.keys(pred).length!==3||pred.APPROVAL!=="ABSTAIN"||
    pred.CRL!=="ABSTAIN"||pred.REVIEW_DELAY!=="ABSTAIN"||
    !dated(x.createdAt)||!dated(x.updatedAt)||
    (x.finishedAt!==null&&!dated(x.finishedAt))||
    (x.failureKind!==null&&typeof x.failureKind!=="string")||
    !Array.isArray(x.recentEvents)||x.recentEvents.length>6)
    throw Error("INVALID_SOURCE_AUDIT");
  const next=x.completedPositions<800?x.completedPositions+1:null;
  const nextAssessment=next===null?null:Math.floor((next-1)/20)+1;
  const nextMethod=next===null?null:(next-1)%20+1;
  if(x.currentAssessmentIndex!==nextAssessment||x.currentMethodIndex!==nextMethod||
    (x.status==="COMPLETE"&&(x.completedPositions!==800||!dated(x.finishedAt)))||
    (x.status==="PENDING"&&x.completedPositions!==0))
    throw Error("INVALID_SOURCE_AUDIT_PROGRESS");
  let last=Number.POSITIVE_INFINITY;
  for(const raw of x.recentEvents){
    const e=obj(raw);
    if(!count(e.position_index)||e.position_index<1||
       e.position_index>x.completedPositions||e.position_index>=last||
       e.assessment_index!==Math.floor((e.position_index-1)/20)+1||
       e.method_index!==(e.position_index-1)%20+1||
       !classes.has(String(e.source_class))||
       !count(e.source_count)||!dated(e.observed_at))
      throw Error("INVALID_SOURCE_AUDIT_EVENT");
    last=e.position_index;
  }
  if(x.recentEvents.length!==Math.min(6,x.completedPositions))
    throw Error("MISSING_SOURCE_AUDIT_EVENTS");
  return {kind:"RUN",nct:"NCT06081894",runId:x.runId as string,
    sourceSnapshotId:x.sourceSnapshotId as string,
    status:x.status as PilotMethodAudit["status"],completedPositions:x.completedPositions,
    totalPositions:800,completedAssessmentGroups:x.completedAssessmentGroups,
    currentAssessmentIndex:nextAssessment,currentMethodIndex:nextMethod,
    createdAt:x.createdAt as string,updatedAt:x.updatedAt as string,
    finishedAt:x.finishedAt as string|null,failureKind:x.failureKind as string|null,
    recentEvents:x.recentEvents as PilotMethodAuditEvent[],
    auditKind:"SAVED_TRIAGE_SOURCE_CLASSIFICATION_VERIFICATION",
    scientificReviewEventsWritten:0,gradeEventsWritten:0,
    prediction:{APPROVAL:"ABSTAIN",CRL:"ABSTAIN",REVIEW_DELAY:"ABSTAIN"},
    accuracy:"NOT_CALIBRATED"};
}
