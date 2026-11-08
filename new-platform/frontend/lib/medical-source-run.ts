/** Strict, source-only status decoder. A 12-stage research run is never an FDA prediction. */
export type SourceRunStage={
  number:number; title:string; state:string; finishedAt:string|null;
};
export type MedicalSourceRun={
  kind:"RUN"; nct:string; runId:string;
  status:"PENDING"|"RUNNING"|"COMPLETE"|"FAILED"|"STOPPED";
  completedStages:number; totalStages:12; stageNumber:number;
  updatedAt:string; startedAt:string;
  stages:SourceRunStage[];
  researchOnly:true; prediction:"ABSTAIN"; calibratedAccuracy:null;
};
export type MedicalSourceRunObservation=MedicalSourceRun|{kind:"NO_RUN";nct:string;researchOnly:true;prediction:"ABSTAIN"};

function record(value:unknown):Record<string,unknown>{
  if(value===null||typeof value!=="object"||Array.isArray(value))throw Error("INVALID_SOURCE_RUN");
  return value as Record<string,unknown>;
}
function integer(v:unknown):v is number{return typeof v==="number"&&Number.isSafeInteger(v);}
const statuses=new Set(["PENDING","RUNNING","COMPLETE","FAILED","STOPPED"]);
const stageStatuses=new Set(["QUEUED","RUNNING","SOURCE_RECORDED","LEADS_ONLY","EVIDENCE_GAP","SOURCE_UNAVAILABLE"]);
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export function validateSourceRun(value:unknown,nct:string):MedicalSourceRun {
  const v=record(value);
  if(v.nct!==nct||typeof v.runId!=="string"||!uuid.test(v.runId)||
     !statuses.has(String(v.status))||v.totalStages!==12||
     !integer(v.completedStages)||v.completedStages<0||v.completedStages>12||
     !integer(v.stageNumber)||v.stageNumber<1||v.stageNumber>12||
     v.decision!=="ABSTAIN"||v.approvalProbability!==null||
     typeof v.updatedAt!=="string"||!Number.isFinite(Date.parse(v.updatedAt))||
     typeof v.startedAt!=="string"||!Number.isFinite(Date.parse(v.startedAt))||
     !Array.isArray(v.stages)||v.stages.length!==12)
    throw Error("INVALID_SOURCE_RUN");
  const stages=v.stages.map((raw,index)=>{
    const s=record(raw);
    if(s.number!==index+1||typeof s.title!=="string"||!s.title||s.title.length>160||
       !stageStatuses.has(String(s.state))||
       (s.finishedAt!==null&&(typeof s.finishedAt!=="string"||!Number.isFinite(Date.parse(s.finishedAt)))))
      throw Error("INVALID_SOURCE_STAGE");
    return {number:s.number as number,title:s.title as string,state:s.state as string,
      finishedAt:s.finishedAt as string|null};
  });
  const completed=stages.filter(x=>x.state!=="RUNNING"&&x.state!=="QUEUED").length;
  if(completed!==v.completedStages)throw Error("INVALID_SOURCE_STAGE_COUNTS");
  return {kind:"RUN",nct,runId:v.runId,status:v.status as MedicalSourceRun["status"],
    completedStages:v.completedStages,totalStages:12,stageNumber:v.stageNumber,
    updatedAt:v.updatedAt,startedAt:v.startedAt,
    stages,researchOnly:true,prediction:"ABSTAIN",calibratedAccuracy:null};
}
